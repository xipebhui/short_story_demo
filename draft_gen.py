#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版复合草稿生成器
直接替换模板中的必要部分，最小化修改
"""

# ================== 配置开关 ==================
# 字幕调试模式 - 开启时只生成前10个字幕，用于测试
SUBTITLE_DEBUG_MODE = False

# 中文字幕开关 - 默认关闭中文字幕
ENABLE_CHINESE_SUBTITLES = False

# 英文字幕开关 - 默认开启英文字幕
ENABLE_ENGLISH_SUBTITLES = True

# 调试模式下的字幕数量限制
DEBUG_SUBTITLE_LIMIT = 2

# ================== 速度控制配置 ==================
# 目标视频时长（秒）- 控制最终视频在1分钟内
TARGET_DURATION_SECONDS = 59.0

# 最大播放速度倍数 - 限制最大速度为2.5倍
MAX_SPEED_FACTOR = 2.0
# ================================================

import json
import os
import sys
import uuid
import shutil
import copy
from pathlib import Path
from pydub import AudioSegment
from typing import List, Dict, Optional

# 字幕模板加载函数
def load_subtitle_templates_from_draft(template_file):
    """从草稿模板文件中加载字幕模板"""
    try:
        with open(template_file, 'r', encoding='utf-8') as f:
            template_data = json.load(f)

        # 从嵌套草稿中获取字幕模板
        nested_draft = template_data['materials']['drafts'][0]['draft']
        texts_templates = nested_draft['materials'].get('texts', [])

        # 获取字幕轨道模板
        text_tracks = [t for t in nested_draft['tracks'] if t.get('type') == 'text']
        track_template = text_tracks[0] if text_tracks else None

        return texts_templates, track_template
    except Exception as e:
        print(f"❌ 从草稿模板加载字幕失败: {e}")
        return [], None

# 默认配置常量
DEFAULT_TEMPLATE_FILE = "./templates/draft_content_fuhe.json"
DEFAULT_TEMPLATE_SETTINGS= "./templates/draft_settings"
DEFAULT_TEMPLATE_INFO_FILE = "./templates/draft_meta_info.json"
DEFAULT_OUTPUT_DIR = "./output/draft_folder"
DEFAULT_SCALE_X = 1.0
DEFAULT_SCALE_Y = 1.0
DEFAULT_GAP = 0
DEFAULT_BLUR_STRENGTH = 0.375
DEFAULT_BACKGROUND_AUDIO_PATH = "./templates/jazz.wav"

# 故事对象类（独立于 short_story_generator.py）
class StoryDialogue:
    def __init__(self, index: int, start: str, end: str, chinese: str, english: str):
        self.index = index
        self.start = start
        self.end = end
        self.chinese = chinese
        self.english = english
        self.audio_path: Optional[str] = None
        self.srt_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'start': self.start,
            'end': self.end,
            'chinese': self.chinese,
            'english': self.english,
            'audio_path': self.audio_path,
            'srt_path': self.srt_path
        }

class StoryContent:
    def __init__(self, story_title: str, start_time: str, end_time: str, dialogue: List[Dict]):
        self.story_title = story_title
        self.start_time = start_time
        self.end_time = end_time
        self.dialogue_list: List[StoryDialogue] = []

        # 将字典数据转换为 StoryDialogue 对象
        for d in dialogue:
            dialogue_obj = StoryDialogue(
                index=d['index'],
                start=d['start'],
                end=d['end'],
                chinese=d['chinese'],
                english=d['english']
            )
            # 如果有语音路径信息，也要赋值
            if 'audio_path' in d:
                dialogue_obj.audio_path = d['audio_path']
            if 'srt_path' in d:
                dialogue_obj.srt_path = d['srt_path']
            self.dialogue_list.append(dialogue_obj)

    def to_dict(self) -> Dict:
        return {
            'story_title': self.story_title,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'dialogue': [d.to_dict() for d in self.dialogue_list]
        }


def time_to_microseconds(time_str):
    """将时间字符串转换为微秒"""
    if isinstance(time_str, (int, float)):
        return int(time_str * 1000000)

    # 处理SRT格式的时间字符串 (HH:MM:SS,mmm)
    if ',' in time_str:
        time_part, ms_part = time_str.split(',')
        parts = time_part.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = parts
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(ms_part) / 1000.0
        else:
            total_seconds = float(time_part) + int(ms_part) / 1000.0
    else:
        parts = time_str.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = parts
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            total_seconds = float(time_str)

    return int(total_seconds * 1000000)


def get_audio_duration(audio_path):
    """获取音频文件时长（秒）"""
    try:
        
        audio = AudioSegment.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"无法获取音频时长 {audio_path}: {e}")
        return 1.0  # 返回默认时长避免除零错误




def calculate_speed_factor(original_duration_seconds):
    """
    根据原始时长计算播放速度，确保目标时长在1分钟内，最大速度2.5倍

    Args:
        original_duration_seconds: 原始视频时长（秒）

    Returns:
        float: 计算出的播放速度倍数
    """
    if original_duration_seconds <= 0:
        return 1.0

    # 按目标时间计算需要的速度
    required_speed = original_duration_seconds / TARGET_DURATION_SECONDS

    # 限制在最大速度以内
    final_speed = min(required_speed, MAX_SPEED_FACTOR)

    # 确保速度至少为1.0（不能慢于原速）
    final_speed = max(final_speed, 1.0)

    print(f"原始时长: {original_duration_seconds:.1f}s")
    print(f"目标时长: {TARGET_DURATION_SECONDS:.1f}s")
    print(f"按时间计算需要速度: {required_speed:.2f}x")
    print(f"最终使用速度: {final_speed:.2f}x")
    print(f"实际输出时长: {original_duration_seconds / final_speed:.1f}s")

    return final_speed


def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4()).upper()


class VideoMaterial:
    """视频材料对象"""
    def __init__(self, material_id, material_name, path, duration, crop):
        self.id = material_id
        self.material_name = material_name
        self.path = path
        self.duration = duration
        self.crop = crop

class AudioMaterial:
    """音频材料对象"""
    def __init__(self, material_id, name, path, duration, audio_type="sound"):
        self.id = material_id
        self.name = name
        self.path = path
        self.duration = duration
        self.type = audio_type

class VideoSegment:
    """视频片段对象"""
    def __init__(self, segment_id, material_id, source_timerange, target_timerange, speed, scale, volume=0.0):
        self.id = segment_id
        self.material_id = material_id
        self.source_timerange = source_timerange
        self.target_timerange = target_timerange
        self.speed = speed
        self.clip = {"scale": scale}
        self.volume = volume

class AudioSegment:
    """音频片段对象"""
    def __init__(self, segment_id, material_id, source_timerange, target_timerange, speed=1.0, volume=1.0):
        self.id = segment_id
        self.material_id = material_id
        self.source_timerange = source_timerange
        self.target_timerange = target_timerange
        self.speed = speed
        self.volume = volume


class DraftGenerator:
    """草稿生成器类"""

    def __init__(self,
                 template_file: str = DEFAULT_TEMPLATE_FILE,
                 output_dir: str = DEFAULT_OUTPUT_DIR,
                 scale_x: float = DEFAULT_SCALE_X,
                 scale_y: float = DEFAULT_SCALE_Y,
                 gap: float = DEFAULT_GAP,
                 blur_strength: float = DEFAULT_BLUR_STRENGTH,
                 background_audio_path: Optional[str] = DEFAULT_BACKGROUND_AUDIO_PATH):
        self.template_file = template_file
        self.output_dir = output_dir
        self.scale_x = scale_x
        self.scale_y = scale_y
        self.gap = gap
        self.blur_strength = blur_strength
        self.background_audio_path = background_audio_path


    def create_nested_draft_simple(self, story: StoryContent, video_path: str):
        """创建简化的嵌套草稿，直接与 StoryContent 对象交互"""
        # 计算总时长
        current_time = 0.0
        segments_info = []

        for dialogue in story.dialogue_list:
            # 如果没有语音文件，创建虚拟音频信息用于字幕处理
            if not dialogue.audio_path:
                # 计算对话时长作为虚拟音频时长
                source_start_seconds = time_to_microseconds(dialogue.start) / 1000000.0
                source_end_seconds = time_to_microseconds(dialogue.end) / 1000000.0
                audio_duration = source_end_seconds - source_start_seconds

                segments_info.append({
                    'target_start': current_time,
                    'audio_duration': audio_duration,
                    'source_start': source_start_seconds,
                    'source_duration': audio_duration,
                    'audio_path': None,  # 标记为虚拟音频
                    'dialogue_obj': dialogue
                })

                current_time += audio_duration
                continue

            current_time += self.gap
            audio_duration = get_audio_duration(dialogue.audio_path)

            # 计算源视频时间
            source_start_seconds = time_to_microseconds(dialogue.start) / 1000000.0
            source_end_seconds = time_to_microseconds(dialogue.end) / 1000000.0
            source_duration = source_end_seconds - source_start_seconds

            segments_info.append({
                'target_start': current_time,
                'audio_duration': audio_duration,
                'source_start': source_start_seconds,
                'source_duration': source_duration,
                'audio_path': dialogue.audio_path,
                'dialogue_obj': dialogue  # 保存对象引用
            })

            current_time += audio_duration

        total_duration = int(current_time * 1000000)

        # 生成材料和片段对象
        video_materials = []
        audio_materials = []
        video_segments = []
        audio_segments = []

        crop_config = {
            "lower_left_x": 0.13364055299539157,
            "lower_left_y": 0.8648233486943162,
            "lower_right_x": 0.8179723502304148,
            "lower_right_y": 0.8648233486943162,
            "upper_left_x": 0.13364055299539157,
            "upper_left_y": 0.0,
            "upper_right_x": 0.8179723502304148,
            "upper_right_y": 0.0
        }

        for i, info in enumerate(segments_info):
            # 跳过虚拟音频（只用于字幕处理）
            if info['audio_path'] is None:
                continue

            # 材料ID
            video_id = generate_uuid()
            audio_id = generate_uuid()

            # 使用原始视频文件名
            video_file_name = os.path.basename(video_path)

            # 创建视频材料对象
            video_material = VideoMaterial(
                material_id=video_id,
                material_name=video_file_name,
                path=f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{video_file_name}",
                duration=44733333,  # 会被实际时长覆盖
                crop=crop_config
            )
            video_materials.append(video_material)

            # 创建音频材料对象
            audio_material = AudioMaterial(
                material_id=audio_id,
                name=os.path.basename(info['audio_path']),
                path=f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{os.path.basename(info['audio_path'])}",
                duration=int(info['audio_duration'] * 1000000),
                audio_type="sound"
            )
            audio_materials.append(audio_material)

            # 创建视频片段对象
            video_speed = info['source_duration'] / max(info['audio_duration'], 0.1)  # 避免除零错误

            # 使用原始源时间，不需要调整
            adjusted_source_start = info['source_start']

            video_segment = VideoSegment(
                segment_id=generate_uuid(),
                material_id=video_id,
                source_timerange={"duration": int(info['source_duration'] * 1000000),
                                  "start": int(adjusted_source_start * 1000000)},
                target_timerange={"duration": int(info['audio_duration'] * 1000000),
                                  "start": int(info['target_start'] * 1000000)},
                speed=video_speed,
                scale={"x": self.scale_x, "y": self.scale_y},
                volume=0.0
            )
            video_segments.append(video_segment)

            # 创建音频片段对象
            audio_segment = AudioSegment(
                segment_id=generate_uuid(),
                material_id=audio_id,
                source_timerange={"duration": int(info['audio_duration'] * 1000000), "start": 0},
                target_timerange={"duration": int(info['audio_duration'] * 1000000),
                                  "start": int(info['target_start'] * 1000000)},
                speed=1.0,
                volume=1.0
            )
            audio_segments.append(audio_segment)

        # 生成字幕材料和片段
        subtitle_materials, subtitle_segments, subtitle_tracks = self._generate_subtitles(segments_info)

        return {
            'duration': total_duration,
            'video_materials': video_materials,
            'audio_materials': audio_materials,
            'video_segments': video_segments,
            'audio_segments': audio_segments,
            'subtitle_materials': subtitle_materials,
            'subtitle_segments': subtitle_segments,
            'subtitle_tracks': subtitle_tracks
        }

    def _generate_subtitles(self, segments_info):
        """生成字幕材料和片段 - 基于模板复制替换"""
        subtitle_materials = []
        subtitle_tracks = []

        # 从草稿模板文件中加载字幕模板
        material_templates, track_template = load_subtitle_templates_from_draft(self.template_file)
        if not material_templates or not track_template:
            print("❌ 无字幕模板，跳过字幕生成")
            return [], [], []

        print(f"✓ 加载字幕模板: {len(material_templates)} 个材料模板")

        # 确定处理的字幕数量
        process_count = len(segments_info)
        if SUBTITLE_DEBUG_MODE:
            process_count = min(DEBUG_SUBTITLE_LIMIT, len(segments_info))
            print(f"🔧 字幕调试模式：只处理前 {process_count} 个字幕")

        # 创建字幕轨道（基于模板）
        subtitle_track = copy.deepcopy(track_template)
        subtitle_track['id'] = generate_uuid()
        subtitle_track['segments'] = []

        # 基于音频片段的target_start来定位字幕时间（不再使用累积时间）

        for i, info in enumerate(segments_info[:process_count]):
            dialogue_obj = info['dialogue_obj']

            # 只处理有SRT文件的对话，加载SRT文件获取逐字字幕
            if not dialogue_obj.srt_path or not os.path.exists(dialogue_obj.srt_path):
                print(f"⚠️ 跳过对话 {dialogue_obj.index}：没有SRT文件")
                continue

            srt_subtitles = self._load_srt_file(dialogue_obj.srt_path)
            if not srt_subtitles:
                print(f"⚠️ 跳过对话 {dialogue_obj.index}：SRT文件为空")
                continue

            # 获取当前音频片段的目标起始时间（微秒）
            audio_target_start = int(info['target_start'] * 1000000)

            for j, subtitle_entry in enumerate(srt_subtitles):
                # 使用第一个模板（只有英文字幕逻辑）
                template_idx = 0

                # 创建字幕材料（基于模板复制）
                subtitle_material = copy.deepcopy(material_templates[template_idx])
                subtitle_material['id'] = generate_uuid()

                # 解析并修改content中的text字段
                try:
                    content_obj = json.loads(subtitle_material['content'])

                    # 去除标点符号并清理文本
                    clean_text = self._clean_subtitle_text(subtitle_entry['text'])
                    if not clean_text:  # 如果清理后为空，跳过
                        continue

                    # 设置文本内容
                    content_obj['text'] = clean_text

                    # 根据文本长度计算range
                    text_length = len(clean_text)
                    if 'styles' in content_obj and content_obj['styles']:
                        for style in content_obj['styles']:
                            if 'range' in style:
                                style['range'] = [0, text_length]

                    subtitle_material['content'] = json.dumps(content_obj, ensure_ascii=False)
                except Exception as e:
                    print(f"⚠️ 字幕内容解析失败: {e}")
                    continue

                subtitle_materials.append(subtitle_material)

                # 创建字幕片段（基于模板复制）
                if track_template['segments']:
                    segment_template = track_template['segments'][0]
                    subtitle_segment = copy.deepcopy(segment_template)
                    subtitle_segment['id'] = generate_uuid()
                    subtitle_segment['material_id'] = subtitle_material['id']

                    # 计算时间偏移（微秒）
                    srt_start_ms = self._srt_time_to_microseconds(subtitle_entry['start'])
                    srt_duration_ms = self._srt_time_to_microseconds(subtitle_entry['end']) - srt_start_ms

                    # 基于音频片段的目标时间进行定位
                    adjusted_start = audio_target_start + srt_start_ms

                    # 更新片段时间
                    subtitle_segment['target_timerange'] = {
                        'start': adjusted_start,
                        'duration': srt_duration_ms
                    }
                    subtitle_segment['source_timerange'] = {
                        'start': 0,
                        'duration': srt_duration_ms
                    }

                    subtitle_track['segments'].append(subtitle_segment)

            # 字幕时间已基于音频片段的target_start进行定位，无需累积时间

        if subtitle_track['segments']:
            subtitle_tracks.append(subtitle_track)

        print(f"✓ 生成字幕: {len(subtitle_materials)} 个材料, {len(subtitle_tracks)} 个轨道")
        return subtitle_materials, [], subtitle_tracks

    def _load_srt_file(self, srt_path):
        """加载SRT文件并解析"""
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()

            entries = []
            for block in content.split('\n\n'):
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # 解析时间
                    time_line = lines[1]
                    if ' --> ' in time_line:
                        start_time, end_time = time_line.split(' --> ')
                        # 文本内容
                        text = '\n'.join(lines[2:])
                        entries.append({
                            'start': start_time.strip(),
                            'end': end_time.strip(),
                            'text': text.strip()
                        })
            return entries
        except Exception as e:
            print(f"❌ 加载SRT文件失败 {srt_path}: {e}")
            return []

    def _srt_time_to_microseconds(self, srt_time):
        """将SRT时间格式转换为微秒"""
        try:
            time_part, milliseconds = srt_time.split(',')
            hours, minutes, seconds = map(int, time_part.split(':'))
            total_microseconds = (hours * 3600 + minutes * 60 + seconds) * 1000000 + int(milliseconds) * 1000
            return total_microseconds
        except Exception as e:
            print(f"❌ 时间转换错误: {e}")
            return 0

    def _clean_subtitle_text(self, text):
        """清理字幕文本，去除标点符号和多余空格"""
        import re

        # 去除常见标点符号
        punctuation_pattern = r'[.,!?;:\'"\-\(\)\[\]{}]'
        clean_text = re.sub(punctuation_pattern, '', text)

        # 去除多余空格并转换为单个空格
        clean_text = re.sub(r'\s+', ' ', clean_text)

        # 去除首尾空格
        clean_text = clean_text.strip()

        return clean_text

    def _format_title_text(self, title):
        """格式化标题文本，按空格切分，超过20字符换行"""
        if not title:
            return ""
        non_tag_title = title.split('#')[0].strip()
        words = non_tag_title.split(' ')
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            # 如果加上这个词会超过20字符，开始新行
            word_length = len(word)
            if current_length > 0:  # 不是第一个词，需要加空格
                test_length = current_length + 1 + word_length
            else:
                test_length = word_length

            if test_length > 20 and current_line:
                # 当前行已有内容且会超长，开始新行
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                # 可以加到当前行
                current_line.append(word)
                current_length = test_length

        # 加上最后一行
        if current_line:
            lines.append(' '.join(current_line))

        return '\n'.join(lines)

    def _add_subtitle_tracks(self, nested_draft, nested_data):
        """添加字幕轨道到嵌套草稿 - 清理旧字幕，在原轨道上添加新字幕"""
        if 'subtitle_materials' not in nested_data or 'subtitle_tracks' not in nested_data:
            return

        # 1. 清理旧的字幕材料
        if 'texts' not in nested_draft['materials']:
            nested_draft['materials']['texts'] = []
        else:
            print(f"🧹 清理旧字幕材料: {len(nested_draft['materials']['texts'])} 个")
            nested_draft['materials']['texts'].clear()

        # 2. 添加新的字幕材料
        for subtitle_material in nested_data['subtitle_materials']:
            nested_draft['materials']['texts'].append(subtitle_material)

        # 3. 清理并更新字幕轨道
        # 找到现有的字幕轨道（type为text的轨道）
        text_tracks = [track for track in nested_draft['tracks'] if track.get('type') == 'text']

        if text_tracks:
            # 清理现有字幕轨道的segments
            for track in text_tracks:
                old_segments_count = len(track.get('segments', []))
                print(f"🧹 清理轨道 {track.get('id', '')[:8]}... 的旧片段: {old_segments_count} 个")
                track['segments'] = []

            # 将新字幕片段添加到第一个字幕轨道
            if nested_data['subtitle_tracks'] and nested_data['subtitle_tracks'][0]['segments']:
                target_track = text_tracks[0]
                new_segments = nested_data['subtitle_tracks'][0]['segments']
                target_track['segments'].extend(new_segments)
                print(f"✓ 在原轨道上添加了 {len(new_segments)} 个新字幕片段")
        else:
            # 如果没有现有字幕轨道，直接添加新轨道
            for subtitle_track in nested_data['subtitle_tracks']:
                nested_draft['tracks'].append(subtitle_track)
            print(f"✓ 添加了 {len(nested_data['subtitle_tracks'])} 个新字幕轨道")

        print(f"✓ 字幕更新完成: {len(nested_data['subtitle_materials'])} 个材料")

    def _update_main_title_text(self, draft, story_title, total_duration):
        """更新主轴的标题文本内容和时长"""
        try:
            # 格式化标题文本
            formatted_title = self._format_title_text(story_title)

            # 更新主轴文本材料
            main_texts = draft['materials'].get('texts', [])
            if main_texts:
                text_material = main_texts[0]
                content = text_material.get('content', '')
                if content:
                    content_obj = json.loads(content)
                    content_obj['text'] = formatted_title

                    # 根据文本长度计算range
                    text_length = len(formatted_title)
                    if 'styles' in content_obj and content_obj['styles']:
                        for style in content_obj['styles']:
                            if 'range' in style:
                                style['range'] = [0, text_length]

                    text_material['content'] = json.dumps(content_obj, ensure_ascii=False)
                    print(f"✓ 更新主轴标题文本: \"{formatted_title.replace(chr(10), ' / ')}\"")

            # 更新主轴文本轨道的时长
            main_tracks = [t for t in draft.get('tracks', []) if t.get('type') == 'text']
            if main_tracks:
                text_track = main_tracks[0]
                segments = text_track.get('segments', [])
                if segments:
                    segment = segments[0]
                    # 确保 timerange 对象存在
                    if 'target_timerange' in segment and segment['target_timerange'] is not None:
                        segment['target_timerange']['duration'] = total_duration
                    if 'source_timerange' in segment and segment['source_timerange'] is not None:
                        segment['source_timerange']['duration'] = total_duration
                    print(f"✓ 更新主轴标题时长: {total_duration / 1000000:.3f}秒")

        except Exception as e:
            print(f"⚠️ 更新主轴标题失败: {e}")

    def generate_from_file(self, enhanced_srt_file: str, video_path: str) -> str:
        """从文件生成草稿，先转换为 StoryContent 对象"""
        print(f"开始从文件生成草稿: {enhanced_srt_file}")

        # 读取文件数据
        with open(enhanced_srt_file, 'r', encoding='utf-8') as f:
            srt_data = json.load(f)

        # 转换为 StoryContent 对象
        if isinstance(srt_data, list) and len(srt_data) > 0:
            # 处理 AI 分析后的格式（包含 story_title 等字段）
            story_data = srt_data[0]
            story = StoryContent(
                story_title=story_data.get('story_title', 'Untitled Story'),
                start_time=story_data.get('start_time', '00:00:00,000'),
                end_time=story_data.get('end_time', '00:00:00,000'),
                dialogue=story_data.get('dialogue', [])
            )
        else:
            raise ValueError(f"不支持的文件格式: {enhanced_srt_file}")

        print(f"成功转换为故事对象: {story.story_title}")
        return self.generate_from_story(story, video_path, 0)

    def generate_from_story(self, story: StoryContent, video_path: str, story_idx: int = 0, video_id: str = None) -> str:
        """从 StoryContent 对象生成草稿，直接使用对象"""
        print(f"开始为故事生成草稿: {story.story_title}")

        # 更新输出目录，为每个故事创建独立的目录
        story_output_dir = os.path.join(self.output_dir, f"{video_id}_story_{story_idx + 1}_{story.story_title.replace(' ', '_')[:20]}")

        return self._generate_draft_internal(story, video_path, story_output_dir)

    def _generate_draft_internal(self, story: StoryContent, video_path: str, custom_output_dir: str = None) -> str:
        """内部草稿生成方法，直接使用 StoryContent 对象"""
        output_dir = custom_output_dir or self.output_dir

        print(f"开始生成简化版复合草稿...")
        print(f"模板文件: {self.template_file}")
        if self.background_audio_path:
            print(f"背景音频: {self.background_audio_path}")

        # 读取模板文件
        with open(self.template_file, 'r', encoding='utf-8') as f:
            draft = json.load(f)

        # 统计有语音文件的对话数量
        audio_dialogues_count = sum(1 for d in story.dialogue_list if d.audio_path)
        print(f"处理故事: {story.story_title}")
        print(f"总对话数: {len(story.dialogue_list)}, 有语音的对话: {audio_dialogues_count}")

        # 创建嵌套草稿数据
        nested_data = self.create_nested_draft_simple(story, video_path)

        # 计算时间和动态速度
        nested_duration = nested_data['duration']
        original_duration_seconds = nested_duration / 1000000.0  # 转换为秒

        # 动态计算播放速度
        speed_factor = calculate_speed_factor(original_duration_seconds)

        main_duration = int(nested_duration / speed_factor)

        # 1. 更新主草稿基本信息
        draft['id'] = generate_uuid()
        draft['duration'] = main_duration

        # 1.1. 更新主轴标题文本
        self._update_main_title_text(draft, story.story_title, main_duration)

        # 2. 替换嵌套草稿内容
        nested_draft_item = draft['materials']['drafts'][0]
        nested_draft = nested_draft_item['draft']

        # 更新嵌套草稿的基本信息
        nested_draft['id'] = generate_uuid()
        nested_draft['duration'] = nested_duration

        # 替换嵌套草稿的材料 - 使用模板复制
        video_template = nested_draft['materials']['videos'][0] if nested_draft['materials']['videos'] else None
        audio_template = nested_draft['materials']['audios'][0] if nested_draft['materials']['audios'] else None

        # 清空原有材料
        nested_draft['materials']['videos'] = []
        nested_draft['materials']['audios'] = []

        # 复制并修改视频材料
        for video_mat in nested_data['video_materials']:
            new_video_material = copy.deepcopy(video_template) if video_template else {}
            new_video_material.update({
                "id": video_mat.id,
                "material_name": video_mat.material_name,
                "path": video_mat.path,
                "duration": video_mat.duration,
                "crop": video_mat.crop,
                "local_material_id": str(uuid.uuid4())
            })
            nested_draft['materials']['videos'].append(new_video_material)

        # 复制并修改音频材料
        for audio_mat in nested_data['audio_materials']:
            new_audio_material = copy.deepcopy(audio_template) if audio_template else {}
            new_audio_material.update({
                "id": audio_mat.id,
                "name": audio_mat.name,
                "path": audio_mat.path,
                "duration": audio_mat.duration,
                "type": audio_mat.type
            })
            nested_draft['materials']['audios'].append(new_audio_material)

        # 替换嵌套草稿的轨道片段 - 使用模板复制
        video_track = nested_draft['tracks'][0]
        audio_track = nested_draft['tracks'][1]

        # 获取模板片段
        video_seg_template = video_track['segments'][0] if video_track['segments'] else None
        audio_seg_template = audio_track['segments'][0] if audio_track['segments'] else None

        # 清空现有片段
        video_track['segments'] = []
        audio_track['segments'] = []

        # 复制并修改视频片段
        for video_seg in nested_data['video_segments']:
            new_video_seg = copy.deepcopy(video_seg_template) if video_seg_template else {}
            new_video_seg.update({
                "id": video_seg.id,
                "material_id": video_seg.material_id,
                "source_timerange": video_seg.source_timerange,
                "target_timerange": video_seg.target_timerange,
                "speed": video_seg.speed,
                "volume": video_seg.volume
            })
            # 更新clip中的scale
            if 'clip' in new_video_seg:
                new_video_seg['clip']['scale'] = video_seg.clip['scale']
            video_track['segments'].append(new_video_seg)

        # 复制并修改音频片段
        for audio_seg in nested_data['audio_segments']:
            new_audio_seg = copy.deepcopy(audio_seg_template) if audio_seg_template else {}
            new_audio_seg.update({
                "id": audio_seg.id,
                "material_id": audio_seg.material_id,
                "source_timerange": audio_seg.source_timerange,
                "target_timerange": audio_seg.target_timerange,
                "speed": audio_seg.speed,
                "volume": audio_seg.volume
            })
            audio_track['segments'].append(new_audio_seg)

        # 处理字幕轨道
        self._add_subtitle_tracks(nested_draft, nested_data)

        # 3. 更新主草稿的复合视频材料时长
        composite_video = draft['materials']['videos'][0]
        composite_video['duration'] = nested_duration

        # 4. 更新主草稿的视频轨道时间
        main_video_segment = draft['tracks'][0]['segments'][0]
        main_video_segment['source_timerange']['duration'] = nested_duration
        main_video_segment['target_timerange']['duration'] = main_duration
        main_video_segment['speed'] = speed_factor

        # 5. 处理背景音频 - 使用深度拷贝
        if self.background_audio_path:
            # 创建背景音频对象
            bg_audio = AudioMaterial(
                material_id=generate_uuid(),
                name=os.path.basename(self.background_audio_path),
                path=f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{os.path.basename(self.background_audio_path)}",
                duration=int(get_audio_duration(self.background_audio_path) * 1000000),
                audio_type="sound"
            )

            # 获取模板音频材料并深度拷贝
            main_audio_template = draft['materials']['audios'][0] if draft['materials']['audios'] else None
            if main_audio_template:
                new_bg_audio_material = copy.deepcopy(main_audio_template)
                new_bg_audio_material.update({
                    "id": bg_audio.id,
                    "name": bg_audio.name,
                    "path": bg_audio.path,
                    "duration": bg_audio.duration,
                    "type": bg_audio.type
                })
                draft['materials']['audios'].append(new_bg_audio_material)

            # 获取模板音频片段并深度拷贝
            main_audio_seg_template = draft['tracks'][2]['segments'][0] if draft['tracks'][2]['segments'] else None
            if main_audio_seg_template:
                new_bg_audio_segment = copy.deepcopy(main_audio_seg_template)
                new_bg_audio_segment.update({
                    "id": generate_uuid(),
                    "material_id": bg_audio.id,
                    "source_timerange": {"duration": main_duration, "start": 0},
                    "target_timerange": {"duration": main_duration, "start": 0},
                    "speed": 1.0
                })
                draft['tracks'][2]['segments'] = [new_bg_audio_segment]
            else:
                # 如果没有模板，清空音频轨道
                draft['tracks'][2]['segments'] = []
        else:
            # 清空音频轨道
            draft['tracks'][2]['segments'] = []

        # 6. 复制文件和保存
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        materials_dir = output_path / "materials"
        materials_dir.mkdir(exist_ok=True)

        # 直接复制原始视频文件
        video_src = Path(video_path)
        video_dest = materials_dir / os.path.basename(video_path)

        if not video_dest.exists():
            shutil.copy2(video_src, video_dest)
            print(f"复制视频文件: {video_dest}")
        else:
            print(f"视频文件已存在: {video_dest}")

        # 复制音频文件
        for dialogue in story.dialogue_list:
            if dialogue.audio_path:
                audio_src = Path(dialogue.audio_path)
                audio_dest = materials_dir / os.path.basename(dialogue.audio_path)
                if not audio_dest.exists():
                    shutil.copy2(audio_src, audio_dest)
                    print(f"复制音频文件: {audio_dest}")

        # 复制背景音频
        if self.background_audio_path:
            bg_audio_src = Path(self.background_audio_path)
            bg_audio_dest = materials_dir / os.path.basename(self.background_audio_path)
            if not bg_audio_dest.exists():
                shutil.copy2(bg_audio_src, bg_audio_dest)
                print(f"复制背景音频文件: {bg_audio_dest}")

        # 复制模板设置文件
        settings_src = Path(DEFAULT_TEMPLATE_SETTINGS)
        if settings_src.exists():
            settings_dest = output_path / "draft_settings"
            if not settings_dest.exists():
                shutil.copy2(settings_src, settings_dest)
                print(f"复制模板设置文件: {settings_dest}")

        # 复制模板信息文件
        info_src = Path(DEFAULT_TEMPLATE_INFO_FILE)
        if info_src.exists():
            info_dest = output_path / "draft_meta_info.json"
            if not info_dest.exists():
                shutil.copy2(info_src, info_dest)
                print(f"复制模板信息文件: {info_dest}")

        # 保存草稿文件
        draft_file = output_path / "draft_content.json"
        with open(draft_file, 'w', encoding='utf-8') as f:
            json.dump(draft, f, ensure_ascii=False, separators=(',', ':'))

        print(f"✓ 简化版复合草稿生成完成: {draft_file}")
        return str(draft_file)


# 为了向后兼容，保留原有的函数接口
def generate_simple_composite_draft(enhanced_srt_file, video_path, template_file, output_dir,
                                   scale_x=1.0, scale_y=1.0, gap=0, blur_strength=0.375,
                                   speed_factor=None, background_audio_path=None):
    """向后兼容的函数接口，speed_factor 参数已废弃，改为动态计算"""
    if speed_factor is not None:
        print(f"⚠️  警告: speed_factor 参数已废弃，现在根据视频时长动态计算速度")

    generator = DraftGenerator(
        template_file=template_file,
        output_dir=output_dir,
        scale_x=scale_x,
        scale_y=scale_y,
        gap=gap,
        blur_strength=blur_strength,
        background_audio_path=background_audio_path
    )
    return generator.generate_from_file(enhanced_srt_file, video_path)


def main():
    if len(sys.argv) < 3:
        print(
            "用法: python draft_gen.py <enhanced_srt_file> <video_path>")
        sys.exit(1)

    enhanced_srt_file = sys.argv[1]
    video_path = sys.argv[2]

    try:
        # 使用新的面向对象接口
        generator = DraftGenerator()
        result = generator.generate_from_file(enhanced_srt_file, video_path)
        print(f"简化版复合草稿生成成功: {result}")
    except Exception as e:
        print(f"生成简化版复合草稿失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()