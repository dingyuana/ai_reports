#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import json
import os
import shutil
import csv
from datetime import datetime
from typing import Optional, List
import uvicorn
from pydantic import BaseModel

# 导入项目模块
from grading_system import GradingSystem
from config import REPORTS_DIR, OUTPUT_DIR, API_CONFIG

# 创建FastAPI应用
app = FastAPI(
    title="实验报告自动批阅系统API",
    description="提供实验报告自动批阅的RESTful API接口",
    version="1.0.0",
)

# 创建评分系统实例
grading_system = GradingSystem(reports_dir=REPORTS_DIR, output_dir=OUTPUT_DIR, api_config=API_CONFIG)

# 定义请求模型
class CriteriaModel(BaseModel):
    criteria: str

# 根路径
@app.get("/")
async def root():
    return {"message": "实验报告自动批阅系统API"}

# API路径前缀
@app.get("/api")
async def api_root():
    return {
        "message": "实验报告自动批阅系统API",
        "endpoints": [
            "/api/set_grading_criteria",
            "/api/upload_report",
            "/api/reports",
            "/api/process_all_reports",
            "/api/summary/download"
        ]
    }

# 设置评分标准
@app.post("/api/set_grading_criteria")
async def set_grading_criteria(criteria_model: CriteriaModel):
    try:
        grading_system.set_grading_criteria(criteria_model.criteria)
        return {"status": "success", "message": "评分标准设置成功"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置评分标准失败: {str(e)}")

# 上传并评分单个报告
@app.post("/api/upload_report")
async def upload_report(
    file: UploadFile = File(...),
    metadata: str = Form(...)
):
    try:
        # 解析元数据
        metadata_dict = json.loads(metadata)
        
        # 保存上传的文件
        file_path = os.path.join(REPORTS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 处理报告
        result = grading_system.grade_report(file_path, metadata_dict)
        
        return {
            "status": "success",
            "message": "报告评分成功",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告评分失败: {str(e)}")

# 获取所有报告列表
from urllib.parse import unquote

@app.get("/api/reports/")
async def get_reports(directory: Optional[str] = None):
    try:
        if directory:
            # URL解码目录名称
            decoded_directory = unquote(directory)
            reports = grading_system.get_all_reports(decoded_directory)
        else:
            # 如果没有提供目录，则获取根目录的报告
            reports = grading_system.get_all_reports()
        return {"status": "success", "reports": reports}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取报告列表失败: {str(e)}")

# 处理所有报告
@app.post("/api/process_all_reports")
async def process_all_reports():
    try:
        results = grading_system.process_all_reports()
        return {
            "status": "success",
            "message": f"成功处理 {len(results)} 份报告",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理报告失败: {str(e)}")

# 批注报告请求模型
class AnnotateScanModel(BaseModel):
    directory: str

@app.post("/api/annotate")
async def annotate_report(scan_model: AnnotateScanModel):
    try:
        # 解码目录名称
        decoded_directory = unquote(scan_model.directory)
        scan_path = os.path.join(REPORTS_DIR, decoded_directory)
        
        # 检查目录是否存在
        if not os.path.exists(scan_path):
            raise HTTPException(status_code=404, detail=f"目录不存在: {decoded_directory}")
        
        # 存储所有文档的内容
        documents_content = []
        # 存储不合格的报告
        failed_reports = []
        
        # 遍历指定目录
        for filename in os.listdir(scan_path):
            file_path = os.path.join(scan_path, filename)
            
            # 检查是否是文件
            if not os.path.isfile(file_path):
                continue
                
            # 获取文件扩展名
            ext = os.path.splitext(filename)[1].lower()
            
            # 只处理PDF和Word文档
            if ext not in ['.pdf', '.doc', '.docx']:
                continue
                
            try:
                # 使用GradingSystem的文档处理器读取内容
                if ext in grading_system.document_processors:
                    processor = grading_system.document_processors[ext]
                    content = processor.extract_text(file_path)
                else:
                    continue  # 跳过不支持的文件类型
                
                # 判断报告是否合格
                is_qualified = len(content) >= 100
                report_status = "合格" if is_qualified else "不合格"
                
                # 将文件名和内容添加到结果列表
                documents_content.append({
                    "filename": filename,
                    "type": "PDF" if ext == '.pdf' else "Word",
                    "content": content if is_qualified else "报告不合格",
                    "status": report_status,
                    "size": os.path.getsize(file_path)
                })
                
                # 如果报告不合格，添加到不合格列表
                if not is_qualified:
                    # 从文件名中提取用户名（假设格式为"用户名_其他内容.扩展名"）
                    username = filename.split('_')[0] if '_' in filename else filename.split('.')[0]
                    failed_reports.append({
                        "username": username,
                        "status": "不合格",
                        "filename": filename
                    })
                    
            except Exception as doc_error:
                # 如果处理某个文档失败，记录错误但继续处理其他文档
                documents_content.append({
                    "filename": filename,
                    "type": "PDF" if ext == '.pdf' else "Word",
                    "error": str(doc_error),
                    "status": "处理失败",
                    "size": os.path.getsize(file_path)
                })
        
        # 如果有不合格的报告，将它们保存为CSV文件
        csv_path = None
        if failed_reports:
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
        
        return {
            "message": f"成功扫描了 {len(documents_content)} 个文档",
            "documents": documents_content,
            "failed_count": len(failed_reports),
            "csv_file": csv_path if failed_reports else None
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文档扫描失败: {str(e)}")

# 下载评分汇总表
@app.get("/api/summary/download")
async def download_summary():
    try:
        summary_path = grading_system.generate_summary()
        return FileResponse(
            path=summary_path,
            filename="评分汇总.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载评分汇总表失败: {str(e)}")

# 主函数
def main():
    uvicorn.run("api_server:app", host="127.0.0.1", port=8000, reload=True)

if __name__ == "__main__":
    main()
