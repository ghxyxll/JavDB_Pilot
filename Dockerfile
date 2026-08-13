# Stage 1: Build Vue 3 Frontend SPA
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend/ ./
RUN npm run build

# Stage 2: Production Python Runtime Environment
FROM python:3.11-slim

WORKDIR /app

# 安装系统时区与基础系统依赖 (设置默认时区为 Asia/Shanghai)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tzdata \
    curl \
    && echo "Asia/Shanghai" > /etc/timezone \
    && ln -fs /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Asia/Shanghai
ENV CONFIG_PATH=/config/config.ini
ENV DATA_DIR=/data
ENV PYTHONUNBUFFERED=1

# 安装 Python 依赖库
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制 Python 后端业务代码
COPY backend/ /app/backend/

# 将第一阶段编译完成的前端静态资源注入后端 static 文件夹
COPY --from=frontend-builder /app/frontend/dist /app/backend/static

# 创建持久化映射目录
RUN mkdir -p /config /data

# 暴露 FastAPI/Web 服务端口
EXPOSE 8000

# 声明 Volume 数据卷 (用于宿主机目录映射)
VOLUME ["/config", "/data"]

WORKDIR /app/backend

CMD ["python", "server.py"]
