# 实验报告自动批阅系统

## 项目概述
这是一个基于AI的实验报告自动批阅系统，能够自动处理和评分学生提交的实验报告。系统支持PDF和Word格式的报告，可以批量处理报告并生成评分汇总。

## 主要功能

### 文档处理
- 支持多种格式的实验报告：
  - PDF文件（.pdf）
  - Word文档（.doc, .docx）
- 自动提取报告文本内容
- 生成带有评语和分数的标注版PDF

### 智能评分
- 基于AI的智能评分系统
- 五个维度的综合评分：
  1. 实验目的明确性 (20分)
  2. 实验方法合理性 (20分)
  3. 数据分析准确性 (20分)
  4. 结论合理性 (20分)
  5. 报告格式规范性 (20分)
- 自动添加评语和对号标注
- 支持自定义评分标准

### 批量处理
- 自动处理整个目录的报告
- 并行处理提高效率
- 错误处理和日志记录
- 生成评分汇总Excel表格，包含：
  - 学生姓名
  - 文件名
  - 总分
  - 详细评语
  - 标注版报告路径

### API支持
- RESTful API接口
- 灵活的评分标准设置
- 单个或批量报告处理
- 实时处理状态查询
- 评分结果下载

## 评分流程

### 1. 文档处理阶段
1. 系统从指定目录读取学生报告文件
2. 根据文件类型（PDF或Word）选择相应的处理器
3. 提取文档中的文本内容
4. 解析学生信息（如姓名、学号等）

### 2. AI评分阶段
1. 将提取的文本内容发送到AI评分模块
2. AI根据预设的评分标准对报告进行分析
3. 评分维度包括：
   - 实验目的明确性
   - 实验方法合理性
   - 数据分析准确性
   - 结论合理性
   - 报告格式规范性
4. AI生成详细评语和各项分数

### 3. 结果处理阶段
1. 系统接收AI评分结果
2. 在报告上添加评语和分数标注
3. 生成带有评分信息的新版报告
4. 将评分结果保存到汇总表格中

### 4. 汇总报告生成
1. 收集所有已评分报告的结果
2. 生成Excel格式的评分汇总表
3. 包含学生信息、各项分数、总分和评语

## API使用指南

系统提供了完整的RESTful API接口，可以通过HTTP请求使用系统功能。

### API基础信息
- **基础URL**: `http://localhost:8000/api`
- **API文档**: `http://localhost:8000/docs` (Swagger UI)
- **响应格式**: JSON

### 主要API端点

#### 1. 设置评分标准
```http
POST /api/set_grading_criteria
Content-Type: application/json

{
  "criteria": "1. 实验目的明确性 (20分)\n2. 实验方法合理性 (20分)\n3. 数据分析准确性 (20分)\n4. 结论合理性 (20分)\n5. 报告格式规范性 (20分)"
}
```

#### 2. 上传并评分单个报告
```http
POST /api/upload_report
Content-Type: multipart/form-data

file: [报告文件]
metadata: {"student_name": "张三", "report_title": "物理实验报告"}
```

#### 3. 处理所有报告
```http
POST /api/process_all_reports
```

#### 4. 下载评分汇总表
```http
GET /api/summary/download
```

### Python示例代码
```python
import requests
import json

# 设置API基础URL
BASE_URL = "http://localhost:8000/api"

# 设置评分标准
def set_criteria():
    criteria = {
        "criteria": "1. 实验目的明确性 (20分)\n2. 实验方法合理性 (20分)\n3. 数据分析准确性 (20分)\n4. 结论合理性 (20分)\n5. 报告格式规范性 (20分)"
    }
    response = requests.post(f"{BASE_URL}/set_grading_criteria", json=criteria)
    return response.json()

# 上传并评分单个报告
def grade_report(file_path, student_name, report_title):
    metadata = {
        "student_name": student_name,
        "report_title": report_title
    }
    
    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {"metadata": json.dumps(metadata)}
        response = requests.post(f"{BASE_URL}/upload_report", files=files, data=data)
    
    return response.json()

# 处理所有报告
def process_all():
    response = requests.post(f"{BASE_URL}/process_all_reports")
    return response.json()

# 下载评分汇总表
def download_summary():
    response = requests.get(f"{BASE_URL}/summary/download")
    # 保存文件
    with open("评分汇总.xlsx", "wb") as f:
        f.write(response.content)
    return "评分汇总表已下载"
```

## 系统架构
系统由以下主要模块组成：

### 核心模块
1. **GradingSystem (grading_system.py)**
   - 系统的核心类，协调各个组件的工作
   - 处理报告评分流程
   - 生成评分汇总

2. **AIGrader (ai_grader.py)**
   - 实现AI评分逻辑
   - 根据评分标准对报告内容进行分析和打分
   - 生成评语和反馈

3. **DocumentProcessor (document_processor.py)**
   - 处理不同格式的文档（PDF和Word）
   - 提取文档内容
   - 支持文档格式转换

4. **FileManager (file_manager.py)**
   - 管理文件的存储和组织
   - 处理报告文件的读取和保存
   - 生成评分汇总表格

