import os
import json
import csv
from datetime import datetime
from urllib.parse import unquote
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from grading_system import GradingSystem
from volcenginesdkarkruntime import Ark
from config import API_CONFIG
import os

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
OUTPUT_DIR = "output"    # 输出目录

# 创建评分系统实例
grading_system = GradingSystem(REPORTS_DIR, OUTPUT_DIR, API_CONFIG)

# 配置ARK模型
ark_api_key = os.getenv('ARK_API_KEY')
if not ark_api_key:
    raise ValueError("ARK_API_KEY environment variable is not set")
ark = Ark(api_key=ark_api_key)

class AnnotateScanModel(BaseModel):
    directory: str

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
    调用ARK模型进行评估，支持重试和超时
    
    Args:
        prompt: 提示文本
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        
    Returns:
        模型响应文本，失败时返回None
    """
    for attempt in range(max_retries):
        try:
            print(f"尝试调用ARK模型 (尝试 {attempt + 1}/{max_retries})")
            
            # 定义同步调用函数
            def sync_call():
                # 使用chat.completions.create替代invoke方法
                completion = ark.chat.completions.create(
                    model="doubao-1-5-thinking-pro-250415",
                    messages=[{"role": "user", "content": prompt}],
                    timeout=timeout
                )
                # 提取回复内容
                if hasattr(completion.choices[0].message, "content"):
                    return completion.choices[0].message.content
                return str(completion.choices[0].message)
            
            # 在线程池中执行API调用，避免阻塞事件循环
            start_time = time.time()
            response = await run_in_threadpool(sync_call)
            elapsed_time = time.time() - start_time
            
            print(f"ARK模型调用成功，耗时: {elapsed_time:.2f}秒")
            return response
            
        except Exception as e:
            print(f"ARK模型调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            
            # 如果已经是最后一次尝试，则返回None
            if attempt == max_retries - 1:
                print(f"ARK模型调用失败，已达到最大重试次数: {max_retries}")
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
                请评估以下实验报告的质量，考虑以下方面：
                1. 内容完整性（是否包含实验目的、步骤、结果等必要部分）
                2. 格式规范性（标题、段落、图表等是否规范）
                3. 内容相关性（内容是否与实验主题相关）
                4. 原创性（是否存在抄袭嫌疑）
                
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

                    # 保存评估结果到JSON文件
                    json_path = os.path.join(OUTPUT_DIR, f"{filename}_result.json")
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
                # 创建输出目录（如果不存在）
                if not os.path.exists(OUTPUT_DIR):
                    os.makedirs(OUTPUT_DIR)

                # 生成CSV文件名（使用时间戳确保唯一性）
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                csv_filename = f"不合格报告_{timestamp}.csv"
                csv_path = os.path.join(OUTPUT_DIR, csv_filename)

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

        return {
            "message": f"成功扫描了 {len(documents_content)} 个文档",
            "documents": documents_content,
            "failed_count": len(failed_reports),
            "csv_file": csv_path if failed_reports else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理报告时出错: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
