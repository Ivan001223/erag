# 多阶段构建的生产级Dockerfile

# 第一阶段：构建阶段
FROM python:3.11-slim as builder

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 升级pip
RUN pip install --upgrade pip

# 复制requirements文件
COPY requirements.txt requirements-prod.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements-prod.txt

# 第二阶段：运行阶段
FROM python:3.11-slim as runtime

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    APP_ENV=production \
    WORKERS=4

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装运行时依赖
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置工作目录
WORKDIR /app

# 复制应用代码
COPY backend/ ./backend/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY entrypoint.sh ./

# 设置权限
RUN chmod +x entrypoint.sh && \
    chown -R appuser:appuser /app

# 创建必要的目录
RUN mkdir -p /app/logs /app/uploads /app/backups && \
    chown -R appuser:appuser /app/logs /app/uploads /app/backups

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动脚本
ENTRYPOINT ["./entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"] 