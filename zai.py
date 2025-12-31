"""
zai.py - ARK API封装模块
提供与智谱AI兼容的接口，用于AI报告批阅系统
"""

from volcenginesdkarkruntime import Ark
from typing import Optional, Dict, Any, List


class ZhipuAiClient:
    """智谱AI客户端封装类（基于ARK API）"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            base_url: API基础URL（可选）
        """
        self.api_key = api_key
        self.base_url = base_url
        
        # 初始化ARK客户端
        if base_url:
            self._client = Ark(api_key=api_key, base_url=base_url)
        else:
            self._client = Ark(api_key=api_key)
    
    @property
    def chat(self):
        """获取聊天接口"""
        return self.ChatInterface(self._client)
    
    class ChatInterface:
        """聊天接口封装"""
        
        def __init__(self, client: Ark):
            self._client = client
        
        @property
        def completions(self):
            """获取完成接口"""
            return self.CompletionsInterface(self._client)
    
    class CompletionsInterface:
        """完成接口封装"""
        
        def __init__(self, client: Ark):
            self._client = client
        
        def create(self, model: str, messages: List[Dict[str, str]], 
                   temperature: Optional[float] = None, 
                   max_tokens: Optional[int] = None,
                   stream: bool = False,
                   **kwargs) -> Any:
            """
            创建聊天完成
            
            Args:
                model: 模型名称
                messages: 消息列表
                temperature: 温度参数
                max_tokens: 最大token数
                stream: 是否流式返回
                **kwargs: 其他参数
                
            Returns:
                响应对象
            """
            params = {
                "model": model,
                "messages": messages,
                "stream": stream,
            }
            
            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            
            # 添加其他参数
            params.update(kwargs)
            
            return self._client.chat.completions.create(**params)
