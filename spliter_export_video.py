#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频切割脚本 - 根据AI分析结果切割导出的视频
目标：将视频切割为35-60秒的片段
"""

import sys
import json
import os
import logging
from typing import List, Dict, Optional
from newapi_client import GeminiClient
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# 目标切割时长（秒）
TARGET_MIN_DURATION = 35
TARGET_MAX_DURATION = 60

# AI 提示词
SPLIT_PROMPT = """
你是一个视频切割助手。我会给你一个视频的故事内容和时长信息，你需要分析并给出最佳的切割方案。

目标要求：
1. 每个片段时长控制在 35-60 秒之间
2. 切割点应该在故事情节的自然断点
3. 保持故事连贯性，不要在关键情节中间切断

输出格式（纯JSON，不要任何解释）：
{
  "segments": [
    {
      "segment_index": 1,
      "start_time": 0.0,
      "end_time": 45.5,
      "reason": "第一段故事开头到转折点"
    },
    {
      "segment_index": 2,
      "start_time": 45.5,
      "end_time": 90.0,
      "reason": "转折点到结局"
    }
  ],
  "total_segments": 2
}
"""


class VideoSplitter:
    """视频切割器"""

    def __init__(self):
        self.client = GeminiClient()

    def load_project_cache(self, cache_file: str) -> Optional[Dict]:
        """加载项目缓存文件"""
        try:
            logger.info(f"📂 加载项目缓存: {cache_file}")
            with open(cache_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)
            logger.info(f"✅ 项目缓存加载成功")
            return project_data
        except Exception as e:
            logger.error(f"❌ 加载项目缓存失败: {e}")
            return None

    def get_video_duration(self, video_path: str) -> Optional[float]:
        """获取视频时长（秒）"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            duration = float(result.stdout.strip())
            logger.info(f"📹 视频时长: {duration:.2f} 秒")
            return duration
        except Exception as e:
            logger.error(f"❌ 获取视频时长失败: {e}")
            return None

    def analyze_split_points(self, project_data: Dict, video_duration: float) -> Optional[Dict]:
        """使用AI分析切割点"""
        try:
            # 构建输入文本
            story_info = {
                "video_duration": video_duration,
                "segments": []
            }

            # 提取所有故事信息
            for segment in project_data.get('segments', []):
                for story in segment.get('stories', []):
                    story_info['segments'].append({
                        "title": story.get('story_title', ''),
                        "dialogue_count": len(story.get('dialogue_list', []))
                    })

            input_text = f"""
视频总时长: {video_duration:.2f} 秒
故事内容: {json.dumps(story_info, ensure_ascii=False, indent=2)}

请分析并给出切割方案，确保每个片段在 {TARGET_MIN_DURATION}-{TARGET_MAX_DURATION} 秒之间。
"""

            logger.info("🤖 正在调用AI分析切割点...")
            result = self.client.analyze_text(input_text, SPLIT_PROMPT)

            if not result:
                logger.error("❌ AI分析返回空结果")
                return None

            # 清理结果
            if result.startswith('```'):
                result = result.replace('```json', '').replace('```', '').strip()

            split_data = json.loads(result)
            logger.info(f"✅ AI分析完成，建议切割为 {split_data.get('total_segments', 0)} 个片段")
            return split_data

        except Exception as e:
            logger.error(f"❌ AI分析失败: {e}")
            return None

    def split_video(self, video_path: str, split_data: Dict, output_dir: str = "./output/split_videos") -> List[str]:
        """切割视频"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_files = []

            for segment in split_data.get('segments', []):
                segment_index = segment['segment_index']
                start_time = segment['start_time']
                end_time = segment['end_time']
                duration = end_time - start_time

                output_file = os.path.join(output_dir, f"{base_name}_part{segment_index}.mp4")

                logger.info(f"✂️ 切割片段 {segment_index}: {start_time:.2f}s - {end_time:.2f}s (时长: {duration:.2f}s)")

                # 使用 ffmpeg 切割
                cmd = [
                    'ffmpeg',
                    '-i', video_path,
                    '-ss', str(start_time),
                    '-t', str(duration),
                    '-c', 'copy',
                    '-y',
                    output_file
                ]

                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"✅ 片段保存: {output_file}")
                output_files.append(output_file)

            return output_files

        except Exception as e:
            logger.error(f"❌ 视频切割失败: {e}")
            return []

    def process(self, cache_file: str, video_path: str) -> List[str]:
        """处理流程：加载缓存 -> AI分析 -> 切割视频"""
        logger.info(f"🎬 开始处理视频切割")

        # 1. 加载项目缓存
        project_data = self.load_project_cache(cache_file)
        if not project_data:
            return []

        # 2. 获取视频时长
        duration = self.get_video_duration(video_path)
        if not duration:
            return []

        # 3. 判断是否需要切割
        if duration <= TARGET_MAX_DURATION:
            logger.info(f"✅ 视频时长 {duration:.2f}s 在目标范围内，无需切割")
            return [video_path]

        # 4. AI分析切割点
        split_data = self.analyze_split_points(project_data, duration)
        if not split_data:
            return []

        # 5. 切割视频
        output_files = self.split_video(video_path, split_data)

        if output_files:
            logger.info(f"✅ 视频切割完成，共 {len(output_files)} 个片段")
        else:
            logger.error("❌ 视频切割失败")

        return output_files


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python spliter_export_video.py <project_cache_file> <exported_video_path>")
        print("示例: python spliter_export_video.py ./output/project_cache/BV123_xxx.json ./output/exported_videos/video.mp4")
        sys.exit(1)

    cache_file = sys.argv[1]
    video_path = sys.argv[2]

    splitter = VideoSplitter()
    result_files = splitter.process(cache_file, video_path)

    if result_files:
        print(f"\n✅ 处理完成！共 {len(result_files)} 个视频片段:")
        for f in result_files:
            print(f"  - {f}")
    else:
        print("\n❌ 处理失败")
        sys.exit(1)