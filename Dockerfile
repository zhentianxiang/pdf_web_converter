FROM registry.cn-hangzhou.aliyuncs.com/tianxiang_app/python:3.6

WORKDIR /app

# 修改 pip3 的安装源为国内的源
RUN mkdir -p /root/.pip && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "index-url = https://mirrors.aliyun.com/pypi/simple/" >> /root/.pip/pip.conf && \
    echo "trusted-host = mirrors.aliyun.com" >> /root/.pip/pip.conf && \
    python3.6 -m pip install --upgrade pip && \
    pip3 install pdf2image poppler-utils pillow requests pyinstaller flask flask_cors

# 打包为可执行文件
COPY pdf_to_images.py ./
RUN pyinstaller --onefile pdf_to_images.py && \
    cp ./dist/pdf_to_images ./pdf_to_images

COPY app.py ./
COPY templates ./templates

# 创建上传和输出目录
RUN mkdir -p uploads converted_images && chmod 777 uploads converted_images

# 暴露端口
EXPOSE 8080

# 启动命令
CMD ["python3", "app.py"]