### API接口 (api.py)
提供RESTful API接口，支持以下功能：
- 设置批阅标准
- 上传并批阅单个报告
- 获取报告列表
- 下载报告文件
- 批量处理报告
- 下载评分汇总表

## 目录结构
```
├── ai_grader.py          # AI评分模块
├── api.py               # API接口定义
├── config.py            # 配置文件
├── create_test_doc.py   # 创建测试文档的脚本
├── document_processor.py # 文档处理模块
├── file_manager.py      # 文件管理模块
├── grading_system.py    # 评分系统核心
├── main.py             # 主程序入口
├── test_main.http      # API测试文件
├── graded_reports/     # 已评分报告存储目录
└── student_reports/    # 学生报告存储目录
```

## API接口说明

### 基础信息
- **Base URL**: `http://localhost:8000/api`
- **文档地址**: `http://localhost:8000/docs` (Swagger UI)
- **响应格式**: JSON

### 主要接口

1. **设置批阅标准**
   - 端点: `/set_grading_criteria`
   - 方法: POST
   - 功能: 设置评分标准

2. **上传并批阅报告**
   - 端点: `/upload_report`
   - 方法: POST
   - 功能: 上传并评分单个报告

3. **获取报告列表**
   - 端点: `/reports`
   - 方法: GET
   - 功能: 获取所有报告信息

4. **处理所有报告**
   - 端点: `/process_all_reports`
   - 方法: POST
   - 功能: 批量处理所有报告

5. **下载评分汇总**
   - 端点: `/summary/download`
   - 方法: GET
   - 功能: 下载评分汇总表

详细的API文档请参考 api.py 文件。

## 使用说明

### 环境要求
- Python 3.7+
- 依赖包：
  - pandas：数据处理和生成评分汇总
  - python-docx：Word文档处理
  - PyPDF2：PDF文档处理
  - requests：API请求
  - fastapi：API服务器（如果使用API功能）
  - uvicorn：ASGI服务器（如果使用API功能）

### 配置说明
系统配置在`config.py`文件中定义，主要包括：

```python
# 文件路径配置
STUDENT_REPORTS_DIR = "student_reports"  # 学生报告目录
GRADED_REPORTS_DIR = "graded_reports"    # 评分后报告目录
SUMMARY_FILE = "grading_summary.xlsx"    # 评分汇总文件名

# API配置
API_HOST = "localhost"  # API主机地址
API_PORT = 8000         # API端口

# 评分配置
DEFAULT_CRITERIA = """
1. 实验目的明确性 (20分)
2. 实验方法合理性 (20分)
3. 数据分析准确性 (20分)
4. 结论合理性 (20分)
5. 报告格式规范性 (20分)
"""
```

您可以根据需要修改这些配置。

### 安装步骤
1. 克隆项目代码
2. 安装依赖：
```bash
pip install -r requirements.txt
```

### 使用方法

#### 1. 命令行方式
1. 将学生报告放入 student_reports 目录
2. 运行主程序：
```bash
python main.py
```
系统将：
- 自动设置默认的评分标准（包括实验目的、方法、数据分析等五个方面）
- 处理所有报告并生成评分
- 在指定目录生成评分汇总表

#### 2. API方式
您可以通过API接口使用系统功能，更灵活地控制评分过程。

启动API服务器：
```bash
# 方法1：使用uvicorn启动
uvicorn api_server:app --reload

# 方法2：直接运行api_server.py
python api_server.py
```

API服务器启动后，您可以：
- 通过 http://localhost:8000/docs 访问API文档（Swagger UI）
- 通过 http://localhost:8000/redoc 访问API参考文档（ReDoc）
- 使用上述API接口进行操作

#### 3. 测试功能
系统提供了测试相关的工具：

1. **创建测试文档**
   使用 create_test_doc.py 可以生成测试用的实验报告：
   ```bash
   python create_test_doc.py
   ```
   这将创建一个包含基本实验报告结构的Word文档，用于测试系统功能。

2. **API测试**
   提供了 test_main.http 文件，可以使用HTTP客户端（如VS Code的REST Client插件）测试API功能：
   - 测试评分标准设置
   - 测试报告上传和处理
   - 测试批量处理功能
   - 测试评分汇总下载

### API使用示例
```python
import requests

# 设置批阅标准
criteria = {
    "criteria": "1. 实验目的明确性 (20分)\n2. 实验方法合理性 (20分)\n..."
}
response = requests.post("http://localhost:8000/api/set_grading_criteria", json=criteria)

# 处理所有报告
response = requests.post("http://localhost:8000/api/process_all_reports")
```

## 注意事项
- 确保报告文件格式正确（支持PDF和Word格式）
- 评分标准需要清晰定义
- 建议在处理大量报告时使用批量处理功能
- 评分结果保存在graded_reports目录下

## 开发说明
- 代码遵循PEP 8规范
- 使用类型注解确保代码可读性
- 包含详细的日志记录
- 模块化设计便于扩展

## 未来改进计划
1. 添加更多文档格式支持
2. 优化AI评分算法
3. 增加用户界面
4. 添加批注功能
5. 支持自定义评分模板
