#!/usr/bin/env python3
"""
播客视频生成器 - Web 版
基于 Flask，复用 main.py 的 FFmpeg 逻辑
"""

import os
import subprocess
import uuid
import threading
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static')

# 配置
UPLOAD_FOLDER = Path(__file__).parent / 'uploads'
OUTPUT_FOLDER = Path(__file__).parent / 'output'
ALLOWED_AUDIO = {'mp3', 'wav', 'm4a', 'aac', 'ogg', 'flac'}
ALLOWED_IMAGE = {'jpg', 'jpeg', 'png', 'webp'}

# 视频参数（与 main.py 一致）
WIDTH = 1080
HEIGHT = 1920
FPS = 30
WAVEFORM_COLOR = "0x00CED1"
WAVEFORM_HEIGHT = 150
WAVEFORM_Y_POSITION = 1400

# 任务状态存储
tasks = {}

# 确保目录存在
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)


def allowed_audio(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_AUDIO


def allowed_image(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE


def get_audio_duration(audio_path: Path) -> float:
    """获取音频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except:
        return 0


def create_video_with_waveform(cover_path: Path, audio_path: Path, output_path: Path, task_id: str) -> bool:
    """
    合成视频：封面 + 音频 + 动态波形
    """
    tasks[task_id]['status'] = 'processing'
    tasks[task_id]['progress'] = 10
    
    # 复杂滤镜
    filter_complex = (
        # 音频波形生成
        f"[1:a]showwaves=s={WIDTH}x{WAVEFORM_HEIGHT}:mode=cline:rate={FPS}:"
        f"colors={WAVEFORM_COLOR}:scale=sqrt[wave];"
        # 封面处理：缩放+高斯模糊背景
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},boxblur=20:5[bg];"
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2[cover];"
        # 封面循环
        f"[cover]loop=loop=-1:size=1:start=0,setpts=N/({FPS}*TB)[looped];"
        # 波形叠加到封面
        f"[looped][wave]overlay=0:{WAVEFORM_Y_POSITION}:shortest=1[v]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(cover_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-progress", "pipe:1",
        str(output_path)
    ]
    
    tasks[task_id]['progress'] = 20
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    
    # 获取音频时长用于计算进度
    duration = get_audio_duration(audio_path)
    
    # 读取进度
    for line in process.stdout:
        if 'out_time_ms=' in line:
            try:
                time_ms = int(line.split('=')[1])
                time_sec = time_ms / 1000000
                if duration > 0:
                    progress = min(20 + int((time_sec / duration) * 70), 90)
                    tasks[task_id]['progress'] = progress
            except:
                pass
    
    process.wait()
    
    if process.returncode == 0:
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['progress'] = 100
        tasks[task_id]['output_file'] = output_path.name
        return True
    else:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = process.stderr.read()
        return False


def process_video_task(task_id: str, audio_path: Path, cover_path: Path, output_path: Path):
    """后台处理视频任务"""
    try:
        create_video_with_waveform(cover_path, audio_path, output_path, task_id)
    except Exception as e:
        tasks[task_id]['status'] = 'failed'
        tasks[task_id]['error'] = str(e)


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/upload', methods=['POST'])
def upload_files():
    """上传音频和封面，开始处理"""
    if 'audio' not in request.files:
        return jsonify({'error': '请上传音频文件'}), 400
    
    audio_file = request.files['audio']
    cover_file = request.files.get('cover')
    
    if audio_file.filename == '':
        return jsonify({'error': '请选择音频文件'}), 400
    
    if not allowed_audio(audio_file.filename):
        return jsonify({'error': '不支持的音频格式'}), 400
    
    # 生成任务ID
    task_id = str(uuid.uuid4())[:8]
    
    # 保存音频
    audio_filename = secure_filename(f"{task_id}_{audio_file.filename}")
    audio_path = UPLOAD_FOLDER / audio_filename
    audio_file.save(str(audio_path))
    
    # 保存封面（如果有）
    if cover_file and cover_file.filename and allowed_image(cover_file.filename):
        cover_filename = secure_filename(f"{task_id}_{cover_file.filename}")
        cover_path = UPLOAD_FOLDER / cover_filename
        cover_file.save(str(cover_path))
    else:
        # 使用默认封面
        default_cover = Path(__file__).parent / 'static' / 'default_cover.jpg'
        if default_cover.exists():
            cover_path = default_cover
        else:
            return jsonify({'error': '请上传封面图片'}), 400
    
    # 输出文件
    output_filename = f"{task_id}_video.mp4"
    output_path = OUTPUT_FOLDER / output_filename
    
    # 初始化任务状态
    tasks[task_id] = {
        'status': 'queued',
        'progress': 0,
        'output_file': None,
        'error': None
    }
    
    # 启动后台处理
    thread = threading.Thread(
        target=process_video_task,
        args=(task_id, audio_path, cover_path, output_path)
    )
    thread.start()
    
    return jsonify({
        'task_id': task_id,
        'message': '开始处理'
    })


@app.route('/api/status/<task_id>')
def get_status(task_id):
    """获取任务状态"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    return jsonify(tasks[task_id])


@app.route('/api/download/<task_id>')
def download_video(task_id):
    """下载生成的视频"""
    if task_id not in tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = tasks[task_id]
    if task['status'] != 'completed':
        return jsonify({'error': '视频尚未完成'}), 400
    
    output_file = OUTPUT_FOLDER / task['output_file']
    if not output_file.exists():
        return jsonify({'error': '文件不存在'}), 404
    
    return send_file(
        str(output_file),
        as_attachment=True,
        download_name=task['output_file']
    )


@app.route('/api/check-ffmpeg')
def check_ffmpeg():
    """检查 FFmpeg 是否可用"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.split('\n')[0]
            return jsonify({'available': True, 'version': version})
    except:
        pass
    return jsonify({'available': False})


if __name__ == '__main__':
    print("🎬 播客视频生成器")
    print("📍 访问地址: http://localhost:5000")
    print("📱 手机访问: http://<你的IP>:5000")
    app.run(host='0.0.0.0', port=5001, debug=True)
