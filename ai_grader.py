from typing import Dict, Any
import requests
import logging
import re

logger = logging.getLogger(__name__)


class AIGrader:
    """AI批阅模块：与AI服务器通信，发送报告和批阅要求，接收反馈"""

    def __init__(self, api_config: Dict[str, str]):
        self.api_key = api_config["api_key"]
        self.api_endpoint = api_config["api_endpoint"]
        self.model = api_config.get("model", "doubao-pro")

    def grade_report(self, report_text: str, criteria: str) -> Dict[str, Any]:
        """调用AI接口批阅报告"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"你是一个专业的教师，需要根据以下标准批阅学生实验报告：{criteria}"},
                {"role": "user", "content": f"请批阅这份实验报告：\n{report_text}"}
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.api_endpoint, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            comments = result["choices"][0]["message"]["content"]
            score = self._extract_score(comments)

            return {"score": score, "comments": comments}

        except Exception as e:
            logger.error(f"AI批阅失败: {e}")
            return {"score": 0, "comments": f"AI批阅失败: {str(e)}"}

    def _extract_score(self, text: str) -> int:
        """从AI返回的文本中提取分数"""
        match = re.search(r'(\d+)\s*分', text)
        return int(match.group(1)) if match else 60  # 默认60分    