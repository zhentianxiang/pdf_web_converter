### 1. 构建镜像

```sh
[root@k8s-master1 ~]# docker build . -t pdf_web_converter:latest
```

### 2. 启动服务

```sh
[root@k8s-master1 ~]# docker-compose up -d
```

### 3. k8s 启动

```sh
[root@k8s-master1 ~]# kubectl apply -f deployment.yaml
```

### 4. 手动执行转换命令

```sh

[root@k8s-master1 ~]# kubectl exec -it pdf-converter-cc7f9d9c8-k9ts2 -- bash

[root@pdf-converter-cc7f9d9c8-k9ts2 app]# ./pdf_to_images -h
usage: pdf_to_images.py [options] pdf_path

PDF转图片工具（支持多线程）

positional arguments:
  pdf_path              要转换的PDF文件路径

optional arguments:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        输出目录路径 (default: output_images)
  --fmt {jpeg,png,tiff}
                        输出图片格式 (default: jpeg)
  --dpi DPI             输出图片分辨率(DPI) (default: 200)
  --prefix PREFIX       自定义输出文件名前缀（默认使用PDF文件名） (default: None)
  --threads THREADS     转换使用的线程数 (default: 4)
  --quality [1-100]     输出图片质量（仅jpeg有效） (default: 95)
  --grayscale           转换为灰度图片 (default: False)
  --size SIZE           强制输出尺寸（格式: 宽x高，例如 1920x1080） (default: None)
  --verbose             显示详细日志信息 (default: False)
  --log-file LOG_FILE   指定日志文件路径（默认为pdf_to_images.log） (default: None)

[root@pdf-converter-cc7f9d9c8-k9ts2 app]# ./pdf_to_images uploads/Navicat2024.pdf  -o output_images --dpi 300 --quality 100 --threads 8 --fmt png --verbose
2025-05-11 00:14:06,601 - INFO - 开始处理PDF文件: uploads/Navicat2024.pdf
2025-05-11 00:14:06,601 - INFO - 输出目录: output_images
2025-05-11 00:14:06,602 - INFO - 输出目录已创建: output_images
2025-05-11 00:14:06,602 - INFO - 开始转换PDF: uploads/Navicat2024.pdf
2025-05-11 00:14:06,602 - INFO - 转换参数 - DPI: 300, 线程数: 8, 格式: PNG, 质量: 100, 灰度: 否, 尺寸: 原始尺寸
2025-05-11 00:14:07,620 - INFO - PDF解析完成，共 5 页，耗时: 1.02秒
2025-05-11 00:14:08,454 - DEBUG - 页面 1/5 已保存: output_images/Navicat2024_1.png (大小: 445.06 KB)
2025-05-11 00:14:09,577 - DEBUG - 页面 2/5 已保存: output_images/Navicat2024_2.png (大小: 1087.50 KB)
2025-05-11 00:14:10,668 - DEBUG - 页面 3/5 已保存: output_images/Navicat2024_3.png (大小: 1245.35 KB)
2025-05-11 00:14:11,684 - DEBUG - 页面 4/5 已保存: output_images/Navicat2024_4.png (大小: 1098.32 KB)
2025-05-11 00:14:12,396 - DEBUG - 页面 5/5 已保存: output_images/Navicat2024_5.png (大小: 103.24 KB)
2025-05-11 00:14:12,397 - INFO - 转换完成，共生成 5 张图片到目录: output_images
2025-05-11 00:14:12,397 - INFO - 总输出大小: 3.89 MB
2025-05-11 00:14:12,421 - INFO - 
==================================================
2025-05-11 00:14:12,421 - INFO - 转换摘要:
2025-05-11 00:14:12,421 - INFO - 总页数处理: 5
2025-05-11 00:14:12,421 - INFO - 成功转换: 5
2025-05-11 00:14:12,421 - INFO - 失败转换: 0
2025-05-11 00:14:12,421 - INFO - 总输出大小: 3.89 MB
2025-05-11 00:14:12,421 - INFO - 输出格式分布:
2025-05-11 00:14:12,421 - INFO -   PNG: 5 张
2025-05-11 00:14:12,421 - INFO - 总耗时: 0:00:05.819325
2025-05-11 00:14:12,421 - INFO - 平均速度: 0.86 页/秒
2025-05-11 00:14:12,421 - INFO - ==================================================
2025-05-11 00:14:12,421 - INFO - 转换成功完成！
```

示例: https://pdf-converter.tianxiang.love/
