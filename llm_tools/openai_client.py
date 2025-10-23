"""OpenAI 兼容 API 客户端（用于 4zapi.com 等）"""
import base64
import json
import logging
from pathlib import Path
from typing import Dict, Any
import requests
import time
import random


class OpenAIVLMClient:
    """OpenAI 格式 API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        timeout: int = 120,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required.")
        if not base_url:
            raise ValueError("API base URL is required.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        
        logging.info("OpenAI VLM client initialized for model '%s'", self.model)

    def _build_prompt(self, expected_class: str) -> str:
        return (
            "You are an agronomy vision expert validating agricultural images. "
            f"The image is expected to show: '{expected_class}'. "
            "\n\nAnalyze this image and return a JSON object with these keys:\n"
            "- is_match (boolean): Does the image match the expected class?\n"
            "- actual_class (string or null): If not matching, what is it? (e.g., 'snail', 'leaf', 'diagram')\n"
            "- quality_score (float 0-1): Image quality assessment\n"
            "- rejection_reason (string or null): Why reject, if applicable\n"
            "- description_en (string): Rich English description\n"
            "- description_zh (string): Rich Chinese description\n"
            "\nRespond ONLY with valid JSON, no other text."
        )

    def analyze_image(self, image_path: Path, expected_class: str) -> Dict[str, Any]:
        """分析图片并返回验证结果（带重试机制）"""
        if not image_path.is_file():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logging.info("Analyzing %s for class '%s'...", image_path, expected_class)

        # 编码图片
        encoded_image = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        
        # OpenAI API 格式
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a meticulous assistant that only outputs valid JSON objects."
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": self._build_prompt(expected_class)
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{encoded_image}"
                            }
                        }
                    ]
                }
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        # 重试机制：处理 429 错误和SSL错误  
        max_retries = 15  # 大幅增加重试次数
        base_delay = 3  # 基础延迟（秒）

        for attempt in range(max_retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.timeout, verify=False)
                response.raise_for_status()
                break  # 成功，跳出重试循环
            except requests.HTTPError as exc:
                if exc.response.status_code == 429 and attempt < max_retries - 1:
                    # 429 错误且还有重试次数，使用指数退避策略
                    delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                    logging.warning(f"Rate limit hit (429), retrying in {delay:.1f}s (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    continue
                else:
                    # 其他错误或重试次数用完
                    logging.error(f"Request failed after {attempt+1} attempts: {exc}")
                    raise RuntimeError(f"HTTP request failed: {exc}") from exc
            except requests.RequestException as exc:
                logging.error(f"Request exception: {exc}")
                raise RuntimeError(f"HTTP request failed: {exc}") from exc

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Failed to decode JSON response from API") from exc

        # 提取响应文本
        content = self._extract_content(data)
        
        # 解析 JSON
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            # 如果不是 JSON，尝试提取 JSON 部分
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                except:
                    raise RuntimeError(f"Model response is not valid JSON: {content[:500]}") from exc
            else:
                raise RuntimeError(f"Model response is not valid JSON: {content[:500]}") from exc

        self._validate_payload(parsed)
        return parsed

    @staticmethod
    def _extract_content(response_payload: Dict[str, Any]) -> str:
        """从 OpenAI API 响应中提取文本内容"""
        try:
            choices = response_payload.get("choices", [])
            if not choices:
                raise RuntimeError("No choices in response")
            
            message = choices[0].get("message", {})
            content = message.get("content", "")
            
            return content
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Unexpected response structure from API") from exc

    @staticmethod
    def _validate_payload(parsed: Dict[str, Any]) -> None:
        """验证返回的 JSON 结构"""
        required_keys = {"is_match", "quality_score", "description_en", "description_zh"}
        missing = required_keys - set(parsed.keys())
        if missing:
            raise RuntimeError(f"Response JSON missing keys: {missing}")
        
        if not isinstance(parsed["is_match"], bool):
            raise RuntimeError("'is_match' must be boolean")
        
        if not isinstance(parsed["quality_score"], (int, float)):
            raise RuntimeError("'quality_score' must be numeric")
