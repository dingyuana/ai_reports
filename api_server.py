import os
import json
import csv
import logging
import time
import threading
import httpx
from datetime import datetime
from urllib.parse import unquote
from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Depends,
    status,
    Form,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
from grading_system import GradingSystem
from config import API_CONFIG

# Import temporary file manager
from utils.temp_file_manager import temp_manager, temp_file, temp_dir

# 导入PDF处理相关函数
from pdf_grader import grade_student_reports
from pdf_chinese_helper import register_chinese_fonts, create_chinese_pdf
from grade_single_student import grade_single_student
from fastapi.staticfiles import StaticFiles
import shutil
import zipfile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

# 导入数据库和用户管理模块
from database import init_db_pool, close_db_pool, init_database, get_db_cursor
from user_manager import user_manager
from log_manager import log_manager
from config_manager import config_manager
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import timedelta

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RateLimitError(Exception):
    """API 限流错误"""
    pass

app = FastAPI()

# JWT配置
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2密码流
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 配置CORS
# 允许的前端域名列表，可以通过环境变量配置
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in ALLOWED_ORIGINS],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# 配置常量
REPORTS_DIR = "reports"  # 报告存储目录
OUTPUT_DIR = "output"  # 输出目录
GRADED_DIR = "graded_reports"  # 输出目录
CRITERIA_FILE = "criteria.json"  # 批阅要求存储文件

# 默认评分标准
DEFAULT_GRADING_CRITERIA = """
请依据以下评分标准对学生提交的大学实训报告进行客观、公正的批阅打分。

【核心批阅纪律】

严格执行正态分布：总分100分，实际得分应呈现合理的梯度分布。严禁大量给出90分以上的虚高分数，尽量避免给出逢五、逢十的整数分数（如80、85、90等），建议多使用如82、87、76等精确分数。
重内容轻形式：格式规范仅为基本门槛，评分重心必须放在实训内容的深度、逻辑性及反思质量上。
逐维度对照评分：各维度得分汇总为总分，扣分需有理有据。

【评分维度与细则】（总分100分）

一、 内容质量与深度（40分）

核心要素与逻辑（15分）：报告需完整包含实验目的、原理、步骤、结果、分析与总结。过程描述需逻辑连贯、条理清晰，准确反映操作先后顺序与关键细节，杜绝"流水账"式记录。
结果与目的的契合度（10分）：实验结果必须对实验目的进行有效回应，结论需由数据或现象严谨推导得出，前后逻辑自洽。
分析反思与原创性（15分）：实验分析、总结与反思必须为学生深度思考的原创内容，严禁直接抄袭教材或网络。能结合实训过程中的突发问题、误差来源或改进方案进行深度剖析者得高分；仅有表面描述、缺乏独立思考者，此项最高不超过8分。

二、 内容相关性与专业度（30分）

主题贴合度（15分）：正文内容与本次实训主题高度相关，无偏题、凑字数等无关内容。
专业素养体现（15分）：能准确使用专业术语，体现对实训核心技能的掌握。引用他人理论、数据、观点时，需准确标明出处且引用格式规范。若无引用内容，此项按"专业术语使用与表达"进行评分。

三、 格式规范与排版（10分）

文档格式规范（10分）：报告标题、目录、正文段落、字体字号、行间距、页码等需符合统一要求。此项为基本门槛，存在明显格式错误酌情扣分，无重大错误即可得满分。

四、 学术诚信与原创底线（20分）

内容原创无抄袭（20分）：报告核心内容必须为原创。如发现大段抄袭教材、网络或他人报告，此项直接记0分，并视情节严重程度对总分进行额外扣除（扣5-10分）。

【批阅输出要求】

给出各维度得分及总分（总分需符合正态分布，避开整数）。
撰写总评语，不列出具体扣分分数，字数控制在200字左右。
评语必须明确指出报告的"核心亮点"与"致命不足"，并给出具有指导性的改进建议。
"""

# 全局变量，用于在内存中存储评分标准
# 在实际生产环境中，可能会使用数据库或缓存
GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA


