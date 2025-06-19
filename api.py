# 实验报告自动批阅系统API文档

## 概述
本API提供实验报告自动批阅功能，支持报告上传、批阅标准设置、报告处理和结果下载等功能。

## 基础信息
- **API Base URL**: `http://localhost:8000/api`
- **文档地址**: `http://localhost:8000/docs` (Swagger UI)
- **响应格式**: JSON

## 认证
本API目前不需要认证。在生产环境中，建议添加适当的认证机制。

## 接口列表

### 1. 设置批阅标准
- **URL**: `/set_grading_criteria`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "criteria": "1. 实验目的明确性 (20分): 学生是否清晰阐述了实验目的?\n2. 实验方法合理性 (20分): 实验步骤是否完整且合理?\n..."
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "message": "批阅标准已设置"
  }
  ```

### 2. 上传并批阅单个报告
- **URL**: `/upload_report`
- **方法**: `POST`
- **请求参数**:
  - `file`: 报告文件 (multipart/form-data)
  - `metadata`: 报告元数据 (JSON格式)
    ```json
    {
      "student_name": "张三",
      "report_title": "物理实验报告"
    }
    ```
  - `criteria` (可选): 临时批阅标准 (字符串)
- **响应**:
  ```json
  {
    "score": 85,
    "comments": "实验目的明确，方法合理，但数据分析部分不够深入...",
    "report_path": "/path/to/annotated_report.pdf"
  }
  ```

### 3. 获取所有报告列表
- **URL**: `/reports`
- **方法**: `GET`
- **响应**:
  ```json
  [
    {
      "filename": "张三_物理实验报告.pdf",
      "student_name": "张三",
      "file_path": "/path/to/reports/张三_物理实验报告.pdf",
      "has_annotation": true,
      "annotation_path": "/path/to/annotated/张三_物理实验报告_批注版.pdf"
    },
    ...
  ]
  ```

### 4. 下载报告文件
- **URL**: `/report/{report_id}/download`
- **方法**: `GET`
- **参数**:
  - `report_id`: 报告文件名 (如: "张三_物理实验报告.pdf")
- **响应**: 文件下载

### 5. 下载批注版报告文件
- **URL**: `/report/{report_id}/annotation/download`
- **方法**: `GET`
- **参数**:
  - `report_id`: 报告文件名 (如: "张三_物理实验报告.pdf")
- **响应**: 文件下载

### 6. 处理所有报告
- **URL**: `/process_all_reports`
- **方法**: `POST`
- **请求体** (可选):
  ```json
  {
    "criteria": "批阅标准字符串"
  }
  ```
- **响应**:
  ```json
  {
    "status": "success",
    "message": "所有报告处理完成",
    "summary_path": "/path/to/summary/评分汇总表.xlsx"
  }
  ```

### 7. 下载评分汇总表
- **URL**: `/summary/download`
- **方法**: `GET`
- **响应**: 文件下载

### 8. 健康检查
- **URL**: `/health`
- **方法**: `GET`
- **响应**:
  ```json
  {
    "status": "ok",
    "message": "服务正常运行"
  }
  ```

## 错误处理
当发生错误时，API将返回以下格式的JSON响应:{
  "detail": "错误描述信息"
}
常见错误代码:
- 400: 错误的请求格式
- 404: 请求的资源不存在
- 500: 服务器内部错误

## 使用示例
以下是使用Python的`requests`库调用API的示例:
import requests

# 设置批阅标准
criteria = {
    "criteria": "1. 实验目的明确性 (20分)\n2. 实验方法合理性 (20分)\n3. 实验数据准确性 (20分)\n4. 数据分析深度 (20分)\n5. 结论合理性 (20分)"
}
response = requests.post("http://localhost:8000/api/set_grading_criteria", json=criteria)
print(response.json())

# 上传并批阅报告
file_path = "path/to/student_report.pdf"
metadata = {
    "student_name": "李四",
    "report_title": "化学实验报告"
}

with open(file_path, "rb") as f:
    files = {"file": f}
    data = {"metadata": json.dumps(metadata)}
    response = requests.post("http://localhost:8000/api/upload_report", files=files, data=data)
    print(response.json())

# 获取报告列表
response = requests.get("http://localhost:8000/api/reports")
print(response.json())