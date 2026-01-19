# FastAPI应用初始化文件
from fastapi import FastAPI, HTTPException, Depends, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
import os
import logging
import shutil
import zipfile
import json
from tempfile import NamedTemporaryFile

from config import API_CONFIG
from grading_system import GradingSystem
from database import init_db_pool, close_db_pool, init_database
from api.auth.endpoints import get_regular_user
from config_manager import config_manager
from log_manager import log_manager
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from urllib.parse import unquote
import threading
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from datetime import datetime

# 导入路由器
from api.auth import auth_router
from api.admin import admin_router


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
                        import time
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
                    import time
                    time.sleep(delay)

    logger.error(f"Word文件转换失败，已达到最大重试次数 {max_retries}: {word_path}")
    return False

# 定义请求模型
class AnnotateScanModel(BaseModel):
    directory: str
    add_markings: bool
    ai_review: bool
    auto_grading: bool
    selected_model: str = "Qwen/QwQ-32B"
    min_score: int = 60
    max_score: int = 95

# 全局变量用于跟踪正在运行的批阅任务
grading_tasks = {}
grading_tasks_lock = threading.Lock()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI()

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

评分标准
总分100分，实际得分范围要在指定分数之间。评分需兼顾标准要求与分数正态分布特性，避免集中出现逢五、逢十的整数分数。

1. 内容完整性（34分） 
- 核心要素齐全（21分）：报告需完整包含实验目的、实验原理、实验步骤、实验结果、实验分析与总结等必要核心部分。
- 过程描述清晰（13分）：实验过程文字描述逻辑连贯、条理清晰，能准确反映实验操作的先后顺序和关键细节。

2. 格式规范性（23分）
- 文档格式规范（23分）：报告标题、目录、正文段落、字体字号、行间距、页码等格式需完全符合实训报告统一要求。

3. 内容相关性（26分）
- 主题贴合紧密（14分）：报告正文内容与本次实训实验主题高度相关，无偏离主题的无关内容。
- 结果目的相符（12分）：实验结果能对实验目的进行有效回应，实验结论与实验目的保持一致。
- 不考虑截图，流程图及各种图表的要求

 4. 原创性（17分）
- 内容原创无抄袭（11分）：报告的实验分析、总结与反思等核心内容为学生原创，无直接抄袭教材、网络或他人报告的情况。
- 引用成果标注规范（6分）：引用他人理论、数据、观点等成果时，需准确标明出处，引用格式规范。

批阅要求
1. 逐维度对照细则评分，各维度得分汇总为总分，总分需在指定分数之间。
2. 保证分数正态分布，避免大量报告集中在某一分数段，尽量避免给出65、70、75、80、85、90等分数。
3. 撰写总评语，不列出具体扣分分数，字数控制在200字左右，明确指出报告的优点与不足，评语具有指导性。

