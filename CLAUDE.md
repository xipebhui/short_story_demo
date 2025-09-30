# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个基于 AI 的视频内容自动化处理项目，将长视频切割成短故事片段，并生成英文配音和草稿文件。主要用于短视频内容生成。

**核心工作流程**：视频下载与切割 → 语音识别生成字幕 → AI 故事分析与切割 → 内容翻译 → 语音合成 → 草稿文件生成

## 常用命令

### 开发运行

```bash
# 基础运行（处理视频 URL）
python short_story_generator.py "<video_url>"

# 指定视频切割时长（分钟）
python short_story_generator.py "<video_url>" 15

# 指定输出目录
python short_story_generator.py "<video_url>" 10 "./custom_output"
```

### 独立模块测试

```bash
# 测试视频下载和切割
python dl_splitter_video.py

# 测试字幕生成
python srt_generate.py <audio_file.mp3>

# 测试 Gemini API 客户端
python newapi_client.py
```

### 环境设置

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 FFmpeg（macOS）
brew install ffmpeg

# 安装 FFmpeg（Ubuntu/Debian）
sudo apt update && sudo apt install ffmpeg
```

## 架构设计

### 核心类与职责

**ShortStoryGenerator**（主控制器）
- 协调整个处理流程
- 管理 VideoProject 和 VideoSegment 对象
- 处理项目缓存（`./output/project_cache/`）
- 依赖：VideoDownloader, SRTGenerator, GeminiClient, TTSClient, DraftGenerator

**VideoProject & VideoSegment**（数据模型）
- VideoProject：代表整个视频项目，包含多个 VideoSegment
- VideoSegment：代表一个视频片段，包含多个 StoryContent
- StoryContent：代表一个完整的短故事，包含多个 StoryDialogue
- StoryDialogue：代表一句对话，包含中英文文本、时间戳、语音路径

**VideoDownloader**（视频处理，`dl_splitter_video.py`）
- 使用 yt-dlp 下载视频
- 使用 FFmpeg 按时长切割视频和音频
- 输出：`./output/org_materials/*.mp4` 和 `*.wav`
- 缓存控制：修改文件头部 `ENABLE_CACHE_CHECK`

**SRTGenerator**（字幕生成，`srt_generate.py`）
- 使用 Whisper 模型进行语音识别
- 生成 JSON 格式字幕文件（非标准 SRT 格式）
- 合并短段落（最大 3 秒）
- 输出：`./output/json_files/*.json`
- 缓存控制：修改文件头部 `ENABLE_CACHE_CHECK`
- 配置：`STORY_DURATIME_SECONDS = 120`（故事时长估算）

**GeminiClient**（AI 分析，`newapi_client.py`）
- 调用 Gemini API 进行内容分析和翻译
- 需要环境变量：`NEWAPI_API_KEY`, `NEWAPI_BASE_URL`
- 使用 retry 装饰器实现自动重试
- 输出：JSON 格式的故事切割结果
- AI 分析结果缓存：`./output/ai_analysis/*.json`

**TTSClient**（语音合成，`tts_client_new.py`）
- 将英文文本转换为语音
- 输出：`./output/tmp_voice/{video_id}_segment_{n}/story_{n}_dialogue_{n}.mp3`

**DraftGenerator**（草稿生成，`draft_gen.py`）
- 基于模板生成剪映草稿文件
- 模板路径：`./templates/draft_content_fuhe.json`, `draft_meta_info.json`
- 输出：`./output/my_draft_folder/story_{n}_{title}/`
- 配置开关：
  - `SUBTITLE_DEBUG_MODE`：调试模式
  - `ENABLE_CHINESE_SUBTITLES`：中文字幕开关
  - `ENABLE_ENGLISH_SUBTITLES`：英文字幕开关
  - `TARGET_DURATION_SECONDS = 59.0`：目标视频时长
  - `MAX_SPEED_FACTOR = 2.0`：最大播放速度

### AI Prompt 设计

系统 prompt 定义在 `short_story_generator.py` 中的 `sys_prompt` 变量：
- 核心要求：保持时间戳不变、故事完整性、1.5 分钟时长控制
- 翻译要求：简洁英文、符合美国文化、人名地名本地化
- 输出格式：纯 JSON，包含 story_title, start_time, end_time, dialogue 数组
- 标题要求：吸引力、悬念、包含原作标签、不超过 90 字符

### 数据流

```
视频 URL
  ↓ [VideoDownloader]
视频片段 (*.mp4, *.wav)
  ↓ [SRTGenerator + Whisper]
字幕 JSON 文件
  ↓ [GeminiClient + sys_prompt]
故事切割结果 (JSON)
  ↓ [TTSClient]
英文语音文件 (*.mp3)
  ↓ [DraftGenerator]
剪映草稿文件 (draft_content.json, draft_meta_info.json)
```

### 缓存机制

项目实现三级缓存：
1. **文件级缓存**：`dl_splitter_video.py` 和 `srt_generate.py` 中的 `ENABLE_CACHE_CHECK`
2. **AI 分析缓存**：`./output/ai_analysis/{video_id}.json`
3. **项目级缓存**：`./output/project_cache/video_project_{url}_{timestamp}.json`

缓存检查逻辑在 `short_story_generator.py` 的 `ai_analysis_story()` 方法中。

## 环境依赖

### 外部服务
- **Gemini API**：文本分析和翻译（需要配置 `.env` 文件）
- **TTS 服务**：语音合成
- **FFmpeg**：视频/音频处理
- **yt-dlp**：视频下载

### Python 环境
- **Python 版本**：<= 3.11
- **关键依赖**：
  - `openai-whisper`：语音识别（首次运行会下载模型）
  - `pydub`：音频处理
  - `requests`：HTTP 请求
  - `retry`：自动重试
  - `yt-dlp`：视频下载
  - `python-dotenv`：环境变量加载

### 环境变量配置

创建 `.env` 文件：
```
NEWAPI_API_KEY=your_api_key_here
NEWAPI_BASE_URL=http://your-api-endpoint
```

## 输出目录结构

```
output/
├── org_materials/          # 原始视频和音频文件
│   ├── {video_id}_segment_0.mp4
│   └── {video_id}_segment_0.wav
├── json_files/             # 字幕 JSON 文件
│   └── {video_id}_segment_0.json
├── ai_analysis/            # AI 分析结果缓存
│   └── {video_id}_segment_0.json
├── tmp_voice/              # 临时语音文件
│   └── {video_id}_segment_0/
│       └── story_0_dialogue_0.mp3
├── my_draft_folder/        # 最终草稿文件
│   └── story_0_{title}/
│       ├── draft_content.json
│       └── draft_meta_info.json
└── project_cache/          # 项目缓存
    └── video_project_{url}_{timestamp}.json
```

## 调试与日志

所有模块使用 Python logging，格式包含文件名和行号：
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
```

日志中的表情符号用于快速识别流程阶段：
- 📥 视频下载
- 🎵 字幕生成
- 📖 AI 故事分析
- 🎤 语音合成
- 💾 缓存操作
- ✅ 成功
- ❌ 失败

## 常见问题

1. **首次运行慢**：Whisper 模型首次运行需下载，使用 small 模型
2. **内存不足**：减少 `max_duration_minutes` 参数（默认 10 分钟）
3. **API 调用失败**：检查 `.env` 配置和网络连接
4. **缓存问题**：删除对应缓存目录重新生成