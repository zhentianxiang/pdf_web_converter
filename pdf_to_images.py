#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pdf2image import convert_from_path
import os
import io
import sys
import time
from typing import List, Optional, Tuple, Dict
import logging
import argparse
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from datetime import timedelta

# 修复标准输出的编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_to_images.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ConversionStats:
    """转换统计信息类"""
    def __init__(self):
        self.start_time = time.time()
        self.total_pages = 0
        self.successful_conversions = 0
        self.failed_conversions = 0
        self.total_image_size = 0  # 字节
        self.output_formats = {}
    
    def update(self, page_count: int, successful: bool, image_size: int = 0, fmt: str = 'jpeg'):
        self.total_pages += page_count
        if successful:
            self.successful_conversions += page_count
            self.total_image_size += image_size
            self.output_formats[fmt] = self.output_formats.get(fmt, 0) + page_count
        else:
            self.failed_conversions += page_count
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def get_stats_summary(self) -> Dict:
        return {
            'total_pages': self.total_pages,
            'successful': self.successful_conversions,
            'failed': self.failed_conversions,
            'total_size_mb': self.total_image_size / (1024 * 1024),
            'formats': self.output_formats,
            'elapsed_seconds': self.get_elapsed_time()
        }

def pdf_to_images(
    pdf_path: str,
    output_folder: str,
    fmt: str = 'jpeg',
    dpi: int = 200,
    output_prefix: Optional[str] = None,
    thread_count: int = 4,
    quality: int = 95,
    grayscale: bool = False,
    size: Optional[Tuple[int, int]] = None,
    stats: Optional[ConversionStats] = None
) -> List[str]:
    """
    将PDF转换为高质量图片（优化版）
    
    参数:
        pdf_path: PDF文件路径
        output_folder: 输出文件夹路径
        fmt: 输出格式 ('jpeg', 'png', 'tiff')
        dpi: 输出分辨率 (DPI)
        output_prefix: 自定义输出文件名前缀
        thread_count: 使用的线程数
        quality: 输出质量 (1-100，仅JPEG有效)
        grayscale: 是否转为灰度图
        size: 可选，强制输出尺寸 (width, height)
        stats: 转换统计对象
    
    返回:
        生成的图片文件路径列表
    
    异常:
        ValueError: 参数无效时抛出
        IOError: 文件操作失败时抛出
    """
    # 参数验证
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF文件不存在: {pdf_path}")
    
    if fmt.lower() not in ('jpeg', 'jpeg', 'png', 'tiff'):
        raise ValueError("不支持的图片格式，请使用 'jpeg', 'png' 或 'tiff'")
    
    fmt = fmt.lower()
    if fmt == 'jpeg':
        fmt = 'jpeg'
    
    # 创建输出目录
    os.makedirs(output_folder, exist_ok=True)
    logger.info(f"输出目录已创建: {output_folder}")
    
    # 获取基础文件名
    base_name = output_prefix if output_prefix else os.path.splitext(os.path.basename(pdf_path))[0]
    
    try:
        # 使用多线程转换PDF
        logger.info(f"开始转换PDF: {pdf_path}")
        logger.info(f"转换参数 - DPI: {dpi}, 线程数: {thread_count}, 格式: {fmt.upper()}, "
                   f"质量: {quality}, 灰度: {'是' if grayscale else '否'}, "
                   f"尺寸: {size if size else '原始尺寸'}")
        
        conversion_start = time.time()
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            thread_count=thread_count,
            grayscale=grayscale,
            size=size
        )
        conversion_time = time.time() - conversion_start
        
        logger.info(f"PDF解析完成，共 {len(images)} 页，耗时: {conversion_time:.2f}秒")
        
        saved_files = []
        total_image_size = 0
        
        # 处理并保存图片
        def process_image(page_num: int, img: Image.Image) -> Tuple[str, int]:
            if size:
                img = img.resize(size, Image.LANCZOS)
                logger.debug(f"页面 {page_num + 1} 已调整尺寸为: {size}")
            
            output_path = os.path.join(output_folder, f"{base_name}_{page_num + 1}.{fmt}")
            save_args = {'quality': quality} if fmt == 'jpeg' else {}
            
            # 使用内存缓冲区计算图片大小
            buffer = io.BytesIO()
            img.save(buffer, fmt.upper(), **save_args)
            image_size = buffer.getbuffer().nbytes
            buffer.close()
            
            # 实际保存到文件
            img.save(output_path, fmt.upper(), **save_args)
            return output_path, image_size
        
        for idx, img in enumerate(images):
            try:
                file_path, img_size = process_image(idx, img)
                saved_files.append(file_path)
                total_image_size += img_size
                logger.debug(f"页面 {idx + 1}/{len(images)} 已保存: {file_path} "
                            f"(大小: {img_size / 1024:.2f} KB)")
            except Exception as e:
                logger.error(f"页面 {idx + 1} 转换失败: {str(e)}")
                if stats:
                    stats.update(1, False)
                continue
        
        logger.info(f"转换完成，共生成 {len(saved_files)} 张图片到目录: {output_folder}")
        logger.info(f"总输出大小: {total_image_size / (1024 * 1024):.2f} MB")
        
        if stats:
            stats.update(len(images), True, total_image_size, fmt)
        
        return saved_files
    
    except Exception as e:
        logger.error(f"转换失败: {str(e)}", exc_info=True)
        if stats:
            stats.update(len(images) if 'images' in locals() else 0, False)
        raise

