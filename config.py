import logging
import os
from dotenv import load_dotenv
from typing import Optional

# 加载环境变量
load_dotenv()

def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """获取环境变量，支持验证和默认值"""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value

def validate_required_env_vars():
    """验证必需的环境变量"""
    required_vars = ["AI_API_KEY", "ARK_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

# 验证必需的环境变量
validate_required_env_vars()

# 基础路径配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORTS_DIR = get_env_var("REPORTS_DIR", os.path.join(BASE_DIR, "student_reports"))
OUTPUT_DIR = get_env_var("OUTPUT_DIR", os.path.join(BASE_DIR, "graded_reports"))
TEMP_DIR = get_env_var("TEMP_DIR", os.path.join(BASE_DIR, "temp"))
LOGS_DIR = get_env_var("LOGS_DIR", os.path.join(BASE_DIR, "logs"))

# 应用程序配置
PORT = int(get_env_var("PORT", "8000"))
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO")
WORKERS = int(get_env_var("WORKERS", "1"))
SECRET_KEY = get_env_var("SECRET_KEY", "default-secret-key-change-in-production")

# 文件处理配置
MAX_FILE_SIZE = int(get_env_var("MAX_FILE_SIZE", "104857600"))  # 100MB
AI_TIMEOUT = int(get_env_var("AI_TIMEOUT", "30"))
MAX_RETRIES = int(get_env_var("MAX_RETRIES", "3"))

# 导入secrets管理器
try:
    from utils.secrets_manager import get_ai_api_key, get_ark_api_key, get_secret_key
    USE_SECRETS_MANAGER = True
except ImportError:
    USE_SECRETS_MANAGER = False

# AI服务器配置
if USE_SECRETS_MANAGER:
    API_CONFIG = {
        "api_key": get_ai_api_key(),
        "api_endpoint": get_env_var("AI_API_ENDPOINT", "https://api.doubao.com/v1/chat/completions"),
        "model": get_env_var("AI_MODEL", "doubao-pro"),
        "timeout": AI_TIMEOUT,
        "max_retries": MAX_RETRIES,
        "temperature": float(get_env_var("AI_TEMPERATURE", "0.7"))
    }
    ARK_API_KEY = get_ark_api_key()
    SECRET_KEY = get_secret_key()
else:
    API_CONFIG = {
        "api_key": get_env_var("AI_API_KEY", required=True),
        "api_endpoint": get_env_var("AI_API_ENDPOINT", "https://api.doubao.com/v1/chat/completions"),
        "model": get_env_var("AI_MODEL", "doubao-pro"),
        "timeout": AI_TIMEOUT,
        "max_retries": MAX_RETRIES,
        "temperature": float(get_env_var("AI_TEMPERATURE", "0.7"))
    }
    ARK_API_KEY = get_env_var("ARK_API_KEY", required=True)

# 支持的文档类型
SUPPORTED_FORMATS = [".pdf", ".docx", ".doc"]

# 安全配置
ALLOWED_HOSTS = get_env_var("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# 日志配置
LOG_CONFIG = {
    "level": getattr(logging, LOG_LEVEL.upper()),
    "format": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    "filename": os.path.join(LOGS_DIR, "grading_system.log")
}

# 健康检查配置
HEALTH_CHECK_CONFIG = {
    "interval": int(get_env_var("HEALTH_CHECK_INTERVAL", "30")),
    "timeout": int(get_env_var("HEALTH_CHECK_TIMEOUT", "10")),
    "retries": int(get_env_var("HEALTH_CHECK_RETRIES", "3"))
}

# 性能配置
PERFORMANCE_CONFIG = {
    "cpu_limit": get_env_var("CPU_LIMIT", "2.0"),
    "memory_limit": get_env_var("MEMORY_LIMIT", "2G"),
    "cpu_reservation": get_env_var("CPU_RESERVATION", "0.5"),
    "memory_reservation": get_env_var("MEMORY_RESERVATION", "512M")
}

# 确保必要的目录存在
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)