#!/usr/bin/env python3
"""
播客音频转视频工作流
- 输入：音频(mp3) + 封面图(jpg/png)
- 输出：9:16 竖屏视频(mp4) + 动态波形
"""

import os
import subprocess
import sys
from pathlib import Path

# 目录配置
BASE_DIR = Path(__file__).parent
INPUT_AUDIO = BASE_DIR / "input" / "audio"
INPUT_COVER = BASE_DIR / "input" / "cover"
OUTPUT_FINAL = BASE_DIR / "output" / "final"
OUTPUT_TEMP = BASE_DIR / "output" / "temp"

# 视频参数
WIDTH = 1080
HEIGHT = 1920
FPS = 30
VIDEO_BITRATE = "5M"

# 波形参数
WAVEFORM_COLOR = "0x00CED1"  # 青色波形
WAVEFORM_HEIGHT = 150
WAVEFORM_Y_POSITION = 1400  # 波形在视频中的Y位置（底部1/3处）


def ensure_dirs():
    """确保所有目录存在"""
    for d in [INPUT_AUDIO, INPUT_COVER, OUTPUT_FINAL, OUTPUT_TEMP]:
        d.mkdir(parents=True, exist_ok=True)


def check_ffmpeg():
    """检查 FFmpeg 是否安装"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ 错误：未找到 FFmpeg，请先安装：brew install ffmpeg")
        return False


def process_cover_blur(cover_path: Path, output_path: Path) -> bool:
    """
    将封面图处理为 9:16 高斯模糊填充
    - 原图居中保留
    - 背景用原图的高斯模糊版本填充
    """
    filter_complex = (
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},boxblur=20:5[bg];"
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease[fg];"
        f"[bg][fg]overlay=(W-w)/2:(H-h)/2"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(cover_path),
        "-filter_complex", filter_complex,
        "-frames:v", "1",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"❌ 封面处理失败：{cover_path}")
        print(result.stderr.decode())
        return False
    return True


def get_audio_duration(audio_path: Path) -> float:
    """获取音频时长（秒）"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(audio_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def create_video_with_waveform(
    cover_path: Path,
    audio_path: Path,
    output_path: Path
) -> bool:
    """
    合成视频：封面 + 音频 + 动态波形
    """
    # 复杂滤镜：
    # 1. 循环封面图作为背景
    # 2. 从音频生成动态波形
    # 3. 将波形叠加到封面上
    filter_complex = (
        # 音频波形生成
        f"[1:a]showwaves=s={WIDTH}x{WAVEFORM_HEIGHT}:mode=cline:rate={FPS}:"
        f"colors={WAVEFORM_COLOR}:scale=sqrt[wave];"
        # 封面循环
        f"[0:v]loop=loop=-1:size=1:start=0,setpts=N/({FPS}*TB),"
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg];"
        # 波形叠加到封面
        f"[bg][wave]overlay=0:{WAVEFORM_Y_POSITION}:shortest=1[v]"
    )
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(cover_path),
        "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", "1:a",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-r", str(FPS),
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path)
    ]
    
    print(f"🎬 正在合成视频...")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        print(f"❌ 视频合成失败")
        print(result.stderr.decode())
        return False
    return True


def process_podcast(audio_file: str, cover_file: str = None):
    """
    处理单个播客
    - audio_file: 音频文件名（在 input/audio/ 下）
    - cover_file: 封面文件名（在 input/cover/ 下），如果不指定则自动匹配同名文件
    """
    audio_path = INPUT_AUDIO / audio_file
    if not audio_path.exists():
        print(f"❌ 音频文件不存在：{audio_path}")
        return False
    
    # 自动匹配封面
    if cover_file is None:
        audio_stem = audio_path.stem
        for ext in [".jpg", ".jpeg", ".png"]:
            candidate = INPUT_COVER / f"{audio_stem}{ext}"
            if candidate.exists():
                cover_file = candidate.name
                break
    
    if cover_file is None:
        # 使用第一个找到的封面
        covers = list(INPUT_COVER.glob("*.jpg")) + list(INPUT_COVER.glob("*.png"))
        if covers:
            cover_file = covers[0].name
        else:
            print(f"❌ 未找到封面图片，请在 input/cover/ 放置 jpg/png 文件")
            return False
    
    cover_path = INPUT_COVER / cover_file
    if not cover_path.exists():
        print(f"❌ 封面文件不存在：{cover_path}")
        return False
    
    print(f"📁 音频：{audio_path.name}")
    print(f"🖼️  封面：{cover_path.name}")
    
    # 处理封面（高斯模糊填充）
    processed_cover = OUTPUT_TEMP / f"cover_9x16_{cover_path.stem}.jpg"
    print(f"🔄 处理封面为 9:16...")
    if not process_cover_blur(cover_path, processed_cover):
        return False
    print(f"✅ 封面处理完成：{processed_cover.name}")
    
    # 合成视频
    output_video = OUTPUT_FINAL / f"{audio_path.stem}_video.mp4"
    if not create_video_with_waveform(processed_cover, audio_path, output_video):
        return False
    
    duration = get_audio_duration(audio_path)
    print(f"✅ 视频生成完成！")
    print(f"   📍 路径：{output_video}")
    print(f"   ⏱️  时长：{duration:.1f} 秒")
    print(f"   📐 比例：9:16 (1080x1920)")
    
    return True


def batch_process():
    """批量处理所有音频文件"""
    audio_files = list(INPUT_AUDIO.glob("*.mp3")) + list(INPUT_AUDIO.glob("*.wav")) + list(INPUT_AUDIO.glob("*.m4a"))
    
    if not audio_files:
        print(f"⚠️  未找到音频文件，请在 input/audio/ 放置 mp3/wav/m4a 文件")
        return
    
    print(f"📦 找到 {len(audio_files)} 个音频文件")
    print("-" * 50)
    
    success = 0
    for audio_path in audio_files:
        print(f"\n🎙️  处理：{audio_path.name}")
        if process_podcast(audio_path.name):
            success += 1
        print("-" * 50)
    
    print(f"\n🎉 完成！成功处理 {success}/{len(audio_files)} 个文件")
    print(f"📂 输出目录：{OUTPUT_FINAL}")


def main():
    ensure_dirs()
    
    if not check_ffmpeg():
        sys.exit(1)
    
    if len(sys.argv) > 1:
        # 指定音频文件
        audio_file = sys.argv[1]
        cover_file = sys.argv[2] if len(sys.argv) > 2 else None
        process_podcast(audio_file, cover_file)
    else:
        # 批量处理
        batch_process()


if __name__ == "__main__":
    main()
