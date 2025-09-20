# Requirements 说明

本项目提供了两个不同的requirements文件，以适应不同的部署环境：

## 文件说明

### requirements.txt
- **用途**: Windows开发环境
- **包含**: 所有依赖，包括Windows特定的包（pywin32, comtypes）
- **适用场景**: 
  - Windows本地开发
  - Windows服务器部署
  - 需要完整Word文档处理功能（.doc文件支持）

### requirements-linux.txt
- **用途**: Linux/Docker环境
- **包含**: 跨平台兼容的依赖，排除Windows特定包
- **适用场景**:
  - Docker容器部署
  - Linux服务器部署
  - CI/CD环境

## 功能差异

### Windows环境 (requirements.txt)
✅ 支持PDF文档处理  
✅ 支持Word .docx文档处理  
✅ 支持Word .doc文档处理  
✅ Word转PDF功能  

### Linux/Docker环境 (requirements-linux.txt)
✅ 支持PDF文档处理  
✅ 支持Word .docx文档处理  
❌ 不支持Word .doc文档处理（会显示错误提示）  
❌ 不支持Word转PDF功能  

## 安装方法

### Windows环境
```bash
pip install -r requirements.txt
```

### Linux/Docker环境
```bash
pip install -r requirements-linux.txt
```

### Docker构建
Dockerfile已配置使用`requirements-linux.txt`：
```dockerfile
COPY requirements-linux.txt requirements.txt ./
RUN pip install -r requirements-linux.txt
```

## 依赖说明

### 核心依赖
- **FastAPI**: Web框架
- **uvicorn**: ASGI服务器
- **PyPDF2**: PDF处理
- **pdfplumber**: PDF文本提取
- **reportlab**: PDF生成和编辑
- **python-docx**: Word .docx文档处理
- **pandas**: 数据处理
- **requests**: HTTP客户端
- **volcengine-python-sdk**: AI服务SDK

### Windows特定依赖
- **pywin32**: Windows API访问
- **comtypes**: COM组件访问
- 用于处理.doc文件和Word转PDF功能

### 监控和工具依赖
- **psutil**: 系统监控
- **cryptography**: 加密功能
- **pillow**: 图像处理
- **matplotlib**: 图表生成

## 故障排除

### 在Linux上遇到Windows依赖错误
如果在Linux环境中使用了`requirements.txt`，可能会遇到以下错误：
```
ERROR: Could not find a version that satisfies the requirement pywin32
```

**解决方案**: 使用`requirements-linux.txt`

### .doc文件处理失败
在Linux/Docker环境中，.doc文件会显示错误信息：
```
Error: Cannot process .doc files in this environment. Please convert to .docx format.
```

**解决方案**: 
1. 将.doc文件转换为.docx格式
2. 或在Windows环境中运行系统

### Word转PDF功能不可用
在Linux/Docker环境中，Word转PDF功能会失败。

**解决方案**:
1. 使用在线转换工具预先转换
2. 或在Windows环境中运行系统
3. 或集成LibreOffice等开源替代方案

## 开发建议

1. **本地开发**: 使用`requirements.txt`获得完整功能
2. **生产部署**: 使用Docker和`requirements-linux.txt`
3. **文档格式**: 推荐使用.docx和.pdf格式以获得最佳兼容性
4. **测试**: 在目标部署环境中测试所有功能

## 版本兼容性

- **Python**: 3.9+
- **操作系统**: Windows 10+, Linux (Ubuntu 18.04+, CentOS 7+)
- **Docker**: 20.10+
- **Docker Compose**: 2.0+