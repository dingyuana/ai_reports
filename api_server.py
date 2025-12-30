import os
import json
import csv
from datetime import datetime
from urllib.parse import unquote
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from grading_system import GradingSystem
from zai import ZhipuAiClient
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

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置常量
REPORTS_DIR = "reports"  # 报告存储目录
OUTPUT_DIR = "output"  # 输出目录
GRADED_DIR = "graded_reports"  # 输出目录

# 全局变量，用于在内存中存储评分标准
# 在实际生产环境中，可能会使用数据库或缓存
GRADING_CRITERIA = """
1. 内容完整性（是否包含实验目的、步骤、结果等必要部分）
2. 格式规范性（标题、段落、图表等是否规范）
3. 内容相关性（内容是否与实验主题相关）
4. 原创性（是否存在抄袭嫌疑）
5. 不要求对图片和表格等非文本内容考核
6. 成绩范围：60-95
"""

# 创建评分系统实例
grading_system = GradingSystem(REPORTS_DIR, OUTPUT_DIR, API_CONFIG)

# 配置智谱AI模型
zhipu_api_key = os.getenv('ARK_API_KEY')
if not zhipu_api_key:
    raise ValueError("ARK_API_KEY environment variable is not set")
zhipu_client = ZhipuAiClient(api_key=zhipu_api_key)


@app.get("/api/reports/")
async def get_report_directories():
    """获取 student_reports 目录下的所有子目录及其文件列表"""
    base_path = "student_reports"
    try:
        if not os.path.exists(base_path) or not os.path.isdir(base_path):
            return []
        
        result = []
        for dir_name in os.listdir(base_path):
            dir_path = os.path.join(base_path, dir_name)
            if os.path.isdir(dir_path):
                files = [
                    f for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                result.append({"name": dir_name, "files": files})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告目录时出错: {str(e)}")


@app.get("/api/graded-reports/")
async def get_graded_reports():
    """获取 graded_reports 目录下的内容（子目录和文件）"""
    base_path = "graded_reports"
    try:
        if not os.path.exists(base_path) or not os.path.isdir(base_path):
            return []
            
        result = []
        for dir_name in os.listdir(base_path):
            dir_path = os.path.join(base_path, dir_name)
            if os.path.isdir(dir_path):
                files = [
                    f for f in os.listdir(dir_path)
                    if os.path.isfile(os.path.join(dir_path, f))
                ]
                result.append({"name": dir_name, "files": files})
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取已评分报告时出错: {str(e)}")


@app.get("/api/download-graded")
async def download_graded_directory(directory: str):
    """压缩指定的已批阅目录并提供下载"""
    target_dir = os.path.join("graded_reports", directory)
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail="目录未找到")

    # 临时zip文件路径
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    # make_archive会自动添加.zip后缀，所以我们提供基础名
    base_zip_name = os.path.join(temp_dir, directory)
    zip_path = shutil.make_archive(base_zip_name, 'zip', target_dir)

    def cleanup():
        os.remove(zip_path)

    return FileResponse(
        path=zip_path,
        filename=f"{directory}_graded.zip",
        media_type='application/zip',
        background=BackgroundTask(cleanup)
    )


class AnnotateScanModel(BaseModel):
    directory: str
    add_markings: bool
    ai_review: bool
    auto_grading: bool


import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


async def run_in_threadpool(func, *args, **kwargs):
    """在线程池中运行函数，避免阻塞事件循环"""
    with ThreadPoolExecutor() as executor:
        return await asyncio.get_event_loop().run_in_executor(
            executor, lambda: func(*args, **kwargs)
        )


