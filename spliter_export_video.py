#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频切割脚本 - 根据 dialogue 时间戳切割导出的视频
目标：将视频切割为36-60秒的片段
"""

import sys
import json
import os
import logging
from typing import List, Dict, Optional
import subprocess
import shutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# 目标切割时长（秒）
TARGET_MIN_DURATION = 36
TARGET_MAX_DURATION = 60

# 视频加速倍数（与 draft_gen.py 中的 MAX_SPEED_FACTOR 保持一致）
VIDEO_SPEED_FACTOR = 1.5


class VideoSplitter:
    """视频切割器"""

    def __init__(self):
        pass

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

    def parse_time_to_seconds(self, time_str: str, apply_speed: bool = True) -> float:
        """将时间字符串 '00:00:05,919' 转换为秒，并应用视频加速"""
        try:
            # 分离时、分、秒和毫秒
            time_part, ms_part = time_str.split(',')
            h, m, s = map(int, time_part.split(':'))
            ms = int(ms_part)
            total_seconds = h * 3600 + m * 60 + s + ms / 1000.0

            # 应用视频加速：导出视频已加速，时间需要除以加速倍数
            if apply_speed:
                total_seconds = total_seconds / VIDEO_SPEED_FACTOR

            return total_seconds
        except Exception as e:
            logger.error(f"❌ 解析时间失败 '{time_str}': {e}")
            return 0.0

    def calculate_split_points(self, story: Dict) -> List[Dict]:
        """根据 dialogue 计算切割点（考虑视频加速）"""
        split_points = []
        current_start = 0.0
        current_dialogues = []

        dialogues = story.get('dialogue', [])
        logger.info(f"  ⚡ 视频加速倍数: {VIDEO_SPEED_FACTOR}x")

        for i, dialogue in enumerate(dialogues):
            # 获取最后一个 video_segment 的结束时间
            video_segments = dialogue.get('video_segments', [])
            if not video_segments:
                continue

            last_segment = video_segments[-1]
            end_time_str = last_segment.get('end', '00:00:00,000')
            # 应用视频加速：原始时间 / 加速倍数
            end_seconds = self.parse_time_to_seconds(end_time_str, apply_speed=True)

            if i == 0:
                logger.info(f"  📝 示例转换: {end_time_str} → {end_seconds:.2f}s (加速后)")

            current_dialogues.append(i)
            duration = end_seconds - current_start

            # 判断是否需要切割
            if duration >= TARGET_MIN_DURATION:
                # 在 36-60s 范围内，保存这个片段
                if duration <= TARGET_MAX_DURATION:
                    split_points.append({
                        'start_time': current_start,
                        'end_time': end_seconds,
                        'duration': duration,
                        'dialogue_indices': current_dialogues.copy()
                    })
                    logger.info(f"  ✓ 片段: {current_start:.2f}s - {end_seconds:.2f}s (时长: {duration:.2f}s, dialogues: {current_dialogues})")

                    # 重置
                    current_start = end_seconds
                    current_dialogues = []
                elif duration > TARGET_MAX_DURATION:
                    # 超过最大时长，需要回退
                    if len(current_dialogues) > 1:
                        # 使用前一个 dialogue 作为结束点
                        prev_dialogue = dialogues[current_dialogues[-2]]
                        prev_segments = prev_dialogue.get('video_segments', [])
                        prev_end_str = prev_segments[-1].get('end', '00:00:00,000')
                        prev_end_seconds = self.parse_time_to_seconds(prev_end_str, apply_speed=True)

                        split_points.append({
                            'start_time': current_start,
                            'end_time': prev_end_seconds,
                            'duration': prev_end_seconds - current_start,
                            'dialogue_indices': current_dialogues[:-1].copy()
                        })
                        logger.info(f"  ✓ 片段: {current_start:.2f}s - {prev_end_seconds:.2f}s (时长: {prev_end_seconds - current_start:.2f}s)")

                        # 从当前 dialogue 重新开始
                        current_start = prev_end_seconds
                        current_dialogues = [i]

        # 检查最后一个片段
        if current_dialogues:
            last_dialogue = dialogues[current_dialogues[-1]]
            last_segments = last_dialogue.get('video_segments', [])
            if last_segments:
                last_end_str = last_segments[-1].get('end', '00:00:00,000')
                last_end_seconds = self.parse_time_to_seconds(last_end_str, apply_speed=True)
                final_duration = last_end_seconds - current_start

                # 只有在时长符合要求时才保存
                if TARGET_MIN_DURATION <= final_duration <= TARGET_MAX_DURATION:
                    split_points.append({
                        'start_time': current_start,
                        'end_time': last_end_seconds,
                        'duration': final_duration,
                        'dialogue_indices': current_dialogues.copy()
                    })
                    logger.info(f"  ✓ 最后片段: {current_start:.2f}s - {last_end_seconds:.2f}s (时长: {final_duration:.2f}s)")
                else:
                    logger.warning(f"  ⚠️ 丢弃最后片段 (时长: {final_duration:.2f}s 不符合要求)")

        return split_points

    def split_video(self, video_path: str, split_points: List[Dict], output_dir: str = "./output/split_videos") -> List[Dict]:
        """切割视频"""
        try:
            # 创建输出目录
            os.makedirs(output_dir, exist_ok=True)

            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_segments = []

            for i, segment in enumerate(split_points, 1):
                start_time = segment['start_time']
                end_time = segment['end_time']
                duration = segment['duration']

                output_file = os.path.join(output_dir, f"{base_name}_part{i}.mp4")

                logger.info(f"✂️ 切割片段 {i}: {start_time:.2f}s - {end_time:.2f}s (时长: {duration:.2f}s)")

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

                output_segments.append({
                    'segment_index': i,
                    'video_path': output_file,
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': duration,
                    'dialogue_indices': segment['dialogue_indices']
                })

            return output_segments

        except Exception as e:
            logger.error(f"❌ 视频切割失败: {e}")
            return []

    def update_project_cache(self, cache_file: str, story_index: int, split_segments: List[Dict]):
        """更新 project cache，保存切割后的视频片段信息"""
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                project_data = json.load(f)

            # 找到对应的 story 并更新
            for segment in project_data.get('segments', []):
                stories = segment.get('stories', [])
                if story_index < len(stories):
                    stories[story_index]['split_video_segments'] = split_segments
                    break

            # 保存更新后的数据
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(project_data, f, ensure_ascii=False, indent=2)

            logger.info(f"✅ Project cache 已更新")

        except Exception as e:
            logger.error(f"❌ 更新 project cache 失败: {e}")

    def organize_videos(self, video_files: List[str]) -> Dict[str, List[str]]:
        """整理视频文件：按 video_id 分组到文件夹中"""
        try:
            logger.info(f"\n📁 开始整理视频文件...")

            organized = {}

            for video_path in video_files:
                if not os.path.exists(video_path):
                    logger.warning(f"⚠️ 视频文件不存在: {video_path}")
                    continue

                # 获取文件名（不含扩展名）
                base_name = os.path.basename(video_path)
                name_without_ext = os.path.splitext(base_name)[0]

                # 解析文件名：BV1684y1r7Qw_story_1_Spongebob'_part1
                parts = name_without_ext.split('_')
                if len(parts) < 2:
                    logger.warning(f"⚠️ 文件名格式不符合规则，跳过: {base_name}")
                    continue

                # 提取 video_id（第一个下划线之前的部分）
                video_id = parts[0]

                # 剩余部分作为新文件名
                new_name = '_'.join(parts[1:]) + os.path.splitext(base_name)[1]

                # 创建目标文件夹
                video_dir = os.path.join(os.path.dirname(video_path), video_id)
                os.makedirs(video_dir, exist_ok=True)

                # 目标文件路径
                target_path = os.path.join(video_dir, new_name)

                # 移动文件
                try:
                    shutil.move(video_path, target_path)
                    logger.info(f"  ✓ {base_name} → {video_id}/{new_name}")

                    # 记录到字典
                    if video_id not in organized:
                        organized[video_id] = []
                    organized[video_id].append(target_path)

                except Exception as e:
                    logger.error(f"  ❌ 移动文件失败 {base_name}: {e}")

            # 输出整理结果
            logger.info(f"\n✅ 视频整理完成！")
            for video_id, files in organized.items():
                logger.info(f"  📁 {video_id}/: {len(files)} 个文件")

            return organized

        except Exception as e:
            logger.error(f"❌ 整理视频文件失败: {e}")
            return {}

    def process(self, cache_file: str) -> List[str]:
        """处理流程：加载缓存 -> 计算切割点 -> 切割视频"""
        logger.info(f"🎬 开始处理视频切割")

        # 1. 加载项目缓存
        project_data = self.load_project_cache(cache_file)
        if not project_data:
            return []

        all_output_files = []

        # 2. 遍历所有 segment 和 story
        for segment in project_data.get('segments', []):
            for story_idx, story in enumerate(segment.get('stories', [])):
                # 检查是否有导出的视频路径
                video_path = story.get('exported_video_path')
                if not video_path or not os.path.exists(video_path):
                    logger.warning(f"⚠️ 跳过故事 '{story.get('story_title')}': 视频路径不存在")
                    continue

                logger.info(f"\n📖 处理故事: {story.get('story_title')}")
                logger.info(f"   视频路径: {video_path}")

                # 3. 获取视频时长
                duration = self.get_video_duration(video_path)
                if not duration:
                    continue

                # 4. 判断是否需要切割
                if duration < TARGET_MIN_DURATION:
                    logger.info(f"⚠️ 视频时长 {duration:.2f}s < {TARGET_MIN_DURATION}s，跳过")
                    continue
                elif duration <= TARGET_MAX_DURATION:
                    logger.info(f"✅ 视频时长 {duration:.2f}s 在目标范围内，无需切割")
                    all_output_files.append(video_path)
                    continue

                # 5. 计算切割点
                logger.info(f"📊 分析 dialogue 数据...")
                split_points = self.calculate_split_points(story)

                if not split_points:
                    logger.warning(f"⚠️ 没有找到符合要求的切割点")
                    continue

                logger.info(f"✂️ 找到 {len(split_points)} 个切割点")

                # 6. 切割视频
                split_segments = self.split_video(video_path, split_points)

                if split_segments:
                    logger.info(f"✅ 视频切割完成，共 {len(split_segments)} 个片段")

                    # 7. 更新 project cache
                    self.update_project_cache(cache_file, story_idx, split_segments)

                    # 收集输出文件
                    for seg in split_segments:
                        all_output_files.append(seg['video_path'])

        if all_output_files:
            logger.info(f"\n✅ 所有视频处理完成，共 {len(all_output_files)} 个视频文件")

            # 整理视频文件到文件夹
            organized = self.organize_videos(all_output_files)

            # 返回整理后的文件路径
            organized_files = []
            for files in organized.values():
                organized_files.extend(files)
            return organized_files if organized_files else all_output_files
        else:
            logger.warning("\n⚠️ 没有生成任何视频文件")
            return all_output_files


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python spliter_export_video.py <project_cache_file>")
        print("示例: python spliter_export_video.py ./output/project_cache/BV123_xxx.json")
        sys.exit(1)

    cache_file = sys.argv[1]

    splitter = VideoSplitter()
    result_files = splitter.process(cache_file)

    if result_files:
        print(f"\n✅ 处理完成！共 {len(result_files)} 个视频文件:")
        for f in result_files:
            print(f"  - {f}")
    else:
        print("\n❌ 处理失败")
        sys.exit(1)