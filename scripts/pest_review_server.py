#!/usr/bin/env python3
"""Local backend service for pest manual review tooling.

This service exposes a lightweight HTTP API consumed by
``docs/pest_manual_review.html`` to provide the following capabilities:

* On-demand LLM analysis for a given image (delegating to
  ``llm_tools.verify_and_describe.XmdbdVLMClient`` when API credentials
  are configured, or returning mock responses otherwise).
* Secure file operations (move/rename) bounded to configured roots so
  that reviewers can immediately act on the LLM suggestions.

The design intentionally avoids third-party web frameworks so it can run
anywhere Python is available. See ``--help`` for CLI options.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import threading
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
import sys

# Add project root to Python path to allow sibling imports
_project_root = Path(__file__).resolve().parents[1]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from llm_tools.verify_and_describe import XmdbdVLMClient, VLMAPIError
except ImportError:  # pragma: no cover - defensive guard when module missing
    XmdbdVLMClient = None  # type: ignore
    VLMAPIError = RuntimeError  # type: ignore

LOGGER = logging.getLogger("pest_review_server")

DEFAULT_ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass
class ServerConfig:
    repo_root: Path
    review_root: Path
    manifest_path: Path
    default_tag: str
    allow_roots: tuple[Path, ...]
    vlm_client: Optional[XmdbdVLMClient]
    mock_mode: bool


class PestReviewService:
    """Core operations shared by HTTP handlers."""

    def __init__(self, config: ServerConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._manifest_path = config.manifest_path
        self._manifest_entries = self._load_manifest()
        self._manifest_index = {
            entry.get("id"): entry
            for entry in self._manifest_entries
            if isinstance(entry, dict) and entry.get("id")
        }

    # ------------------------------------------------------------------
    # LLM analysis
    # ------------------------------------------------------------------
    def _load_manifest(self) -> list[dict[str, Any]]:
        if not self._manifest_path.exists():
            LOGGER.warning("Manifest file not found at %s; starting with empty list", self._manifest_path)
            return []
        try:
            raw = self._manifest_path.read_text(encoding="utf-8")
        except OSError as exc:
            LOGGER.error("Failed to read manifest: %s", exc)
            return []

        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end < start:
            LOGGER.error("Manifest file has unexpected format (missing JSON array)")
            return []
        try:
            data = json.loads(raw[start:end + 1])
        except json.JSONDecodeError as exc:
            LOGGER.error("Manifest JSON decode error: %s", exc)
            return []

        if not isinstance(data, list):
            LOGGER.error("Manifest root is not a list; ignoring contents")
            return []
        return data

    def _write_manifest_locked(self) -> None:
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self._manifest_entries, indent=2, ensure_ascii=False)
        payload = f"const pestReviewManifest = {content};\n"
        try:
            self._manifest_path.write_text(payload, encoding="utf-8")
        except OSError as exc:
            LOGGER.error("Failed to write manifest: %s", exc)

    def _update_manifest_locked(self, item_id: Optional[str], target_class: str, dest_path: Path) -> None:
        if not item_id:
            LOGGER.debug("Skip manifest update for unnamed item")
            return
        entry = self._manifest_index.get(item_id)
        if not entry:
            LOGGER.warning("Manifest entry not found for id=%s; skipping update", item_id)
            return
        rel_dest = dest_path.relative_to(self._config.repo_root)
        entry["keyword"] = target_class
        entry["path"] = str(rel_dest).replace(os.sep, "/")
        self._write_manifest_locked()

    def analyze(self, rel_path: str, keyword: Optional[str] = None) -> Dict[str, Any]:
        path = self._resolve(rel_path)
        expected = keyword or path.parent.name
        LOGGER.info("Analyze request for %s (expected=%s)", path, expected)

        if not self._config.vlm_client:
            LOGGER.warning("VLM client unavailable; returning mock payload")
            # Provide a deterministic mock to ease front-end development
            return {
                "mock": True,
                "is_match": True,
                "actual_class": expected,
                "quality_score": 0.75,
                "rejection_reason": None,
                "description_en": f"Placeholder analysis for {expected}.",
                "description_zh": f"关于 {expected} 的占位分析。",
            }

        try:
            result = self._config.vlm_client.analyze_image(path, expected)
        except (FileNotFoundError, VLMAPIError) as exc:
            LOGGER.error("Analysis failed: %s", exc)
            raise

        result.setdefault("mock", False)
        return result

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------
    def reclassify(
        self,
        item_id: Optional[str],
        rel_path: str,
        target_class: str,
        rename_mode: str = "keep",
        custom_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        src = self._resolve(rel_path)
        base_root = self._match_allowed_root(src)
        if not base_root:
            raise PermissionError(f"Path {src} is outside allowed roots")

        safe_class = self._sanitize_target(target_class)
        dest_dir = base_root / safe_class
        dest_dir.mkdir(parents=True, exist_ok=True)

        new_name = self._build_new_name(src, safe_class, rename_mode, custom_name)
        dest_path = dest_dir / new_name

        LOGGER.info("Moving %s -> %s", src, dest_path)
        with self._lock:
            if dest_path.exists():
                LOGGER.warning("Destination already exists, generating fallback name")
                dest_path = dest_dir / self._build_new_name(src, safe_class, "uuid", None)
            src.rename(dest_path)
            self._update_manifest_locked(item_id, safe_class, dest_path)

        rel_dest = dest_path.relative_to(self._config.repo_root)
        return {
            "new_path": str(rel_dest).replace(os.sep, "/"),
            "target_class": safe_class,
            "filename": dest_path.name,
            "id": item_id,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve(self, rel_path: str) -> Path:
        candidate = (self._config.repo_root / rel_path).resolve()
        if not candidate.exists():
            raise FileNotFoundError(f"File not found: {candidate}")
        if not self._is_within_allowed(candidate):
            raise PermissionError(f"Access to {candidate} is forbidden")
        if candidate.suffix.lower() not in DEFAULT_ALLOWED_EXTS:
            raise ValueError(f"Unsupported file type: {candidate.suffix}")
        return candidate

    def _is_within_allowed(self, path: Path) -> bool:
        return any(self._is_relative_to(path, root) for root in self._config.allow_roots)

    def _match_allowed_root(self, path: Path) -> Optional[Path]:
        for root in self._config.allow_roots:
            if self._is_relative_to(path, root):
                return root
        return None

    @staticmethod
    def _is_relative_to(path: Path, base: Path) -> bool:
        try:
            path.relative_to(base)
            return True
        except ValueError:
            return False

    @staticmethod
    def _sanitize_target(name: str) -> str:
        clean = name.strip()
        if not clean:
            raise ValueError("target_class must not be empty")
        if any(token in clean for token in ("../", "..\\", "/", "\\")):
            raise ValueError("target_class contains forbidden path separators")
        return clean

    def _build_new_name(
        self,
        src: Path,
        target_class: str,
        rename_mode: str,
        custom_name: Optional[str],
    ) -> str:
        ext = src.suffix.lower()
        if rename_mode == "keep":
            return src.name
        if rename_mode == "custom":
            if not custom_name:
                raise ValueError("custom_name required when rename_mode='custom'")
            if any(token in custom_name for token in ("../", "..\\", "/", "\\")):
                raise ValueError("custom_name contains forbidden characters")
            return custom_name
        # default: uuid-based rename honoring dataset naming pattern
        sanitized_class = target_class.replace("/", "-").strip()
        tag = self._config.default_tag.strip("_") or "web"
        return f"{sanitized_class}__{tag}__{uuid.uuid4().hex}{ext}"


class PestReviewRequestHandler(BaseHTTPRequestHandler):
    server_version = "PestReviewHTTP/0.1"

    @property
    def service(self) -> PestReviewService:
        return self.server.service  # type: ignore[attr-defined]

    def _set_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    # --------------------------------------------------------------
    # HTTP verbs
    # --------------------------------------------------------------
    def do_OPTIONS(self) -> None:  # pylint: disable=invalid-name
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:  # pylint: disable=invalid-name
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "invalid_json"}, HTTPStatus.BAD_REQUEST)
            return

        if self.path == "/api/analyze":
            self._handle_analyze(payload)
            return
        if self.path == "/api/reclassify":
            self._handle_reclassify(payload)
            return

        self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)

    # --------------------------------------------------------------
    # Handlers
    # --------------------------------------------------------------
    def _handle_analyze(self, payload: Dict[str, Any]) -> None:
        rel_path = payload.get("path")
        keyword = payload.get("keyword")
        if not rel_path:
            self._send_json({"error": "missing_path"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            result = self.service.analyze(rel_path, keyword)
        except FileNotFoundError:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        except PermissionError:
            self._send_json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
            return
        except ValueError as exc:
            self._send_json({"error": "bad_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        except VLMAPIError as exc:  # type: ignore
            self._send_json({"error": "vlm_error", "message": str(exc)}, HTTPStatus.BAD_GATEWAY)
            return

        self._send_json({"data": result})

    def _handle_reclassify(self, payload: Dict[str, Any]) -> None:
        item_id = payload.get("id")
        rel_path = payload.get("path")
        target_class = payload.get("target_class")
        rename_mode = payload.get("rename_mode", "keep")
        custom_name = payload.get("custom_name")
        if not rel_path or not target_class:
            self._send_json({"error": "missing_fields"}, HTTPStatus.BAD_REQUEST)
            return
        try:
            outcome = self.service.reclassify(item_id, rel_path, target_class, rename_mode, custom_name)
        except FileNotFoundError:
            self._send_json({"error": "not_found"}, HTTPStatus.NOT_FOUND)
            return
        except PermissionError:
            self._send_json({"error": "forbidden"}, HTTPStatus.FORBIDDEN)
            return
        except ValueError as exc:
            self._send_json({"error": "bad_request", "message": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        self._send_json({"data": outcome})

    # --------------------------------------------------------------
    # Utilities
    # --------------------------------------------------------------
    def _send_json(self, payload: Dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._set_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # pragma: no cover - reduce noise
        LOGGER.info("%s - %s", self.address_string(), fmt % args)


def build_vlm_client(args: argparse.Namespace) -> Optional[XmdbdVLMClient]:
    if args.mock or XmdbdVLMClient is None:
        return None

    api_key = args.api_key or os.getenv("VLM_API_KEY")
    base_url = args.api_base or os.getenv("VLM_API_BASE", "https://xmdbd.online/v1")
    model = args.model or os.getenv("VLM_MODEL", "gemini-2.5-flash")
    timeout = args.timeout or int(os.getenv("VLM_TIMEOUT", "120"))
    verify_ssl_env = os.getenv("VLM_VERIFY_SSL")
    verify_ssl = args.verify_ssl
    if verify_ssl_env is not None:
        verify_ssl = verify_ssl_env.lower() not in {"0", "false", "no"}

    if not api_key:
        LOGGER.warning("VLM API key not configured; falling back to mock mode")
        return None

    return XmdbdVLMClient(
        api_key=api_key,
        base_url=base_url,
        model=model,
        timeout=timeout,
        verify_ssl=verify_ssl,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local backend for pest manual review UI")
    parser.add_argument("--port", type=int, default=5178, help="Port to bind the HTTP server")
    parser.add_argument(
        "--root",
        default="web_scraper/scraped_images",
        help="Primary root containing review images (relative to repo root)",
    )
    parser.add_argument(
        "--manifest",
        default="web_scraper/pest_review_manifest.js",
        help="Path to the review manifest JS file (relative to repo root)",
    )
    parser.add_argument(
        "--allow-root",
        action="append",
        default=None,
        help="Additional roots allowed for operations (relative to repo root)",
    )
    parser.add_argument("--tag", default="web", help="Source tag used for UUID renames")
    parser.add_argument("--api-key", help="Override VLM API key")
    parser.add_argument("--api-base", help="Override VLM base URL")
    parser.add_argument("--model", help="Override VLM model name")
    parser.add_argument("--timeout", type=int, help="Request timeout in seconds")
    parser.add_argument("--no-verify-ssl", dest="verify_ssl", action="store_false", default=True)
    parser.add_argument("--mock", action="store_true", help="Force mock responses (no network)")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )

    repo_root = Path(__file__).resolve().parents[1]
    review_root = (repo_root / args.root).resolve()
    if not review_root.exists():
        raise SystemExit(f"Review root not found: {review_root}")

    manifest_path = (repo_root / args.manifest).resolve()

    allowed = [review_root]
    if args.allow_root:
        for rel in args.allow_root:
            candidate = (repo_root / rel).resolve()
            allowed.append(candidate)

    vlm_client = build_vlm_client(args)

    config = ServerConfig(
        repo_root=repo_root,
        review_root=review_root,
        manifest_path=manifest_path,
        default_tag=args.tag,
        allow_roots=tuple(allowed),
        vlm_client=vlm_client,
        mock_mode=vlm_client is None,
    )
    service = PestReviewService(config)

    class _Server(ThreadingHTTPServer):
        # attach service for handlers
        def __init__(self, server_address: tuple[str, int], handler_cls: type[BaseHTTPRequestHandler]):
            super().__init__(server_address, handler_cls)
            self.service = service  # type: ignore[attr-defined]

    httpd = _Server(("0.0.0.0", args.port), PestReviewRequestHandler)
    LOGGER.info("Pest review server running on port %s (mock=%s)", args.port, config.mock_mode)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("Shutting down server")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
