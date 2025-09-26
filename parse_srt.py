#!/usr/bin/env python3
"""
SRT JSON 解析器 - 增强版本
1. 合并时间连续的对话记录
2. 生成英文翻译的TTS音频
3. 在JSON中添加音频文件路径
"""

import json
import os
import hashlib
from tts_client_new import TTSClient


def time_to_seconds(time_str):
    """将时间字符串转换为秒数"""
    time_part, ms_part = time_str.split(',')
    h, m, s = map(int, time_part.split(':'))
    ms = int(ms_part)
    return h * 3600 + m * 60 + s + ms / 1000.0


def should_merge(prev_end, curr_start, gap_seconds=1.0):
    """判断是否应该合并：时间间隔小于等于gap_seconds"""
    prev_time = time_to_seconds(prev_end)
    curr_time = time_to_seconds(curr_start)
    return abs(curr_time - prev_time) <= gap_seconds


def merge_dialogues(dialogues):
    """合并连续的对话"""
    if not dialogues:
        return []
    
    merged = []
    current = dialogues[0].copy()
    
    for next_dialogue in dialogues[1:]:
        if should_merge(current["end_time"], next_dialogue["start_time"]):
            # 合并对话
            current["end_time"] = next_dialogue["end_time"]
            current["translation"] += " " + next_dialogue["translation"]
            current["original_text"] += " " + next_dialogue["original_text"]
        else:
            # 不合并，保存当前对话
            merged.append(current)
            current = next_dialogue.copy()
    
    merged.append(current)
    return merged


def get_audio_filename(text):
    """根据文本内容生成音频文件名，使用MD5确保相同内容文件名一致"""
    # 使用文本的完整MD5哈希值生成文件名
    text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
    return f"audio_{text_hash}.mp3"


def generate_audio_for_dialogues(dialogues, output_dir, voice="en-US-BrianNeural"):
    """为对话生成TTS音频，跳过已存在的文件"""
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 初始化TTS客户端
    tts_client = TTSClient()
    
    for i, dialogue in enumerate(dialogues):
        translation = dialogue['translation']
        audio_filename = get_audio_filename(translation)
        audio_path = os.path.join(output_dir, audio_filename)
        
        # 检查文件是否已存在
        if os.path.exists(audio_path):
            print(f"跳过已存在的音频 {i+1}/{len(dialogues)}: {audio_filename}")
            # 直接添加路径信息
            dialogue['audio_file'] = audio_path
            dialogue['audio_filename'] = audio_filename
            continue
        
        print(f"生成音频 {i+1}/{len(dialogues)}: {audio_filename}")
        print(f"  文本: {translation[:100]}...")
        
        try:
            # 生成音频
            audio_data = tts_client.generate_speech(translation, voice)
            
            # 保存音频文件
            with open(audio_path, 'wb') as f:
                f.write(audio_data)
            
            # 在对话中添加音频路径
            dialogue['audio_file'] = audio_path
            dialogue['audio_filename'] = audio_filename
            
            print(f"  ✓ 生成成功: {len(audio_data)} 字节")
            
        except Exception as e:
            print(f"  ✗ 生成失败: {e}")
            dialogue['audio_file'] = None
            dialogue['audio_filename'] = None


def compress_and_generate_audio(input_file, output_file, voice="en-US-BrianNeural"):
    """压缩JSON文件并生成TTS音频"""
    # 读取原始JSON文件
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建音频输出目录
    audio_output_dir = "output/tmp_voice"
    
    # 压缩对话
    total_original = 0
    total_merged = 0
    
    for section in data:
        original_count = len(section['dialogues'])
        section['dialogues'] = merge_dialogues(section['dialogues'])
        merged_count = len(section['dialogues'])
        
        total_original += original_count
        total_merged += merged_count
        
        print(f"{section['title']}: {original_count} -> {merged_count} 条对话")
        
        # 为每个章节的对话生成音频
        generate_audio_for_dialogues(section['dialogues'], audio_output_dir, voice)
    
    print(f"\n总计: {total_original} -> {total_merged} 条对话")
    print(f"音频文件保存到: {audio_output_dir}")
    
    # 保存增强后的JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"增强JSON完成: {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("用法:")
        print("  python parse_srt.py input.json output.json [voice]")
        print("示例:")
        print("  python parse_srt.py input/input-srt.json output/enhanced-srt.json")
        print("  python parse_srt.py input/input-srt.json output/enhanced-srt.json en-US-JennyNeural")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else "en-US-BrianNeural"
    
    print(f"使用语音: {voice}")
    compress_and_generate_audio(input_file, output_file, voice)
