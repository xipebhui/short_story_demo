#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享数据模型 - 用于 short_story_generator 和 draft_gen 模块
"""

from typing import List, Dict, Optional
from datetime import datetime


class StoryDialogue:
    """对话片段 - 一个音频对应多个视频片段"""
    def __init__(self, index: int,
                 video_segments: List[Dict[str, str]],  # [{'start': '00:00:00,000', 'end': '00:00:02,000'}, ...]
                 chinese: str,
                 english: str):
        self.index = index
        self.video_segments = video_segments  # 多个视频片段
        self.chinese = chinese
        self.english = english
        self.audio_path: Optional[str] = None
        self.srt_path: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'video_segments': self.video_segments,
            'chinese': self.chinese,
            'english': self.english,
            'audio_path': self.audio_path,
            'srt_path': self.srt_path
        }


class StoryContent:
    """故事内容"""
    def __init__(self, story_title: str,
                 start_index: int,
                 end_index: int,
                 dialogue: List[Dict]):
        self.story_title = story_title
        self.start_index = start_index
        self.end_index = end_index
        self.dialogue_list: List[StoryDialogue] = []

        # 将字典数据转换为 StoryDialogue 对象
        for d in dialogue:
            dialogue_obj = StoryDialogue(
                index=d.get('index', 0),
                video_segments=d.get('video_segments', []),
                chinese=d['chinese'],
                english=d.get('english', 'God bless you')
            )
            self.dialogue_list.append(dialogue_obj)

    def to_dict(self) -> Dict:
        return {
            'story_title': self.story_title,
            'start_index': self.start_index,
            'end_index': self.end_index,
            'dialogue': [d.to_dict() for d in self.dialogue_list]
        }


class VideoSegment:
    """视频段数据结构"""
    def __init__(self, url: str, segment_index: int,
                 start_time: str, duration: str,
                 org_video_file_path: str,
                 org_audio_file_path: str):
        self.url = url
        self.segment_index = segment_index
        self.start_time = start_time
        self.duration = duration
        self.org_video_file_path = org_video_file_path
        self.org_audio_file_path = org_audio_file_path
        self.srt_file_path: Optional[str] = None
        self.stories: List[StoryContent] = []

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'segment_index': self.segment_index,
            'start_time': self.start_time,
            'duration': self.duration,
            'org_video_file_path': self.org_video_file_path,
            'org_audio_file_path': self.org_audio_file_path,
            'srt_file_path': self.srt_file_path,
            'stories': [story.to_dict() for story in self.stories]
        }


class VideoProject:
    """视频项目"""
    def __init__(self, url: str):
        self.url = url
        self.segments: List[VideoSegment] = []
        self.project_created_time = datetime.now()

    def add_segment(self, segment: VideoSegment):
        self.segments.append(segment)

    def to_dict(self) -> Dict:
        return {
            'url': self.url,
            'project_created_time': self.project_created_time.isoformat(),
            'segments': [segment.to_dict() for segment in self.segments]
        }