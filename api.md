# API 接口文档

## API 接口一览表

| 序号 | 接口 | 方法 | 描述 | 状态 |
|------|------|------|------|------|
| 1 | /api/upload | POST | 上传报告文件 | 已实现 |
| 2 | /api/annotate | POST | 扫描指定目录下的报告文件 | 已实现 |
| 3 | /api/download/{filename} | GET | 下载报告文件 | 已实现 |
| 4 | /api/download/annotated/{filename} | GET | 下载批注版报告 | 已实现 |
| 5 | /api/reports/ | GET | 获取指定目录下的报告列表 | 已实现 |

## 接口列表

### 1. 上传报告文件
- **URL**: `/upload`
- **方法**: `POST`
- **参数**: 
  - `file`: 报告文件
- **响应**:
  ```json
  {
    "message": "文件上传成功",
    "filename": "张三_物理实验报告.pdf"
  }
  ```

### 2. 扫描指定目录下的报告文件
- **URL**: `/api/annotate`
- **方法**: `POST`
- **请求体**:
  ```json
  {
    "directory": "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一"
  }
  ```
- **响应**:
  ```json
  {
    "message": "成功扫描了 X 个文档",
    "documents": [
      {
        "filename": "张三_物理实验报告.pdf",
        "type": "PDF",
        "content": "文档内容预览...",
        "status": "合格",
        "size": 12345
      },
      {
        "filename": "李四_实验报告.docx",
        "type": "Word",
        "content": "报告不合格",
        "status": "不合格",
        "size": 67890
      }
    ],
    "failed_count": 1,
    "csv_file": "output/不合格报告_20230615_123045.csv"
  }
  ```
- **说明**:
  1. `directory`参数需要使用`encodeURIComponent()`进行编码，因为可能包含特殊字符
  2. 接口会扫描指定目录下的所有PDF和Word文档（支持.pdf、.doc、.docx格式）
  3. 内容少于100字符的报告将被标记为"不合格"
  4. 所有不合格的报告将被导出为CSV文件，包含用户名、状态和文件名
  5. `failed_count`表示不合格报告的数量
  6. `csv_file`表示CSV文件的路径，如果没有不合格报告则为null
  7. 如果某个文档处理失败，将返回错误信息而不是内容

### 3. 获取指定目录下的报告列表
- **URL**: `/reports/`
- **方法**: `GET`
- **查询参数**:
  - `directory`: 可选，目录名称 (如: "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一")
  - 如果不提供目录参数，则返回根目录下的报告列表
- **响应**:
  ```json
  [
    {
      "filename": "张三_物理实验报告.pdf",
      "path": "/path/to/reports/内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一/张三_物理实验报告.pdf",
      "status": "未处理"
    },
    ...
  ]
  ```

### 4. 下载报告文件
- **URL**: `/download/{filename}`
- **方法**: `GET`
- **参数**:
  - `filename`: 报告文件名
- **响应**: 文件流

### 5. 下载批注版报告
- **URL**: `/download/annotated/{filename}`
- **方法**: `GET`
- **参数**:
  - `filename`: 批注版报告文件名
- **响应**: 文件流

## 使用示例

### 获取指定目录下的报告列表
```javascript
// 获取指定目录下的报告列表
const directory = "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一";
const encodedDirectory = encodeURIComponent(directory);

fetch(`/api/reports/?directory=${encodedDirectory}`)
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));

// 获取根目录下的报告列表
fetch('/api/reports/')
  .then(response => response.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
```

注意：
1. 由于目录名称可能包含特殊字符，请使用`encodeURIComponent()`函数对目录参数进行编码
2. 如果不提供directory参数，将返回根目录下的报告列表

### 上传报告文件
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('/api/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data))
.catch(error => console.error('Error:', error));
```

### 扫描指定目录下的报告文件
```javascript
// 扫描指定目录下的报告文件
const directory = "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一";
const encodedDirectory = encodeURIComponent(directory);

fetch('/api/annotate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    directory: encodedDirectory
  })
})
.then(response => response.json())
.then(data => {
  console.log(`成功扫描了 ${data.documents.length} 个文档`);
  
  // 处理文档列表
  data.documents.forEach(doc => {
    console.log(`文件名: ${doc.filename}, 类型: ${doc.type}, 状态: ${doc.status}, 大小: ${doc.size} 字节`);
    console.log(`内容预览: ${doc.content.substring(0, 100)}...`);
  });
  
  // 处理不合格报告CSV文件
  if (data.failed_count > 0 && data.csv_file) {
    console.log(`发现 ${data.failed_count} 个不合格报告，已导出到 ${data.csv_file}`);
    
    // 可以提供下载CSV文件的链接
    const csvLink = document.createElement('a');
    csvLink.href = `/${data.csv_file}`;
    csvLink.download = data.csv_file.split('/').pop();
    csvLink.textContent = '下载不合格报告CSV';
    document.body.appendChild(csvLink);
  } else {
    console.log('没有发现不合格报告');
  }
})
.catch(error => console.error('Error:', error));
```

### 下载报告文件
```javascript
fetch('/api/download/张三_物理实验报告.pdf')
  .then(response => response.blob())
  .then(blob => {
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '张三_物理实验报告.pdf';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
  })
  .catch(error => console.error('Error:', error));
```
