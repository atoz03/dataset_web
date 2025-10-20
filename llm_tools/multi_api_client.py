"""多API源负载均衡客户端"""
import logging
import random
from pathlib import Path
from typing import Dict, Any, List, Union
from gemini_client import GeminiVLMClient
from openai_client import OpenAIVLMClient


class MultiAPIClient:
    """支持多个API源的负载均衡客户端"""
    
    def __init__(self, api_configs: List[Dict[str, str]], timeout: int = 120):
        """
        初始化多API客户端
        
        Args:
            api_configs: API配置列表，每个配置包含 api_key, base_url, model, type (可选)
            timeout: 请求超时时间
        """
        if not api_configs:
            raise ValueError("At least one API config is required")
        
        self.clients = []
        self.client_names = []
        
        for idx, config in enumerate(api_configs):
            try:
                client_type = config.get('type', 'gemini').lower()
                
                if client_type == 'openai':
                    client = OpenAIVLMClient(
                        api_key=config['api_key'],
                        base_url=config['base_url'],
                        model=config['model'],
                        timeout=timeout
                    )
                else:  # gemini
                    client = GeminiVLMClient(
                        api_key=config['api_key'],
                        base_url=config['base_url'],
                        model=config['model'],
                        timeout=timeout
                    )
                
                self.clients.append(client)
                name = config.get('name', f"API-{idx+1}")
                self.client_names.append(name)
                logging.info(f"✅ Initialized {name} ({client_type}): {config['base_url']}")
            except Exception as e:
                logging.error(f"❌ Failed to initialize API {idx+1}: {e}")
        
        if not self.clients:
            raise RuntimeError("No API clients could be initialized")
        
        logging.info(f"Multi-API client ready with {len(self.clients)} sources")
        
        # 统计每个客户端的成功/失败次数
        self.success_counts = [0] * len(self.clients)
        self.failure_counts = [0] * len(self.clients)
        self.current_index = 0
    
    def analyze_image(self, image_path: Path, expected_class: str) -> Dict[str, Any]:
        """
        使用负载均衡策略分析图片
        
        策略：
        1. 80%概率使用第一个API（免费），20%概率使用第二个API（付费加速）
        2. 失败时自动切换到其他API
        3. 优先使用成功率高的客户端
        """
        import random
        
        # 按成功率排序客户端索引
        indices = list(range(len(self.clients)))
        
        # 计算成功率（避免除零）
        def success_rate(idx):
            total = self.success_counts[idx] + self.failure_counts[idx]
            if total == 0:
                return 0.5  # 未使用的客户端给中等优先级
            return self.success_counts[idx] / total
        
        # 负载分配：第一个API优先（免费），其他API分担压力
        if len(self.clients) > 1:
            # 60%概率用第一个（免费），40%概率用第二个（付费但更稳定）- 提高并发时增加付费比例
            if random.random() < 0.6:
                indices = [0] + [i for i in range(1, len(self.clients))]
            else:
                indices = list(range(1, len(self.clients))) + [0]
        
        # 按成功率微调顺序（但保持主要负载策略）
        indices.sort(key=success_rate, reverse=True)
        
        # 尝试所有客户端直到成功
        last_error = None
        for idx in indices:
            client = self.clients[idx]
            client_name = self.client_names[idx]
            
            try:
                logging.debug(f"Trying {client_name} (success: {self.success_counts[idx]}, failure: {self.failure_counts[idx]})")
                result = client.analyze_image(image_path, expected_class)
                
                # 成功
                self.success_counts[idx] += 1
                logging.debug(f"✅ {client_name} succeeded")
                return result
                
            except Exception as e:
                # 失败，记录并尝试下一个
                self.failure_counts[idx] += 1
                logging.warning(f"❌ {client_name} failed: {e}")
                last_error = e
                continue
        
        # 所有客户端都失败
        logging.error(f"All {len(self.clients)} API clients failed")
        raise RuntimeError(f"All API sources failed. Last error: {last_error}")
    
    def get_stats(self) -> str:
        """返回统计信息"""
        stats = []
        for idx, name in enumerate(self.client_names):
            success = self.success_counts[idx]
            failure = self.failure_counts[idx]
            total = success + failure
            rate = (success / total * 100) if total > 0 else 0
            stats.append(f"{name}: {success}/{total} ({rate:.1f}%)")
        return " | ".join(stats)
