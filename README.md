### 1. 构建镜像

```sh
docker build . -t pdf_web_converter:latest
```

### 2. 启动服务

```sh
docker-compose up -d
```

### 3. k8s 启动

```sh
kubectl apply -f deployment.yaml
```

示例: https://pdf-converter.tianxiang.love/
