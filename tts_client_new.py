#!/usr/bin/env python3
"""
TTS客户端 - 简化版本
只保留最基本的功能，使用旧服务，异步执行
完全独立，无需外部依赖
"""

import os
import json
import time
import requests
import logging
from pydub import AudioSegment
import subprocess
import tempfile
import shutil
from dotenv import load_dotenv


# 默认加载当前目录下的 .env
load_dotenv()


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger('urllib3').disabled = True


class TTSService:
    """简化的TTS服务"""

    def __init__(self):
        self.base_url = os.environ.get('TTS_OLD_URL', 'http://localhost:3000')
        self.session = requests.Session()

    def _whisper_audio_to_srt(self, audio_data: bytes) -> str:
        """使用 Whisper 将音频转换为 SRT 字幕"""
        try:
            logger.info("开始使用 Whisper 作为兜底策略生成字幕")

            # 创建临时音频文件
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_audio:
                temp_audio.write(audio_data)
                temp_audio_path = temp_audio.name

            # 创建临时输出目录
            temp_dir = tempfile.mkdtemp()

            try:
                # 使用 whisper 命令行工具转换音频
                cmd = [
                    'whisper',
                    temp_audio_path,
                    '--output_dir', temp_dir,
                    '--output_format', 'srt',
                    '--language', 'en',
                    '--model', 'base',
                    '--word_timestamps', 'True',
                    '--max_words_per_line', '1'
                ]

                logger.info(f"执行 Whisper 命令: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

                if result.returncode == 0:
                    # 查找生成的 SRT 文件
                    base_name = os.path.splitext(os.path.basename(temp_audio_path))[0]
                    srt_file_path = os.path.join(temp_dir, f"{base_name}.srt")

                    if os.path.exists(srt_file_path):
                        with open(srt_file_path, 'r', encoding='utf-8') as f:
                            srt_content = f.read()
                        logger.info(f"Whisper 生成字幕成功，大小: {len(srt_content)} 字符")
                        return srt_content
                    else:
                        logger.error(f"未找到生成的 SRT 文件: {srt_file_path}")
                        return None
                else:
                    logger.error(f"Whisper 执行失败: {result.stderr}")
                    return None

            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_audio_path)
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.warning(f"清理临时文件失败: {e}")

        except subprocess.TimeoutExpired:
            logger.error("Whisper 执行超时")
            return None
        except FileNotFoundError:
            logger.error("未找到 whisper 命令，请确保已安装 openai-whisper")
            return None
        except Exception as e:
            logger.error(f"Whisper 转换过程中发生错误: {e}")
            return None

    def generate(self, text: str, voice: str) -> tuple[bytes, str]:
        """生成语音，使用异步接口，返回音频数据和字幕文本"""

        # 创建任务（异步接口会快速返回）
        url = f"{self.base_url}/api/v1/tts/create"
        payload = {
            'text': text,
            'voice': voice,
            'pitch': '+0Hz',
            'volume': '+0%',
            'rate': '+0%'
        }

        # 快速创建任务
        response = self.session.post(url, json=payload, timeout=10)
        task_data = response.json()
        task_id = task_data.get('taskId') or task_data.get('data', {}).get('id')
        logger.info(f"任务创建成功，ID: {task_id}")

        # 轮询任务状态（短间隔检查）
        status_url = f"{self.base_url}/api/v1/tts/task/{task_id}"
        while True:
            time.sleep(1)  # 缩短等待时间
            status_response = self.session.get(status_url, timeout=5)
            status_data = status_response.json()
            task_info = status_data.get('data', {})
            status = task_info.get('status')

            if status == 'completed':
                result = task_info.get('result', {})
                audio_file = result.get('audio') or result.get('file')
                srt_file = result.get('srt')

                # 快速下载音频
                filename = audio_file.split('/')[-1] if '/' in audio_file else audio_file
                download_url = f"{self.base_url}/api/v1/tts/download/{filename}"
                logger.info(f"下载音频: {download_url}")
                audio_response = self.session.get(download_url, timeout=15)

                # 下载字幕文件
                subtitle_text = None
                if srt_file:
                    # 提取文件名
                    srt_filename = srt_file.split('/')[-1] if '/' in srt_file else srt_file
                    srt_download_url = f"{self.base_url}/api/v1/tts/download/{srt_filename}"
                    logger.info(f"下载字幕: {srt_download_url}")

                    srt_response = self.session.get(srt_download_url, timeout=30)
                    if srt_response.status_code == 200:
                        subtitle_text = srt_response.text
                    else:
                        logger.warning(f"下载字幕失败: {srt_response.status_code}")
                        # 使用 Whisper 作为兜底策略
                        subtitle_text = self._whisper_audio_to_srt(audio_response.content)
                        if subtitle_text:
                            logger.info("Whisper 兜底策略成功生成字幕")
                        else:
                            logger.warning("Whisper 兜底策略也失败了，将返回空字幕")
                else:
                    # 如果没有 srt_file，也尝试使用 Whisper 生成字幕
                    logger.info("未获取到字幕文件，尝试使用 Whisper 生成字幕")
                    subtitle_text = self._whisper_audio_to_srt(audio_response.content)
                    if subtitle_text:
                        logger.info("Whisper 成功生成字幕")
                    else:
                        logger.warning("Whisper 生成字幕失败，将返回空字幕")

                return audio_response.content, subtitle_text

            elif status == 'failed':
                logger.error(f"TTS生成失败: {status_data}")
                raise Exception("TTS生成失败")


