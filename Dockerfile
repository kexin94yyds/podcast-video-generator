FROM python:3.11-slim

# 安装 FFmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码
COPY . .

# 创建必要目录
RUN mkdir -p uploads output

# 暴露端口
EXPOSE 5001

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "2", "--timeout", "600", "app:app"]
