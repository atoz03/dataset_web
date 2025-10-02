import os
import argparse
import base64
import mimetypes
import json
from pathlib import Path
import logging
from typing import Dict, Any

import requests

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        if not verify_ssl:
            try:
                from urllib3 import disable_warnings
                from urllib3.exceptions import InsecureRequestWarning

                disable_warnings(InsecureRequestWarning)
                logging.warning("TLS verification disabled for XMDBD VLM client; proceed with caution.")
            except ImportError:
                logging.warning("urllib3 not available; unable to suppress insecure request warnings.")
        logging.info("XMDBD VLM client initialized for model '%s'", self.model)

    def _build_prompt(self, expected_class: str) -> str:
        return (
            "You are an agronomy vision expert. You are validating high-resolution images of plant leaves. "
            f"The image is expected to belong to the class '{expected_class}'. "
            "Analyse the image to check whether the content semantically matches the expected class, assess the image quality (sharpness, lighting, presence of watermarks/screenshots), and craft rich bilingual descriptions. "
            "Return a JSON object with the following keys: "
            "is_match (boolean), quality_score (float 0-1), rejection_reason (null or string), "
            "description_en (string) and description_zh (string)."
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

        encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = "application/octet-stream"
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a meticulous assistant that only outputs valid JSON objects.",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._build_prompt(expected_class),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{encoded_image}",
                            },
                        },
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        data = self._post("/chat/completions", payload)
        content = self._extract_content(data)

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise VLMAPIError("Model response is not valid JSON") from exc

        self._validate_payload(parsed)
        return parsed

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


def process_directory(
    client: XmdbdVLMClient,
    root_dir: Path,
    action: str = "move",
    output_metadata: bool = True
) -> None:
    """
    处理指定目录下的所有图像。

    Args:
        client: VLM API 客户端。
        root_dir: 要处理的根目录 (例如 `datasets/diseases`)。
        action: 对不匹配的图像执行的操作 ('move' 或 'delete')。
        output_metadata: 是否为匹配的图像生成元数据文件。
    """
    if not root_dir.is_dir():
        logging.error(f"Error: Directory not found at {root_dir}")
        return

    rejected_dir = root_dir / ".rejected_by_llm"
    if action == "move":
        rejected_dir.mkdir(exist_ok=True)

    image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    
    # 遍历所有子目录（即类别目录）
    for class_dir in root_dir.iterdir():
        if not class_dir.is_dir() or class_dir.name.startswith('.'):
            continue

        expected_class = class_dir.name
        logging.info(f"--- Processing class: {expected_class} ---")

        for image_path in class_dir.iterdir():
            if image_path.is_file() and image_path.suffix.lower() in image_extensions:
                try:
                    result = client.analyze_image(image_path, expected_class)

                    if not result.get("is_match"):
                        logging.warning(f"REJECTED: {image_path}. Reason: {result.get('rejection_reason')}")
                        if action == "move":
                            target_dir = rejected_dir / expected_class
                            target_dir.mkdir(exist_ok=True)
                            image_path.rename(target_dir / image_path.name)
                        elif action == "delete":
                            image_path.unlink()
                        elif action == "dry-run":
                            logging.info("[dry-run] Would move to %s", rejected_dir / expected_class / image_path.name)
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

    args = parser.parse_args()

    if not args.api_key:
        logging.error("API key is missing. Please provide it via --api-key or the VLM_API_KEY environment variable.")
        return

    verify_ssl = True
    env_verify = os.environ.get("VLM_VERIFY_SSL")
    if env_verify is not None:
        verify_ssl = env_verify.lower() in {"1", "true", "yes"}
    if args.insecure:
        verify_ssl = False

    try:
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
        output_metadata=not args.no_metadata
    )

    logging.info("Processing complete.")

if __name__ == "__main__":
    main()
