# Short Story Demo 项目

## 项目简介

这是一个基于 AI 的视频处理项目，能够自动将视频内容转换为短故事形式。项目的核心功能是分析视频内容，生成字幕，并通过 AI 将内容切割成适合短视频平台的故事片段，同时生成对应的英文翻译和语音。

## 核心功能

项目主要围绕 `short_story_generator.py` 实现以下功能流程：

1. **视频下载与切割** - 下载指定视频并按时长切割成段
2. **语音识别** - 为每个视频段生成 SRT 字幕文件
3. **AI 故事分析** - 使用 AI 分析字幕内容，切割成完整的故事片段
4. **内容翻译** - 将中文内容翻译成英文，适配美国文化
5. **语音合成** - 为英文翻译生成语音文件
6. **草稿生成** - 生成用于视频制作的草稿文件

## 系统要求

- **Python 版本**: Python <= 3.11
- **操作系统**: 支持 Windows, macOS, Linux

## 依赖外部服务

项目依赖以下外部服务：

1. **Gemini API** - 用于 AI 文本分析和翻译
2. **TTS 服务** - 用于语音合成（Text-to-Speech）
3. **FFmpeg** - 用于视频/音频处理
4. **yt-dlp** - 用于视频下载
5. **Whisper** - 用于语音识别生成字幕

## 安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 FFmpeg（根据操作系统选择）
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg

# Windows: 下载并安装 FFmpeg
```

## 项目结构

```
short_story_demo/
├── short_story_generator.py    # 核心主程序
├── dl_splitter_video.py       # 视频下载和切割模块
├── srt_generate.py            # SRT 字幕生成模块
├── newapi_client.py           # Gemini API 客户端
├── tts_client_new.py          # TTS 语音合成客户端
├── draft_gen.py               # 草稿生成模块
├── requirements.txt           # Python 依赖列表
├── output/                    # 输出目录
│   ├── org_materials/         # 原始视频和音频文件
│   ├── ai_analysis/           # AI 分析结果缓存
│   └── tmp_voice/             # 临时语音文件
└── README.md                  # 项目说明文档
```

## 运行方式

### 基础用法

```bash
python short_story_generator.py <video_url>
```

### 完整参数

```bash
python short_story_generator.py <video_url> [max_duration_minutes] [output_dir]
```

**参数说明：**
- `video_url`: 视频 URL（必需）
- `max_duration_minutes`: 视频切割的最大时长（分钟，默认：10）
- `output_dir`: 输出目录（默认：./output/org_materials）

### 使用示例

```bash
# 基础使用
python short_story_generator.py "https://www.bilibili.com/video/BV1abc123def"

# 指定切割时长为 15 分钟
python short_story_generator.py "https://www.bilibili.com/video/BV1abc123def" 15

# 指定输出目录
python short_story_generator.py "https://www.bilibili.com/video/BV1abc123def" 10 "./my_output"
```

## 配置选项

### 缓存控制

项目支持缓存机制来避免重复处理：

- **dl_splitter_video.py**: 修改文件头部 `ENABLE_CACHE_CHECK = True/False`
- **srt_generate.py**: 修改文件头部 `ENABLE_CACHE_CHECK = True/False`

设置为 `True` 时，程序会检查已存在的处理结果并跳过重复处理。

## 输出文件

项目运行后会生成以下文件：

1. **视频文件**: `output/org_materials/*.mp4`
2. **音频文件**: `output/org_materials/*.wav`
3. **字幕文件**: `output/*.srt`
4. **AI 分析结果**: `output/ai_analysis/*.json`
5. **语音文件**: `output/tmp_voice/*/story_*_dialogue_*.mp3`
6. **项目缓存**: `output/video_project_*.json`

## 功能特点

- ✅ **智能缓存**: 自动检测已处理文件，避免重复计算
- ✅ **故事切割**: AI 智能分析内容，确保故事完整性
- ✅ **文化适配**: 自动将人物和地点名称适配美国文化
- ✅ **时长控制**: 支持 1-2 分钟的短视频时长控制
- ✅ **批量处理**: 支持长视频自动切割成多个片段
- ✅ **错误恢复**: 完善的异常处理和进度显示

## 注意事项

1. 确保网络连接稳定，用于访问外部 API 服务
2. 首次运行时会下载 Whisper 模型，需要一定时间
3. 处理大文件时请确保有足够的磁盘空间
4. 建议在处理前检查视频 URL 的有效性

## 故障排除

### 常见问题

1. **FFmpeg 未找到**: 确保 FFmpeg 已正确安装并添加到系统 PATH
2. **API 调用失败**: 检查网络连接和 API 密钥配置
3. **内存不足**: 减少 `max_duration_minutes` 参数或处理较小的视频文件
4. **权限错误**: 确保输出目录有写入权限

### 日志查看

程序运行过程中会显示详细的处理日志，包括：
- 📥 视频下载进度
- 🎵 字幕生成状态
- 🤖 AI 分析结果
- 🎤 语音合成进度
- 💾 缓存使用情况

## 开发说明

项目采用模块化设计，主要模块职责：

- **ShortStoryGenerator**: 主控制器，协调各模块工作
- **VideoDownloader**: 视频下载和切割
- **SRTGenerator**: 语音识别和字幕生成
- **GeminiClient**: AI 文本分析服务
- **TTSClient**: 语音合成服务
- **DraftGenerator**: 草稿文件生成

每个模块都支持独立测试和缓存机制。