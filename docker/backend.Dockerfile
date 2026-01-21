FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
# 注意：构建上下文是项目根目录，所以可以直接复制 requirements.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY backend/ .

# 创建必要的目录
RUN mkdir -p staticfiles media logs

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
