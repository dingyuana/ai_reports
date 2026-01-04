import os
import json
import csv
import logging
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

# 配置日志记录器
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
CRITERIA_FILE = "criteria.json"  # 批阅要求存储文件

# 默认评分标准
DEFAULT_GRADING_CRITERIA = """
请依据以下评分标准对学生提交的大学实训报告进行客观、公正的批阅打分。

评分标准
总分100分，实际得分范围60-95分。评分需兼顾标准要求与分数正态分布特性，避免集中出现逢五、逢十的整数分数。

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
1. 逐维度对照细则评分，各维度得分汇总为总分，总分需在60-95分之间。
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
# 5. 非文本内容（20分）
#   配套图片、表格等非文本内容齐全（10分）
#   非文本内容与文本内容紧密结合，有助于理解（10分）
"""

# 全局变量，用于在内存中存储评分标准
# 在实际生产环境中，可能会使用数据库或缓存
GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA


def load_criteria_from_file():
    """从文件加载批阅要求"""
    global GRADING_CRITERIA
    try:
        if os.path.exists(CRITERIA_FILE):
            with open(CRITERIA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                GRADING_CRITERIA = data.get('criteria', DEFAULT_GRADING_CRITERIA)
                logger.info(f"已从文件加载批阅要求: {CRITERIA_FILE}")
        else:
            logger.info(f"批阅要求文件不存在，使用默认标准")
    except Exception as e:
        logger.error(f"加载批阅要求文件失败: {e}")
        GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA


def save_criteria_to_file(criteria: str):
    """将批阅要求保存到文件"""
    try:
        with open(CRITERIA_FILE, 'w', encoding='utf-8') as f:
            json.dump({'criteria': criteria}, f, ensure_ascii=False, indent=2)
        logger.info(f"批阅要求已保存到文件: {CRITERIA_FILE}")
    except Exception as e:
        logger.error(f"保存批阅要求文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存批阅要求失败: {str(e)}")


# 服务器启动时加载批阅要求
@app.on_event("startup")
async def startup_event():
    """服务器启动时执行的操作"""
    load_criteria_from_file()
    logger.info("服务器已启动，批阅要求已加载")


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
    selected_model: str = "glm-4.5-flash"


import asyncio
import time
from concurrent.futures import ThreadPoolExecutor


async def run_in_threadpool(func, *args, **kwargs):
    """在线程池中运行函数，避免阻塞事件循环"""
    with ThreadPoolExecutor() as executor:
        return await asyncio.get_event_loop().run_in_executor(
            executor, lambda: func(*args, **kwargs)
        )


async def invoke_ark_model(prompt: str, model_name: str = "glm-4.5-flash", max_retries: int = 10, timeout: int = 30) -> Optional[str]:
    """
    调用大模型进行评估，支持重试和超时

    Args:
        prompt: 提示文本
        model_name: 模型名称
        max_retries: 最大重试次数
        timeout: 超时时间（秒）

    Returns:
        模型响应文本，失败时返回None
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试调用AI模型 {model_name} (尝试 {attempt + 1}/{max_retries})")

            # 定义同步调用函数
            def sync_call():
                # 根据模型名称选择不同的调用方式
                if model_name in ["thudm/glm-z1-9b-0414", "qwen/qwen3-8b", "zai-org/GLM-4.6V"]:
                    # 调用硅基流动API
                    import requests
                    
                    # 硅基流动API配置
                    API_KEY = "sk-kmqzqvmpwqhdxanpafbkytnfrdstifwgdvcglzrjkolyhzsq"
                    API_URL = "https://api.siliconflow.cn/v1/chat/completions"
                    
                    # 硅基流动API使用完整的模型标识符
                    siliconflow_model_name = model_name
                    
                    # 构建请求参数
                    payload = {
                        "model": siliconflow_model_name,  # 模型名称
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3
                    }
                    
                    # 发送请求
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {API_KEY}"
                    }
                    response = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
                    
                    # 处理响应
                    if response.status_code == 200:
                        result = response.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        raise Exception(f"API请求失败，状态码: {response.status_code}, 错误信息: {response.text}")
                else:
                    # 默认调用智谱AI模型
                    response = zhipu_client.chat.completions.create(
                        model="glm-4.5-flash",
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

            print(f"AI模型 {model_name} 调用成功，耗时: {elapsed_time:.2f}秒")
            return response

        except Exception as e:
            print(f"AI模型 {model_name} 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")

            # 如果已经是最后一次尝试，则返回None
            if attempt == max_retries - 1:
                print(f"AI模型 {model_name} 调用失败，已达到最大重试次数: {max_retries}")
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
    print(f"接收到批阅请求: 目录='{scan_model.directory}', 增加对号={scan_model.add_markings}, 增加评语={scan_model.ai_review}, 自动批分={scan_model.auto_grading}")
    
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

        # 提前创建graded_reports_dir目录，用于存储临时文件
        graded_reports_dir = os.path.join(GRADED_DIR, decoded_directory)
        os.makedirs(graded_reports_dir, exist_ok=True)

        # 遍历目录中的所有文件
        for filename in os.listdir(scan_path):
            print(f"正在处理文件: {filename}")
            file_path = os.path.join(scan_path, filename)
            if not os.path.isfile(file_path):
                continue

            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()
            content = ""
            base_filename = os.path.splitext(filename)[0]
            
            # 检查是否需要调用模型
            need_ai_processing = scan_model.auto_grading or scan_model.ai_review
            
            # 如果只选择了增加对号，不需要调用模型，直接处理
            if not need_ai_processing and scan_model.add_markings:
                logger.info(f"只选择了增加对号，不需要调用模型，直接处理: {file_path}")
                
                processor = grading_system.document_processors['.pdf']
                output_ext = '.pdf'
                final_output_path = os.path.join(graded_reports_dir, f"{base_filename}_graded{output_ext}")
                
                # 处理Word文件（转换为PDF后添加对号）
                if ext in ['.doc', '.docx']:
                    # 使用WordProcessor转换为PDF
                    word_processor = grading_system.document_processors[ext]
                    
                    # 构建转换后的PDF路径
                    converted_pdf_path = os.path.join(graded_reports_dir, f"{base_filename}_converted.pdf")
                    
                    # 转换为PDF
                    if not word_processor.convert_to_pdf(file_path, converted_pdf_path):
                        logger.error(f"转换Word文件为PDF失败: {file_path}")
                        continue
                    
                    # 添加对号标注
                    processor.add_checkmarks(converted_pdf_path, final_output_path)
                    
                    # 清理临时文件
                    if os.path.exists(converted_pdf_path):
                        try:
                            os.remove(converted_pdf_path)
                        except Exception as e:
                            logger.warning(f"清理临时文件失败: {e}")
                # 处理PDF文件（直接添加对号）
                elif ext == '.pdf':
                    # 直接为PDF文件添加对号标注
                    processor.add_checkmarks(file_path, final_output_path)
                else:
                    continue  # 跳过不支持的文件类型
                    
                # 记录处理结果
                documents_content.append({
                    "filename": filename,
                    "type": "PDF",
                    "content": "",
                    "status": "处理完成",
                    "score": 0,
                    "comments": "",
                    "size": os.path.getsize(file_path),
                    "ai_failed": False
                })
                continue
            
            # 如果需要调用模型，执行正常流程
            if need_ai_processing:
                try:
                    # 先将Word文件转换为PDF，然后从PDF中提取文本
                    if ext in ['.doc', '.docx']:
                        logger.info(f"正在将Word文件转换为PDF以提取文本: {file_path}")
                        
                        # 使用WordProcessor转换为PDF
                        word_processor = grading_system.document_processors[ext]
                        
                        # 构建临时PDF路径
                        temp_pdf_path = os.path.join(graded_reports_dir, f"{base_filename}_temp.pdf")
                        
                        # 转换为PDF
                        if not word_processor.convert_to_pdf(file_path, temp_pdf_path):
                            logger.error(f"转换Word文件为PDF失败: {file_path}")
                            continue
                        
                        # 使用PDF处理器提取文本
                        pdf_processor = grading_system.document_processors['.pdf']
                        content = pdf_processor.extract_text(temp_pdf_path)
                        
                        # 清理临时PDF文件
                        if os.path.exists(temp_pdf_path):
                            try:
                                os.remove(temp_pdf_path)
                            except:
                                pass
                    elif ext == '.pdf':
                        # 对于PDF文件，直接提取文本
                        processor = grading_system.document_processors[ext]
                        content = processor.extract_text(file_path)
                    else:
                        continue  # 跳过不支持的文件类型

                    # 使用ARK大模型评估报告质量
                    prompt = f"""
                作为一个大学资深老师
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
                        response = await invoke_ark_model(prompt, model_name=scan_model.selected_model)
                        print(f"ARK模型评估结果: {response}")

                        if response is None:
                            evaluation = {
                                "score": 50,
                                "is_qualified": True,
                                "comments": "无法获取AI评估，使用默认评估",
                                "reasons": ["AI评估失败，已重试10次"],
                                "ai_failed": True
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
                                    score_match = re.search(r'"score"\s*:\s*(\d+)', response) or re.search(r'分数[:：]\s*(\d+)', response)
                                    score = int(score_match.group(1)) if score_match else 75  # 默认分数
                                    
                                    # 尝试从响应中提取评语
                                    comments_match = re.search(r'"comments"\s*:\s*"([^"]+)"', response) or re.search(r'评语[:：]\s*([^\n]+)', response)
                                    comments = comments_match.group(1) if comments_match else "AI评估通过，整体表现良好。"  # 默认评语
                                    
                                    # 尝试从响应中提取合格状态
                                    is_qualified = True
                                    if "不合格" in response or "不通过" in response:
                                        is_qualified = False
                                    
                                    # 尝试从响应中提取原因
                                    reasons = []
                                    reasons_match = re.search(r'"reasons"\s*:\s*\[([^\]]+)\]', response)
                                    if reasons_match:
                                        reasons_str = reasons_match.group(1)
                                        reasons = [reason.strip(' "') for reason in reasons_str.split(',')]
                                    elif not is_qualified:
                                        reasons = ["AI评估不通过"]
                                    
                                    # 构建评估结果
                                    evaluation = {
                                        "score": score,
                                        "is_qualified": is_qualified,
                                        "comments": comments,
                                        "reasons": reasons
                                    }
                                    print(f"使用提取的评估结果: {evaluation}")
                                except Exception as e:
                                    print(f"提取AI评估结果失败: {e}")
                                    # 如果提取也失败，使用默认评估
                                    evaluation = {
                                        "score": 75,
                                        "is_qualified": True,
                                        "comments": "AI评估通过，整体表现良好。",
                                        "reasons": []
                                    }

                    # 获取评估结果
                    score = evaluation.get("score", 0)
                    is_qualified = evaluation.get("is_qualified", False)
                    comments = evaluation.get("comments", "")
                    reasons = evaluation.get("reasons", [])
                    ai_failed = evaluation.get("ai_failed", False)

                    # 将文件名和内容添加到结果列表
                    documents_content.append({
                        "filename": filename,
                        "type": "PDF" if ext == '.pdf' else "Word",
                        "content": content[:5000],
                        "status": "合格" if is_qualified else "不合格",
                        "score": score,
                        "comments": comments,
                        "size": os.path.getsize(file_path),
                        "ai_failed": ai_failed
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
                    # 为PDF和Word文档都生成批阅后的文件（目录已提前创建）
                    
                    if ext in ['.pdf', '.doc', '.docx']:
                        # 对于Word文件，先转换为PDF，然后统一使用PDF处理器处理
                        if ext in ['.doc', '.docx']:
                            logger.info(f"正在将Word文件转换为PDF: {file_path}")
                            
                            # 使用WordProcessor转换为PDF
                            word_processor = grading_system.document_processors[ext]
                            
                            # 构建转换后的PDF路径
                            converted_pdf_path = os.path.join(graded_reports_dir, f"{base_filename}_converted.pdf")
                            
                            # 转换为PDF
                            if not word_processor.convert_to_pdf(file_path, converted_pdf_path):
                                logger.error(f"转换Word文件为PDF失败: {file_path}")
                                continue
                            
                            # 切换到PDF处理器和转换后的PDF路径
                            processor = grading_system.document_processors['.pdf']
                            processing_path = converted_pdf_path
                            output_ext = '.pdf'  # 最终输出为PDF
                        else:
                            # 对于PDF文件，直接使用
                            processor = grading_system.document_processors[ext]
                            processing_path = file_path
                            output_ext = '.pdf'
                        
                        # 使用PDF处理器添加评语和分数
                        intermediate_file_path = os.path.join(graded_reports_dir, f"{base_filename}_temp{output_ext}")
                        # 只有当选择了自动批分时才添加分数
                        add_score = scan_model.auto_grading
                        processor.add_comments_and_score(
                            processing_path,  # 处理的文件路径（可能是转换后的PDF）
                            comments,   # 评语
                            score,      # 分数
                            intermediate_file_path,  # 输出文件路径
                            add_score   # 是否添加分数
                        )
                        
                        # 生成最终的graded文件
                        final_output_path = os.path.join(graded_reports_dir, f"{base_filename}_graded{output_ext}")
                        
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
                        if ext in ['.doc', '.docx'] and os.path.exists(converted_pdf_path):
                            try:
                                os.remove(converted_pdf_path)
                                logger.info(f"已清理临时转换文件: {converted_pdf_path}")
                            except Exception as e:
                                logger.warning(f"清理临时转换文件失败: {e}")
                        
                        # 确保只保留最终的graded文件，删除可能存在的旧文件
                        old_file_path = os.path.join(graded_reports_dir, f"{base_filename}{output_ext}")
                        if os.path.exists(old_file_path):
                            try:
                                os.remove(old_file_path)
                                logger.info(f"已清理旧文件: {old_file_path}")
                            except Exception as e:
                                logger.warning(f"清理旧文件失败: {e}")

                except Exception as e:
                    print(f"评估过程中出错: {str(e)}")
                    documents_content.append({
                        "filename": filename,
                        "type": "PDF" if ext == '.pdf' else "Word",
                        "content": content[:500],
                        "status": "未知",
                        "score": 0,
                        "comments": "评估过程中出错",
                        "size": os.path.getsize(file_path),
                        "ai_failed": False
                    })



        # 创建综合报告CSV文件，包含所有报告的详细信息
        try:
            # 生成综合CSV文件名（使用时间戳确保唯一性）
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            comprehensive_csv_filename = f"报告评分汇总_{timestamp}.csv"
            
            # 将CSV文件保存到graded_reports目录，这样在压缩时会包含在内
            comprehensive_csv_path = os.path.join(graded_reports_dir, comprehensive_csv_filename)

            # 写入综合CSV文件
            with open(comprehensive_csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['学号', '姓名', '实验名称', '得分', '评语', '状态', '备注']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                
                # 遍历所有处理过的文档
                for doc in documents_content:
                    # 从文件名中提取信息
                    filename = doc['filename']
                    parts = filename.split('-')
                    
                    # 尝试提取学号、姓名、实验名称
                    student_id = "未知"
                    student_name = "未知"
                    experiment_name = "未知"
                    
                    if len(parts) >= 3:
                        # 假设文件名格式：班级-学号-姓名-实验名称.pdf
                        student_id = parts[1]  # 学号
                        student_name = parts[2].split('.')[0]  # 姓名
                        # 提取实验名称（移除文件扩展名）
                        experiment_name = "-".join(parts[3:]).split('.')[0] if len(parts) > 3 else "未知"
                    else:
                        # 如果文件名格式不符合预期，使用文件名作为实验名称
                        student_name = filename.split('.')[0]
                        experiment_name = filename.split('.')[0]
                    
                    # 获取报告状态和备注
                    status = doc['status']
                    remarks = ""
                    if status == "未知" or status == "不合格":
                        remarks = doc.get('comments', '未能正确识别判断')
                    
                    # 如果AI评估失败，在备注中标记
                    if doc.get('ai_failed', False):
                        if remarks:
                            remarks += "；AI评估失败（已重试10次）"
                        else:
                            remarks = "AI评估失败（已重试10次）"
                    
                    # 写入CSV行
                    writer.writerow({
                        '学号': student_id,
                        '姓名': student_name,
                        '实验名称': experiment_name,
                        '得分': doc['score'],
                        '评语': doc['comments'],
                        '状态': status,
                        '备注': remarks
                    })
            
            print(f"综合报告评分汇总CSV已生成: {comprehensive_csv_path}")
        except Exception as csv_error:
            print(f"生成综合CSV文件失败: {str(csv_error)}")

        # 返回结果
        return {
            "message": f"成功扫描了 {len(documents_content)} 个文档",
            "failed_count": len(failed_reports),
            "documents": documents_content
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
    save_criteria_to_file(GRADING_CRITERIA)
    logger.info(f"新的评分标准已设置并保存")
    return {"message": "评分标准已成功更新"}


@app.get("/api/criteria")
async def get_criteria():
    """获取当前的评分标准"""
    return {"criteria": GRADING_CRITERIA}


@app.post("/api/criteria/reset")
async def reset_criteria():
    """恢复默认的评分标准"""
    global GRADING_CRITERIA
    GRADING_CRITERIA = DEFAULT_GRADING_CRITERIA
    save_criteria_to_file(GRADING_CRITERIA)
    logger.info(f"已恢复默认评分标准")
    return {"message": "评分标准已恢复为默认值"}


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
