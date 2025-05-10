import os
import subprocess
import shutil
import logging
from datetime import datetime
from flask import Flask, request, render_template, jsonify, send_file, make_response, abort
from flask_cors import CORS
from werkzeug.utils import secure_filename
import threading
from concurrent.futures import ThreadPoolExecutor

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许所有跨域请求

# 配置常量
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'output_images'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB 最大文件大小
MAX_CONCURRENT_JOBS = 4  # 最大并发转换任务数

# 确保目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 应用配置
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

# 自定义模板语法
app.jinja_env.variable_start_string = '{%'
app.jinja_env.variable_end_string = '%}'

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pdf_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 任务执行器
executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS)

# 活动任务跟踪
active_tasks = {}

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files(directory, max_age_hours=24):
    """清理超过指定时间的旧文件"""
    now = datetime.now()
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            file_age = now - datetime.fromtimestamp(os.path.getmtime(filepath))
            if file_age.total_seconds() > max_age_hours * 3600:
                try:
                    os.remove(filepath)
                    logger.info(f"已清理旧文件: {filepath}")
                except Exception as e:
                    logger.error(f"清理文件失败 {filepath}: {e}")

def convert_pdf_to_images(task_id, filepath, output_dir, user_args):
    """执行PDF转换任务（支持动态参数）"""
    try:
        active_tasks[task_id] = {
            'status': 'processing',
            'start_time': datetime.now(),
            'file': os.path.basename(filepath)
        }

        logger.info(f"开始转换任务 {task_id}: {filepath}")
        
        # 动态构建命令行
        cmd = [
            './pdf_to_images',
            filepath,
            '-o', output_dir,
            '--fmt', user_args.get('format', 'jpeg'),
            '--threads', str(user_args.get('threads', 4)),
            '--dpi', '300',
            '--quality', '100',
            '--log-file', user_args.get('log_file', f'conversion_{task_id}.log')
        ]

        if user_args.get('size'):
            cmd.extend(['--size', user_args['size']])
        if user_args.get('grayscale'):
            cmd.append('--grayscale')
        if user_args.get('prefix'):
            cmd.extend(['--prefix', user_args['prefix']])

        logger.info(f"执行命令: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )

        # 保存日志内容到任务中
        active_tasks[task_id]['log'] = result.stdout + "\n" + result.stderr

        zip_path = shutil.make_archive(output_dir, 'zip', output_dir)

        active_tasks[task_id].update({
            'status': 'completed',
            'end_time': datetime.now(),
            'zipfile': os.path.basename(zip_path),
            'output_dir': output_dir,
            'success': True
        })

        logger.info(f"任务 {task_id} 成功完成: {zip_path}")
        shutil.rmtree(output_dir, ignore_errors=True)

    except subprocess.CalledProcessError as e:
        error_msg = f"转换失败: {e.stderr if e.stderr else str(e)}"
        logger.error(f"任务 {task_id} 失败: {error_msg}")
        active_tasks[task_id].update({
            'status': 'failed',
            'end_time': datetime.now(),
            'error': error_msg,
            'success': False,
            'log': e.stderr or str(e)
        })

    except Exception as e:
        error_msg = f"系统错误: {str(e)}"
        logger.error(f"任务 {task_id} 系统错误: {error_msg}")
        active_tasks[task_id].update({
            'status': 'failed',
            'end_time': datetime.now(),
            'error': error_msg,
            'success': False,
            'log': error_msg
        })

@app.route('/')
def index():
    """首页"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    """文件上传处理"""
    if 'file' not in request.files:
        return jsonify({"error": "未找到上传文件"}), 400
    
    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "文件名为空"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "只支持 PDF 文件"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    try:
        file.save(filepath)
    except IOError as e:
        logger.error(f"文件保存失败: {filename} - {str(e)}")
        return jsonify({"error": "文件保存失败"}), 500

    # 创建输出目录
    prefix = os.path.splitext(filename)[0]
    output_dir = os.path.join(app.config['OUTPUT_FOLDER'], prefix)
    os.makedirs(output_dir, exist_ok=True)

    # 生成唯一任务ID
    task_id = f"{prefix}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    log_path = f'conversion_{task_id}.log'

    # 提取并修复格式参数
    format_ = request.form.get('format', 'jpeg')
    if format_ == 'jpg':
        format_ = 'jpeg'  # 自动修正为合法值

    # 提取用户传参
    user_args = {
        'format': format_,
        'threads': request.form.get('threads', '4'),
        'size': request.form.get('size'),
        'grayscale': request.form.get('grayscale', 'false').lower() == 'true',
        'prefix': request.form.get('prefix'),
        'log_file': log_path
    }

    logger.info(f"接收到转换任务 {task_id} 参数: {user_args}")

    try:
        executor.submit(convert_pdf_to_images, task_id, filepath, output_dir, user_args)
    except Exception as e:
        logger.error(f"无法启动转换任务: {str(e)}")
        return jsonify({"error": "无法启动转换任务"}), 500

    return jsonify({
        "message": "转换任务已开始",
        "task_id": task_id,
        "status_url": f"/status/{task_id}"
    }), 202


@app.route('/status/<task_id>')
def get_status(task_id):
    """获取任务状态"""
    task = active_tasks.get(task_id)
    if not task:
        return jsonify({"error": "任务ID不存在"}), 404

    response = {
        "task_id": task_id,
        "status": task['status'],
        "filename": task.get('file', ''),
        "start_time": task['start_time'].isoformat() if 'start_time' in task else None
    }

    if 'end_time' in task:
        response['end_time'] = task['end_time'].isoformat()
        if task.get('success'):
            response['download_url'] = f"/download/{task['zipfile']}"
        elif 'error' in task:
            response['error'] = task['error']

    if 'log' in task:
        response['log'] = task['log']

    return jsonify(response)

@app.route('/download/<filename>')
def download(filename):
    """下载转换结果"""
    # 安全检查文件名
    if not filename.endswith('.zip') or '/' in filename or '\\' in filename:
        abort(400, description="无效的文件名")
    
    zip_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
    
    if not os.path.exists(zip_path):
        abort(404, description="文件未找到")
    
    # 设置适当的MIME类型和下载文件名
    response = make_response(send_file(zip_path, as_attachment=True))
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@app.route('/cleanup', methods=['POST'])
def cleanup():
    """清理旧文件"""
    try:
        # 清理上传文件
        cleanup_old_files(app.config['UPLOAD_FOLDER'])
        
        # 清理输出文件
        cleanup_old_files(app.config['OUTPUT_FOLDER'])
        
        return jsonify({"message": "清理完成"}), 200
    except Exception as e:
        logger.error(f"清理失败: {str(e)}")
        return jsonify({"error": "清理失败"}), 500

@app.before_request
def before_request():
    """请求前清理旧文件"""
    if request.endpoint != 'cleanup':
        # 每天只清理一次
        last_cleanup = getattr(app, 'last_cleanup', None)
        if last_cleanup is None or (datetime.now() - last_cleanup).days >= 1:
            threading.Thread(target=cleanup_old_files, args=(app.config['UPLOAD_FOLDER'],)).start()
            threading.Thread(target=cleanup_old_files, args=(app.config['OUTPUT_FOLDER'],)).start()
            app.last_cleanup = datetime.now()

if __name__ == '__main__':
    # 启动时清理旧文件
    cleanup_old_files(UPLOAD_FOLDER)
    cleanup_old_files(OUTPUT_FOLDER)
    
    # 运行应用
    app.run(debug=True, host='0.0.0.0', port=8080, threaded=True)
