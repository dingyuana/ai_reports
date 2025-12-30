"""
文件名: ai_grader.py
作用: 实现AI批阅功能，与AI服务器通信，发送报告内容和批阅标准，接收评分和评语
实现路径:
    1. 初始化AI批阅器，配置API连接参数
    2. 实现与AI服务的通信接口
    3. 处理AI返回的评分和评语
功能:
    - 连接外部AI服务（如智谱AI）
    - 发送报告内容和批阅标准
    - 接收AI生成的评语
    - 从评语中提取分数
使用方式:
    - 在grading_system.py中被实例化
    - 通过grade_report方法发送报告内容进行批阅
    - 返回包含分数和评语的字典
依赖:
    - zai: 用于智谱AI通信
    - re: 用于正则表达式提取分数
"""

from typing import Dict, Any
import logging
import re
from zai import ZhipuAiClient

# 配置日志记录器
logger = logging.getLogger(__name__)


class AIGrader:
    """AI批阅模块：与AI服务器通信，发送报告和批阅要求，接收反馈"""

    def __init__(self, api_config: Dict[str, str]):
        self.api_key = api_config["api_key"]
        self.model = api_config.get("model", "glm-4.7")
        self.client = ZhipuAiClient(api_key=self.api_key)

    def grade_report(self, report_text: str, criteria: str) -> Dict[str, Any]:
        """调用AI接口批阅报告"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": f"你是一个专业的教师，需要根据以下标准批阅学生实验报告：{criteria}"
                    },
                    {
                        "role": "user",
                        "content": f"请批阅这份实验报告：\n{report_text}"
                    }
                ],
                temperature=0.3
            )

            comments = response.choices[0].message.content
            score = self._extract_score(comments)

            return {"score": score, "comments": comments}

        except Exception as e:
            logger.error(f"AI批阅失败: {e}")
            # 如果AI服务失败，返回模拟评分
            return self._generate_mock_grade(report_text, criteria)

    def _generate_mock_grade(self, report_text: str, criteria: str) -> Dict[str, Any]:
        """生成模拟评分，用于API密钥未配置或AI服务不可用时"""
        import random
        
        # 基于报告长度和关键词简单评估
        length_score = min(20, max(5, len(report_text) // 100))  # 基于长度评分
        
        # 检查是否包含关键部分
        content_keywords = ['实验目的', '实验原理', '实验步骤', '实验结果', '数据分析', '结论']
        found_keywords = [keyword for keyword in content_keywords if keyword in report_text]
        content_score = min(40, len(found_keywords) * 8)  # 基于内容完整性评分
        
        # 综合评分
        base_score = length_score * 0.3 + content_score * 0.7
        score = max(30, min(100, int(base_score + random.randint(-10, 10))))  # 添加随机因素避免重复
        
        # 生成评语
        comments = f"报告总评：这是一份{ '质量较好' if score >= 80 else '内容一般' if score >= 60 else '需要改进' }的实验报告。\n"
        comments += f"评分细节：内容完整性{content_score}分，报告长度{length_score}分。\n"
        comments += f"包含部分：{', '.join(found_keywords) if found_keywords else '未检测到关键部分'}。\n"
        comments += "建议：请确保实验报告包含实验目的、原理、步骤、结果和结论等基本要素。"
        
        return {"score": score, "comments": comments}

    def _extract_score(self, text: str) -> int:
        """从AI返回的文本中提取分数"""
        match = re.search(r'(\d+)\s*分', text)
        return int(match.group(1)) if match else 60  # 默认60分