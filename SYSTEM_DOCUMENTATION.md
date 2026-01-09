# AI 实验报告自动批阅系统 - 完整技术文档

## 目录
1. [系统概述](#系统概述)
2. [数据库设计](#数据库设计)
3. [后端架构](#后端架构)
4. [前端架构](#前端架构)
5. [API接口文档](#api接口文档)
6. [系统模块图](#系统模块图)
7. [业务流程泳道图](#业务流程泳道图)
8. [部署架构](#部署架构)

---

## 系统概述

### 系统简介
AI 实验报告自动批阅系统是一个基于人工智能的实验报告自动化评分平台，支持批量处理 PDF 和 Word 格式的实验报告，提供智能评分、评语生成、用户管理、数据统计等功能。

### 核心功能
- **智能批阅**：基于 AI 模型的自动评分和评语生成
- **多格式支持**：支持 PDF、Word（.doc/.docx）格式
- **用户管理**：多用户系统，支持管理员和普通用户
- **配置管理**：用户可自定义评分标准和分数范围
- **数据统计**：提供详细的使用数据统计和可视化
- **批量处理**：支持批量上传和批阅报告

### 技术栈
- **后端**：Python + FastAPI + PostgreSQL
- **前端**：HTML5 + CSS3 + JavaScript（原生）
- **AI服务**：豆包大模型（Doubao）
- **部署**：Docker + Docker Compose + Nginx

---

## 数据库设计

### 数据库表结构

#### 1. users（用户表）
存储系统用户信息，包括管理员和普通用户。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PRIMARY KEY | 用户ID，自增主键 |
| username | VARCHAR(50) | UNIQUE NOT NULL | 用户名，唯一 |
| password | VARCHAR(255) | NOT NULL | 密码（bcrypt加密） |
| email | VARCHAR(100) | UNIQUE | 邮箱地址 |
| role | VARCHAR(20) | DEFAULT 'user' | 角色：user/admin/super_admin |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否激活 |
| last_login | TIMESTAMP | NULL | 最后登录时间 |

**索引**：
- PRIMARY KEY: id
- UNIQUE: username
- UNIQUE: email

**触发器**：
- `update_users_updated_at`: 更新时自动更新 updated_at 字段

**默认数据**：
```sql
INSERT INTO users (username, password, email, role) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzW5W5W5W5', 'admin@example.com', 'super_admin')
```

---

#### 2. logs（日志表）
记录系统操作日志，用于审计和监控。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PRIMARY KEY | 日志ID，自增主键 |
| user_id | INTEGER | REFERENCES users(id) ON DELETE SET NULL | 用户ID |
| action | VARCHAR(100) | NOT NULL | 操作类型 |
| details | TEXT | NULL | 操作详情 |
| ip_address | VARCHAR(45) | NULL | IP地址 |
| user_agent | TEXT | NULL | 用户代理 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**：
- PRIMARY KEY: id
- INDEX: user_id (idx_logs_user_id)
- INDEX: created_at (idx_logs_created_at)

**外键约束**：
- user_id → users(id) ON DELETE SET NULL

---

#### 3. grading_records（批阅记录表）
记录报告批阅的历史记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PRIMARY KEY | 记录ID，自增主键 |
| user_id | INTEGER | REFERENCES users(id) ON DELETE SET NULL | 用户ID |
| directory_name | VARCHAR(255) | NOT NULL | 目录名称 |
| file_count | INTEGER | DEFAULT 0 | 文件数量 |
| qualified_count | INTEGER | DEFAULT 0 | 合格数量 |
| unqualified_count | INTEGER | DEFAULT 0 | 不合格数量 |
| min_score | FLOAT | NULL | 最低分数 |
| max_score | FLOAT | NULL | 最高分数 |
| model_used | VARCHAR(100) | NULL | 使用的AI模型 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引**：
- PRIMARY KEY: id
- INDEX: user_id (idx_grading_records_user_id)
- INDEX: created_at (idx_grading_records_created_at)

**外键约束**：
- user_id → users(id) ON DELETE SET NULL

---

#### 4. user_configs（用户配置表）
存储用户的个性化配置，包括评分标准和分数范围。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PRIMARY KEY | 配置ID，自增主键 |
| user_id | INTEGER | UNIQUE REFERENCES users(id) ON DELETE CASCADE | 用户ID |
| criteria | TEXT | NOT NULL | 评分标准 |
| min_score | INTEGER | DEFAULT 60 | 最低分数 |
| max_score | INTEGER | DEFAULT 95 | 最高分数 |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引**：
- PRIMARY KEY: id
- UNIQUE: user_id (idx_user_configs_user_id)

**外键约束**：
- user_id → users(id) ON DELETE CASCADE

---

### ER图

```mermaid
erDiagram
    users ||--o{ logs : "产生"
    users ||--o{ grading_records : "创建"
    users ||--|| user_configs : "拥有"
    
    users {
        int id PK
        string username UK
        string password
        string email UK
        string role
        timestamp created_at
        timestamp updated_at
        boolean is_active
        timestamp last_login
    }
    
    logs {
        int id PK
        int user_id FK
        string action
        text details
        string ip_address
        text user_agent
        timestamp created_at
    }
    
    grading_records {
        int id PK
        int user_id FK
        string directory_name
        int file_count
        int qualified_count
        int unqualified_count
        float min_score
        float max_score
        string model_used
        timestamp created_at
    }
    
    user_configs {
        int id PK
        int user_id FK
        text criteria
        int min_score
        int max_score
        timestamp created_at
        timestamp updated_at
    }
```

---

## 后端架构

### 核心模块

#### 1. api_server.py（API服务器）
FastAPI 应用主文件，提供所有 RESTful API 接口。

**主要功能**：
- 用户认证和授权（JWT）
- 用户管理（CRUD）
- 报告上传和批阅
- 配置管理
- 日志记录
- 统计数据

**关键类和函数**：
- `get_current_user()`: 获取当前登录用户
- `get_current_active_user()`: 获取当前激活用户
- `require_admin()`: 管理员权限验证
- `login()`: 用户登录
- `register()`: 用户注册

---

#### 2. user_manager.py（用户管理器）
管理用户相关的所有操作。

**主要方法**：
- `create_user()`: 创建新用户
- `authenticate_user()`: 用户认证
- `get_user_by_id()`: 根据ID获取用户
- `get_user_by_username()`: 根据用户名获取用户
- `get_all_users()`: 获取所有用户
- `update_user_role()`: 更新用户角色
- `activate_user()`: 激活用户
- `deactivate_user()`: 停用用户
- `delete_user()`: 删除用户
- `is_admin()`: 检查是否为管理员
- `is_super_admin()`: 检查是否为超级管理员

---

#### 3. config_manager.py（配置管理器）
管理用户配置和评分标准。

**主要方法**：
- `get_user_config()`: 获取用户配置
- `create_user_config()`: 创建用户配置
- `update_user_config()`: 更新用户配置
- `delete_user_config()`: 删除用户配置
- `get_default_config()`: 获取默认配置

---

#### 4. log_manager.py（日志管理器）
管理系统操作日志。

**主要方法**：
- `log_action()`: 记录操作日志
- `log_user_login()`: 记录用户登录
- `get_logs()`: 获取日志列表
- `get_user_logs()`: 获取用户日志
- `get_logs_by_action()`: 根据操作类型获取日志

---

#### 5. grading_system.py（批阅系统）
核心批阅逻辑，协调文档处理和AI评分。

**主要类**：
- `GradingSystem`: 批阅系统主类

**主要方法**：
- `grade_reports()`: 批量批阅报告
- `grade_single_report()`: 批阅单个报告
- `extract_scores()`: 提取评分结果

---

#### 6. document_processor.py（文档处理器）
处理各种格式的文档。

**主要类**：
- `DocumentProcessor`: 文档处理器基类
- `PDFProcessor`: PDF文档处理器
- `WordProcessor`: Word文档处理器

**主要方法**：
- `extract_text()`: 提取文档文本
- `add_annotations()`: 添加批注
- `save_annotated()`: 保存批注版文档

---

#### 7. ai_grader.py（AI评分器）
与AI服务交互，获取评分和评语。

**主要方法**：
- `grade_report()`: 评分报告
- `extract_score()`: 提取分数
- `generate_feedback()`: 生成评语

---

#### 8. file_manager.py（文件管理器）
管理文件存储和检索。

**主要方法**：
- `save_file()`: 保存文件
- `get_file()`: 获取文件
- `delete_file()`: 删除文件
- `list_files()`: 列出文件
- `export_to_excel()`: 导出到Excel

---

### 后端架构图

```mermaid
graph TB
    subgraph "API层"
        API[FastAPI Server<br/>api_server.py]
    end
    
    subgraph "业务逻辑层"
        UM[UserManager<br/>user_manager.py]
        CM[ConfigManager<br/>config_manager.py]
        LM[LogManager<br/>log_manager.py]
        GS[GradingSystem<br/>grading_system.py]
    end
    
    subgraph "数据处理层"
        DP[DocumentProcessor<br/>document_processor.py]
        AG[AIGrader<br/>ai_grader.py]
        FM[FileManager<br/>file_manager.py]
    end
    
    subgraph "数据存储层"
        DB[(PostgreSQL)]
        FS[文件系统<br/>reports/]
    end
    
    subgraph "外部服务"
        AI[豆包AI服务]
    end
    
    API --> UM
    API --> CM
    API --> LM
    API --> GS
    
    GS --> DP
    GS --> AG
    GS --> FM
    
    UM --> DB
    CM --> DB
    LM --> DB
    FM --> FS
    
    AG --> AI
    
    classDef api fill:#f96,stroke:#333,stroke-width:2px
    classDef business fill:#9f6,stroke:#333,stroke-width:2px
    classDef data fill:#69f,stroke:#333,stroke-width:2px
    classDef storage fill:#f9f,stroke:#333,stroke-width:2px
    classDef external fill:#999,stroke:#333,stroke-width:2px
    
    class API api
    class UM,CM,LM,GS business
    class DP,AG,FM data
    class DB,FS storage
    class AI external
```

---

## 前端架构

### 前端文件结构

```
front/
├── index.html              # 主页面
├── login.html              # 登录页面
├── admin_dashboard.html    # 管理员仪表板
├── admin_users.html        # 用户管理页面
├── admin_logs.html         # 日志查看页面
├── style.css               # 主样式
├── login.css               # 登录页面样式
├── admin.css               # 管理后台样式
├── script.js               # 主页面脚本
├── login.js               # 登录页面脚本
├── admin_dashboard.js      # 管理员仪表板脚本
├── admin_users.js          # 用户管理脚本
└── admin_logs.js           # 日志查看脚本
```

---

### 前端页面说明

#### 1. index.html（主页面）
用户批阅报告的主界面。

**功能模块**：
- 左侧：批阅要求配置
- 中间：已批阅报告列表
- 右侧：批阅操作和结果

**主要功能**：
- 配置评分标准
- 上传报告
- 查看批阅结果
- 下载批注版报告

---

#### 2. login.html（登录页面）
用户登录界面。

**主要功能**：
- 用户名/密码登录
- 表单验证
- 错误提示
- 记住登录状态

---

#### 3. admin_dashboard.html（管理员仪表板）
管理员数据统计和可视化界面。

**主要功能**：
- 系统概览统计
- 用户活跃度图表
- 操作分布图表
- 用户工作量图表
- 每日汇总图表
- 最近活动列表

---

#### 4. admin_users.html（用户管理页面）
管理员管理用户界面。

**主要功能**：
- 用户列表展示
- 创建新用户
- 编辑用户信息
- 删除用户
- 激活/停用用户
- 查看用户详情

---

#### 5. admin_logs.html（日志查看页面）
管理员查看系统日志界面。

**主要功能**：
- 日志列表展示
- 按用户筛选
- 按操作类型筛选
- 按时间范围筛选
- 日志详情查看

---

### 前端架构图

```mermaid
graph TB
    subgraph "用户界面层"
        Main[主页面<br/>index.html]
        Login[登录页面<br/>login.html]
        AdminDash[管理员仪表板<br/>admin_dashboard.html]
        AdminUsers[用户管理<br/>admin_users.html]
        AdminLogs[日志查看<br/>admin_logs.html]
    end
    
    subgraph "样式层"
        Style[主样式<br/>style.css]
        LoginStyle[登录样式<br/>login.css]
        AdminStyle[管理样式<br/>admin.css]
    end
    
    subgraph "脚本层"
        Script[主脚本<br/>script.js]
        LoginScript[登录脚本<br/>login.js]
        AdminDashScript[仪表板脚本<br/>admin_dashboard.js]
        AdminUsersScript[用户管理脚本<br/>admin_users.js]
        AdminLogsScript[日志脚本<br/>admin_logs.js]
    end
    
    subgraph "API通信层"
        Fetch[Fetch API]
        Auth[认证模块]
    end
    
    Main --> Style
    Main --> Script
    Login --> LoginStyle
    Login --> LoginScript
    AdminDash --> AdminStyle
    AdminDash --> AdminDashScript
    AdminUsers --> AdminStyle
    AdminUsers --> AdminUsersScript
    AdminLogs --> AdminStyle
    AdminLogs --> AdminLogsScript
    
    Script --> Fetch
    LoginScript --> Fetch
    AdminDashScript --> Fetch
    AdminUsersScript --> Fetch
    AdminLogsScript --> Fetch
    
    Fetch --> Auth
    
    classDef ui fill:#f96,stroke:#333,stroke-width:2px
    classDef css fill:#9f6,stroke:#333,stroke-width:2px
    classDef js fill:#69f,stroke:#333,stroke-width:2px
    classDef api fill:#f9f,stroke:#333,stroke-width:2px
    
    class Main,Login,AdminDash,AdminUsers,AdminLogs ui
    class Style,LoginStyle,AdminStyle css
    class Script,LoginScript,AdminDashScript,AdminUsersScript,AdminLogsScript js
    class Fetch,Auth api
```

---

## API接口文档

### 认证相关接口

#### 1. 用户注册
- **URL**: `/api/auth/register`
- **方法**: `POST`
- **请求体**:
```json
{
  "username": "testuser",
  "password": "password123",
  "email": "test@example.com"
}
```
- **响应**:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

#### 2. 用户登录
- **URL**: `/api/auth/login`
- **方法**: `POST`
- **请求体** (form-data):
```
username: testuser
password: password123
```
- **响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "role": "user"
  }
}
```

---

#### 3. 获取当前用户信息
- **URL**: `/api/auth/me`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "id": 1,
  "username": "testuser",
  "email": "test@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z"
}
```

---

### 用户管理接口（管理员）

#### 4. 获取所有用户
- **URL**: `/api/admin/users`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
[
  {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "super_admin",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": "2024-01-05T15:32:48Z"
  }
]
```

---

#### 5. 创建用户
- **URL**: `/api/admin/users`
- **方法**: `POST`
- **请求头**:
```
Authorization: Bearer <token>
```
- **请求体**:
```json
{
  "username": "newuser",
  "password": "password123",
  "email": "newuser@example.com",
  "role": "user"
}
```
- **响应**:
```json
{
  "id": 2,
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "user",
  "is_active": true,
  "created_at": "2024-01-05T00:00:00Z"
}
```

---

#### 6. 更新用户
- **URL**: `/api/admin/users/{user_id}`
- **方法**: `PUT`
- **请求头**:
```
Authorization: Bearer <token>
```
- **请求体**:
```json
{
  "email": "updated@example.com",
  "role": "admin"
}
```
- **响应**:
```json
{
  "id": 2,
  "username": "newuser",
  "email": "updated@example.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2024-01-05T00:00:00Z"
}
```

---

#### 7. 删除用户
- **URL**: `/api/admin/users/{user_id}`
- **方法**: `DELETE`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "message": "用户删除成功"
}
```

---

### 报告批阅接口

#### 8. 上传报告
- **URL**: `/api/upload`
- **方法**: `POST`
- **请求头**:
```
Authorization: Bearer <token>
```
- **请求体** (form-data):
```
file: <binary file>
```
- **响应**:
```json
{
  "message": "文件上传成功",
  "filename": "张三_物理实验报告.pdf"
}
```

---

#### 9. 批阅报告
- **URL**: `/api/annotate`
- **方法**: `POST`
- **请求头**:
```
Authorization: Bearer <token>
```
- **请求体**:
```json
{
  "directory": "内蒙古民族大学-电子-22级-6班-嵌入图形界面开发-嵌入式图形界面开发实验一"
}
```
- **响应**:
```json
{
  "message": "成功扫描了 5 个文档",
  "documents": [
    {
      "filename": "张三_物理实验报告.pdf",
      "type": "PDF",
      "content": "文档内容预览...",
      "status": "合格",
      "score": 85,
      "size": 12345
    }
  ],
  "failed_count": 1,
  "csv_file": "output/不合格报告_20240105_123045.csv"
}
```

---

#### 10. 获取报告列表
- **URL**: `/api/reports/`
- **方法**: `GET`
- **查询参数**:
- `directory`: 可选，目录名称
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
[
  {
    "filename": "张三_物理实验报告.pdf",
    "path": "/path/to/reports/...",
    "status": "已批阅"
  }
]
```

---

#### 11. 下载批注版报告
- **URL**: `/api/download-graded`
- **方法**: `GET`
- **查询参数**:
- `filename`: 文件名
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**: 文件流

---

### 配置管理接口

#### 12. 获取用户配置
- **URL**: `/api/criteria`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "criteria": "评分标准内容...",
  "min_score": 60,
  "max_score": 95
}
```

---

#### 13. 更新用户配置
- **URL**: `/api/criteria`
- **方法**: `POST`
- **请求头**:
```
Authorization: Bearer <token>
```
- **请求体**:
```json
{
  "criteria": "新的评分标准...",
  "min_score": 60,
  "max_score": 95
}
```
- **响应**:
```json
{
  "message": "评分标准已更新"
}
```

---

#### 14. 重置用户配置
- **URL**: `/api/criteria/reset`
- **方法**: `POST`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "message": "评分标准已重置为默认值",
  "criteria": "默认评分标准...",
  "min_score": 60,
  "max_score": 95
}
```

---

### 统计数据接口（管理员）

#### 15. 获取系统概览
- **URL**: `/api/admin/stats/overview`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "total_users": 10,
  "active_users": 8,
  "total_reports": 100,
  "total_gradings": 95,
  "today_users": 5,
  "today_gradings": 10
}
```

---

#### 16. 获取用户活跃度
- **URL**: `/api/admin/stats/user-activity`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "dates": ["2024-01-01", "2024-01-02"],
  "active_users": [5, 8]
}
```

---

#### 17. 获取操作分布
- **URL**: `/api/admin/stats/action-distribution`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "actions": ["login", "upload", "grade", "download"],
  "counts": [50, 30, 20, 15]
}
```

---

#### 18. 获取用户工作量
- **URL**: `/api/admin/stats/user-work`
- **方法**: `GET`
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "users": ["user1", "user2", "user3"],
  "upload_counts": [10, 15, 8],
  "grade_counts": [8, 12, 6]
}
```

---

### 日志接口（管理员）

#### 19. 获取所有日志
- **URL**: `/api/admin/logs`
- **方法**: `GET`
- **查询参数**:
- `user_id`: 可选，用户ID
- `action`: 可选，操作类型
- `limit`: 可选，返回数量
- **请求头**:
```
Authorization: Bearer <token>
```
- **响应**:
```json
{
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "username": "admin",
      "action": "login",
      "details": "用户登录",
      "ip_address": "192.168.1.1",
      "created_at": "2024-01-05T15:32:48Z"
    }
  ],
  "total": 100
}
```

---

### 健康检查接口

#### 20. 健康检查
- **URL**: `/health` 或 `/api/health`
- **方法**: `GET`
- **响应**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-05T15:32:48Z"
}
```

---

## 系统模块图

### 整体架构模块图

```mermaid
graph TB
    subgraph "前端层"
        UI[用户界面<br/>HTML/CSS/JS]
    end
    
    subgraph "API网关层"
        API[FastAPI Server]
        Auth[JWT认证]
    end
    
    subgraph "业务逻辑层"
        UserMgmt[用户管理]
        ConfigMgmt[配置管理]
        LogMgmt[日志管理]
        GradingMgmt[批阅管理]
    end
    
    subgraph "数据处理层"
        DocProc[文档处理]
        AIGrading[AI评分]
        FileMgmt[文件管理]
    end
    
    subgraph "数据存储层"
        DB[(PostgreSQL)]
        FileSys[文件系统]
    end
    
    subgraph "外部服务"
        Doubao[豆包AI]
    end
    
    UI --> API
    API --> Auth
    Auth --> UserMgmt
    Auth --> ConfigMgmt
    Auth --> LogMgmt
    Auth --> GradingMgmt
    
    GradingMgmt --> DocProc
    GradingMgmt --> AIGrading
    GradingMgmt --> FileMgmt
    
    UserMgmt --> DB
    ConfigMgmt --> DB
    LogMgmt --> DB
    FileMgmt --> FileSys
    
    AIGrading --> Doubao
    
    classDef frontend fill:#f96,stroke:#333,stroke-width:2px
    classDef gateway fill:#fc6,stroke:#333,stroke-width:2px
    classDef business fill:#9f6,stroke:#333,stroke-width:2px
    classDef data fill:#69f,stroke:#333,stroke-width:2px
    classDef storage fill:#f9f,stroke:#333,stroke-width:2px
    classDef external fill:#999,stroke:#333,stroke-width:2px
    
    class UI frontend
    class API,Auth gateway
    class UserMgmt,ConfigMgmt,LogMgmt,GradingMgmt business
    class DocProc,AIGrading,FileMgmt data
    class DB,FileSys storage
    class Doubao external
```

---

### 批阅流程模块图

```mermaid
graph TB
    Start[开始批阅] --> Upload[上传报告]
    Upload --> Extract[提取文本]
    Extract --> AI[AI评分]
    AI --> Score[提取分数]
    Score --> Annotate[添加批注]
    Annotate --> Save[保存结果]
    Save --> Export[导出汇总]
    Export --> End[完成]
    
    classDef start fill:#f96,stroke:#333,stroke-width:2px
    classDef process fill:#9f6,stroke:#333,stroke-width:2px
    classDef end fill:#69f,stroke:#333,stroke-width:2px
    
    class Start,End start
    class Upload,Extract,AI,Score,Annotate,Save,Export process
```

---

## 业务流程泳道图

### 用户登录流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API服务器
    participant Auth as 认证模块
    participant DB as 数据库
    
    User->>Frontend: 输入用户名和密码
    Frontend->>API: POST /api/auth/login
    API->>Auth: 验证用户凭证
    Auth->>DB: 查询用户信息
    DB-->>Auth: 返回用户数据
    Auth->>Auth: 验证密码
    Auth->>Auth: 生成JWT Token
    Auth->>DB: 更新最后登录时间
    Auth-->>API: 返回Token和用户信息
    API-->>Frontend: 返回登录结果
    Frontend->>Frontend: 存储Token到localStorage
    Frontend-->>User: 显示登录成功
```

---

### 报告批阅流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API服务器
    participant Grading as 批阅系统
    participant DocProc as 文档处理器
    participant AI as AI服务
    participant FileSys as 文件系统
    
    User->>Frontend: 上传报告文件
    Frontend->>API: POST /api/upload
    API->>FileSys: 保存文件
    FileSys-->>API: 返回文件路径
    API-->>Frontend: 返回上传成功
    
    User->>Frontend: 点击批阅按钮
    Frontend->>API: POST /api/annotate
    API->>Grading: 开始批阅
    Grading->>FileSys: 获取文件列表
    FileSys-->>Grading: 返回文件列表
    
    loop 每个文件
        Grading->>DocProc: 处理文档
        DocProc->>DocProc: 提取文本
        DocProc-->>Grading: 返回文本内容
        Grading->>AI: 发送文本评分
        AI->>AI: AI分析评分
        AI-->>Grading: 返回评分结果
        Grading->>DocProc: 添加批注
        DocProc-->>Grading: 返回批注版文档
        Grading->>FileSys: 保存批注版文档
    end
    
    Grading->>Grading: 生成汇总表
    Grading-->>API: 返回批阅结果
    API-->>Frontend: 返回批阅结果
    Frontend-->>User: 显示批阅结果
```

---

### 用户管理流程（管理员）

```mermaid
sequenceDiagram
    participant Admin as 管理员
    participant Frontend as 前端
    participant API as API服务器
    participant UserMgmt as 用户管理器
    participant DB as 数据库
    participant LogMgmt as 日志管理器
    
    Admin->>Frontend: 查看用户列表
    Frontend->>API: GET /api/admin/users
    API->>UserMgmt: 获取所有用户
    UserMgmt->>DB: 查询用户表
    DB-->>UserMgmt: 返回用户列表
    UserMgmt-->>API: 返回用户数据
    API-->>Frontend: 返回用户列表
    Frontend-->>Admin: 显示用户列表
    
    Admin->>Frontend: 创建新用户
    Frontend->>API: POST /api/admin/users
    API->>UserMgmt: 创建用户
    UserMgmt->>DB: 插入用户记录
    DB-->>UserMgmt: 返回用户ID
    UserMgmt->>LogMgmt: 记录操作日志
    LogMgmt->>DB: 插入日志记录
    UserMgmt-->>API: 返回新用户信息
    API-->>Frontend: 返回创建结果
    Frontend-->>Admin: 显示创建成功
    
    Admin->>Frontend: 删除用户
    Frontend->>API: DELETE /api/admin/users/{id}
    API->>UserMgmt: 删除用户
    UserMgmt->>DB: 删除用户记录
    DB-->>UserMgmt: 删除成功
    UserMgmt->>LogMgmt: 记录操作日志
    LogMgmt->>DB: 插入日志记录
    UserMgmt-->>API: 返回删除结果
    API-->>Frontend: 返回删除结果
    Frontend-->>Admin: 显示删除成功
```

---

### 配置管理流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant Frontend as 前端
    participant API as API服务器
    participant ConfigMgmt as 配置管理器
    participant DB as 数据库
    
    User->>Frontend: 查看评分标准
    Frontend->>API: GET /api/criteria
    API->>ConfigMgmt: 获取用户配置
    ConfigMgmt->>DB: 查询用户配置
    DB-->>ConfigMgmt: 返回配置数据
    ConfigMgmt-->>API: 返回配置
    API-->>Frontend: 返回评分标准
    Frontend-->>User: 显示评分标准
    
    User->>Frontend: 修改评分标准
    Frontend->>API: POST /api/criteria
    API->>ConfigMgmt: 更新用户配置
    ConfigMgmt->>DB: 更新配置记录
    DB-->>ConfigMgmt: 更新成功
    ConfigMgmt-->>API: 返回更新结果
    API-->>Frontend: 返回更新结果
    Frontend-->>User: 显示更新成功
    
    User->>Frontend: 重置评分标准
    Frontend->>API: POST /api/criteria/reset
    API->>ConfigMgmt: 重置为默认配置
    ConfigMgmt->>DB: 更新配置记录
    DB-->>ConfigMgmt: 更新成功
    ConfigMgmt-->>API: 返回默认配置
    API-->>Frontend: 返回重置结果
    Frontend-->>User: 显示重置成功
```

---

### 统计数据查询流程

```mermaid
sequenceDiagram
    participant Admin as 管理员
    participant Frontend as 前端
    participant API as API服务器
    participant Stats as 统计模块
    participant DB as 数据库
    
    Admin->>Frontend: 查看系统概览
    Frontend->>API: GET /api/admin/stats/overview
    API->>Stats: 获取概览数据
    Stats->>DB: 查询用户数、报告数等
    DB-->>Stats: 返回统计数据
    Stats-->>API: 返回概览数据
    API-->>Frontend: 返回概览数据
    Frontend-->>Admin: 显示概览图表
    
    Admin->>Frontend: 查看用户活跃度
    Frontend->>API: GET /api/admin/stats/user-activity
    API->>Stats: 获取活跃度数据
    Stats->>DB: 查询每日活跃用户
    DB-->>Stats: 返回活跃度数据
    Stats-->>API: 返回活跃度数据
    API-->>Frontend: 返回活跃度数据
    Frontend-->>Admin: 显示活跃度图表
    
    Admin->>Frontend: 查看操作分布
    Frontend->>API: GET /api/admin/stats/action-distribution
    API->>Stats: 获取操作分布数据
    Stats->>DB: 查询各操作类型数量
    DB-->>Stats: 返回分布数据
    Stats-->>API: 返回分布数据
    API-->>Frontend: 返回分布数据
    Frontend-->>Admin: 显示分布图表
```

---

## 部署架构

### Docker部署架构

```mermaid
graph TB
    subgraph "外部网络"
        Internet[互联网]
    end
    
    subgraph "Nginx层"
        Nginx[Nginx<br/>反向代理]
    end
    
    subgraph "应用层"
        App[AI批阅系统<br/>FastAPI]
    end
    
    subgraph "数据层"
        Postgres[(PostgreSQL<br/>数据库)]
        Reports[报告存储<br/>Volume]
        Graded[已批阅报告<br/>Volume]
        Logs[日志存储<br/>Volume]
    end
    
    subgraph "外部服务"
        Doubao[豆包AI服务]
    end
    
    Internet --> Nginx
    Nginx --> App
    App --> Postgres
    App --> Reports
    App --> Graded
    App --> Logs
    App --> Doubao
    
    classDef external fill:#999,stroke:#333,stroke-width:2px
    classDef proxy fill:#f96,stroke:#333,stroke-width:2px
    classDef app fill:#9f6,stroke:#333,stroke-width:2px
    classDef data fill:#69f,stroke:#333,stroke-width:2px
    classDef service fill:#f9f,stroke:#333,stroke-width:2px
    
    class Internet external
    class Nginx proxy
    class App app
    class Postgres,Reports,Graded,Logs data
    class Doubao service
```

---

### 网络架构图

```mermaid
graph LR
    subgraph "客户端"
        Browser[浏览器]
    end
    
    subgraph "负载均衡层"
        LB[负载均衡器]
    end
    
    subgraph "Web服务器层"
        Nginx1[Nginx 1]
        Nginx2[Nginx 2]
    end
    
    subgraph "应用服务器层"
        App1[FastAPI 1]
        App2[FastAPI 2]
        App3[FastAPI 3]
    end
    
    subgraph "数据层"
        DB[(PostgreSQL<br/>主从复制)]
        Redis[(Redis<br/>缓存)]
    end
    
    Browser --> LB
    LB --> Nginx1
    LB --> Nginx2
    Nginx1 --> App1
    Nginx1 --> App2
    Nginx2 --> App2
    Nginx2 --> App3
    App1 --> DB
    App2 --> DB
    App3 --> DB
    App1 --> Redis
    App2 --> Redis
    App3 --> Redis
```

---

### 数据流向图

```mermaid
graph TB
    subgraph "用户操作"
        Upload[上传报告]
        Grade[批阅报告]
        Download[下载结果]
    end
    
    subgraph "前端处理"
        UI[用户界面]
        JS[JavaScript逻辑]
    end
    
    subgraph "API层"
        API[FastAPI API]
        Auth[JWT认证]
    end
    
    subgraph "业务层"
        Grading[批阅系统]
        Config[配置管理]
        UserMgmt[用户管理]
    end
    
    subgraph "数据层"
        DB[(PostgreSQL)]
        Files[文件系统]
    end
    
    subgraph "AI服务"
        AI[豆包AI]
    end
    
    Upload --> UI
    Grade --> UI
    Download --> UI
    UI --> JS
    JS --> API
    API --> Auth
    Auth --> Grading
    Auth --> Config
    Auth --> UserMgmt
    Grading --> DB
    Grading --> Files
    Grading --> AI
    Config --> DB
    UserMgmt --> DB
```

---

## 附录

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| AI_API_KEY | AI服务API密钥 | - |
| ARK_API_KEY | 豆包API密钥 | - |
| DATABASE_URL | 数据库连接URL | postgresql://... |
| SECRET_KEY | JWT密钥 | your_secret_key_here |
| PORT | 服务端口 | 8000 |
| LOG_LEVEL | 日志级别 | INFO |

### 端口说明

| 端口 | 服务 | 说明 |
|------|------|------|
| 8000 | FastAPI | 后端API服务 |
| 5432 | PostgreSQL | 数据库服务 |

### 目录结构

```
ai_report/
├── api_server.py              # API服务器
├── user_manager.py            # 用户管理器
├── config_manager.py          # 配置管理器
├── log_manager.py             # 日志管理器
├── grading_system.py          # 批阅系统
├── document_processor.py      # 文档处理器
├── ai_grader.py               # AI评分器
├── file_manager.py            # 文件管理器
├── database.py                # 数据库连接
├── database/
│   └── init.sql              # 数据库初始化脚本
├── front/                     # 前端文件
│   ├── index.html
│   ├── login.html
│   ├── admin_dashboard.html
│   ├── admin_users.html
│   ├── admin_logs.html
│   ├── style.css
│   ├── login.css
│   ├── admin.css
│   ├── script.js
│   ├── login.js
│   ├── admin_dashboard.js
│   ├── admin_users.js
│   └── admin_logs.js
├── student_reports/           # 学生报告存储
├── graded_reports/            # 已批阅报告存储
├── output_data/               # 输出数据
├── logs/                      # 日志文件
├── docker-compose.yml         # Docker编排文件
├── Dockerfile                 # Docker镜像构建文件
├── requirements.txt           # Python依赖
├── .env                       # 环境变量配置
└── README.md                  # 项目说明
```

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0.0 | 2024-01-05 | 初始版本，包含完整功能 |

---

## 联系方式

如有问题或建议，请联系开发团队。
