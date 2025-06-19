import logging
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "student_reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "graded_reports")

# AI服务器配置
API_CONFIG = {
    "api_key": os.getenv("AI_API_KEY", ""),
    "api_endpoint": "https://api.doubao.com/v1/chat/completions",
    "model": "doubao-pro",
    "timeout": 30,  # 请求超时时间(秒)
    "max_retries": 3,  # 最大重试次数
    "temperature": 0.7  # AI生成温度
}

# 支持的文档类型
SUPPORTED_FORMATS = [".pdf", ".docx"]

# 日志配置
LOG_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    "filename": os.path.join(BASE_DIR, "grading_system.log")  # 日志文件路径
}