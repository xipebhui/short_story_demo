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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)


class TTSService:
    """简化的TTS服务"""
    
    def __init__(self):
        self.base_url = os.environ.get('TTS_OLD_URL', 'http://localhost:3000')
        self.session = requests.Session()
    
    def generate(self, text: str, voice: str) -> tuple[bytes, str]:
        """生成语音，使用异步接口，返回音频数据和字幕文本"""
        logger.info(f"开始生成TTS任务，文本长度: {len(text)}, 语音: {voice}")
        
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
                        logger.info(f"字幕下载成功，大小: {len(subtitle_text)} 字符")
                    else:
                        logger.error(f"下载字幕失败: {srt_response.status_code}")
                
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
        logger.info(f"音频文件保存成功: {output_file}")
        
        # 保存字幕文件（如果有的话）
        subtitle_file = None
        if subtitle_text:
            subtitle_file = output_file.replace('.mp3', '.srt').replace('.wav', '.srt')
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                f.write(subtitle_text)
            logger.info(f"字幕文件保存成功: {subtitle_file}")
        
        return subtitle_file
    
    
    
    def generate_story_audio(self, story_text: str, voice: str = "en-US-BrianNeural") -> bytes:
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
            batch_lines = lines[i:i+batch_size]
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
    
    if len(sys.argv) != 4:
        print("用法: python tts_client_new.py <story_file> <voice> <output_file>")
        sys.exit(1)
    
    story_file = sys.argv[1]
    voice = sys.argv[2]
    output_file = sys.argv[3]
    
    # 读取故事文件
    with open(story_file, 'r', encoding='utf-8') as f:
        story_text = f.read()
    
    # 生成音频
    client = TTSClient()
    audio_data = client.generate_and_save_audio(story_text, output_file, voice)
    

