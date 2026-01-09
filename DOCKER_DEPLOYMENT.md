# Docker 部署指南

本指南介绍如何使用 Docker 部署实验报告自动批阅系统。

## 目录

- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [部署步骤](#部署步骤)
- [常用命令](#常用命令)
- [故障排除](#故障排除)

## 快速开始

### 1. 环境准备

确保已安装 Docker 和 Docker Compose：

```bash
# 检查 Docker 版本
docker --version
docker-compose --version
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
nano .env
```

必须配置的环境变量：
```env
AI_API_KEY=your_ai_api_key_here
ARK_API_KEY=your_ark_api_key_here
PORT=8000
```

### 3. 启动服务

```bash
# 构建并启动服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 4. 访问应用

- Web 应用：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| PORT | 服务端口 | 8000 |
| AI_API_KEY | AI 服务 API 密钥 | 必填 |
| ARK_API_KEY | ARK 模型 API 密钥 | 必填 |
| LOG_LEVEL | 日志级别 | INFO |
| MAX_FILE_SIZE | 最大文件大小（字节） | 104857600 |

### 端口映射

| 主机端口 | 容器端口 | 说明 |
|----------|----------|------|
| 8000 | 8000 | API 服务 |

### 数据卷

| 数据卷 | 说明 |
|--------|------|
| ai_report_student_reports | 学生报告存储 |
| ai_report_graded_reports | 已评分报告存储 |
| ai_report_output_data | 输出数据存储 |
| ai_report_app_logs | 应用日志 |

## 部署步骤

### 步骤 1: 克隆项目

```bash
git clone <repository-url>
cd ai_report
```

### 步骤 2: 配置环境

```bash
# 复制环境变量文件
cp .env.example .env

# 编辑配置
nano .env
```

### 步骤 3: 构建镜像

```bash
docker-compose build
```

### 步骤 4: 启动服务

```bash
docker-compose up -d
```

### 步骤 5: 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 运行健康检查
./scripts/health-check.sh all
```

## 常用命令

### 启动服务
```bash
docker-compose up -d
```

### 停止服务
```bash
docker-compose down
```

### 查看日志
```bash
# 实时查看日志
docker-compose logs -f

# 查看最近100行
docker-compose logs --tail=100
```

### 重启服务
```bash
docker-compose restart
```

### 重建镜像
```bash
docker-compose build --no-cache
docker-compose up -d
```

### 数据备份
```bash
./scripts/backup.sh
```

### 数据恢复
```bash
./scripts/restore.sh backup_xxx.tar.gz
```

## 故障排除

### 1. 端口被占用

如果端口 8000 已被占用，修改 `.env` 文件中的 PORT 值：

```env
PORT=8080
```

然后更新 docker-compose.yml 中的端口映射。

### 2. 容器启动失败

```bash
# 查看详细日志
docker-compose logs app

# 检查容器状态
docker-compose ps -a
```

### 3. 内存不足

如果容器频繁崩溃，可能是内存不足。增加 Docker 内存限制或减少线程数：

```bash
# 在 .env 中减少线程数
WORKERS=1
```

### 4. 数据库连接失败

确保 PostgreSQL 服务已启动：

```bash
docker-compose up -d postgres
```

## SSL/HTTPS 配置

### 生成自签名证书

```bash
./scripts/generate-ssl-cert.sh generate-san
```

### 启用 HTTPS

```bash
docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

## 监控配置

### 启用监控栈

```bash
docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d
```

监控服务：
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093

## 性能优化

### 调整线程数

在 `.env` 文件中调整：

```env
WORKERS=2  # 根据 CPU 核心数调整
```

### 增加内存限制

在 docker-compose.yml 中调整：

```yaml
deploy:
  resources:
    limits:
      memory: 4G
```

## 安全建议

1. **使用强密码**：修改默认的 SECRET_KEY
2. **限制 API 访问**：配置 ALLOWED_HOSTS
3. **启用 HTTPS**：在生产环境中使用 SSL
4. **定期备份**：使用备份脚本定期备份数据
5. **监控日志**：定期检查应用日志

## 更新系统

```bash
# 拉取最新代码
git pull

# 重建并重启
docker-compose down
docker-compose build
docker-compose up -d
```