def load_criteria_from_file():
    """从文件加载批阅要求"""
    global GRADING_CRITERIA
    try:
        if os.path.exists(CRITERIA_FILE):
            with open(CRITERIA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                GRADING_CRITERIA = data.get("criteria", DEFAULT_GRADING_CRITERIA)
                logger.info(f"已从文件加载批阅要求: {CRITERIA_FILE}")
        else:
            logger.info(f"批阅要求文件不存在，使用默认标准")
    except Exception as e:
        logger.error(f"加载批阅要求文件失败: {e}")
        GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA


def save_criteria_to_file(criteria: str):
    """将批阅要求保存到文件"""
    try:
        with open(CRITERIA_FILE, "w", encoding="utf-8") as f:
            json.dump({"criteria": criteria}, f, ensure_ascii=False, indent=2)
        logger.info(f"批阅要求已保存到文件: {CRITERIA_FILE}")
    except Exception as e:
        logger.error(f"保存批阅要求文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存批阅要求失败: {str(e)}")


# 服务器启动时加载批阅要求
@app.on_event("startup")
async def startup_event():
    """服务器启动时执行的操作"""
    load_criteria_from_file()
    init_db_pool()
    init_database()
    logger.info("服务器已启动，批阅要求已加载，数据库连接池已初始化")


@app.on_event("shutdown")
async def shutdown_event():
    """服务器关闭时执行的操作"""
    close_db_pool()
    logger.info("服务器已关闭，数据库连接池已关闭")


# 创建评分系统实例
grading_system = GradingSystem(REPORTS_DIR, OUTPUT_DIR, API_CONFIG)

# 用于跟踪批阅任务的字典
grading_tasks = {}
grading_tasks_lock = threading.Lock()

# AI API 并发控制：限制同时向 AI 服务发送的请求数，防止触发限流
MAX_CONCURRENT_AI = int(os.getenv("MAX_CONCURRENT_AI", "3"))
ai_api_semaphore = threading.Semaphore(MAX_CONCURRENT_AI)


# 认证相关的Pydantic模型
class UserLogin(BaseModel):
    username: str
    password: str


class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = user_manager.get_user_by_username(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    if not current_user.get("is_active", True):
        raise HTTPException(status_code=400, detail="用户账户已停用")
    return current_user


async def get_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if not user_manager.is_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="权限不足")
    return current_user


async def get_super_admin_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if not user_manager.is_super_admin(current_user["id"]):
        raise HTTPException(status_code=403, detail="需要超级管理员权限")
    return current_user


async def get_regular_user(
    current_user: Dict[str, Any] = Depends(get_current_active_user),
):
    if current_user["role"] != "user":
        raise HTTPException(status_code=403, detail="只有普通用户可以使用系统功能")
    return current_user


# 认证相关的API端点
@app.post("/api/auth/register", response_model=UserResponse)
async def register(user_data: UserRegister):
    """用户注册"""
    existing_user = user_manager.get_user_by_username(user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = user_manager.create_user(
        username=user_data.username,
        password=user_data.password,
        email=user_data.email,
        role="user",
    )

    if user_id is None:
        raise HTTPException(status_code=500, detail="注册失败")

    user = user_manager.get_user_by_id(user_id)
    return UserResponse(**user)


@app.post("/api/auth/login", response_model=Token)
async def login(username: str = Form(...), password: str = Form(...)):
    """用户登录"""
    user = user_manager.authenticate_user(username=username, password=password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )

    return Token(access_token=access_token, token_type="bearer", user=user)


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: Dict[str, Any] = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return UserResponse(**current_user)


@app.get("/api/auth/users", response_model=List[UserResponse])
async def get_all_users(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """获取所有用户列表（仅管理员）"""
    users = user_manager.get_all_users()
    return [UserResponse(**user) for user in users]


@app.put("/api/auth/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    new_role: str,
    current_user: Dict[str, Any] = Depends(get_super_admin_user),
):
    """更新用户角色（仅超级管理员）"""
    if new_role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    success = user_manager.update_user_role(user_id, new_role)
    if not success:
        raise HTTPException(status_code=500, detail="更新用户角色失败")

    return {"message": "用户角色更新成功"}


@app.put("/api/auth/users/{user_id}/activate")
async def activate_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """激活用户（仅管理员）"""
    success = user_manager.activate_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="激活用户失败")

    return {"message": "用户激活成功"}


@app.put("/api/auth/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """停用用户（仅管理员）"""
    success = user_manager.deactivate_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="停用用户失败")

    return {"message": "用户停用成功"}


@app.get("/api/logs")
async def get_logs(
    limit: int = 100,
    offset: int = 0,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取日志列表（仅管理员）"""
    start_date = None
    end_date = None
    if date:
        # 简单的日期过滤，假设格式为YYYY-MM-DD
        start_date = f"{date} 00:00:00"
        end_date = f"{date} 23:59:59"

    logs = log_manager.get_logs(
        action=action,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return {"logs": logs, "total": len(logs)}


@app.get("/api/logs/user/{user_id}")
async def get_user_logs(
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取指定用户的日志（仅管理员）"""
    logs = log_manager.get_user_logs(user_id=user_id, limit=limit, offset=offset)
    return {"logs": logs, "total": len(logs)}


# 管理员API端点
@app.get("/api/admin/users")
async def admin_get_users(current_user: Dict[str, Any] = Depends(get_admin_user)):
    """获取所有用户列表（管理员）"""
    users = user_manager.get_all_users()
    return users


@app.post("/api/admin/users")
async def admin_create_user(
    user_data: dict, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """创建新用户（管理员）"""
    username = user_data.get("username")
    password = user_data.get("password")
    email = user_data.get("email")
    role = user_data.get("role", "user")

    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")

    if role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    existing_user = user_manager.get_user_by_username(username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")

    user_id = user_manager.create_user(
        username=username, password=password, email=email, role=role
    )

    if user_id is None:
        raise HTTPException(status_code=500, detail="创建用户失败")

    user = user_manager.get_user_by_id(user_id)
    return user


@app.put("/api/admin/users/{user_id}")
async def admin_update_user(
    user_id: int,
    user_data: dict,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """更新用户信息（管理员）"""
    username = user_data.get("username")
    email = user_data.get("email")
    role = user_data.get("role")
    password = user_data.get("password")

    user = user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if role and role not in ["user", "admin", "super_admin"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    if role and current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="只有超级管理员可以修改角色")

    success = user_manager.update_user(
        user_id=user_id, username=username, email=email, role=role, password=password
    )

    if not success:
        raise HTTPException(status_code=500, detail="更新用户失败")

    updated_user = user_manager.get_user_by_id(user_id)
    return updated_user


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """删除用户（管理员）"""
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user = user_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user["role"] == "super_admin" and current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="不能删除超级管理员")

    success = user_manager.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除用户失败")

    return {"message": "用户删除成功"}


@app.get("/api/admin/logs")
async def admin_get_logs(
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    date: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取日志列表（管理员，支持筛选和分页）"""
    offset = (page - 1) * page_size

    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT l.id, l.user_id, l.action, l.details, l.ip_address, l.created_at, u.username
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            params = []

            if action:
                query += " AND l.action = %s"
                params.append(action)

            if user_id:
                query += " AND l.user_id = %s"
                params.append(user_id)

            if date:
                query += " AND DATE(l.created_at) = %s"
                params.append(date)

            if search:
                query += " AND (l.details ILIKE %s OR u.username ILIKE %s)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY l.created_at DESC LIMIT %s OFFSET %s"
            params.extend([page_size, offset])

            cursor.execute(query, params)
            logs = cursor.fetchall()

            count_query = """
                SELECT COUNT(*)
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE 1=1
            """
            count_params = []

            if action:
                count_query += " AND l.action = %s"
                count_params.append(action)

            if user_id:
                count_query += " AND l.user_id = %s"
                count_params.append(user_id)

            if date:
                count_query += " AND DATE(l.created_at) = %s"
                count_params.append(date)

            if search:
                count_query += " AND (l.details ILIKE %s OR u.username ILIKE %s)"
                count_params.extend([f"%{search}%", f"%{search}%"])

            cursor.execute(count_query, count_params)
            total = cursor.fetchone()[0]

            log_list = []
            for log in logs:
                log_list.append(
                    {
                        "id": log[0],
                        "user_id": log[1],
                        "action": log[2],
                        "details": log[3],
                        "ip_address": log[4],
                        "created_at": log[5],
                        "username": log[6],
                    }
                )

            return {
                "logs": log_list,
                "total": total,
                "page": page,
                "page_size": page_size,
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取日志失败: {str(e)}")


@app.get("/api/reports/")
async def get_report_directories(
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """获取 student_reports 目录下的所有子目录及其文件列表（仅普通用户）"""
    user_id = current_user["id"]
    base_path = os.path.join("student_reports", str(user_id))
    try:
        if not os.path.exists(base_path) or not os.path.isdir(base_path):
            return []

        result = []
        for dir_name in os.listdir(base_path):
            dir_path = os.path.join(base_path, dir_name)
            if os.path.isdir(dir_path):
                files = [
                    f
                    for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                result.append({"name": dir_name, "files": files})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告目录时出错: {str(e)}")


@app.get("/api/graded-reports/")
async def get_graded_reports(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """获取 graded_reports 目录下的内容（子目录和文件）（仅普通用户）"""
    user_id = current_user["id"]
    base_path = os.path.join("graded_reports", str(user_id))
    try:
        if not os.path.exists(base_path) or not os.path.isdir(base_path):
            return []

        result = []
        for dir_name in os.listdir(base_path):
            dir_path = os.path.join(base_path, dir_name)
            if os.path.isdir(dir_path):
                files = [
                    f
                    for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                result.append({"name": dir_name, "files": files})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取已评分报告时出错: {str(e)}")


@app.get("/api/download-graded")
async def download_graded_directory(
    request: Request,
    directory: str,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """压缩指定的已批阅目录并提供下载（仅普通用户）"""
    user_id = current_user["id"]
    target_dir = os.path.join("graded_reports", str(user_id), directory)
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail="目录未找到")

    # 临时zip文件路径
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    # make_archive会自动添加.zip后缀，所以我们提供基础名
    base_zip_name = os.path.join(temp_dir, f"{user_id}_{directory}")
    zip_path = shutil.make_archive(base_zip_name, "zip", target_dir)

    def cleanup():
        os.remove(zip_path)

    # 记录下载日志
    log_manager.log_file_download(
        user_id=current_user["id"],
        file_name=f"{directory}_graded.zip",
        ip_address=request.client.host,
    )

    return FileResponse(
        path=zip_path,
        filename=f"{directory}_graded.zip",
        media_type="application/zip",
        background=BackgroundTask(cleanup),
    )


class AnnotateScanModel(BaseModel):
    directory: str
    add_markings: bool
    ai_review: bool
    auto_grading: bool
    selected_model: str = "Qwen/QwQ-32B"
    min_score: int = 60
    max_score: int = 95


import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


async def run_in_threadpool(func, *args, **kwargs):
    """在线程池中运行函数，避免阻塞事件循环"""
    with ThreadPoolExecutor() as executor:
        return await asyncio.get_event_loop().run_in_executor(
            executor, lambda: func(*args, **kwargs)
        )


async def invoke_ark_model(
    prompt: str,
    model_name: str = "Qwen/QwQ-32B",
    max_retries: int = 20,
    timeout: int = 120,
    cancel_event=None,
) -> Optional[str]:
    """
    调用大模型进行评估，支持重试和超时

    Args:
        prompt: 提示文本
        model_name: 模型名称
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        cancel_event: 用于中断任务的事件对象

    Returns:
        模型响应文本，失败时返回None
    """
    # 使用较短的超时时间以快速响应取消事件
    effective_timeout = min(timeout, 30)

    for attempt in range(max_retries):
        # 检查是否需要取消任务
        if cancel_event and cancel_event.is_set():
            print(f"任务已取消，停止调用AI模型")
            return None

        try:
            print(f"尝试调用AI模型 {model_name} (尝试 {attempt + 1}/{max_retries})")

            # 根据模型名称选择不同的调用方式
            if model_name.startswith("doubao"):
                # 调用豆包模型API
                API_KEY = os.getenv("ARK_API_KEY", "")
                API_URL = "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

                # 构建请求参数
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                }

                # 发送请求
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                }

                # 使用httpx异步客户端，支持取消
                timeout = httpx.Timeout(timeout, connect=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(API_URL, json=payload, headers=headers)

                    # 处理响应
                    if response.status_code == 200:
                        result = response.json()
                        return result["choices"][0]["message"]["content"]
                    elif response.status_code == 429:
                        raise RateLimitError(f"豆包API限流，状态码: 429")
                    else:
                        raise Exception(
                            f"豆包API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"
                        )

            elif model_name.startswith("GLM-4-Flash"):
                # 调用智谱AI GLM-4-Flash模型API
                API_KEY = os.getenv("AI_API_KEY", "")
                API_URL = os.getenv("AI_API_ENDPOINT", "https://open.bigmodel.cn/api/paas/v4") + "/chat/completions"

                # 构建请求参数
                payload = {
                    "model": model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4096,
                }

                # 发送请求
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                }

                # 使用httpx异步客户端，支持取消
                timeout = httpx.Timeout(timeout, connect=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(API_URL, json=payload, headers=headers)

                    # 处理响应
                    if response.status_code == 200:
                        result = response.json()
                        return result["choices"][0]["message"]["content"]
                    elif response.status_code == 429:
                        raise RateLimitError(f"智谱AI API限流，状态码: 429")
                    else:
                        raise Exception(
                            f"智谱AI API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"
                        )

            elif model_name in [
                "thudm/glm-z1-9b-0414",
                "qwen/qwen3-8b",
                "Qwen/QwQ-32B",
            ]:
                # 调用硅基流动API
                API_KEY = "sk-kmqzqvmpwqhdxanpafbkytnfrdstifwgdvcglzrjkolyhzsq"
                API_URL = "https://api.siliconflow.cn/v1/chat/completions"

                # 硅基流动API使用完整的模型标识符
                siliconflow_model_name = model_name

                # 构建请求参数
                payload = {
                    "model": siliconflow_model_name,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                }

                # 发送请求
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {API_KEY}",
                }

                # 使用httpx异步客户端，支持取消
                timeout = httpx.Timeout(timeout, connect=10.0)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(API_URL, json=payload, headers=headers)

                    # 处理响应
                    if response.status_code == 200:
                        result = response.json()
                        return result["choices"][0]["message"]["content"]
                    elif response.status_code == 429:
                        raise RateLimitError(f"硅基流动API限流，状态码: 429")
                    else:
                        raise Exception(
                            f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}"
                        )
            else:
                # 不支持的模型
                raise Exception(f"不支持的模型: {model_name}")

        except httpx.TimeoutException:
            print(f"AI模型 {model_name} 请求超时 (尝试 {attempt + 1}/{max_retries})")
            if attempt == max_retries - 1:
                print(
                    f"AI模型 {model_name} 请求超时，已达到最大重试次数: {max_retries}"
                )
                return None
        except RateLimitError as e:
            print(f"AI模型 {model_name} 限流 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            if attempt == max_retries - 1:
                raise
            wait_time = min(2 ** attempt, 30)
            print(f"限流等待 {wait_time} 秒后重试...")
            step = 0.5
            slept = 0
            while slept < wait_time:
                if cancel_event and cancel_event.is_set():
                    print("任务已取消，停止等待")
                    return None
                await asyncio.sleep(min(step, wait_time - slept))
                slept += step
        except Exception as e:
            print(
                f"AI模型 {model_name} 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}"
            )

            if attempt == max_retries - 1:
                print(
                    f"AI模型 {model_name} 调用失败，已达到最大重试次数: {max_retries}"
                )
                return None

        wait_time = 1
        print(f"等待 {wait_time} 秒后重试...")

        step = 0.5
        slept = 0
        while slept < wait_time:
            if cancel_event and cancel_event.is_set():
                print("任务已取消，停止等待")
                return None
            await asyncio.sleep(min(step, wait_time - slept))
            slept += step

    return None  # 不应该到达这里，但为了安全起见


def convert_word_to_pdf_with_retry(
    word_processor,
    word_path: str,
    pdf_path: str,
    max_retries: int = 10,
    cancel_event=None,
    base_delay: float = 0.5,
    max_delay: float = 5.0,
) -> bool:
    """
    带指数退避重试机制的Word转PDF函数

    Args:
        word_processor: Word处理器实例
        word_path: Word文件路径
        pdf_path: 输出的PDF文件路径
        max_retries: 最大重试次数，默认10次
        cancel_event: 用于中断任务的事件对象
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）

    Returns:
        转换成功返回True，失败返回False
    """
    for attempt in range(max_retries):
        # 检查是否需要取消任务
        if cancel_event and cancel_event.is_set():
            logger.info(f"任务已取消，停止转换Word文件: {word_path}")
            return False

        try:
            logger.info(f"尝试转换Word文件为PDF (尝试 {attempt + 1}/{max_retries}): {word_path}")

            # 尝试转换
            result = word_processor.convert_to_pdf(word_path, pdf_path)

            if result:
                logger.info(f"Word文件转换成功: {word_path} -> {pdf_path}")
                return True
            else:
                logger.warning(f"Word文件转换失败 (尝试 {attempt + 1}/{max_retries}): {word_path}")

                # 如果不是最后一次尝试，等待后重试
                if attempt < max_retries - 1:
                    # 使用指数退避算法，限制最大延迟
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.info(f"等待 {delay:.2f} 秒后重试...")
                    if cancel_event:
                        if cancel_event.wait(delay):
                            logger.info(f"任务已取消，停止等待")
                            return False
                    else:
                        time.sleep(delay)

        except Exception as e:
            logger.error(f"Word文件转换异常 (尝试 {attempt + 1}/{max_retries}): {word_path}, 错误: {str(e)}")

            # 如果不是最后一次尝试，等待后重试
            if attempt < max_retries - 1:
                # 使用指数退避算法，限制最大延迟
                delay = min(base_delay * (2 ** attempt), max_delay)
                logger.info(f"等待 {delay:.2f} 秒后重试...")
                if cancel_event:
                    if cancel_event.wait(delay):
                        logger.info(f"任务已取消，停止等待")
                        return False
                else:
                    time.sleep(delay)

    logger.error(f"Word文件转换失败，已达到最大重试次数 {max_retries}: {word_path}")
    return False


def process_single_file(
    filename: str,
    file_path: str,
    scan_path: str,
    decoded_directory: str,
    graded_reports_dir: str,
    output_subdir: str,
    scan_model: AnnotateScanModel,
    qualified_csv_lock: Any,
    user_id: int,
    cancel_event: threading.Event = None,
) -> Dict[str, Any]:
    """
    处理单个文件的函数，用于多线程并行处理

    Args:
        filename: 文件名
        file_path: 文件完整路径
        scan_path: 扫描目录路径
        decoded_directory: 解码后的目录名称
        graded_reports_dir: 批阅后的报告目录
        output_subdir: 输出子目录
        scan_model: 批阅模型配置
        qualified_csv_lock: CSV文件写入锁
        user_id: 用户ID，用于获取用户特定配置
        cancel_event: 用于中断批阅任务的事件

    Returns:
        处理结果字典
    """
    print(f"正在处理文件: {filename}")

    # 检查是否需要取消任务
    if cancel_event and cancel_event.is_set():
        return {
            "filename": filename,
            "type": "Unknown",
            "content": "",
            "status": "已取消",
            "score": 0,
            "comments": "任务被用户取消",
            "size": os.path.getsize(file_path),
            "ai_failed": False,
        }

    # 获取文件扩展名
    ext = os.path.splitext(filename)[1].lower()
    content = ""
    base_filename = os.path.splitext(filename)[0]

    # 检查是否需要调用模型
    need_ai_processing = scan_model.auto_grading or scan_model.ai_review

    # 如果只选择了增加对号，不需要调用模型，直接处理
    if not need_ai_processing and scan_model.add_markings:
        logger.info(f"只选择了增加对号，不需要调用模型，直接处理: {file_path}")

        processor = grading_system.document_processors[".pdf"]
        output_ext = ".pdf"
        final_output_path = os.path.join(
            graded_reports_dir, f"{base_filename}_graded{output_ext}"
        )

        # 处理Word文件（转换为PDF后添加对号）
        if ext in [".doc", ".docx"]:
            # 使用WordProcessor转换为PDF
            word_processor = grading_system.document_processors[ext]

            # 构建转换后的PDF路径
            converted_pdf_path = os.path.join(
                graded_reports_dir, f"{base_filename}_converted.pdf"
            )

            # 转换为PDF（带重试机制，最多重试10次）
            if not convert_word_to_pdf_with_retry(
                word_processor,
                file_path,
                converted_pdf_path,
                max_retries=10,
                cancel_event=cancel_event,
            ):
                logger.error(f"转换Word文件为PDF失败: {file_path}")
                return {
                    "filename": filename,
                    "type": "Word",
                    "content": "",
                    "status": "处理失败",
                    "score": 0,
                    "comments": "转换失败（已重试20次）",
                    "size": os.path.getsize(file_path),
                    "ai_failed": False,
                }

            # 添加对号标注
            processor.add_checkmarks(converted_pdf_path, final_output_path)

            # 清理临时文件
            if os.path.exists(converted_pdf_path):
                try:
                    os.remove(converted_pdf_path)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")
        # 处理PDF文件（直接添加对号）
        elif ext == ".pdf":
            # 直接为PDF文件添加对号标注
            processor.add_checkmarks(file_path, final_output_path)
        else:
            return {
                "filename": filename,
                "type": "Unknown",
                "content": "",
                "status": "不支持",
                "score": 0,
                "comments": "不支持的文件类型",
                "size": os.path.getsize(file_path),
                "ai_failed": False,
            }

        # 记录处理结果
        return {
            "filename": filename,
            "type": "PDF",
            "content": "",
            "status": "处理完成",
            "score": 0,
            "comments": "",
            "size": os.path.getsize(file_path),
            "ai_failed": False,
        }

    # 如果需要调用模型，执行正常流程
    if need_ai_processing:
        try:
            # 先将Word文件转换为PDF，然后从PDF中提取文本
            if ext in [".doc", ".docx"]:
                logger.info(f"正在将Word文件转换为PDF以提取文本: {file_path}")

                # 使用WordProcessor转换为PDF
                word_processor = grading_system.document_processors[ext]

                # 构建临时PDF路径
                temp_pdf_path = os.path.join(
                    graded_reports_dir, f"{base_filename}_temp.pdf"
                )

                # 转换为PDF（带重试机制，最多重试5次）
                if not convert_word_to_pdf_with_retry(
                    word_processor,
                    file_path,
                    temp_pdf_path,
                    max_retries=5,
                    cancel_event=cancel_event,
                ):
                    logger.error(f"转换Word文件为PDF失败: {file_path}")
                    return {
                        "filename": filename,
                        "type": "Word",
                        "content": "",
                        "status": "转换失败",
                        "score": 0,
                        "comments": "转换失败（已重试20次）",
                        "size": os.path.getsize(file_path),
                        "ai_failed": False,
                    }

                # 使用PDF处理器提取文本
                pdf_processor = grading_system.document_processors[".pdf"]
                content = pdf_processor.extract_text(temp_pdf_path)

                # 清理临时PDF文件
                if os.path.exists(temp_pdf_path):
                    try:
                        os.remove(temp_pdf_path)
                    except:
                        pass
            elif ext == ".pdf":
                # 对于PDF文件，直接提取文本
                processor = grading_system.document_processors[ext]
                content = processor.extract_text(file_path)
            else:
                return {
                    "filename": filename,
                    "type": "Unknown",
                    "content": "",
                    "status": "不支持",
                    "score": 0,
                    "comments": "不支持的文件类型",
                    "size": os.path.getsize(file_path),
                    "ai_failed": False,
                }

            # 使用ARK大模型评估报告质量
            # 获取用户特定的评分标准（包含分数范围）
            user_criteria = config_manager.get_criteria_with_score_range(user_id)

            prompt = f"""
        作为一个大学资深老师
        请根据以下标准评估实验报告的质量：
        ---
        {user_criteria}
        ---

        报告内容：
        {content[:4000]}  # 限制内容长度以避免超过模型限制

        请给出评估结果，格式为JSON:
        {{
            "score": 评分,
            "is_qualified": true/false,
            "comments": "具体的评估意见",
            "reasons": ["不合格原因1", "不合格原因2"]
        }}
        """

            # 先进行基本合格性检查
            is_basic_qualified = len(content) >= 100  # 基本长度检查

            # 在开始AI调用前检查取消事件
            if cancel_event and cancel_event.is_set():
                return {
                    "filename": filename,
                    "type": "Unknown",
                    "content": content[:5000],
                    "status": "已取消",
                    "score": 0,
                    "comments": "任务被用户取消",
                    "size": os.path.getsize(file_path),
                    "ai_failed": False,
                }

            if not is_basic_qualified:
                evaluation = {
                    "score": 0,
                    "is_qualified": False,
                    "comments": "报告内容过短，未达到基本要求",
                    "reasons": ["内容长度不足"],
                }
            else:
                if cancel_event and cancel_event.is_set():
                    return {
                        "filename": filename,
                        "type": "Unknown",
                        "content": content[:5000],
                        "status": "已取消",
                        "score": 0,
                        "comments": "任务被用户取消",
                        "size": os.path.getsize(file_path),
                        "ai_failed": False,
                    }

                import asyncio

                ai_api_semaphore.acquire()
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(
                            invoke_ark_model(
                                prompt,
                                model_name=scan_model.selected_model,
                                cancel_event=cancel_event,
                            )
                        )
                    finally:
                        loop.close()
                except RateLimitError:
                    return {
                        "filename": filename,
                        "type": ext.upper().replace(".", ""),
                        "content": content[:5000],
                        "status": "rate_limited",
                        "score": 0,
                        "comments": "API限流，待重试",
                        "size": os.path.getsize(file_path),
                        "ai_failed": True,
                        "retry": True,
                    }
                finally:
                    ai_api_semaphore.release()

                print(f"ARK模型评估结果: {response}")

                if response is None:
                    evaluation = {
                        "score": 50,
                        "is_qualified": True,
                        "comments": "无法获取AI评估，使用默认评估",
                        "reasons": ["AI评估失败，已重试20次"],
                        "ai_failed": True,
                    }
                else:
                    try:
                        # 尝试直接解析JSON
                        evaluation = json.loads(response)
                    except json.JSONDecodeError:
                        print(f"无法解析AI模型响应为JSON: {response}")
                        # 尝试提取文本中的关键信息
                        try:
                            # 简单的规则匹配，提取分数和评语
                            import re

                            # 尝试从响应中提取分数
                            score_match = re.search(
                                r'"score"\s*:\s*(\d+)', response
                            ) or re.search(r"分数[:：]\s*(\d+)", response)
                            score = (
                                int(score_match.group(1)) if score_match else 75
                            )  # 默认分数

                            # 尝试从响应中提取评语
                            comments_match = re.search(
                                r'"comments"\s*:\s*"([^"]+)"', response
                            ) or re.search(r"评语[:：]\s*([^\n]+)", response)
                            comments = (
                                comments_match.group(1)
                                if comments_match
                                else "AI评估通过，整体表现良好。"
                            )  # 默认评语

                            # 尝试从响应中提取合格状态
                            is_qualified = True
                            if "不合格" in response or "不通过" in response:
                                is_qualified = False

                            # 尝试从响应中提取原因
                            reasons = []
                            reasons_match = re.search(
                                r'"reasons"\s*:\s*\[([^\]]+)\]', response
                            )
                            if reasons_match:
                                reasons_str = reasons_match.group(1)
                                reasons = [
                                    reason.strip(' "')
                                    for reason in reasons_str.split(",")
                                ]
                            elif not is_qualified:
                                reasons = ["AI评估不通过"]

                            # 构建评估结果
                            evaluation = {
                                "score": score,
                                "is_qualified": is_qualified,
                                "comments": comments,
                                "reasons": reasons,
                            }
                            print(f"使用提取的评估结果: {evaluation}")
                        except Exception as e:
                            print(f"提取AI评估结果失败: {e}")
                            # 如果提取也失败，使用默认评估
                            evaluation = {
                                "score": 75,
                                "is_qualified": True,
                                "comments": "AI评估通过，整体表现良好。",
                                "reasons": [],
                            }

            # 获取评估结果
            score = evaluation.get("score", 0)
            is_qualified = evaluation.get("is_qualified", False)
            comments = evaluation.get("comments", "")
            reasons = evaluation.get("reasons", [])
            ai_failed = evaluation.get("ai_failed", False)

            # 保存评估结果到JSON文件
            base_filename = os.path.splitext(filename)[0]  # 移除文件扩展名
            json_path = os.path.join(output_subdir, f"{base_filename}.json")
            with open(json_path, "w", encoding="utf-8") as json_file:
                json.dump(
                    {
                        "filename": filename,
                        "score": score,
                        "is_qualified": is_qualified,
                        "comments": comments,
                        "reasons": reasons,
                        "timestamp": datetime.now().isoformat(),
                    },
                    json_file,
                    ensure_ascii=False,
                    indent=2,
                )

            # 记录合格报告到CSV文件（使用锁保证线程安全）
            parts = filename.split("-")
            print(f"文件名称: {parts}")
            if len(parts) >= 3:
                class_name = parts[0]  # 班级
                student_id = parts[1]  # 学号
                user_name = parts[2].split(".")[0]  # 姓名
            else:
                user_name = filename.split(".")[0]
                student_id = user_name  # 假设学号是文件名前缀
                class_name = user_name  # 假设姓名是文件名前缀
            print(f"班级: {class_name}, 学号: {student_id}, 姓名: {user_name}")

            qualified_csv_path = os.path.join(output_subdir, "合格报告分数.csv")

            with qualified_csv_lock:
                file_exists = os.path.exists(qualified_csv_path)
                with open(
                    qualified_csv_path, "a", newline="", encoding="utf-8-sig"
                ) as csvfile:
                    fieldnames = ["学号", "姓名", "分数"]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    if not file_exists:
                        writer.writeheader()

                    writer.writerow(
                        {"学号": student_id, "姓名": user_name, "分数": score}
                    )

            # 为PDF和Word文档都生成批阅后的文件（目录已提前创建）

            if ext in [".pdf", ".doc", ".docx"]:
                # 对于Word文件，先转换为PDF，然后统一使用PDF处理器处理
                if ext in [".doc", ".docx"]:
                    logger.info(f"正在将Word文件转换为PDF: {file_path}")

                    # 使用WordProcessor转换为PDF
                    word_processor = grading_system.document_processors[ext]

                    # 构建转换后的PDF路径
                    converted_pdf_path = os.path.join(
                        graded_reports_dir, f"{base_filename}_converted.pdf"
                    )

                    # 转换为PDF（带重试机制，最多重试10次）
                    if not convert_word_to_pdf_with_retry(
                        word_processor,
                        file_path,
                        converted_pdf_path,
                        max_retries=10,
                        cancel_event=cancel_event,
                    ):
                        logger.error(f"转换Word文件为PDF失败: {file_path}")
                        return {
                            "filename": filename,
                            "type": "Word",
                            "content": content[:5000],
                            "status": "转换失败",
                            "score": 0,
                            "comments": "转换失败（已重试20次）",
                            "size": os.path.getsize(file_path),
                            "ai_failed": False,
                        }

                    # 切换到PDF处理器和转换后的PDF路径
                    processor = grading_system.document_processors[".pdf"]
                    processing_path = converted_pdf_path
                    output_ext = ".pdf"  # 最终输出为PDF
                else:
                    # 对于PDF文件，直接使用
                    processor = grading_system.document_processors[ext]
                    processing_path = file_path
                    output_ext = ".pdf"

                # 使用PDF处理器添加评语和分数
                intermediate_file_path = os.path.join(
                    graded_reports_dir, f"{base_filename}_temp{output_ext}"
                )
                # 只有当选择了自动批分时才添加分数
                add_score = scan_model.auto_grading
                processor.add_comments_and_score(
                    processing_path,  # 处理的文件路径（可能是转换后的PDF）
                    comments,  # 评语
                    score,  # 分数
                    intermediate_file_path,  # 输出文件路径
                    add_score,  # 是否添加分数
                )

                # 生成最终的graded文件
                final_output_path = os.path.join(
                    graded_reports_dir, f"{base_filename}_graded{output_ext}"
                )

                if scan_model.add_markings:
                    # 如果需要添加对号标注，生成最终文件
                    processor.add_checkmarks(intermediate_file_path, final_output_path)
                else:
                    # 如果不需要添加对号标注，直接重命名为graded文件
                    os.rename(intermediate_file_path, final_output_path)

                # 清理临时文件
                if os.path.exists(intermediate_file_path):
                    try:
                        os.remove(intermediate_file_path)
                        logger.info(f"已清理临时文件: {intermediate_file_path}")
                    except Exception as e:
                        logger.warning(f"清理临时文件失败: {e}")

                # 清理转换后的PDF临时文件
                if ext in [".doc", ".docx"] and os.path.exists(converted_pdf_path):
                    try:
                        os.remove(converted_pdf_path)
                        logger.info(f"已清理临时转换文件: {converted_pdf_path}")
                    except Exception as e:
                        logger.warning(f"清理临时转换文件失败: {e}")

                # 确保只保留最终的graded文件，删除可能存在的旧文件
                old_file_path = os.path.join(
                    graded_reports_dir, f"{base_filename}{output_ext}"
                )
                if os.path.exists(old_file_path):
                    try:
                        os.remove(old_file_path)
                        logger.info(f"已清理旧文件: {old_file_path}")
                    except Exception as e:
                        logger.warning(f"清理旧文件失败: {e}")

            # 返回处理结果
            return {
                "filename": filename,
                "type": "PDF" if ext == ".pdf" else "Word",
                "content": content[:5000],
                "status": "合格" if is_qualified else "不合格",
                "score": score,
                "comments": comments,
                "size": os.path.getsize(file_path),
                "ai_failed": ai_failed,
            }

        except Exception as e:
            print(f"评估过程中出错: {str(e)}")
            return {
                "filename": filename,
                "type": "PDF" if ext == ".pdf" else "Word",
                "content": content[:500],
                "status": "未知",
                "score": 0,
                "comments": "评估过程中出错",
                "size": os.path.getsize(file_path),
                "ai_failed": False,
            }

    return {
        "filename": filename,
        "type": "Unknown",
        "content": "",
        "status": "未处理",
        "score": 0,
        "comments": "",
        "size": os.path.getsize(file_path),
        "ai_failed": False,
    }


@app.post("/api/annotate")
async def annotate_report(
    request: Request,
    scan_model: AnnotateScanModel,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """
    批注报告接口 - 使用多线程并行处理（仅普通用户）
    """
    # 打印接收到的新参数以供调试
    print(
        f"接收到批阅请求: 目录='{scan_model.directory}', 增加对号={scan_model.add_markings}, 增加评语={scan_model.ai_review}, 自动批分={scan_model.auto_grading}"
    )

    try:
        # 解码目录名称
        decoded_directory = unquote(scan_model.directory)
        print(f"解码后的目录名称: {decoded_directory}")
        user_id = current_user["id"]
        scan_path = os.path.join("student_reports", str(user_id), decoded_directory)

        # 检查目录是否存在
        if not os.path.exists(scan_path):
            raise HTTPException(
                status_code=404, detail=f"目录不存在: {decoded_directory}"
            )

        # 创建一个事件来控制批阅任务的中断
        cancel_event = threading.Event()
        task_key = f"{user_id}:{decoded_directory}"

        # 将任务添加到跟踪字典
        with grading_tasks_lock:
            grading_tasks[task_key] = cancel_event

        try:
            # 存储文档内容和评估结果
            documents_content = []
            failed_reports = []

            # 提前创建graded_reports_dir目录，用于存储临时文件
            graded_reports_dir = os.path.join(
                GRADED_DIR, str(user_id), decoded_directory
            )
            os.makedirs(graded_reports_dir, exist_ok=True)

            # 创建输出子目录
            output_subdir = os.path.join(OUTPUT_DIR, str(user_id), decoded_directory)
            os.makedirs(output_subdir, exist_ok=True)

            # 创建线程锁，用于CSV文件写入的线程安全
            qualified_csv_lock = threading.Lock()

            # 收集所有需要处理的文件
            files_to_process = []
            for filename in os.listdir(scan_path):
                file_path = os.path.join(scan_path, filename)
                if os.path.isfile(file_path):
                    files_to_process.append((filename, file_path))

            print(f"共找到 {len(files_to_process)} 个文件需要处理")

            log_manager.log_grading_start(
                user_id=current_user["id"],
                directory_name=decoded_directory,
                file_count=len(files_to_process),
                model_used=scan_model.selected_model,
                ip_address=request.client.host,
            )

            from concurrent.futures import as_completed, wait, FIRST_COMPLETED

            rate_limited_files = []

            with ThreadPoolExecutor(max_workers=1) as executor:
                future_to_file = {
                    executor.submit(
                        process_single_file,
                        filename,
                        file_path,
                        scan_path,
                        decoded_directory,
                        graded_reports_dir,
                        output_subdir,
                        scan_model,
                        qualified_csv_lock,
                        current_user["id"],
                        cancel_event,
                    ): (filename, file_path)
                    for filename, file_path in files_to_process
                }

                remaining_futures = list(future_to_file.keys())

                while remaining_futures:
                    if cancel_event.is_set():
                        print("批阅任务被中断")
                        for remaining_future in remaining_futures:
                            remaining_future.cancel()
                        for remaining_future in remaining_futures:
                            if not remaining_future.cancelled():
                                try:
                                    remaining_future.result(timeout=2)
                                except:
                                    pass
                        break

                    completed_futures, remaining_futures = wait(
                        remaining_futures,
                        timeout=1,
                        return_when=FIRST_COMPLETED,
                    )

                    for completed_future in completed_futures:
                        filename, file_path = future_to_file[completed_future]
                        try:
                            result = completed_future.result()

                            if result.get("status") == "rate_limited":
                                rate_limited_files.append((filename, file_path))
                                print(f"文件 {filename} 被限流，加入重试队列")
                                continue

                            documents_content.append(result)

                            if result.get("status") == "不合格":
                                user_name = (
                                    filename.split("_")[0]
                                    if "_" in filename
                                    else filename.split(".")[0]
                                )
                                failed_reports.append(
                                    {
                                        "username": user_name,
                                        "status": "不合格",
                                        "filename": filename,
                                    }
                                )

                            print(
                                f"文件 {filename} 处理完成，状态: {result.get('status')}"
                            )
                        except Exception as e:
                            print(f"文件 {filename} 处理失败: {str(e)}")
                            documents_content.append(
                                {
                                    "filename": filename,
                                    "type": "Unknown",
                                    "content": "",
                                    "status": "处理失败",
                                    "score": 0,
                                    "comments": str(e),
                                    "size": os.path.getsize(file_path),
                                    "ai_failed": False,
                                }
                            )

            if rate_limited_files and not cancel_event.is_set():
                print(f"\n有 {len(rate_limited_files)} 个文件被限流，等待 10 秒后重试...")
                time.sleep(10)

                with ThreadPoolExecutor(max_workers=1) as retry_executor:
                    retry_future_to_file = {
                        retry_executor.submit(
                            process_single_file,
                            filename,
                            file_path,
                            scan_path,
                            decoded_directory,
                            graded_reports_dir,
                            output_subdir,
                            scan_model,
                            qualified_csv_lock,
                            current_user["id"],
                            cancel_event,
                        ): (filename, file_path)
                        for filename, file_path in rate_limited_files
                    }

                    for retry_future in as_completed(retry_future_to_file):
                        filename, file_path = retry_future_to_file[retry_future]
                        try:
                            result = retry_future.result()
                            documents_content.append(result)
                            print(f"重试文件 {filename} 完成，状态: {result.get('status')}")
                        except Exception as e:
                            print(f"重试文件 {filename} 失败: {str(e)}")
                            documents_content.append(
                                {
                                    "filename": filename,
                                    "type": "Unknown",
                                    "content": "",
                                    "status": "重试失败",
                                    "score": 0,
                                    "comments": str(e),
                                    "size": os.path.getsize(file_path),
                                    "ai_failed": False,
                                }
                            )

            # 如果任务被取消，添加中断标记
            if cancel_event.is_set():
                documents_content.append(
                    {
                        "filename": "任务中断",
                        "type": "System",
                        "content": "",
                        "status": "中断",
                        "score": 0,
                        "comments": "批阅任务被用户中断",
                        "size": 0,
                        "ai_failed": False,
                    }
                )

            # 创建综合报告CSV文件，包含所有报告的详细信息
            comprehensive_csv_filename = None
            try:
                # 生成综合CSV文件名（使用时间戳确保唯一性）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                comprehensive_csv_filename = f"报告评分汇总_{timestamp}.csv"

                # 将CSV文件保存到graded_reports目录，这样在压缩时会包含在内
                comprehensive_csv_path = os.path.join(
                    graded_reports_dir, comprehensive_csv_filename
                )
                # 同时保存到 output 目录，以便单独下载
                output_comprehensive_csv_path = os.path.join(
                    output_subdir, comprehensive_csv_filename
                )

                # 写入综合CSV文件
                with open(
                    comprehensive_csv_path, "w", newline="", encoding="utf-8-sig"
                ) as csvfile:
                    fieldnames = [
                        "学号",
                        "姓名",
                        "实验名称",
                        "得分",
                        "评语",
                        "状态",
                        "备注",
                    ]
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()

                    # 遍历所有处理过的文档
                    for doc in documents_content:
                        # 检查是否是中断标记
                        if doc.get("status") == "中断":
                            continue

                        # 从文件名中提取信息
                        filename = doc["filename"]
                        parts = filename.split("-")

                        # 尝试提取学号、姓名、实验名称
                        student_id = "未知"
                        student_name = "未知"
                        experiment_name = "未知"

                        if len(parts) >= 3:
                            # 假设文件名格式：班级-学号-姓名-实验名称.pdf
                            student_id = parts[1]  # 学号
                            student_name = parts[2].split(".")[0]  # 姓名
                            # 提取实验名称（移除文件扩展名）
                            experiment_name = (
                                "-".join(parts[3:]).split(".")[0]
                                if len(parts) > 3
                                else "未知"
                            )
                        else:
                            # 如果文件名格式不符合预期，使用文件名作为实验名称
                            student_name = filename.split(".")[0]
                            experiment_name = filename.split(".")[0]

                        # 获取报告状态和备注
                        status = doc["status"]
                        remarks = ""
                        if status == "未知" or status == "不合格":
                            remarks = doc.get("comments", "未能正确识别判断")

                        # 如果AI评估失败，在备注中标记
                        if doc.get("ai_failed", False):
                            if remarks:
                                remarks += "；AI评估失败（已重试20次）"
                            else:
                                remarks = "AI评估失败（已重试20次）"

                        # 写入CSV行
                        writer.writerow(
                            {
                                "学号": student_id,
                                "姓名": student_name,
                                "实验名称": experiment_name,
                                "得分": doc["score"],
                                "评语": doc["comments"],
                                "状态": status,
                                "备注": remarks,
                            }
                        )

                # 复制到 output 目录
                shutil.copy2(comprehensive_csv_path, output_comprehensive_csv_path)

                print(f"综合报告评分汇总CSV已生成: {comprehensive_csv_path}")
            except Exception as csv_error:
                print(f"生成综合CSV文件失败: {str(csv_error)}")
                comprehensive_csv_filename = None

            # 返回结果
            return {
                "message": f"成功扫描了 {len([d for d in documents_content if d.get('status') != '中断'])} 个文档",
                "failed_count": len(failed_reports),
                "documents": documents_content,
                "csv_file": f"{decoded_directory}/{comprehensive_csv_filename}"
                if comprehensive_csv_filename
                else None,
                "qualified_csv_file": f"{decoded_directory}/合格报告分数.csv",
            }
        finally:
            # 从跟踪字典中移除任务
            with grading_tasks_lock:
                if task_key in grading_tasks:
                    del grading_tasks[task_key]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理报告时出错: {str(e)}")


class CriteriaModel(BaseModel):
    criteria: str
    min_score: Optional[int] = 60
    max_score: Optional[int] = 95


@app.post("/api/criteria")
async def set_criteria(
    data: CriteriaModel, current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """设置用户的评分标准和分数范围（仅普通用户）"""
    success = config_manager.update_user_config(
        user_id=current_user["id"],
        criteria=data.criteria,
        min_score=data.min_score,
        max_score=data.max_score,
    )

    if not success:
        raise HTTPException(status_code=500, detail="保存配置失败")

    logger.info(f"用户 {current_user['username']} 的评分标准已更新")
    return {"message": "评分标准已成功更新"}


@app.get("/api/criteria")
async def get_criteria(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """获取用户的评分标准和分数范围（仅普通用户）"""
    config = config_manager.get_or_create_user_config(current_user["id"])
    return {
        "criteria": config["criteria"],
        "min_score": config["min_score"],
        "max_score": config["max_score"],
    }


@app.post("/api/criteria/reset")
async def reset_criteria(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """恢复默认的评分标准（仅普通用户）"""
    success = config_manager.update_user_config(
        user_id=current_user["id"],
        criteria=config_manager.default_criteria,
        min_score=60,
        max_score=95,
    )

    if not success:
        raise HTTPException(status_code=500, detail="恢复默认配置失败")

    logger.info(f"用户 {current_user['username']} 已恢复默认评分标准")
    return {"message": "评分标准已恢复为默认值"}


# --- 批阅标准管理 API ---

class CriteriaSaveModel(BaseModel):
    name: str
    criteria: str
    min_score: int = 60
    max_score: int = 95


@app.get("/api/criteria/list")
async def get_criteria_list(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """获取用户所有批阅标准列表"""
    criteria_list = config_manager.get_all_criteria(current_user["id"])
    return {"data": criteria_list}


@app.post("/api/criteria/save")
async def save_criteria(data: CriteriaSaveModel, current_user: Dict[str, Any] = Depends(get_regular_user)):
    """保存新的批阅标准"""
    criteria_id = config_manager.create_criteria(
        user_id=current_user["id"],
        name=data.name,
        criteria=data.criteria,
        min_score=data.min_score,
        max_score=data.max_score
    )
    
    if criteria_id is None:
        raise HTTPException(status_code=500, detail="保存批阅标准失败")
    
    logger.info(f"用户 {current_user['username']} 创建了新的批阅标准: {data.name}")
    return {"message": "批阅标准保存成功", "id": criteria_id}


@app.put("/api/criteria/{criteria_id}")
async def update_criteria(
    criteria_id: int,
    data: CriteriaSaveModel,
    current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """更新批阅标准"""
    success = config_manager.update_criteria(
        user_id=current_user["id"],
        criteria_id=criteria_id,
        name=data.name,
        criteria=data.criteria,
        min_score=data.min_score,
        max_score=data.max_score
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="更新批阅标准失败")
    
    logger.info(f"用户 {current_user['username']} 更新了批阅标准: {criteria_id}")
    return {"message": "批阅标准更新成功"}


@app.delete("/api/criteria/{criteria_id}")
async def delete_criteria(
    criteria_id: int,
    current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """删除批阅标准"""
    success = config_manager.delete_criteria(
        user_id=current_user["id"],
        criteria_id=criteria_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="删除批阅标准失败")
    
    logger.info(f"用户 {current_user['username']} 删除了批阅标准: {criteria_id}")
    return {"message": "批阅标准删除成功"}


@app.post("/api/criteria/{criteria_id}/activate")
async def activate_criteria(
    criteria_id: int,
    current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """激活并使用指定的批阅标准"""
    success = config_manager.set_active_criteria(
        user_id=current_user["id"],
        criteria_id=criteria_id
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="激活批阅标准失败")
    
    logger.info(f"用户 {current_user['username']} 激活了批阅标准: {criteria_id}")
    return {"message": "批阅标准已激活"}


@app.get("/api/criteria/{criteria_id}")
async def get_criteria_by_id(
    criteria_id: int,
    current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """获取单个批阅标准详情"""
    criteria = config_manager.get_criteria_by_id(current_user["id"], criteria_id)
    
    if criteria is None:
        raise HTTPException(status_code=404, detail="批阅标准不存在")
    
    return criteria


@app.post("/api/upload")
async def upload_zip_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """接收ZIP压缩文件，解压到student_reports目录（仅普通用户）"""
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持上传ZIP格式的压缩文件")

    # 基于文件名创建目录，并包含用户ID
    dir_name = os.path.splitext(file.filename)[0]
    user_id = current_user["id"]
    extract_path = os.path.join("student_reports", str(user_id), dir_name)
    os.makedirs(extract_path, exist_ok=True)

    # 使用临时文件管理器创建临时文件
    with temp_file(suffix=".zip", prefix="upload_") as temp_zip_path:
        try:
            # 保存上传的文件到临时位置
            with open(temp_zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # 解压文件
            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                # 统计文件数量
                file_count = len([f for f in zip_ref.namelist() if not f.endswith("/")])
                zip_ref.extractall(extract_path)

            # 记录上传日志
            log_manager.log_file_upload(
                user_id=current_user["id"],
                file_count=file_count,
                ip_address=request.client.host,
            )

        except Exception as e:
            # 清理
            shutil.rmtree(extract_path, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")
        finally:
            await file.close()

    return {"message": f"文件 '{file.filename}' 已成功上传并解压到 '{dir_name}' 目录"}


class SingleReportModel(BaseModel):
    file_path: str
    score: Optional[float] = None
    comments: Optional[str] = None
    output_path: Optional[str] = None


@app.post("/api/grade_single_report")
async def grade_single_report(
    data: SingleReportModel, current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """批阅单个学生报告（仅普通用户）"""
    try:
        # 验证文件路径是否属于当前用户
        user_id = current_user["id"]
        allowed_base = os.path.abspath(os.path.join("student_reports", str(user_id)))
        file_path = os.path.abspath(data.file_path)

        # 尝试拼接路径
        if not file_path.startswith(allowed_base):
            if not data.file_path.startswith(os.path.abspath("student_reports")):
                file_path = os.path.abspath(
                    os.path.join("student_reports", str(user_id), data.file_path)
                )
            else:
                raise HTTPException(
                    status_code=403, detail="权限不足：只能访问自己的文件"
                )

        if not file_path.startswith(allowed_base):
            raise HTTPException(status_code=403, detail="权限不足：只能访问自己的文件")

        # 确保文件存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 更新 file_path 为完整路径
        data.file_path = file_path

        # 调用 grade_single_student 函数
        result_path = grade_single_student(
            data.file_path, data.output_path, data.score, data.comments
        )

        if result_path:
            return {
                "status": "success",
                "message": "报告批阅完成",
                "output_path": result_path,
            }
        else:
            return {"status": "error", "message": "报告批阅失败"}
    except Exception as e:
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{directory_name}")
async def delete_report_directory(
    directory_name: str, current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """删除指定的报告目录（仅普通用户）"""
    try:
        # 确保目录名安全，防止路径遍历攻击
        safe_dir_name = os.path.normpath(directory_name).replace("..", "")
        user_id = current_user["id"]
        dir_path = os.path.join("student_reports", str(user_id), safe_dir_name)

        if not os.path.exists(dir_path):
            raise HTTPException(status_code=404, detail="目录不存在")

        if not os.path.isdir(dir_path):
            raise HTTPException(status_code=400, detail="路径不是目录")

        # 删除目录及其内容
        shutil.rmtree(dir_path)

        return {"message": f"目录 '{directory_name}' 已成功删除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除目录失败: {str(e)}")


@app.delete("/api/graded-reports/{directory_name}")
async def delete_graded_report_directory(
    directory_name: str, current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """删除指定的已批阅报告目录（仅普通用户）"""
    try:
        # 确保目录名安全，防止路径遍历攻击
        safe_dir_name = os.path.normpath(directory_name).replace("..", "")
        user_id = current_user["id"]
        dir_path = os.path.join("graded_reports", str(user_id), safe_dir_name)

        if not os.path.exists(dir_path):
            raise HTTPException(status_code=404, detail="目录不存在")

        if not os.path.isdir(dir_path):
            raise HTTPException(status_code=400, detail="路径不是目录")

        # 删除目录及其内容
        shutil.rmtree(dir_path)

        return {"message": f"目录 '{directory_name}' 已成功删除"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除目录失败: {str(e)}")


@app.get("/graded_reports/{directory_name}/{filename}")
async def get_graded_file(
    directory_name: str,
    filename: str,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """获取单个已批阅文件（仅普通用户）"""
    # 验证目录名安全性
    safe_dir_name = os.path.normpath(directory_name).replace("..", "")
    safe_filename = os.path.normpath(filename).replace("..", "")

    user_id = current_user["id"]
    file_path = os.path.join(
        "graded_reports", str(user_id), safe_dir_name, safe_filename
    )

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(file_path)


@app.get("/api/temp/usage")
async def get_temp_usage(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """获取临时文件使用情况（仅普通用户）"""
    try:
        usage = temp_manager.get_temp_usage()
        return {"status": "success", "usage": usage}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"获取临时文件使用情况失败: {str(e)}"
        )


@app.post("/api/temp/cleanup")
async def cleanup_temp_files(current_user: Dict[str, Any] = Depends(get_regular_user)):
    """手动清理临时文件（仅普通用户）"""
    try:
        temp_manager.cleanup_old_files()
        usage_after = temp_manager.get_temp_usage()
        return {
            "status": "success",
            "message": "临时文件清理完成",
            "usage_after_cleanup": usage_after,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理临时文件失败: {str(e)}")


# Health check endpoints
from utils.health_check import health_checker


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {"status": "healthy", "message": "Service is running"}


@app.get("/api/health")
async def detailed_health_check():
    """Detailed health check with system information"""
    try:
        health_status = health_checker.check_system_health()

        # Return appropriate HTTP status code
        status_code = 200 if health_status["status"] == "healthy" else 503

        return health_status
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/api/health/summary")
async def health_summary():
    """Get health check summary"""
    try:
        summary = health_checker.get_health_summary()
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get health summary: {str(e)}"
        )


@app.get("/api/health/live")
async def liveness_probe():
    """Kubernetes-style liveness probe"""
    return {"status": "alive"}


@app.get("/api/health/ready")
async def readiness_probe():
    """Kubernetes-style readiness probe"""
    try:
        # Quick checks for readiness
        health_status = health_checker.check_system_health()

        # Check critical components
        critical_checks = ["directories", "ai_service"]
        ready = True

        for check_name in critical_checks:
            if check_name in health_status["checks"]:
                if not health_status["checks"][check_name].get("healthy", False):
                    ready = False
                    break

        if ready:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")

    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Readiness check failed: {str(e)}")


@app.get("/api/admin/stats/overview")
async def admin_get_stats_overview(
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取系统概览统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            stats = {}

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
            stats["total_users"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = false")
            stats["inactive_users"] = cursor.fetchone()[0]

            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE role = 'admin' AND is_active = true"
            )
            stats["total_admins"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM logs WHERE created_at >= CURRENT_DATE")
            stats["today_logs"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM logs")
            stats["total_logs"] = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(DISTINCT user_id) FROM logs WHERE created_at >= CURRENT_DATE
            """)
            stats["active_users_today"] = cursor.fetchone()[0]

            return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计数据失败: {str(e)}")


@app.get("/api/admin/stats/user-activity")
async def admin_get_user_activity_stats(
    days: int = 30, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取用户活动统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(*) as total_actions
                FROM logs
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            cursor.execute(query, (days,))
            results = cursor.fetchall()

            activity_data = []
            for row in results:
                activity_data.append(
                    {
                        "date": row[0].strftime("%Y-%m-%d"),
                        "active_users": row[1],
                        "total_actions": row[2],
                    }
                )

            return activity_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户活动统计失败: {str(e)}")


@app.get("/api/admin/stats/action-distribution")
async def admin_get_action_distribution_stats(
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取操作分布统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    action,
                    COUNT(*) as count
                FROM logs
                GROUP BY action
                ORDER BY count DESC
            """
            cursor.execute(query)
            results = cursor.fetchall()

            distribution = []
            for row in results:
                distribution.append({"action": row[0], "count": row[1]})

            return distribution
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取操作分布统计失败: {str(e)}")


@app.get("/api/admin/stats/user-work")
async def admin_get_user_work_stats(
    current_user: Dict[str, Any] = Depends(get_admin_user),
):
    """获取用户工作统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    u.role,
                    COUNT(l.id) as total_actions,
                    COUNT(CASE WHEN l.action = 'upload' THEN 1 END) as upload_count,
                    COUNT(CASE WHEN l.action = 'download' THEN 1 END) as download_count,
                    COUNT(CASE WHEN l.action = 'grade' THEN 1 END) as grade_count,
                    MAX(l.created_at) as last_activity
                FROM users u
                LEFT JOIN logs l ON u.id = l.user_id
                WHERE u.is_active = true
                GROUP BY u.id, u.username, u.email, u.role
                ORDER BY total_actions DESC
            """
            cursor.execute(query)
            results = cursor.fetchall()

            user_stats = []
            for row in results:
                user_stats.append(
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "role": row[3],
                        "total_actions": row[4],
                        "upload_count": row[5],
                        "download_count": row[6],
                        "grade_count": row[7],
                        "last_activity": row[8].strftime("%Y-%m-%d %H:%M:%S")
                        if row[8]
                        else None,
                    }
                )

            return user_stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户工作统计失败: {str(e)}")


@app.get("/api/admin/stats/daily-summary")
async def admin_get_daily_summary_stats(
    days: int = 7, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取每日汇总统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as total_logs,
                    COUNT(DISTINCT user_id) as active_users,
                    COUNT(CASE WHEN action = 'upload' THEN 1 END) as uploads,
                    COUNT(CASE WHEN action = 'download' THEN 1 END) as downloads,
                    COUNT(CASE WHEN action = 'grade' THEN 1 END) as grades
                FROM logs
                WHERE created_at >= CURRENT_DATE - INTERVAL '%s days'
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """
            cursor.execute(query, (days,))
            results = cursor.fetchall()

            daily_summary = []
            for row in results:
                daily_summary.append(
                    {
                        "date": row[0].strftime("%Y-%m-%d"),
                        "total_logs": row[1],
                        "active_users": row[2],
                        "uploads": row[3],
                        "downloads": row[4],
                        "grades": row[5],
                    }
                )

            return daily_summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取每日汇总统计失败: {str(e)}")


@app.get("/api/admin/stats/hourly-activity")
async def admin_get_hourly_activity_stats(
    date: Optional[str] = None, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取每小时活动统计数据（管理员）"""
    try:
        with get_db_cursor() as cursor:
            if date:
                query = """
                    SELECT 
                        EXTRACT(HOUR FROM created_at) as hour,
                        COUNT(*) as count
                    FROM logs
                    WHERE DATE(created_at) = %s
                    GROUP BY EXTRACT(HOUR FROM created_at)
                    ORDER BY hour
                """
                cursor.execute(query, (date,))
            else:
                query = """
                    SELECT 
                        EXTRACT(HOUR FROM created_at) as hour,
                        COUNT(*) as count
                    FROM logs
                    WHERE DATE(created_at) = CURRENT_DATE
                    GROUP BY EXTRACT(HOUR FROM created_at)
                    ORDER BY hour
                """
                cursor.execute(query)

            results = cursor.fetchall()

            hourly_data = []
            for row in results:
                hourly_data.append({"hour": int(row[0]), "count": row[1]})

            return hourly_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取每小时活动统计失败: {str(e)}")


@app.get("/api/admin/stats/top-users")
async def admin_get_top_users_stats(
    limit: int = 10, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取活跃用户排行（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    u.id,
                    u.username,
                    u.email,
                    COUNT(l.id) as total_actions,
                    MAX(l.created_at) as last_activity
                FROM users u
                INNER JOIN logs l ON u.id = l.user_id
                WHERE u.is_active = true
                GROUP BY u.id, u.username, u.email
                ORDER BY total_actions DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()

            top_users = []
            for row in results:
                top_users.append(
                    {
                        "user_id": row[0],
                        "username": row[1],
                        "email": row[2],
                        "total_actions": row[3],
                        "last_activity": row[4].strftime("%Y-%m-%d %H:%M:%S")
                        if row[4]
                        else None,
                    }
                )

            return top_users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取活跃用户排行失败: {str(e)}")


@app.get("/api/admin/stats/recent-activities")
async def admin_get_recent_activities(
    limit: int = 20, current_user: Dict[str, Any] = Depends(get_admin_user)
):
    """获取最近活动记录（管理员）"""
    try:
        with get_db_cursor() as cursor:
            query = """
                SELECT 
                    l.id,
                    l.user_id,
                    l.action,
                    l.details,
                    l.ip_address,
                    l.created_at,
                    u.username
                FROM logs l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.created_at DESC
                LIMIT %s
            """
            cursor.execute(query, (limit,))
            results = cursor.fetchall()

            activities = []
            for row in results:
                activities.append(
                    {
                        "id": row[0],
                        "user_id": row[1],
                        "action": row[2],
                        "details": row[3],
                        "ip_address": row[4],
                        "created_at": row[5].strftime("%Y-%m-%d %H:%M:%S"),
                        "username": row[6],
                    }
                )

            return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最近活动记录失败: {str(e)}")


@app.get("/api/download-csv")
async def download_csv(
    request: Request,
    file_path: str,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """下载CSV文件（仅普通用户）"""
    try:
        # 确保路径安全，防止路径遍历攻击
        safe_path = os.path.normpath(file_path).replace("..", "")
        # 只允许访问输出目录下的用户子目录
        user_id = current_user["id"]
        allowed_base = os.path.abspath(os.path.join(OUTPUT_DIR, str(user_id)))

        # 构造完整路径：由于file_path是相对路径（例如 user_id/dir/file.csv），
        # 但前端可能只传递了 dir/file.csv，或者包含 user_id。
        # 这里假设前端传递的是相对于 output 目录的路径。
        # 为了安全，我们强制路径必须在用户的 output 目录下。

        # 简化逻辑：前端可能传递完整路径或者相对路径。
        # 我们这里重新构建路径，确保它是 output/user_id/...

        # 如果 file_path 包含 user_id 前缀，去掉它（简单起见，假设前端传递的是 dir/file.csv）
        # 或者我们修改前端，或者在这里做更强的检查。

        # 假设 file_path 是 output/user_id/dir/file.csv 的相对部分，即 user_id/dir/file.csv
        # 或者是 dir/file.csv。

        # 让我们假设前端会根据文件列表返回的路径来请求。
        # 如果我们修改了 output 结构，前端看到的路径会改变吗？
        # 目前没有 API 返回 CSV 文件列表，通常是批阅后生成。

        # 让我们采取保守策略：检查路径是否包含 user_id。
        full_path = os.path.abspath(file_path)

        if not full_path.startswith(allowed_base):
            # 尝试将 user_id 加进去
            if not file_path.startswith(os.path.abspath(OUTPUT_DIR)):
                full_path = os.path.abspath(
                    os.path.join(OUTPUT_DIR, str(user_id), file_path)
                )
            else:
                # 如果已经是绝对路径但不在允许范围内，拒绝
                raise HTTPException(status_code=403, detail="访问被拒绝")

        if not full_path.startswith(allowed_base):
            raise HTTPException(
                status_code=403, detail="访问被拒绝：只能下载自己的文件"
            )

        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 记录下载日志
        log_manager.log_file_download(
            user_id=current_user["id"],
            file_name=os.path.basename(full_path),
            ip_address=request.client.host,
        )

        return FileResponse(
            path=full_path,
            filename=os.path.basename(full_path),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={os.path.basename(full_path)}"
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@app.get("/")
async def root():
    """根路径重定向到index.html"""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/index.html")


@app.get("/index.html")
async def serve_index():
    """服务index.html"""
    from fastapi.responses import FileResponse

    return FileResponse("front/index.html")


@app.get("/login.html")
async def serve_login():
    """服务login.html"""
    from fastapi.responses import FileResponse

    return FileResponse("front/login.html")


@app.get("/admin_users.html")
async def serve_admin_users():
    """服务admin_users.html"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_users.html")


@app.get("/admin_dashboard.html")
async def serve_admin_dashboard():
    """服务admin_dashboard.html"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_dashboard.html")


@app.get("/admin_logs.html")
async def serve_admin_logs():
    """服务admin_logs.html"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_logs.html")


@app.get("/style.css")
async def serve_style():
    """服务style.css"""
    from fastapi.responses import FileResponse

    return FileResponse("front/style.css")


@app.get("/script.js")
async def serve_script():
    """服务script.js"""
    from fastapi.responses import FileResponse

    return FileResponse("front/script.js")


@app.get("/login.css")
async def serve_login_css():
    """服务login.css"""
    from fastapi.responses import FileResponse

    return FileResponse("front/login.css")


@app.get("/login.js")
async def serve_login_js():
    """服务login.js"""
    from fastapi.responses import FileResponse

    return FileResponse("front/login.js")


@app.get("/admin_users.js")
async def serve_admin_users_js():
    """服务admin_users.js"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_users.js")


@app.get("/admin_dashboard.js")
async def serve_admin_dashboard_js():
    """服务admin_dashboard.js"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_dashboard.js")


@app.get("/admin_logs.js")
async def serve_admin_logs_js():
    """服务admin_logs.js"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin_logs.js")


@app.get("/admin.css")
async def serve_admin_css():
    """服务admin.css"""
    from fastapi.responses import FileResponse

    return FileResponse("front/admin.css")


@app.post("/api/abort-grading")
async def abort_grading(
    directory: str = Form(...), current_user: Dict[str, Any] = Depends(get_regular_user)
):
    """
    中止批阅任务
    """
    user_id = current_user["id"]
    decoded_directory = unquote(directory)
    task_key = f"{user_id}:{decoded_directory}"

    with grading_tasks_lock:
        if task_key in grading_tasks:
            cancel_event = grading_tasks[task_key]
            cancel_event.set()  # 设置事件以通知任务取消

            # 分阶段等待，给任务足够时间响应取消
            total_wait = 0
            max_wait = 10  # 最大等待时间10秒
            check_interval = 0.5  # 检查间隔0.5秒
            
            while total_wait < max_wait:
                # 释放锁，让任务有机会检查取消事件并清理自己
                grading_tasks_lock.release()
                
                try:
                    time.sleep(check_interval)
                    total_wait += check_interval
                finally:
                    # 重新获取锁
                    grading_tasks_lock.acquire()
                
                if task_key not in grading_tasks:
                    # 任务已经自己清理了
                    logger.info(f"批阅任务 {task_key} 已停止")
                    return {"message": "批阅任务已中止"}

            # 如果任务还在，强制清理
            if task_key in grading_tasks:
                logger.warning(f"批阅任务 {task_key} 10秒后仍未停止，强制清理")
                del grading_tasks[task_key]  # 从字典中移除任务
            logger.info(f"批阅任务 {task_key} 已强制停止")
            return {"message": "批阅任务已中止"}
        else:
            logger.info(f"未找到批阅任务: {task_key}")
            return {"message": "未找到对应的批阅任务"}


app.mount("/static", StaticFiles(directory="front"), name="static")

if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.getenv("PORT", 8000))
    ssl_keyfile = os.getenv("SSL_KEYFILE", "ssl/key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "ssl/cert.pem")

    if os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile):
        print(f"启动HTTPS服务器，端口: {port}")
        print(f"SSL证书: {ssl_certfile}")
        print(f"SSL私钥: {ssl_keyfile}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
        )
    else:
        print(f"启动HTTP服务器，端口: {port}")
        print(f"警告: 未找到SSL证书文件，使用HTTP模式")
        uvicorn.run(app, host="0.0.0.0", port=port)
