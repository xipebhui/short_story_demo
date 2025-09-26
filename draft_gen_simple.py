#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版复合草稿生成器
直接替换模板中的必要部分，最小化修改
"""

import json
import os
import sys
import uuid
import shutil
import copy
from pathlib import Path
from pydub import AudioSegment


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
        from pydub import AudioSegment as AS
        audio = AS.from_file(audio_path)
        return len(audio) / 1000.0
    except Exception as e:
        print(f"无法获取音频时长 {audio_path}: {e}")
        return 1.0  # 返回默认时长避免除零错误


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


def create_nested_draft_simple(dialogues, video_path, scale_x, scale_y, gap, blur_strength):
    """创建简化的嵌套草稿，只包含必要的数据"""
    
    # 计算总时长
    current_time = 0.0
    segments_info = []
    
    for dialogue in dialogues:
        current_time += gap
        audio_duration = get_audio_duration(dialogue['audio_file'])
        
        # 计算源视频时间
        source_start_seconds = time_to_microseconds(dialogue['start_time']) / 1000000.0
        source_end_seconds = time_to_microseconds(dialogue['end_time']) / 1000000.0
        source_duration = source_end_seconds - source_start_seconds
        
        segments_info.append({
            'target_start': current_time,
            'audio_duration': audio_duration,
            'source_start': source_start_seconds,
            'source_duration': source_duration,
            'audio_path': dialogue['audio_file']
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
        # 材料ID
        video_id = generate_uuid()
        audio_id = generate_uuid()
        
        # 创建视频材料对象
        video_material = VideoMaterial(
            material_id=video_id,
            material_name=os.path.basename(video_path),
            path=f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{os.path.basename(video_path)}",
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
        video_segment = VideoSegment(
            segment_id=generate_uuid(),
            material_id=video_id,
            source_timerange={"duration": int(info['source_duration'] * 1000000), "start": int(info['source_start'] * 1000000)},
            target_timerange={"duration": int(info['audio_duration'] * 1000000), "start": int(info['target_start'] * 1000000)},
            speed=video_speed,
            scale={"x": scale_x, "y": scale_y},
            volume=0.0
        )
        video_segments.append(video_segment)
        
        # 创建音频片段对象
        audio_segment = AudioSegment(
            segment_id=generate_uuid(),
            material_id=audio_id,
            source_timerange={"duration": int(info['audio_duration'] * 1000000), "start": 0},
            target_timerange={"duration": int(info['audio_duration'] * 1000000), "start": int(info['target_start'] * 1000000)},
            speed=1.0,
            volume=1.0
        )
        audio_segments.append(audio_segment)
    
    return {
        'duration': total_duration,
        'video_materials': video_materials,
        'audio_materials': audio_materials,
        'video_segments': video_segments,
        'audio_segments': audio_segments
    }


def generate_simple_composite_draft(enhanced_srt_file, video_path, template_file, output_dir, 
                                   scale_x=1.0, scale_y=1.0, gap=0, blur_strength=0.375, 
                                   speed_factor=1.5, background_audio_path=None):
    """生成简化版复合草稿"""
    
    print(f"开始生成简化版复合草稿...")
    print(f"模板文件: {template_file}")
    print(f"速度倍数: {speed_factor}x")
    if background_audio_path:
        print(f"背景音频: {background_audio_path}")
    
    # 读取数据
    with open(enhanced_srt_file, 'r', encoding='utf-8') as f:
        srt_data = json.load(f)
    
    with open(template_file, 'r', encoding='utf-8') as f:
        draft = json.load(f)
    
    dialogues = srt_data[0]['dialogues']
    print(f"处理 {len(dialogues)} 个对话片段")
    
    # 创建嵌套草稿数据
    nested_data = create_nested_draft_simple(dialogues, video_path, scale_x, scale_y, gap, blur_strength)
    
    # 计算时间
    nested_duration = nested_data['duration']
    main_duration = int(nested_duration / speed_factor)
    
    # 1. 更新主草稿基本信息
    draft['id'] = generate_uuid()
    draft['duration'] = main_duration
    
    # print("="*30)
    # print(draft)
    # print("="*30)
    # 2. 替换嵌套草稿内容
    nested_draft_item = draft['materials']['drafts'][0]
    nested_draft = nested_draft_item['draft']
    
    # 更新嵌套草稿的基本信息
    nested_draft['id'] = generate_uuid()
    nested_draft['duration'] = nested_duration
    
    # 替换嵌套草稿的材料 - 使用模板复制
    # 获取模板材料
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
    
    # 3. 更新主草稿的复合视频材料时长
    composite_video = draft['materials']['videos'][0]
    composite_video['duration'] = nested_duration
    
    # 4. 更新主草稿的视频轨道时间
    main_video_segment = draft['tracks'][0]['segments'][0]
    main_video_segment['source_timerange']['duration'] = nested_duration
    main_video_segment['target_timerange']['duration'] = main_duration
    main_video_segment['speed'] = speed_factor
    
    # 5. 处理背景音频 - 使用深度拷贝
    if background_audio_path:
        # 创建背景音频对象
        bg_audio = AudioMaterial(
            material_id=generate_uuid(),
            name=os.path.basename(background_audio_path),
            path=f"##_draftpath_placeholder_0E685133-18CE-45ED-8CB8-2904A212EC80_##/materials/{os.path.basename(background_audio_path)}",
            duration=int(get_audio_duration(background_audio_path) * 1000000),
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
                "speed": 1.0,
                "volume": 1.5219134092330933
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
    
    # 复制视频文件
    video_dest = materials_dir / os.path.basename(video_path)
    if not video_dest.exists():
        shutil.copy2(video_path, video_dest)
        print(f"复制视频文件: {video_dest}")
    
    # 复制音频文件
    for dialogue in dialogues:
        if 'audio_file' in dialogue:
            audio_src = Path(dialogue['audio_file'])
            audio_dest = materials_dir / os.path.basename(dialogue['audio_file'])
            if not audio_dest.exists():
                shutil.copy2(audio_src, audio_dest)
                print(f"复制音频文件: {audio_dest}")
    
    # 复制背景音频
    if background_audio_path:
        bg_audio_src = Path(background_audio_path)
        bg_audio_dest = materials_dir / os.path.basename(background_audio_path)
        if not bg_audio_dest.exists():
            shutil.copy2(bg_audio_src, bg_audio_dest)
            print(f"复制背景音频文件: {bg_audio_dest}")
    
    # 保存草稿文件
    draft_file = output_path / "draft_content.json"
    with open(draft_file, 'w', encoding='utf-8') as f:
        json.dump(draft, f, ensure_ascii=False, separators=(',', ':'))
    
    print(f"✓ 简化版复合草稿生成完成: {draft_file}")
    return str(draft_file)


def main():
    if len(sys.argv) < 5:
        print("用法: python draft_gen_simple.py <enhanced_srt_file> <video_path> <template_file> <output_dir> [scale_x] [scale_y] [gap] [blur_strength] [speed_factor] [background_audio_path]")
        sys.exit(1)
    
    enhanced_srt_file = sys.argv[1]
    video_path = sys.argv[2]
    template_file = sys.argv[3]
    output_dir = sys.argv[4]
    scale_x = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0
    scale_y = float(sys.argv[6]) if len(sys.argv) > 6 else 1.0
    gap = float(sys.argv[7]) if len(sys.argv) > 7 else 0
    blur_strength = float(sys.argv[8]) if len(sys.argv) > 8 else 0.375
    speed_factor = float(sys.argv[9]) if len(sys.argv) > 9 else 1.5
    background_audio_path = sys.argv[10] if len(sys.argv) > 10 else None
    
    try:
        result = generate_simple_composite_draft(
            enhanced_srt_file, video_path, template_file, output_dir,
            scale_x, scale_y, gap, blur_strength, speed_factor, background_audio_path
        )
        print(f"简化版复合草稿生成成功: {result}")
    except Exception as e:
        print(f"生成简化版复合草稿失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
