# 播客音频转视频工作流

将播客音频 + 封面图自动合成为微信视频号适配的 9:16 竖屏视频。

## 功能

- ✅ 封面图自动处理为 9:16（高斯模糊填充）
- ✅ 动态音频波形
- ✅ 批量处理
- ✅ 自动匹配同名封面

## 目录结构

```
播客工作流/
├── input/
│   ├── audio/     # 放音频文件 (mp3/wav/m4a)
│   └── cover/     # 放封面图片 (jpg/png)
├── output/
│   ├── final/     # 生成的视频
│   └── temp/      # 临时文件
├── main.py        # 主程序
└── README.md
```

## 使用方法

### 1. 安装 FFmpeg

```bash
brew install ffmpeg
```

### 2. 放置素材

- 音频文件放入 `input/audio/`
- 封面图片放入 `input/cover/`

> 💡 如果音频和封面同名（如 `episode01.mp3` 和 `episode01.jpg`），会自动匹配

### 3. 运行

```bash
# 批量处理所有音频
python3 main.py

# 处理单个音频
python3 main.py episode01.mp3

# 指定封面
python3 main.py episode01.mp3 cover.jpg
```

### 4. 获取视频

生成的视频在 `output/final/` 目录

## 输出规格

- 分辨率：1080 × 1920 (9:16)
- 帧率：30fps
- 视频编码：H.264
- 音频编码：AAC 192kbps