def parse_size(size_str: Optional[str]) -> Optional[Tuple[int, int]]:
    """解析尺寸字符串，例如 '1920x1080' -> (1920, 1080)"""
    if not size_str:
        return None
    try:
        width, height = map(int, size_str.lower().split('x'))
        return (width, height)
    except ValueError:
        raise ValueError("尺寸格式错误，请使用 '宽x高' 格式，例如 '1920x1080'")

def print_summary(stats: ConversionStats):
    """打印转换摘要信息"""
    summary = stats.get_stats_summary()
    elapsed = timedelta(seconds=summary['elapsed_seconds'])
    
    logger.info("\n" + "=" * 50)
    logger.info("转换摘要:")
    logger.info(f"总页数处理: {summary['total_pages']}")
    logger.info(f"成功转换: {summary['successful']}")
    logger.info(f"失败转换: {summary['failed']}")
    logger.info(f"总输出大小: {summary['total_size_mb']:.2f} MB")
    logger.info("输出格式分布:")
    for fmt, count in summary['formats'].items():
        logger.info(f"  {fmt.upper()}: {count} 张")
    logger.info(f"总耗时: {elapsed}")
    logger.info(f"平均速度: {summary['total_pages'] / summary['elapsed_seconds']:.2f} 页/秒")
    logger.info("=" * 50)

def main():
    # 修复帮助信息的编码问题
    parser = argparse.ArgumentParser(
        description="PDF转图片工具（支持多线程）",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        prog='pdf_to_images.py',
        usage='%(prog)s [options] pdf_path'
    )
    parser.add_argument(
        'pdf_path',
        help='要转换的PDF文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        default='output_images',
        help='输出目录路径'
    )
    parser.add_argument(
        '--fmt',
        choices=['jpeg', 'png', 'tiff'],
        default='jpeg',
        help='输出图片格式'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=200,
        help='输出图片分辨率(DPI)'
    )
    parser.add_argument(
        '--prefix',
        help='自定义输出文件名前缀（默认使用PDF文件名）'
    )
    parser.add_argument(
        '--threads',
        type=int,
        default=4,
        help='转换使用的线程数'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=95,
        choices=range(1, 101),
        metavar="[1-100]",
        help='输出图片质量（仅jpeg有效）'
    )
    parser.add_argument(
        '--grayscale',
        action='store_true',
        help='转换为灰度图片'
    )
    parser.add_argument(
        '--size',
        help='强制输出尺寸（格式: 宽x高，例如 1920x1080）'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细日志信息'
    )
    parser.add_argument(
        '--log-file',
        help='指定日志文件路径（默认为pdf_to_images.log）'
    )
    
    args = parser.parse_args()
    
    # 设置日志级别和日志文件
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file, encoding='utf-8')
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    # 初始化统计对象
    stats = ConversionStats()
    
    try:
        # 解析尺寸参数
        size = parse_size(args.size)
        
        # 记录开始信息
        logger.info(f"开始处理PDF文件: {args.pdf_path}")
        logger.info(f"输出目录: {args.output}")
        
        # 调用转换函数
        results = pdf_to_images(
            pdf_path=args.pdf_path,
            output_folder=args.output,
            fmt=args.fmt,
            dpi=args.dpi,
            output_prefix=args.prefix,
            thread_count=args.threads,
            quality=args.quality,
            grayscale=args.grayscale,
            size=size,
            stats=stats
        )
        
        # 打印摘要
        print_summary(stats)
        logger.info("转换成功完成！")
        
    except Exception as e:
        logger.error(f"程序执行出错: {e}", exc_info=True)
        print_summary(stats)
        sys.exit(1)

if __name__ == "__main__":
    main()
