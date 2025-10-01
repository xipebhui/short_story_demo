#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B站视频下载脚本 - 简化版本
支持同时切割视频和音频文件
"""

# 配置选项
ENABLE_CACHE_CHECK = True  # 是否启用缓存检测，True=检测已存在文件并跳过，False=总是重新处理

import subprocess
import sys
import os
import argparse
import logging
import glob
import json
import math
from typing import Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class VideoDownloader:
    """B站视频下载和切割处理类"""

    def __init__(self,
                 max_duration_minutes: int = 4,
                 output_dir: str = "./output/org_materials"):
        """
        初始化视频下载器

        Args:
            max_duration_minutes: 切割的最大时长（分钟）
            output_dir: 输出目录
        """
        self.max_duration_minutes = max_duration_minutes
        self.output_dir = output_dir
        self.logger = logging.getLogger(f"{__name__}.VideoDownloader")

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            self.logger.info(f"Created output directory: {self.output_dir}")

    def _run_command(self, cmd: list) -> Tuple[int, str, str]:
        """Execute shell command and return result"""
        try:
            self.logger.info(f"Executing command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return result.returncode, result.stdout, result.stderr
        except Exception as e:
            return 1, "", str(e)


    def _get_audio_duration(self, audio_file: str) -> float:
        """Get audio duration in seconds using ffprobe"""
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            audio_file
        ]

        returncode, stdout, stderr = self._run_command(cmd)


        try:
            probe_data = json.loads(stdout)
            duration = float(probe_data['format']['duration'])
            self.logger.info(f"音频时长: {duration:.2f} 秒 ({duration/60:.2f} 分钟)")
            return duration
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to parse audio duration: {e}")
            return 0.0


    def _split_media_by_duration(self, video_file: str, audio_file: str) -> List[dict]:
        """Split both audio and video into segments of specified duration (in minutes)"""
        if not os.path.exists(audio_file):
            self.logger.error(f"Audio file not found: {audio_file}")
            return []

        if not os.path.exists(video_file):
            self.logger.error(f"Video file not found: {video_file}")
            return []

        # Convert seconds to HH:MM:SS format
        def seconds_to_time(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

        # Get total duration
        total_duration = self._get_audio_duration(audio_file)
        if total_duration == 0:
            self.logger.error("Cannot get audio duration")
            return []

        max_duration_seconds = self.max_duration_minutes * 60

        # Check if splitting is needed
        if total_duration <= max_duration_seconds:
            self.logger.info(f"媒体时长 {total_duration/60:.2f} 分钟，无需切割")
            return [{
                "url": None,  # Will be set by process_video method
                "org_video_file_path": video_file,
                "org_audio_file_path": audio_file,
                "segment_index": 1,
                "start_time": "00:00:00.000",
                "duration": seconds_to_time(total_duration)
            }]

        # Calculate number of segments
        num_segments = math.ceil(total_duration / max_duration_seconds)
        self.logger.info(f"媒体将被切割为 {num_segments} 段，每段最长 {self.max_duration_minutes} 分钟")

        # Generate segment file paths
        audio_base_name = os.path.splitext(os.path.basename(audio_file))[0]
        video_base_name = os.path.splitext(os.path.basename(video_file))[0]
        video_ext = os.path.splitext(video_file)[1]

        media_segments = []

        for i in range(num_segments):
            start_time = i * max_duration_seconds
            segment_duration = min(max_duration_seconds, total_duration - start_time)

            start_time_str = seconds_to_time(start_time)
            duration_str = seconds_to_time(segment_duration)

            self.logger.info(f"生成第 {i+1}/{num_segments} 段: {start_time_str} - {duration_str}")

            # Generate segment filenames
            audio_segment_filename = f"{audio_base_name}_part{i+1:02d}.wav"
            video_segment_filename = f"{video_base_name}_part{i+1:02d}{video_ext}"

            audio_segment_path = os.path.join(self.output_dir, audio_segment_filename)
            video_segment_path = os.path.join(self.output_dir, video_segment_filename)

            # Split audio
            audio_cmd = [
                "ffmpeg",
                "-i", audio_file,
                "-ss", start_time_str,
                "-t", duration_str,
                "-c", "copy",  # Copy without re-encoding
                "-y",  # Overwrite output file
                audio_segment_path
            ]

            returncode, stdout, stderr = self._run_command(audio_cmd)

            if returncode != 0:
                self.logger.error(f"音频切割第 {i+1} 段失败: {stderr}")
                continue

            self.logger.info(f"✓ 音频第 {i+1} 段保存成功: {audio_segment_path}")

            # Split video
            video_cmd = [
                "ffmpeg",
                "-i", video_file,
                "-ss", start_time_str,
                "-t", duration_str,
                "-c", "copy",  # Copy without re-encoding
                "-y",  # Overwrite output file
                video_segment_path
            ]

            returncode, stdout, stderr = self._run_command(video_cmd)

            if returncode != 0:
                self.logger.error(f"视频切割第 {i+1} 段失败: {stderr}")
                continue

            self.logger.info(f"✓ 视频第 {i+1} 段保存成功: {video_segment_path}")

            # 创建包含视频和音频路径的字典对象
            segment_dict = {
                "url": None,  # Will be set by process_video method
                "org_video_file_path": video_segment_path,
                "org_audio_file_path": audio_segment_path,
                "segment_index": i + 1,
                "start_time": start_time_str,
                "duration": duration_str
            }
            media_segments.append(segment_dict)

        self.logger.info(f"媒体切割完成，共生成 {len(media_segments)} 个媒体段")
        return media_segments


    def _download_video(self, url: str) -> str:
        """Download video using yt-dlp"""
        self.logger.info(f"Downloading video from: {url}")

        title = url.split("/")[-1].split("?")[0]
        # Download video with best quality
        cmd = [
            "yt-dlp",
            "-f", "bestvideo+bestaudio/best",
            "-o", f"{self.output_dir}/{title}.mp4",
            url
        ]

        returncode, stdout, stderr = self._run_command(cmd)

        if returncode != 0:
            self.logger.error("Video download failed")
            self.logger.error(f"Error details: {stderr}")
            return None

        self.logger.info("Video downloaded successfully")

        # Find downloaded video file
        # Look for common video extensions
        video_extensions = ['*.mp4', '*.mkv', '*.webm', '*.avi', '*.mov']
        video_files = []

        for ext in video_extensions:
            video_files.extend(glob.glob(os.path.join(self.output_dir, ext)))

        if video_files:
            # Get the most recently created file
            video_file = max(video_files, key=os.path.getctime)
            self.logger.info(f"Found video file: {video_file}")
            return video_file
        else:
            self.logger.error("Could not find downloaded video file")
            return None


    def _extract_audio(self, video_file: str) -> str:
        """Extract audio from video using ffmpeg"""
        if not video_file or not os.path.exists(video_file):
            self.logger.error("Video file not found")
            return None

        # Generate audio filename
        base_name = os.path.splitext(os.path.basename(video_file))[0]
        audio_file = os.path.join(self.output_dir, f"{base_name}.wav")

        self.logger.info(f"Extracting audio to: {audio_file}")

        # Extract audio using ffmpeg
        cmd = [
            "ffmpeg",
            "-i", video_file,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # WAV format
            "-ar", "44100",  # Sample rate
            "-ac", "2",  # Stereo
            "-y",  # Overwrite output file
            audio_file
        ]

        returncode, stdout, stderr = self._run_command(cmd)

        if returncode != 0:
            self.logger.error("Audio extraction failed")
            self.logger.error(f"Error details: {stderr}")
            return None

        self.logger.info("Audio extracted successfully")
        return audio_file

    def _check_existing_files(self, url: str) -> List[dict]:
        """检查是否已存在处理结果文件"""
        if not ENABLE_CACHE_CHECK:
            return []

        # 从URL提取文件名
        title = url.split("/")[-1].split("?")[0]
        
        # 预期的文件路径
        expected_video = os.path.join(self.output_dir, f"{title}.mp4")
        expected_audio = os.path.join(self.output_dir, f"{title}.wav")
        
        # 检查基本文件是否存在
        if not (os.path.exists(expected_video) and os.path.exists(expected_audio)):
            return []
        
        self.logger.info(f"找到缓存文件: {title}.mp4, {title}.wav")
        
        # 检查是否有切割的段落文件
        video_segments = glob.glob(os.path.join(self.output_dir, f"{title}_part*.mp4"))
        audio_segments = glob.glob(os.path.join(self.output_dir, f"{title}_part*.wav"))
        
        if video_segments and audio_segments and len(video_segments) == len(audio_segments):
            # 返回切割的段落
            media_segments = []
            for i, (video_seg, audio_seg) in enumerate(zip(sorted(video_segments), sorted(audio_segments)), 1):
                media_segments.append({
                    "url": url,
                    "org_video_file_path": video_seg,
                    "org_audio_file_path": audio_seg,
                    "segment_index": i,
                    "start_time": "缓存文件",
                    "duration": "缓存文件"
                })
            
            self.logger.info(f"发现缓存切割文件，共 {len(media_segments)} 个段落")
            return media_segments
        else:
            # 返回单个完整文件
            self.logger.info("发现缓存完整文件")
            return [{
                "url": url,
                "org_video_file_path": expected_video,
                "org_audio_file_path": expected_audio,
                "segment_index": 1,
                "start_time": "00:00:00.000",
                "duration": "缓存文件"
            }]

    def process_video(self, url: str) -> List[dict]:
        """
        主要的公共方法：下载视频并切割

        Args:
            url: 视频URL

        Returns:
            List[dict]: 媒体段列表，每个元素包含:
                {
                    "url": "原始视频URL",
                    "org_video_file_path": "视频文件路径",
                    "org_audio_file_path": "音频文件路径"
                }
        """
        self.logger.info("========== 开始视频处理 ==========")
        self.logger.info(f"视频URL: {url}")
        self.logger.info(f"最大切割时长: {self.max_duration_minutes} 分钟")
        self.logger.info(f"输出目录: {self.output_dir}")
        self.logger.info(f"缓存检测: {'启用' if ENABLE_CACHE_CHECK else '禁用'}")

        # 检查是否存在缓存文件
        existing_segments = self._check_existing_files(url)
        if existing_segments:
            self.logger.info("========== 发现缓存文件，跳过处理 ==========")
            self.logger.info(f"找到 {len(existing_segments)} 个已存在的媒体段:")
            for i, segment in enumerate(existing_segments, 1):
                self.logger.info(f"  {i}. URL: {segment['url']}")
                self.logger.info(f"     视频: {segment['org_video_file_path']}")
                self.logger.info(f"     音频: {segment['org_audio_file_path']}")
            return existing_segments

        # 下载视频
        video_file = self._download_video(url)
        if not video_file:
            self.logger.error("Failed to download video")
            return []

        # 提取音频
        audio_file = self._extract_audio(video_file)
        if not audio_file:
            self.logger.error("Failed to extract audio")
            return []

        # 切割媒体
        self.logger.info("========== 开始媒体切割处理 ==========")
        media_segments = self._split_media_by_duration(video_file, audio_file)

        if not media_segments:
            self.logger.error("Failed to process media segments")
            return []

        # 为每个媒体段添加URL信息
        for segment in media_segments:
            segment["url"] = url

        self.logger.info("========== Process completed ==========")
        self.logger.info("Video downloaded and media processed successfully!")
        self.logger.info(f"Generated {len(media_segments)} media segment(s):")

        for i, segment in enumerate(media_segments, 1):
            self.logger.info(f"  {i}. URL: {segment['url']}")
            self.logger.info(f"     视频: {segment['org_video_file_path']}")
            self.logger.info(f"     音频: {segment['org_audio_file_path']}")

        return media_segments


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Simple Bilibili video downloader with video and audio extraction and splitting")
    parser.add_argument("url", help="Bilibili video URL")
    parser.add_argument("-o", "--output", default="./output/org_materials", help="Output directory (default: ./output/org_materials)")
    parser.add_argument("--max-duration", type=int, default=10,
                       help="Maximum media duration per segment in minutes (default: 10)")

    args = parser.parse_args()

    # 创建视频下载器实例
    downloader = VideoDownloader(
        max_duration_minutes=args.max_duration,
        output_dir=args.output
    )

    # 处理视频
    try:
        media_segments = downloader.process_video(args.url)
        if media_segments:
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        logger.error(f"处理视频时发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()