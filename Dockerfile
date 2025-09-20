# 使用官方 Python 3.12 slim 作为基础镜像
FROM python:3.12-slim

# 设置国内 Debian 源
RUN echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list

# 安装依赖工具（cryptography 需要 libssl-dev, libffi-dev, cargo）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libssl-dev \
    libffi-dev \
    cargo \
    poppler-utils \
 && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 创建临时目录（后续用 tmpfs 覆盖）
RUN mkdir -p /app/tmp

# 复制依赖文件
COPY requirements-linux.txt requirements.txt ./

# 使用国内 pip 源安装依赖（加 --default-timeout 提升构建稳定性）
RUN pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip install --no-cache-dir --default-timeout=100 -r requirements-linux.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码
COPY . .

# 设置环境变量（让程序能直接找到临时目录）
ENV TMP_DIR=/app/tmp

# 暴露端口
EXPOSE 8000

# 以非 root 用户运行，提高安全性
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# 启动应用
CMD ["python", "main.py"]
