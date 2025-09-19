# Docker Deployment Guide

本文档提供了实验报告自动批阅系统的完整Docker部署指南。

## 目录

- [系统要求](#系统要求)
- [快速开始](#快速开始)
- [详细部署步骤](#详细部署步骤)
- [配置说明](#配置说明)
- [SSL/HTTPS配置](#sslhttps配置)
- [数据管理](#数据管理)
- [监控和健康检查](#监控和健康检查)
- [故障排除](#故障排除)
- [维护操作](#维护操作)

## 系统要求

### 最低要求
- **操作系统**: Linux, macOS, Windows 10/11
- **Docker**: 20.10.0 或更高版本
- **Docker Compose**: 2.0.0 或更高版本
- **内存**: 2GB RAM
- **存储**: 10GB 可用空间
- **网络**: 互联网连接（用于AI服务调用）

### 推荐配置
- **CPU**: 4核心或更多
- **内存**: 4GB RAM 或更多
- **存储**: 50GB 可用空间
- **网络**: 稳定的互联网连接

## 快速开始

### 1. 克隆项目
```bash
git clone <repository-url>
cd grading-system
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
```

### 3. 部署系统
```bash
# 使用部署脚本（推荐）
./scripts/deploy.sh

# 或手动部署
docker-compose up -d
```

### 4. 验证部署
```bash
# 检查服务状态
docker-compose ps

# 运行健康检查
./scripts/health-check.sh all
```

访问 http://localhost 查看应用程序。

## 详细部署步骤

### 步骤 1: 环境准备

#### 安装 Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# CentOS/RHEL
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Windows/macOS
# 下载并安装 Docker Desktop
```

#### 安装 Docker Compose
```bash
# Linux
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

### 步骤 2: 项目配置

#### 创建目录结构
```bash
mkdir -p student_reports graded_reports output logs temp
```

#### 配置环境变量
编辑 `.env` 文件：

```env
# 必需配置
AI_API_KEY=your_ai_api_key_here
ARK_API_KEY=your_ark_api_key_here

# 可选配置
PORT=8000
LOG_LEVEL=INFO
MAX_FILE_SIZE=104857600
AI_TIMEOUT=30
WORKERS=1

# 安全配置
SECRET_KEY=your_secret_key_here
ALLOWED_HOSTS=localhost,127.0.0.1,your-domain.com

# 性能配置
CPU_LIMIT=2.0
MEMORY_LIMIT=2G
```

### 步骤 3: 部署选项

#### 选项 A: 使用部署脚本（推荐）
```bash
# 基本部署
./scripts/deploy.sh

# 启用 SSL
./scripts/deploy.sh --ssl

# 跳过备份
./scripts/deploy.sh --no-backup
```

#### 选项 B: 手动部署
```bash
# 构建并启动服务
docker-compose build
docker-compose up -d

# 查看日志
docker-compose logs -f
```

#### 选项 C: 使用 SSL/HTTPS
```bash
# 生成 SSL 证书
./scripts/generate-ssl-cert.sh generate-san

# 使用 SSL 配置部署
docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

### 步骤 4: 验证部署

#### 检查服务状态
```bash
# 查看所有服务
docker-compose ps

# 查看特定服务日志
docker-compose logs app
docker-compose logs nginx
```

#### 运行健康检查
```bash
# 基本健康检查
./scripts/health-check.sh

# 详细健康检查
./scripts/health-check.sh detailed

# 所有健康检查
./scripts/health-check.sh all
```

#### 测试功能
```bash
# 测试 API 端点
curl http://localhost/api/criteria

# 测试文件上传
curl -X POST -F "file=@test.zip" http://localhost/api/upload
```

## 配置说明

### 环境变量详解

#### 必需变量
| 变量名 | 描述 | 示例 |
|--------|------|------|
| `AI_API_KEY` | AI服务API密钥 | `sk-xxx...` |
| `ARK_API_KEY` | ARK模型API密钥 | `ak-xxx...` |

#### 应用配置
| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `PORT` | `8000` | 应用程序端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `WORKERS` | `1` | 工作进程数 |
| `MAX_FILE_SIZE` | `104857600` | 最大文件大小（字节） |
| `AI_TIMEOUT` | `30` | AI服务超时时间（秒） |

#### 安全配置
| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `SECRET_KEY` | `default-secret-key...` | 应用程序密钥 |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | 允许的主机名 |

#### 性能配置
| 变量名 | 默认值 | 描述 |
|--------|--------|------|
| `CPU_LIMIT` | `2.0` | CPU限制 |
| `MEMORY_LIMIT` | `2G` | 内存限制 |
| `CPU_RESERVATION` | `0.5` | CPU预留 |
| `MEMORY_RESERVATION` | `512M` | 内存预留 |

### Docker Compose 配置

#### 基本配置文件
- `docker-compose.yml`: 主配置文件
- `docker-compose.ssl.yml`: SSL/HTTPS配置
- `docker-compose.secrets.yml`: 密钥管理配置

#### 服务说明
- **app**: 主应用程序容器
- **nginx**: 反向代理和静态文件服务器

#### 数据卷
- `student_reports`: 学生报告存储
- `graded_reports`: 已评分报告存储
- `output_data`: 输出数据
- `app_logs`: 应用程序日志
- `temp_files`: 临时文件（tmpfs）

## SSL/HTTPS配置

### 生成SSL证书

#### 自签名证书（开发环境）
```bash
# 基本自签名证书
./scripts/generate-ssl-cert.sh generate

# 带SAN的证书（推荐）
./scripts/generate-ssl-cert.sh generate-san

# 自定义配置
./scripts/generate-ssl-cert.sh --cn yourdomain.com --days 730 generate-san
```

#### 使用现有证书
```bash
# 将证书文件放置到 ssl 目录
mkdir -p ssl
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem
```

### 启用HTTPS
```bash
# 使用SSL配置部署
docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d

# 或使用部署脚本
./scripts/deploy.sh --ssl
```

### 验证SSL配置
```bash
# 验证证书
./scripts/generate-ssl-cert.sh verify

# 测试HTTPS连接
curl -k https://localhost/health
```

## 数据管理

### 备份数据

#### 自动备份
```bash
# 创建备份
./scripts/backup.sh

# 自定义备份目录
./scripts/backup.sh -d /path/to/backups

# 指定项目名称
./scripts/backup.sh -p myproject
```

#### 备份内容
- 学生报告文件
- 已评分报告
- 输出数据
- 应用程序日志

### 恢复数据

#### 列出可用备份
```bash
./scripts/restore.sh list
```

#### 恢复所有数据
```bash
./scripts/restore.sh restore-all 20231201_143022
```

#### 恢复特定卷
```bash
./scripts/restore.sh restore-volume student_reports 20231201_143022
```

#### 验证备份完整性
```bash
./scripts/restore.sh verify 20231201_143022
```

### 数据迁移

#### 导出数据
```bash
# 创建完整备份
./scripts/backup.sh

# 导出特定目录
docker run --rm -v grading_student_reports:/data -v $(pwd):/backup alpine tar czf /backup/student_reports.tar.gz -C /data .
```

#### 导入数据
```bash
# 从备份恢复
./scripts/restore.sh restore-all <timestamp>

# 导入特定数据
docker run --rm -v grading_student_reports:/data -v $(pwd):/backup alpine tar xzf /backup/student_reports.tar.gz -C /data
```

## 监控和健康检查

### 健康检查端点

| 端点 | 描述 | 用途 |
|------|------|------|
| `/health` | 基本健康检查 | 负载均衡器检查 |
| `/api/health` | 详细健康检查 | 系统监控 |
| `/api/health/live` | 存活性探针 | Kubernetes liveness |
| `/api/health/ready` | 就绪性探针 | Kubernetes readiness |
| `/api/health/summary` | 健康检查摘要 | 监控仪表板 |

### 使用健康检查脚本

#### 基本检查
```bash
./scripts/health-check.sh
```

#### 详细检查
```bash
./scripts/health-check.sh detailed
```

#### 所有检查
```bash
./scripts/health-check.sh all
```

#### 自定义配置
```bash
# 检查特定主机
./scripts/health-check.sh -H app -p 8000 ready

# 启用详细输出
./scripts/health-check.sh -v all

# 自定义超时
./scripts/health-check.sh -t 30 detailed
```

### 监控指标

#### 系统指标
- CPU使用率
- 内存使用率
- 磁盘空间
- 网络连接

#### 应用指标
- 响应时间
- 错误率
- 请求数量
- AI服务连接状态

#### 业务指标
- 处理的报告数量
- 评分成功率
- 文件上传成功率

### 日志管理

#### 查看日志
```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs app
docker-compose logs nginx

# 实时跟踪日志
docker-compose logs -f

# 查看最近的日志
docker-compose logs --tail=100
```

#### 日志轮转
日志文件会自动轮转，保留最近30天的日志。

#### 日志级别
可通过 `LOG_LEVEL` 环境变量配置：
- `DEBUG`: 调试信息
- `INFO`: 一般信息（默认）
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误

## 故障排除

### 常见问题

#### 1. 容器启动失败

**症状**: 容器无法启动或立即退出

**排查步骤**:
```bash
# 查看容器状态
docker-compose ps

# 查看详细日志
docker-compose logs app

# 检查配置文件
docker-compose config
```

**常见原因**:
- 环境变量未配置
- 端口冲突
- 权限问题
- 资源不足

#### 2. 健康检查失败

**症状**: 健康检查返回错误状态

**排查步骤**:
```bash
# 运行详细健康检查
./scripts/health-check.sh detailed

# 检查服务状态
docker-compose ps

# 查看应用日志
docker-compose logs app
```

**常见原因**:
- AI服务连接失败
- 磁盘空间不足
- 内存不足
- 网络问题

#### 3. 文件上传失败

**症状**: 无法上传文件或上传后处理失败

**排查步骤**:
```bash
# 检查文件大小限制
grep MAX_FILE_SIZE .env

# 检查磁盘空间
df -h

# 查看处理日志
docker-compose logs app | grep upload
```

**常见原因**:
- 文件大小超限
- 磁盘空间不足
- 文件格式不支持
- 权限问题

#### 4. AI服务调用失败

**症状**: 评分功能不工作

**排查步骤**:
```bash
# 检查API密钥配置
grep API_KEY .env

# 测试网络连接
docker-compose exec app ping api.doubao.com

# 查看AI服务日志
docker-compose logs app | grep -i "ai\|ark"
```

**常见原因**:
- API密钥错误或过期
- 网络连接问题
- API配额用完
- 服务端问题

### 调试技巧

#### 1. 进入容器调试
```bash
# 进入应用容器
docker-compose exec app bash

# 进入nginx容器
docker-compose exec nginx sh
```

#### 2. 查看容器资源使用
```bash
# 查看资源使用情况
docker stats

# 查看特定容器
docker stats grading-system-app
```

#### 3. 网络调试
```bash
# 查看网络配置
docker network ls
docker network inspect grading-network

# 测试容器间连接
docker-compose exec app ping nginx
```

#### 4. 卷调试
```bash
# 查看卷信息
docker volume ls
docker volume inspect grading_student_reports

# 检查卷内容
docker run --rm -v grading_student_reports:/data alpine ls -la /data
```

### 性能优化

#### 1. 资源限制调整
```env
# 增加资源限制
CPU_LIMIT=4.0
MEMORY_LIMIT=4G
```

#### 2. 工作进程调整
```env
# 增加工作进程数
WORKERS=4
```

#### 3. 缓存优化
```bash
# 清理Docker缓存
docker system prune -f

# 清理未使用的镜像
docker image prune -f
```

## 维护操作

### 系统更新

#### 使用更新脚本（推荐）
```bash
# 标准更新
./scripts/update.sh

# 不创建备份的更新
./scripts/update.sh --no-backup

# 自定义健康检查参数
./scripts/update.sh --retries 10 --interval 15
```

#### 手动更新
```bash
# 拉取最新镜像
docker-compose pull

# 重新构建应用
docker-compose build --no-cache

# 重启服务
docker-compose up -d --force-recreate
```

### 扩容操作

#### 水平扩容
```bash
# 扩展应用实例
docker-compose up -d --scale app=3

# 配置负载均衡
# 需要修改nginx配置支持多实例
```

#### 垂直扩容
```env
# 增加资源限制
CPU_LIMIT=4.0
MEMORY_LIMIT=8G
```

### 清理操作

#### 清理临时文件
```bash
# 通过API清理
curl -X POST http://localhost/api/temp/cleanup

# 手动清理
docker-compose exec app find /app/temp -type f -mtime +1 -delete
```

#### 清理日志文件
```bash
# 清理旧日志
docker-compose exec app find /app/logs -name "*.log" -mtime +30 -delete

# 轮转日志
docker-compose restart app
```

#### 清理Docker资源
```bash
# 清理未使用的资源
docker system prune -f

# 清理所有未使用的资源（包括卷）
docker system prune -a --volumes
```

### 安全维护

#### 更新密钥
```bash
# 生成新的密钥
openssl rand -hex 32

# 更新环境变量
nano .env

# 重启服务
docker-compose restart
```

#### 更新SSL证书
```bash
# 生成新证书
./scripts/generate-ssl-cert.sh generate-san

# 重启nginx
docker-compose restart nginx
```

#### 安全扫描
```bash
# 扫描镜像漏洞
docker scan grading-system_app

# 检查容器安全配置
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image grading-system_app
```

## 生产环境建议

### 安全配置
1. 使用强密码和密钥
2. 启用HTTPS
3. 配置防火墙
4. 定期更新系统和依赖
5. 使用非root用户运行容器

### 监控配置
1. 设置日志聚合
2. 配置监控告警
3. 定期健康检查
4. 性能监控

### 备份策略
1. 定期自动备份
2. 异地备份存储
3. 备份恢复测试
4. 备份保留策略

### 高可用配置
1. 多实例部署
2. 负载均衡配置
3. 故障转移机制
4. 数据库集群（如需要）

## 支持和帮助

如果遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查应用程序日志
3. 运行健康检查脚本
4. 查看GitHub Issues
5. 联系技术支持

---

**注意**: 本文档会随着系统更新而更新，请定期查看最新版本。