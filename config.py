import logging
import os

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = os.path.join(BASE_DIR, "student_reports")
OUTPUT_DIR = os.path.join(BASE_DIR, "graded_reports")

# AI服务器配置
API_CONFIG = {
    "api_key": "your_api_key_here",
    "api_endpoint": "https://api.doubao.com/v1/chat/completions",
    "model": "doubao-pro"
}

# 日志配置
LOG_CONFIG = {
    "level": logging.INFO,
    "format": '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}