class TTSClient:
    """TTS客户端类 - 简化版本"""

    def __init__(self):
        """初始化TTS客户端，只使用旧服务"""
        self.service = TTSService()

    def generate_speech(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> tuple[bytes, str]:
        """
        生成语音

        Args:
            text: 要转换的文本
            voice: 语音类型

        Returns:
            (音频数据（字节）, 字幕文本)
        """
        return self.service.generate(text, voice)

    def generate_and_save_audio(self, text: str, output_file: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str:
        """
        直接生成语音并保存为音频文件

        Args:
            text: 要转换的文本
            output_file: 输出音频文件路径
            voice: 语音类型

        Returns:
            字幕文件路径（如果有的话）
        """
        logger.info(f"开始生成音频文件: {output_file}")

        # 生成音频和字幕
        audio_data, subtitle_text = self.generate_speech(text, voice)

        # 保存音频文件
        with open(output_file, 'wb') as f:
            f.write(audio_data)
        

        # 保存字幕文件（如果有的话）
        subtitle_file = None
        if subtitle_text:
            subtitle_file = output_file.replace('.mp3', '.srt').replace('.wav', '.srt')
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write(subtitle_text)
            

        return subtitle_file

    def generate_story_audio(self, story_text: str, voice: str = "zh-HK-HiuMaanNeural") -> bytes:
        """
        生成故事音频

        Args:
            story_text: 故事文本内容
            voice: 语音类型

        Returns:
            合并后的音频数据（字节）
        """
        # 按行分割文本
        lines = [line.strip() for line in story_text.split('\n') if line.strip()]

        # 每3行合并为一批处理
        batch_size = 3
        audio_segments = []

        for i in range(0, len(lines), batch_size):
            batch_lines = lines[i:i + batch_size]
            batch_text = " ".join(batch_lines)

            # 生成音频
            audio_data, _ = self.generate_speech(batch_text, voice)  # 忽略字幕

            # 转换为AudioSegment
            import io
            audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="mp3")
            audio_segments.append(audio_segment)

        # 合并所有音频
        combined = AudioSegment.empty()
        for segment in audio_segments:
            combined += segment

        # 导出为字节数据
        import io
        output = io.BytesIO()
        combined.export(output, format="mp3")
        return output.getvalue()


# 简单的命令行接口
if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("用法: python tts_client_new.py <story_file>  <output_file>")
        sys.exit(1)

    story_file = sys.argv[1]
    output_file = sys.argv[2]

    # 读取故事文件
    with open(story_file, 'r', encoding='utf-8') as f:
        story_text = f.read()

    # 生成音频
    client = TTSClient()
    audio_data = client.generate_and_save_audio(story_text, output_file)
