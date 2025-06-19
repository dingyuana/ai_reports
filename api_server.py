#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
import json
import os
import shutil
from typing import Optional
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
        grading_system.set_criteria(criteria_model.criteria)
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
@app.get("/api/reports")
async def get_reports():
    try:
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
