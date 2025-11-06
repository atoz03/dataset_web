import os
import argparse
import base64
import mimetypes
import json
from pathlib import Path
import logging
from typing import Dict, Any
import concurrent.futures
from datetime import datetime

import requests
import re
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 尝试导入客户端
try:
    from gemini_client import GeminiVLMClient
    GEMINI_CLIENT_AVAILABLE = True
except ImportError:
    GEMINI_CLIENT_AVAILABLE = False

try:
    from multi_api_client import MultiAPIClient
    MULTI_API_CLIENT_AVAILABLE = True
except ImportError:
    MULTI_API_CLIENT_AVAILABLE = False

# 配置日志记录


class VLMAPIError(RuntimeError):
    """封装远程 VLM API 调用失败时的异常。"""


class XmdbdVLMClient:
    """实际可用的 XMDBD 多模态 LLM 客户端。"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
        verify_ssl: bool = True,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")
        if not base_url:
            raise ValueError("API base URL is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        })
        self.session.verify = verify_ssl
        # Avoid inheriting system proxy env to reduce ProxyError/RemoteDisconnected
        try:
            self.session.trust_env = False
        except Exception:
            pass
        if not verify_ssl:
            try:
                from urllib3 import disable_warnings
                from urllib3.exceptions import InsecureRequestWarning

                disable_warnings(InsecureRequestWarning)
                logging.warning("TLS verification disabled for XMDBD VLM client; proceed with caution.")
            except ImportError:
                logging.warning("urllib3 not available; unable to suppress insecure request warnings.")
        # Increase connection pool to reduce 'Connection pool is full' warnings
        try:
            pool_size = int(os.environ.get("VLM_POOL_MAXSIZE", "64"))
        except Exception:
            pool_size = 64
        # Robust HTTP retries for transient errors and proxy resets
        retry = Retry(
            total=int(os.environ.get("VLM_HTTP_TOTAL_RETRIES", "3")),
            backoff_factor=float(os.environ.get("VLM_HTTP_BACKOFF", "0.5")),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"POST"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_size, pool_maxsize=pool_size)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Retries for non-JSON outputs
        try:
            self._max_retries = max(0, int(os.environ.get("VLM_MAX_RETRIES", "2")))
        except Exception:
            self._max_retries = 2

        logging.info("XMDBD VLM client initialized for model '%s'", self.model)

    def _build_prompt(self, expected_class: str) -> str:
        return (
            "You are an agronomy vision expert. You are validating high-resolution images of plant leaves. "
            f"The image is expected to belong to the class '{expected_class}'. "
            "1. Analyze the image to check whether the content semantically matches the expected class. "
            "2. If it does not match, identify the actual class of the main subject in the image (e.g., 'snail', 'seashell', 'marine slug'). Use a concise, one or two-word English label. "
            "3. Assess the image quality (sharpness, lighting, presence of watermarks/screenshots). "
            "4. Craft rich bilingual descriptions. "
            "Return a JSON object with the following keys: "
            "is_match (boolean), "
            "actual_class (string, null if is_match is true, or if the actual class cannot be determined), "
            "quality_score (float 0-1), "
            "rejection_reason (string; when is_match is false this MUST be a concise, non-empty reason; never null), "
            "description_en (string), "
            "description_zh (string)."
        )

    def _post(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:  # pragma: no cover - network errors
            raise VLMAPIError(f"HTTP request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:  # pragma: no cover - unexpected non-JSON response
            raise VLMAPIError("Failed to decode JSON response from VLM API") from exc

    def analyze_image(self, image_path: Path, expected_class: str) -> Dict[str, Any]:
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logging.info("Analyzing %s for class '%s'...", image_path, expected_class)

        # Compress large images to avoid 413 errors (max 500KB)
        image_bytes = image_path.read_bytes()
        max_size_bytes = 500 * 1024  # 500KB

        if len(image_bytes) > max_size_bytes:
            try:
                from PIL import Image
                import io

                img = Image.open(io.BytesIO(image_bytes))

                # Convert RGBA to RGB if necessary
                if img.mode == 'RGBA':
                    img = img.convert('RGB')

                # Compress with progressive quality reduction
                quality = 85
                while quality > 20:
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=quality, optimize=True)
                    compressed_bytes = buffer.getvalue()

                    if len(compressed_bytes) <= max_size_bytes:
                        image_bytes = compressed_bytes
                        logging.info(f"Compressed {image_path.name} from {len(image_path.read_bytes())/1024:.1f}KB to {len(compressed_bytes)/1024:.1f}KB (quality={quality})")
                        break
                    quality -= 10

            except Exception as e:
                logging.warning(f"Failed to compress {image_path.name}: {e}, using original")

        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        def build_payload(strict: bool = False) -> Dict[str, Any]:
            sys_text = "Respond with ONLY a single valid JSON object. No code fences, no extra text."
            if not strict:
                sys_text = "You are a meticulous assistant that only outputs valid JSON objects."
            return {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": sys_text,
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": self._build_prompt(expected_class)},
                            {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{encoded_image}"}},
                        ],
                    },
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            }

        def coerce_json(text: str) -> Dict[str, Any]:
            try:
                return json.loads(text)
            except Exception:
                pass
            m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
            if m:
                inner = m.group(1)
                try:
                    return json.loads(inner)
                except Exception:
                    pass
            start = text.find('{')
            while start != -1:
                depth = 0
                for i in range(start, len(text)):
                    c = text[i]
                    if c == '{':
                        depth += 1
                    elif c == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[start:i+1]
                            try:
                                return json.loads(candidate)
                            except Exception:
                                break
                start = text.find('{', start + 1)
            raise VLMAPIError("Model response is not valid JSON")

        delay = 0.5
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            strict = attempt > 0
            data = self._post("/chat/completions", build_payload(strict=strict))
            content = self._extract_content(data)
            try:
                parsed = coerce_json(content)
                # Ensure non-empty rejection_reason when not matched
                try:
                    if not parsed.get("is_match"):
                        rr = parsed.get("rejection_reason")
                        if not isinstance(rr, str) or not rr.strip():
                            actual = parsed.get("actual_class") or "unknown"
                            parsed["rejection_reason"] = f"Expected '{expected_class}', got '{actual}'."
                except Exception:
                    pass
                self._validate_payload(parsed)
                return parsed
            except Exception as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(delay)
                    delay *= 2
                    continue
                break
        raise VLMAPIError(str(last_exc) if last_exc else "Model response is not valid JSON")

    @staticmethod
    def _extract_content(response_payload: Dict[str, Any]) -> str:
        try:
            message_content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise VLMAPIError("Unexpected response structure from VLM API") from exc

        if isinstance(message_content, list):
            # 某些模型会以多段内容返回，拼接其中的文本段
            parts: list[str] = []
            for item in message_content:
                if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
                    parts.append(item["text"])
            message_content = "".join(parts)

        if not isinstance(message_content, str):
            raise VLMAPIError("Received non-text content from VLM API")

        return message_content

    @staticmethod
    def _validate_payload(payload: Dict[str, Any]) -> None:
        required_keys = {
            "is_match": bool,
            "actual_class": (str, type(None)),
            "quality_score": (int, float),
            "rejection_reason": (str, type(None)),
            "description_en": str,
            "description_zh": str,
        }
        for key, expected_type in required_keys.items():
            if key not in payload:
                raise VLMAPIError(f"Missing key '{key}' in model response")
            if not isinstance(payload[key], expected_type):
                raise VLMAPIError(
                    f"Value for '{key}' has unexpected type {type(payload[key]).__name__}, "
                    f"expected {expected_type}."
                )


def _get_target_dir(rejected_dir: Path, expected_class: str, result: Dict[str, Any]) -> Path:
    """Determine the target directory for a rejected image."""
    actual_class = result.get("actual_class")
    if actual_class and isinstance(actual_class, str) and actual_class.strip():
        # Sanitize the class name to be a valid directory name
        sanitized_class = "".join(c for c in actual_class.strip().lower() if c.isalnum() or c in (' ', '_')).rstrip().replace(' ', '_')
        return rejected_dir / sanitized_class
    # Fallback to the original expected class directory
    return rejected_dir / expected_class


def _process_single_image(
    client: XmdbdVLMClient,
    image_path: Path,
    expected_class: str,
    action: str,
    rejected_dir: Path,
    output_metadata: bool
) -> None:
    """Analyzes a single image and performs the required action."""
    try:
        result = client.analyze_image(image_path, expected_class)

        if not result.get("is_match"):
            reason = result.get('rejection_reason', 'No reason provided')
            logging.warning(f"REJECTED: {image_path}. Reason: {reason}")

            if action == "move":
                target_dir = _get_target_dir(rejected_dir, expected_class, result)
                target_dir.mkdir(parents=True, exist_ok=True)
                image_path.rename(target_dir / image_path.name)
            elif action == "delete":
                image_path.unlink()
            elif action == "dry-run":
                target_dir = _get_target_dir(rejected_dir, expected_class, result)
                target_path = target_dir / image_path.name
                logging.info("[dry-run] Would move %s to %s", image_path, target_path)
        else:
            logging.info(f"ACCEPTED: {image_path}")
            if output_metadata and action != "dry-run":
                metadata_path = image_path.with_suffix('.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

    except VLMAPIError as exc:
        logging.error("Failed to process %s: %s", image_path, exc)
    except Exception as exc:  # pragma: no cover - defensive guard
        logging.exception("Unexpected error while processing %s", image_path)


def process_directory(
    client: XmdbdVLMClient,
    root_dir: Path,
    action: str = "move",
    output_metadata: bool = True,
    max_workers: int = 4,
    skip_existing_metadata: bool = False
) -> None:
    """
    Concurrently processes all images in a directory using a thread pool.

    Args:
        client: VLM API 客户端。
        root_dir: 要处理的根目录 (例如 `datasets/diseases`)。
        action: 对不匹配的图像执行的操作 ('move', 'delete', 'dry-run')。
        output_metadata: 是否为匹配的图像生成元数据文件。
        max_workers: 用于处理图像的并发工作线程数。
    """
    if not root_dir.is_dir():
        logging.error(f"Error: Directory not found at {root_dir}")
        return

    rejected_dir = root_dir / ".rejected_by_llm"
    if action == "move":
        rejected_dir.mkdir(exist_ok=True)

    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    tasks = []

    # Check if root_dir itself is a class directory (i.e., contains image files directly)
    if any(p.is_file() and p.suffix.lower() in image_extensions for p in root_dir.glob('*')):
        logging.info("Root directory appears to be a single class directory. Processing it directly.")
        expected_class = root_dir.name
        for image_path in root_dir.rglob('*'):
            # Skip hidden directories (starting with .)
            if any(part.startswith('.') for part in image_path.parts):
                continue
            if image_path.is_file() and image_path.suffix.lower() in image_extensions:
                if skip_existing_metadata and image_path.with_suffix('.json').exists():
                    continue
                tasks.append((image_path, expected_class))
    else:
        logging.info("Scanning for images in subdirectories...")
        for class_dir in root_dir.iterdir():
            if not class_dir.is_dir() or class_dir.name.startswith('.'):
                continue

            expected_class = class_dir.name
            for image_path in class_dir.rglob('*'):
                # Skip hidden directories (starting with .)
                if any(part.startswith('.') for part in image_path.parts):
                    continue
                if image_path.is_file() and image_path.suffix.lower() in image_extensions:
                    if skip_existing_metadata and image_path.with_suffix('.json').exists():
                        continue
                    tasks.append((image_path, expected_class))

    if not tasks:
        logging.info("No images found to process.")
        return

    logging.info(f"Found {len(tasks)} images. Starting processing with {max_workers} workers...")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create a dictionary to hold future-to-task mapping for error reporting
        future_to_task = {
            executor.submit(
                _process_single_image,
                client,
                image_path,
                expected_class,
                action,
                rejected_dir,
                output_metadata
            ): (image_path, expected_class)
            for image_path, expected_class in tasks
        }

        for future in concurrent.futures.as_completed(future_to_task):
            task_info = future_to_task[future]
            try:
                future.result()  # We call result() to raise any exceptions from the thread
            except Exception as exc:  # pragma: no cover - defensive guard
                logging.exception(
                    "A task for image %s in class %s generated an unhandled exception.",
                    task_info[0], task_info[1]
                )

def main():
    parser = argparse.ArgumentParser(
        description="Use a Vision-Language Model (VLM) to verify and describe images in a dataset.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--root",
        type=str,
        required=True,
        help="The root directory to process (e.g., 'datasets/diseases')."
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=os.environ.get("VLM_API_KEY"),
        help="API key for the VLM service. Can also be set via VLM_API_KEY environment variable."
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default=os.environ.get("VLM_API_BASE", "https://xmdbd.online/v1"),
        help="Base URL for the VLM service. Defaults to https://xmdbd.online/v1 or the VLM_API_BASE env var."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.environ.get("VLM_MODEL", "gemini-2.5-flash"),
        help="Model identifier to use. Defaults to gemini-2.5-flash or the VLM_MODEL env var."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.environ.get("VLM_TIMEOUT", "120")),
        help="Timeout (seconds) for each API request. Defaults to 120 seconds or VLM_TIMEOUT env var."
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification when calling the VLM API (use with caution)."
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["move", "delete", "dry-run"],
        default="move",
        help=(
            "Action to take for mismatched images:\n"
            "  - move: Move to a '.rejected_by_llm' subdirectory (default).\n"
            "  - delete: Permanently delete the image.\n"
            "  - dry-run: Only log actions without moving or deleting files."
        )
    )
    parser.add_argument(
        "--no-metadata",
        action="store_true",
        help="If set, do not write .json metadata files for accepted images."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("VLM_WORKERS", "4")),
        help="Number of concurrent workers for processing images. Defaults to 4 or VLM_WORKERS env var."
    )
    parser.add_argument(
        "--skip-existing-metadata",
        action="store_true",
        help="Skip images that already have a sibling .json metadata file."
    )

    args = parser.parse_args()

    # --- New logging setup ---
    log_dir = Path("logs")
    date_str = datetime.now().strftime("%Y-%m-%d")
    time_str = datetime.now().strftime("%H%M%S")

    # New log directory structure: logs/YYYY-MM-DD/llm_enhancement_HHMMSS
    run_log_dir = log_dir / date_str / f"llm_enhancement_{time_str}"
    run_log_dir.mkdir(parents=True, exist_ok=True)

    log_file_path = run_log_dir / "run.log"

    # Configure logging to both file and console
    # Remove any existing handlers to prevent duplicate logs in interactive sessions
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler() # Also log to console
        ]
    )
    logging.info(f"Logging to {log_file_path}")
    # --- End new logging setup ---

    if not args.api_key:
        logging.error("API key is missing. Please provide it via --api-key or the VLM_API_KEY environment variable.")
        return

    # 检测使用哪个客户端
    # 检查是否使用多API配置
    use_multi_api = os.environ.get("VLM_USE_MULTI_API", "false").lower() in {"true", "1", "yes"}
    
    try:
        if use_multi_api and MULTI_API_CLIENT_AVAILABLE:
            # 多API负载均衡模式
            logging.info("🔀 Using Multi-API load balancing mode")
            api_configs = []
            
            # 主API
            if os.environ.get("VLM_API_KEY") and os.environ.get("VLM_API_BASE"):
                api_configs.append({
                    'name': 'Primary (Free)',
                    'api_key': os.environ.get("VLM_API_KEY"),
                    'base_url': os.environ.get("VLM_API_BASE"),
                    'model': os.environ.get("VLM_MODEL", "gemini-2.0-flash-exp"),
                    'type': os.environ.get("VLM_TYPE", "gemini")
                })
            
            # 备用API
            if os.environ.get("VLM_API_KEY_2") and os.environ.get("VLM_API_BASE_2"):
                api_configs.append({
                    'name': 'Backup (Paid)',
                    'api_key': os.environ.get("VLM_API_KEY_2"),
                    'base_url': os.environ.get("VLM_API_BASE_2"),
                    'model': os.environ.get("VLM_MODEL_2", "gemini-2.0-flash-001"),
                    'type': os.environ.get("VLM_TYPE_2", "openai")
                })
            
            if not api_configs:
                logging.error("Multi-API mode enabled but no API configs found in environment")
                return
            
            client = MultiAPIClient(api_configs, timeout=args.timeout)
            logging.info(f"✅ Multi-API client ready with {len(api_configs)} sources")
            
        else:
            # 单API模式（兼容旧逻辑）
            use_gemini_client = "localhost" in args.api_base.lower() or "generativelanguage.googleapis.com" in args.api_base.lower()
            
            if use_gemini_client and GEMINI_CLIENT_AVAILABLE:
                logging.info("Using Gemini API client (detected Google/local proxy endpoint)")
                client = GeminiVLMClient(
                    api_key=args.api_key,
                    base_url=args.api_base,
                    model=args.model,
                    timeout=args.timeout,
                )
            else:
                logging.info("Using OpenAI-compatible API client")
                verify_ssl = True
                env_verify = os.environ.get("VLM_VERIFY_SSL")
                if env_verify is not None:
                    verify_ssl = env_verify.lower() in {"1", "true", "yes"}
                if args.insecure:
                    verify_ssl = False
                
                client = XmdbdVLMClient(
                    api_key=args.api_key,
                    base_url=args.api_base,
                    model=args.model,
                    timeout=args.timeout,
                    verify_ssl=verify_ssl,
                )
    except Exception as exc:
        logging.error("Failed to initialize VLM client: %s", exc)
        return
    root_path = Path(args.root)
    
    process_directory(
        client,
        root_path,
        action=args.action,
        output_metadata=not args.no_metadata,
        max_workers=args.workers,
        skip_existing_metadata=args.skip_existing_metadata
    )

    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