async def invoke_ark_model(prompt: str, max_retries: int = 3, timeout: int = 30) -> Optional[str]:
    """
    调用智谱AI模型进行评估，支持重试和超时

    Args:
        prompt: 提示文本
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    Returns:
        模型响应文本，失败时返回None
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试调用智谱AI模型 (尝试 {attempt + 1}/{max_retries})")

            # 定义同步调用函数
            def sync_call():
                response = zhipu_client.chat.completions.create(
                    model="glm-4.7",
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3
                )
                # 提取回复内容
                if hasattr(response.choices[0].message, "content"):
                    return response.choices[0].message.content
                return str(response.choices[0].message)

            # 在线程池中执行API调用，避免阻塞事件循环
            start_time = time.time()
            response = await run_in_threadpool(sync_call)
            elapsed_time = time.time() - start_time

            print(f"智谱AI模型调用成功，耗时: {elapsed_time:.2f}秒")
            return response

        except Exception as e:
            print(f"智谱AI模型调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")

            # 如果已经是最后一次尝试，则返回None
            if attempt == max_retries - 1:
                print(f"智谱AI模型调用失败，已达到最大重试次数: {max_retries}")
                return None

            # 指数退避策略
            wait_time = 2 ** attempt  # 1, 2, 4, 8...秒
            print(f"等待 {wait_time} 秒后重试...")
            await asyncio.sleep(wait_time)

    return None  # 不应该到达这里，但为了安全起见


@app.post("/api/annotate")
async def annotate_report(scan_model: AnnotateScanModel):
    """
    批注报告接口
    """
    # 打印接收到的新参数以供调试
    print(f"接收到批阅请求: 目录='{scan_model.directory}', 增加标志={scan_model.add_markings}, AI审核={scan_model.ai_review}, 自动批分={scan_model.auto_grading}")
    
    try:
        # 解码目录名称
        decoded_directory = unquote(scan_model.directory)
        print(f"解码后的目录名称: {decoded_directory}")
        scan_path = os.path.join("student_reports", decoded_directory)

        # 检查目录是否存在
        if not os.path.exists(scan_path):
            raise HTTPException(status_code=404, detail=f"目录不存在: {decoded_directory}")

        # 存储文档内容和评估结果
        documents_content = []
        failed_reports = []

        # 遍历目录中的所有文件
        for filename in os.listdir(scan_path):
            print(f"正在处理文件: {filename}")
            file_path = os.path.join(scan_path, filename)
            if not os.path.isfile(file_path):
                continue

            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()

            try:
                # 使用GradingSystem的文档处理器读取内容
                if ext in grading_system.document_processors:
                    processor = grading_system.document_processors[ext]
                    content = processor.extract_text(file_path)
                else:
                    continue  # 跳过不支持的文件类型

                # 使用ARK大模型评估报告质量
                prompt = f"""
                请根据以下标准评估实验报告的质量：
                ---
                {GRADING_CRITERIA}
                ---

                报告内容：
                {content[:4000]}  # 限制内容长度以避免超过模型限制

                请给出评估结果，格式为JSON:
                {{
                    "score": 0-100的评分,
                    "is_qualified": true/false,
                    "comments": "具体的评估意见",
                    "reasons": ["不合格原因1", "不合格原因2"]
                }}
                """

                try:
                    # 先进行基本合格性检查
                    is_basic_qualified = len(content) >= 100  # 基本长度检查

                    if not is_basic_qualified:
                        # 如果不合格，直接记录结果
                        evaluation = {
                            "score": 0,
                            "is_qualified": False,
                            "comments": "报告内容过短，未达到基本要求",
                            "reasons": ["内容长度不足"]
                        }
                    else:
                        # 如果基本合格，再调用ARK模型进行详细评估
                        response = await invoke_ark_model(prompt)
                        print(f"ARK模型评估结果: {response}")

                        if response is None:
                            evaluation = {
                                "score": 50,
                                "is_qualified": True,
                                "comments": "无法获取AI评估，使用默认评估",
                                "reasons": ["AI评估失败"]
                            }
                        else:
                            try:
                                evaluation = json.loads(response)
                            except json.JSONDecodeError:
                                print(f"无法解析ARK响应为JSON: {response}")
                                evaluation = {
                                    "score": 50,
                                    "is_qualified": True,
                                    "comments": "无法解析AI评估结果，使用默认评估",
                                    "reasons": ["AI评估结果解析失败"]
                                }

                    # 获取评估结果
                    score = evaluation.get("score", 0)
                    is_qualified = evaluation.get("is_qualified", False)
                    comments = evaluation.get("comments", "")
                    reasons = evaluation.get("reasons", [])

                    # 将文件名和内容添加到结果列表
                    documents_content.append({
                        "filename": filename,
                        "type": "PDF" if ext == '.pdf' else "Word",
                        "content": content[:5000],
                        "status": "合格" if is_qualified else "不合格",
                        "score": score,
                        "comments": comments,
                        "size": os.path.getsize(file_path)
                    })

                    # 创建输出子目录
                    output_subdir = os.path.join(OUTPUT_DIR, decoded_directory)
                    os.makedirs(output_subdir, exist_ok=True)

                    # 保存评估结果到JSON文件
                    base_filename = os.path.splitext(filename)[0]  # 移除文件扩展名
                    json_path = os.path.join(output_subdir, f"{base_filename}.json")
                    with open(json_path, 'w', encoding='utf-8') as json_file:
                        json.dump({
                            "filename": filename,
                            "score": score,
                            "is_qualified": is_qualified,
                            "comments": comments,
                            "reasons": reasons,
                            "timestamp": datetime.now().isoformat()
                        }, json_file, ensure_ascii=False, indent=2)

                    # 记录不合格报告
                    if not is_qualified:
                        user_name = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
                        failed_reports.append({
                            "username": user_name,
                            "status": "不合格",
                            "filename": filename
                        })

                    # 记录合格报告到CSV文件
                    parts = filename.split('-')
                    print(f"文件名称: {parts}")
                    if len(parts) >= 3:
                        class_name = parts[0]  # 班级
                        student_id = parts[1]  # 学号
                        user_name = parts[2].split('.')[0]  # 姓名
                    else:
                        user_name = filename.split('.')[0]
                        student_id = user_name  # 假设学号是文件名前缀
                        class_name  = user_name # 假设姓名是文件名前缀
                    print(f"班级: {class_name}, 学号: {student_id}, 姓名: {user_name}")
                    qualified_csv_path = os.path.join(output_subdir, "合格报告分数.csv")
                    file_exists = os.path.exists(qualified_csv_path)

                    with open(qualified_csv_path, 'a', newline='', encoding='utf-8-sig') as csvfile:
                        fieldnames = ['学号', '姓名', '分数']
                        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                        if not file_exists:
                            writer.writeheader()

                        writer.writerow({
                            '学号': student_id,
                            '姓名': user_name,
                            '分数': score
                        })
                    # 如果是PDF文件，调用 generate_graded_pdf 函数
                    if ext == '.pdf':
                        graded_reports_dir = os.path.join(GRADED_DIR, decoded_directory)
                        os.makedirs(graded_reports_dir, exist_ok=True)
                        output_pdf_path = os.path.join(graded_reports_dir, f"{base_filename}.pdf")
                        grade_student_reports(decoded_directory)

                except Exception as e:
                    print(f"评估过程中出错: {str(e)}")
                    documents_content.append({
                        "filename": filename,
                        "type": "PDF" if ext == '.pdf' else "Word",
                        "content": content[:500],
                        "status": "未知",
                        "score": 0,
                        "comments": "评估过程中出错",
                        "size": os.path.getsize(file_path)
                    })

            except Exception as doc_error:
                print(f"处理文档失败: {str(doc_error)}")
                continue

        # 如果有不合格的报告，将它们保存为CSV文件
        csv_path = None
        if failed_reports:
            try:
                # 创建输出子目录
                output_subdir = os.path.join(OUTPUT_DIR, decoded_directory)
                os.makedirs(output_subdir, exist_ok=True)

                # 生成CSV文件名（使用时间戳确保唯一性）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"不合格报告_{timestamp}.csv"
                csv_path = os.path.join(output_subdir, csv_filename)

                # 写入CSV文件
                with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    fieldnames = ['用户名', '状态', '文件名']
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                    writer.writeheader()
                    for report in failed_reports:
                        writer.writerow({
                            '用户名': report['username'],
                            '状态': report['status'],
                            '文件名': report['filename']
                        })
            except Exception as csv_error:
                print(f"生成CSV文件失败: {str(csv_error)}")
                csv_path = None

        # 返回合格报告的CSV文件路径
        qualified_csv_path = None
        if 'output_subdir' in locals():
            qualified_csv_path = os.path.join(output_subdir, "合格报告分数.csv")
        
        # 确保返回相对路径，便于前端访问
        qualified_csv_file_url = None
        if qualified_csv_path and os.path.exists(qualified_csv_path):
            # 将绝对路径转换为API可访问的路径
            qualified_csv_file_url = qualified_csv_path
            
        failed_csv_file_url = None
        if csv_path and os.path.exists(csv_path):
            # 将绝对路径转换为API可访问的路径
            failed_csv_file_url = csv_path
        
        return {
            "message": f"成功扫描了 {len(documents_content)} 个文档",
            # "documents": documents_content,
            "failed_count": len(failed_reports),
            "csv_file": failed_csv_file_url,
            "qualified_csv_file": qualified_csv_file_url
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理报告时出错: {str(e)}")


class CriteriaModel(BaseModel):
    criteria: str


@app.post("/api/criteria")
async def set_criteria(data: CriteriaModel):
    """设置全局的评分标准"""
    global GRADING_CRITERIA
    GRADING_CRITERIA = data.criteria
    print(f"新的评分标准已设置: {GRADING_CRITERIA}")
    return {"message": "评分标准已成功更新"}


@app.get("/api/criteria")
async def get_criteria():
    """获取当前的评分标准"""
    return {"criteria": GRADING_CRITERIA}


@app.post("/api/upload")
async def upload_zip_file(file: UploadFile = File(...)):
    """接收ZIP压缩文件，解压到student_reports目录"""
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="只支持上传ZIP格式的压缩文件")

    # 基于文件名创建目录
    dir_name = os.path.splitext(file.filename)[0]
    extract_path = os.path.join("student_reports", dir_name)
    os.makedirs(extract_path, exist_ok=True)

    # 使用临时文件管理器创建临时文件
    with temp_file(suffix='.zip', prefix='upload_') as temp_zip_path:
        try:
            # 保存上传的文件到临时位置
            with open(temp_zip_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            # 解压文件
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)

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
async def grade_single_report(data: SingleReportModel):
    """批阅单个学生报告"""
    try:
        # 确保文件存在
        if not os.path.exists(data.file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 调用 grade_single_student 函数
        result_path = grade_single_student(
            data.file_path,
            data.output_path,
            data.score,
            data.comments
        )
        
        if result_path:
            return {
                "status": "success",
                "message": "报告批阅完成",
                "output_path": result_path
            }
        else:
            return {
                "status": "error",
                "message": "报告批阅失败"
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/reports/{directory_name}")
async def delete_report_directory(directory_name: str):
    """删除指定的报告目录"""
    try:
        # 确保目录名安全，防止路径遍历攻击
        safe_dir_name = os.path.normpath(directory_name).replace("..", "")
        dir_path = os.path.join("student_reports", safe_dir_name)
        
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
async def delete_graded_report_directory(directory_name: str):
    """删除指定的已批阅报告目录"""
    try:
        # 确保目录名安全，防止路径遍历攻击
        safe_dir_name = os.path.normpath(directory_name).replace("..", "")
        dir_path = os.path.join("graded_reports", safe_dir_name)
        
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


if __name__ == "__main__":
    import uvicorn

    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


@app.get("/api/temp/usage")
async def get_temp_usage():
    """获取临时文件使用情况"""
    try:
        usage = temp_manager.get_temp_usage()
        return {
            "status": "success",
            "usage": usage
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取临时文件使用情况失败: {str(e)}")

@app.post("/api/temp/cleanup")
async def cleanup_temp_files():
    """手动清理临时文件"""
    try:
        temp_manager.cleanup_old_files()
        usage_after = temp_manager.get_temp_usage()
        return {
            "status": "success",
            "message": "临时文件清理完成",
            "usage_after_cleanup": usage_after
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
        return {
            "status": "success",
            "summary": summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")

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

@app.get("/api/download-csv")
async def download_csv(file_path: str):
    """下载CSV文件"""
    try:
        # 确保路径安全，防止路径遍历攻击
        safe_path = os.path.normpath(file_path).replace("..", "")
        full_path = os.path.abspath(safe_path)
        
        # 只允许访问输出目录下的文件
        allowed_base = os.path.abspath(OUTPUT_DIR)
        if not full_path.startswith(allowed_base):
            raise HTTPException(status_code=403, detail="访问被拒绝")
        
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(
            path=full_path,
            filename=os.path.basename(full_path),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={os.path.basename(full_path)}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")

# 挂载静态文件目录
# 注意：这必须在所有API路由之后进行，以确保API路由优先匹配
app.mount("/", StaticFiles(directory="front", html=True), name="front")
