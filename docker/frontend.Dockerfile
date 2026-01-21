FROM node:18-alpine

# 设置工作目录
WORKDIR /app

# 复制 package 文件
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 3000

# 启动开发服务器
CMD ["npm", "run", "dev"]
