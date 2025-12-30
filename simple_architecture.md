# AI实验报告自动批阅系统 - 简化架构图

## 系统架构

```mermaid
graph TB
    subgraph "客户端"
        Web[Web界面]
    end
    
    subgraph "应用服务层"
        API[API服务器<br/>FastAPI]
        Core[核心系统<br/>GradingSystem]
        AI[AI评分器<br/>AIGrader]
        Doc[文档处理器<br/>DocumentProcessor]
        File[文件管理器<br/>FileManager]
    end
    
    subgraph "外部服务"
        AI_SVC[AI服务<br/>豆包大模型]
    end
    
    subgraph "数据层"
        Stu[学生报告目录]
        Grad[已评分报告目录]
        Out[输出数据目录]
    end
    
    Web --> API
    API --> Core
    Core --> AI
    Core --> Doc
    Core --> File
    AI --> AI_SVC
    Doc --> Stu
    File --> Stu
    File --> Grad
    File --> Out
```

## 数据流向

```mermaid
flowchart LR
    subgraph "输入"
        A[学生报告文件<br/>PDF/DOC/DOCX]
    end
    
    subgraph "处理"
        B[文档处理<br/>提取文本]
        C[AI评分<br/>生成评语和分数]
        D[添加标注<br/>评语和对号]
    end
    
    subgraph "输出"
        E[已评分报告<br/>PDF格式]
        F[评分汇总<br/>Excel/CSV]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    D --> F
```

## 部署架构

```mermaid
graph LR
    subgraph "外部访问"
        User[用户]
        Internet[互联网]
    end
    
    subgraph "Nginx层"
        Nginx[Nginx<br/>反向代理/SSL]
    end
    
    subgraph "应用层"
        Docker[Docker容器<br/>AI报告系统]
    end
    
    subgraph "监控层"
        Monitor[监控系统<br/>Prometheus+Grafana]
    end
    
    User <--> Internet
    Internet --> Nginx
    Nginx --> Docker
    Monitor -.-> Docker
```

## 模块关系

- **GradingSystem**: 核心协调器，管理整个评分流程
- **DocumentProcessor**: 处理不同格式文档（PDF/Word）
- **AIGrader**: 与AI服务交互，获取评分和评语
- **FileManager**: 管理文件存储和检索
- **API Server**: 提供REST API接口
- **Frontend**: 提供Web用户界面

该系统采用模块化设计，各组件职责清晰，易于维护和扩展。