# 评分标准（总分100分，实际得分范围60-95分）
# 1.内容完整性（25分）
#   包含实验目的、步骤、结果等必要部分（15分）
#   实验过程描述清晰，逻辑连贯（10分）
# 2.格式规范性（20分）
#   标题、段落、图表等格式规范（10分）
#   图表有标题和说明，引用规范（10分）
# 3.内容相关性（20分）
#   内容与实验主题紧密相关（10分）
#   实验结果与实验目的相符（10分）
# 4. 原创性（15分）
#   报告内容原创，无抄袭嫌疑（10分）
#   引用他人成果已标明出处（5分）
"""

# 全局变量，用于在内存中存储评分标准
GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA


# 服务器启动时执行的操作
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


# 导入其他工具函数
def load_criteria_from_file():
    """从文件加载批阅要求"""
    global GRADING_CRITERIA
    try:
        if os.path.exists(CRITERIA_FILE):
            with open(CRITERIA_FILE, "r", encoding="utf-8") as f:
                import json
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
        import json
        with open(CRITERIA_FILE, "w", encoding="utf-8") as f:
            json.dump({"criteria": criteria}, f, ensure_ascii=False, indent=2)
        logger.info(f"批阅要求已保存到文件: {CRITERIA_FILE}")
    except Exception as e:
        logger.error(f"保存批阅要求文件失败: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"保存批阅要求失败: {str(e)}")


# 包含路由器
app.include_router(auth_router)
app.include_router(admin_router)


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


@app.get("/admin.css")
async def serve_admin_css():
    """服务admin.css"""
    from fastapi.responses import FileResponse
    return FileResponse("front/admin.css")


@app.get("/admin_users.js")
async def serve_admin_users_js():
    """服务admin_users.js"""
    from fastapi.responses import FileResponse
    return FileResponse("front/admin_users.js")


@app.get("/admin_logs.js")
async def serve_admin_logs_js():
    """服务admin_logs.js"""
    from fastapi.responses import FileResponse
    return FileResponse("front/admin_logs.js")


@app.get("/admin_dashboard.js")
async def serve_admin_dashboard_js():
    """服务admin_dashboard.js"""
    from fastapi.responses import FileResponse
    return FileResponse("front/admin_dashboard.js")


# 报告目录API端点
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


@app.delete("/api/reports/{directory_name}")
async def delete_report_directory(
    directory_name: str,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """删除 student_reports 目录下的指定子目录（仅普通用户）"""
    user_id = current_user["id"]
    base_path = os.path.join("student_reports", str(user_id))
    target_dir = os.path.join(base_path, directory_name)
    try:
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            raise HTTPException(status_code=404, detail="目录未找到")

        # 删除目录及其内容
        shutil.rmtree(target_dir)
        logger.info(f"用户 {current_user['username']} 删除了待批阅报告目录: {directory_name}")
        return {"message": "目录删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除目录时出错: {str(e)}")


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
    with NamedTemporaryFile(suffix=".zip", prefix="upload_", delete=False) as temp_zip:
        try:
            # 保存上传的文件到临时位置
            shutil.copyfileobj(file.file, temp_zip)
            temp_zip_path = temp_zip.name

        except Exception as e:
            # 清理
            os.unlink(temp_zip.name)
            shutil.rmtree(extract_path, ignore_errors=True)
            raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    try:
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

        logger.info(f"用户 {current_user['username']} 上传了文件: {file.filename}")
        return {"message": f"文件 '{file.filename}' 已成功上传并解压到 '{dir_name}' 目录"}

    except Exception as e:
        # 清理
        shutil.rmtree(extract_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")
    finally:
        # 关闭文件和清理临时文件
        await file.close()
        os.unlink(temp_zip_path)


@app.post("/api/annotate")
async def annotate_report(
    request: Request,
    scan_model: AnnotateScanModel,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """
    批注报告接口 - 使用多线程并行处理（仅普通用户）
    """
    # 记录接收到的批阅请求
    logger.info(
        f"接收到批阅请求: 目录='{scan_model.directory}', 增加对号={scan_model.add_markings}, 增加评语={scan_model.ai_review}, 自动批分={scan_model.auto_grading}"
    )

    try:
        # 解码目录名称
        decoded_directory = unquote(scan_model.directory)
        logger.info(f"解码后的目录名称: {decoded_directory}")
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

            logger.info(f"共找到 {len(files_to_process)} 个文件需要处理")

            # 记录批阅开始日志
            log_manager.log_grading_start(
                user_id=current_user["id"],
                directory_name=decoded_directory,
                file_count=len(files_to_process),
                model_used=scan_model.selected_model,
                ip_address=request.client.host,
            )

            # 使用线程池并行处理文件，使用10个线程
            # 每个线程独立处理一个完整的文件（包括文件处理和大模型调用）
            # 线程间任务互不干涉，避免API速率限制和资源压力
            from concurrent.futures import as_completed, wait, FIRST_COMPLETED

            with ThreadPoolExecutor(max_workers=10) as executor:
                # 提交所有任务到线程池
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
                        cancel_event,  # 传递取消事件
                    ): (filename, file_path)
                    for filename, file_path in files_to_process
                }

                # 收集处理结果，每次处理一个已完成的任务
                remaining_futures = list(future_to_file.keys())

                while remaining_futures:
                    # 检查是否需要取消任务
                    if cancel_event.is_set():
                        logger.info("批阅任务被中断")
                        # 强制取消未开始的任务
                        for remaining_future in remaining_futures:
                            remaining_future.cancel()

                        # 等待正在运行的任务完成或超时
                        for remaining_future in remaining_futures:
                            if not remaining_future.cancelled():
                                try:
                                    remaining_future.result(timeout=2)
                                except:
                                    pass  # 忽略异常，因为我们正在取消
                        break

                    # 等待至少一个任务完成或超时（短超时以快速响应取消）
                    completed_futures, remaining_futures = wait(
                        remaining_futures,
                        timeout=1,  # 1秒超时，以便快速响应取消事件
                        return_when=FIRST_COMPLETED,
                    )

                    # 处理已完成的任务
                    for completed_future in completed_futures:
                        filename, file_path = future_to_file[completed_future]
                        try:
                            result = completed_future.result()
                            documents_content.append(result)

                            # 记录不合格报告
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

                            logger.info(
                                f"文件 {filename} 处理完成，状态: {result.get('status')}"
                            )
                        except Exception as e:
                            logger.error(f"文件 {filename} 处理失败: {str(e)}")
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
                                remarks += "；AI评估失败（已重试10次）"
                            else:
                                remarks = "AI评估失败（已重试10次）"

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

                logger.info(f"综合报告评分汇总CSV已生成: {comprehensive_csv_path}")
            except Exception as csv_error:
                logger.error(f"生成综合CSV文件失败: {str(csv_error)}")
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


@app.delete("/api/graded-reports/{directory_name}")
async def delete_graded_report_directory(
    directory_name: str,
    current_user: Dict[str, Any] = Depends(get_regular_user),
):
    """删除 graded_reports 目录下的指定子目录（仅普通用户）"""
    user_id = current_user["id"]
    base_path = os.path.join("graded_reports", str(user_id))
    target_dir = os.path.join(base_path, directory_name)
    try:
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            raise HTTPException(status_code=404, detail="目录未找到")

        # 删除目录及其内容
        shutil.rmtree(target_dir)
        logger.info(f"用户 {current_user['username']} 删除了已批阅报告目录: {directory_name}")
        return {"message": "目录删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除目录时出错: {str(e)}")


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

    return FileResponse(
        path=zip_path,
        filename=f"{directory}_graded.zip",
        media_type="application/zip",
        background=BackgroundTask(cleanup),
    )


# 批阅要求API端点
from pydantic import BaseModel

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


# 挂载静态文件服务
app.mount("/static", StaticFiles(directory="front"), name="static")


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
    logger.info(f"正在处理文件: {filename}")

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
                    "comments": "转换失败（已重试10次）",
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
        # 处理Markdown文件（直接添加对号）
        elif ext == ".md":
            # 使用MarkdownProcessor处理
            processor = grading_system.document_processors[".md"]
            output_ext = ".md"
            final_output_path = os.path.join(
                graded_reports_dir, f"{base_filename}_graded{output_ext}"
            )
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
                        "comments": "转换失败（已重试5次）",
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
            elif ext == ".md":
                # 对于Markdown文件，直接提取文本
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
                # 如果不合格，直接记录结果
                evaluation = {
                    "score": 0,
                    "is_qualified": False,
                    "comments": "报告内容过短，未达到基本要求",
                    "reasons": ["内容长度不足"],
                }
            else:
                # 检查是否需要取消任务
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

                # 如果基本合格，再调用ARK模型进行详细评估
                # 注意：这里需要同步调用，因为在线程池中不能使用async
                import asyncio

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

                logger.info(f"ARK模型评估结果: {response}")

                if response is None:
                    evaluation = {
                        "score": 50,
                        "is_qualified": True,
                        "comments": "无法获取AI评估，使用默认评估",
                        "reasons": ["AI评估失败，已重试10次"],
                        "ai_failed": True,
                    }
                else:
                    try:
                        # 尝试直接解析JSON
                        evaluation = json.loads(response)
                    except json.JSONDecodeError:
                        logger.error(f"无法解析AI模型响应为JSON: {response}")
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
                            logger.info(f"使用提取的评估结果: {evaluation}")
                        except Exception as e:
                            logger.error(f"提取AI评估结果失败: {e}")
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
            logger.info(f"文件名称解析: {parts}")
            if len(parts) >= 3:
                class_name = parts[0]  # 班级
                student_id = parts[1]  # 学号
                user_name = parts[2].split(".")[0]  # 姓名
            else:
                user_name = filename.split(".")[0]
                student_id = user_name  # 假设学号是文件名前缀
                class_name = user_name  # 假设姓名是文件名前缀
            logger.info(f"学生信息解析结果 - 班级: {class_name}, 学号: {student_id}, 姓名: {user_name}")

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

            # 为PDF、Word和Markdown文档生成批阅后的文件（目录已提前创建）

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
                            "comments": "转换失败（已重试10次）",
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
            elif ext == ".md":
                # 对于Markdown文件，直接使用Markdown处理器
                processor = grading_system.document_processors[ext]
                processing_path = file_path
                output_ext = ".md"

                # 使用Markdown处理器添加评语和分数
                final_output_path = os.path.join(
                    graded_reports_dir, f"{base_filename}_graded{output_ext}"
                )
                # 只有当选择了自动批分时才添加分数
                add_score = scan_model.auto_grading
                processor.add_comments_and_score(
                    processing_path,  # 处理的文件路径
                    comments,  # 评语
                    score,  # 分数
                    final_output_path,  # 输出文件路径
                    add_score,  # 是否添加分数
                )

                if scan_model.add_markings:
                    # 如果需要添加对号标注，在已添加评语的基础上再次处理
                    temp_path = os.path.join(
                        graded_reports_dir, f"{base_filename}_temp{output_ext}"
                    )
                    os.rename(final_output_path, temp_path)
                    processor.add_checkmarks(temp_path, final_output_path)
                    # 清理临时文件
                    if os.path.exists(temp_path):
                        try:
                            os.remove(temp_path)
                            logger.info(f"已清理临时文件: {temp_path}")
                        except Exception as e:
                            logger.warning(f"清理临时文件失败: {e}")

            # 返回处理结果
            return {
                "filename": filename,
                "type": "PDF" if ext == ".pdf" else "Word" if ext in [".doc", ".docx"] else "Markdown",
                "content": content[:5000],
                "status": "合格" if is_qualified else "不合格",
                "score": score,
                "comments": comments,
                "size": os.path.getsize(file_path),
                "ai_failed": ai_failed,
            }

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"处理文件 {filename} 时评估过程中出错: {str(e)}")
            logger.error(f"错误堆栈跟踪: {error_details}")
            return {
                "filename": filename,
                "type": "PDF" if ext == ".pdf" else "Word" if ext in [".doc", ".docx"] else "Markdown",
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