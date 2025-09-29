# -*- coding: utf-8 -*-
"""
字幕模板常量定义
用于视频草稿生成中的字幕材料和片段模板
"""

# 默认字幕材料模板
SUBTITLE_MATERIAL_TEMPLATE = {
    "id": "",
    "type": "text",
    "font": {
        "id": "",
        "path": "jiashuhei.ttf",
        "size": 18
    },
    "words": {
        "text": "",
        "fontstyle": {
            "size": 18,
            "color": [1.0, 1.0, 1.0, 1.0],
            "strokecolor": [0.0, 0.0, 0.0, 1.0],
            "strokewidth": 2,
            "letterspace": 0,
            "linespace": 0,
            "bold": False,
            "italic": False,
            "underline": False
        }
    },
    "duration": 3000000,
    "extra_info": ""
}

# 中文字幕材料模板
CHINESE_SUBTITLE_MATERIAL_TEMPLATE = {
    "id": "",
    "type": "text",
    "font": {
        "id": "",
        "path": "jiashuhei.ttf",
        "size": 24
    },
    "words": {
        "text": "",
        "fontstyle": {
            "size": 24,
            "color": [1.0, 1.0, 1.0, 1.0],  # 白色
            "strokecolor": [0.0, 0.0, 0.0, 1.0],  # 黑色描边
            "strokewidth": 3,
            "letterspace": 0,
            "linespace": 0,
            "bold": True,
            "italic": False,
            "underline": False
        }
    },
    "duration": 3000000,
    "extra_info": ""
}

# 英文字幕材料模板
ENGLISH_SUBTITLE_MATERIAL_TEMPLATE = {
    "id": "",
    "type": "text",
    "font": {
        "id": "",
        "path": "Impact.ttf",
        "size": 20
    },
    "words": {
        "text": "",
        "fontstyle": {
            "size": 20,
            "color": [1.0, 1.0, 0.0, 1.0],  # 黄色
            "strokecolor": [0.0, 0.0, 0.0, 1.0],  # 黑色描边
            "strokewidth": 2,
            "letterspace": 0,
            "linespace": 0,
            "bold": True,
            "italic": False,
            "underline": False
        }
    },
    "duration": 3000000,
    "extra_info": ""
}

# 字幕片段模板
SUBTITLE_SEGMENT_TEMPLATE = {
    "id": "",
    "material_id": "",
    "track_index": 1,
    "target_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "source_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "extra_material_refs": [],
    "uniform_scale": {
        "on": True,
        "value": 1.0
    },
    "transform": {
        "position": {
            "x": 0.5,
            "y": 0.8
        },
        "rotation": 0.0,
        "scale": {
            "x": 1.0,
            "y": 1.0
        }
    },
    "visible": True,
    "volume": 1.0,
    "animation": {
        "animations": [
            {
                "id": "",
                "type": "app_in",
                "duration": 500000,
                "start_time": 0,
                "end_time": 500000,
                "material_animations": []
            }
        ]
    }
}

# 中文字幕片段模板（上方显示）
CHINESE_SUBTITLE_SEGMENT_TEMPLATE = {
    "id": "",
    "material_id": "",
    "track_index": 1,
    "target_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "source_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "extra_material_refs": [],
    "uniform_scale": {
        "on": True,
        "value": 1.0
    },
    "transform": {
        "position": {
            "x": 0.5,
            "y": 0.2  # 上方位置
        },
        "rotation": 0.0,
        "scale": {
            "x": 1.0,
            "y": 1.0
        }
    },
    "visible": True,
    "volume": 1.0,
    "animation": {
        "animations": [
            {
                "id": "",
                "type": "app_in",
                "duration": 500000,
                "start_time": 0,
                "end_time": 500000,
                "material_animations": [
                    {
                        "id": "",
                        "type": "fade_in",
                        "start_time": 0,
                        "duration": 500000,
                        "material_animation_keyframes": [
                            {
                                "start_time": 0,
                                "end_time": 500000,
                                "start_value": 0.0,
                                "end_value": 1.0,
                                "curve_type": "bezier"
                            }
                        ]
                    }
                ]
            }
        ]
    }
}

# 英文字幕片段模板（下方显示）
ENGLISH_SUBTITLE_SEGMENT_TEMPLATE = {
    "id": "",
    "material_id": "",
    "track_index": 2,
    "target_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "source_timerange": {
        "duration": 3000000,
        "start": 0
    },
    "extra_material_refs": [],
    "uniform_scale": {
        "on": True,
        "value": 1.0
    },
    "transform": {
        "position": {
            "x": 0.5,
            "y": 0.8  # 下方位置
        },
        "rotation": 0.0,
        "scale": {
            "x": 1.0,
            "y": 1.0
        }
    },
    "visible": True,
    "volume": 1.0,
    "animation": {
        "animations": [
            {
                "id": "",
                "type": "app_in",
                "duration": 500000,
                "start_time": 0,
                "end_time": 500000,
                "material_animations": [
                    {
                        "id": "",
                        "type": "slide_up",
                        "start_time": 0,
                        "duration": 500000,
                        "material_animation_keyframes": [
                            {
                                "start_time": 0,
                                "end_time": 500000,
                                "start_value": 0.0,
                                "end_value": 1.0,
                                "curve_type": "ease_out"
                            }
                        ]
                    }
                ]
            }
        ]
    }
}

# 字幕动画效果模板
SUBTITLE_ANIMATIONS = {
    "fade_in": {
        "id": "",
        "type": "fade_in",
        "start_time": 0,
        "duration": 500000,
        "material_animation_keyframes": [
            {
                "start_time": 0,
                "end_time": 500000,
                "start_value": 0.0,
                "end_value": 1.0,
                "curve_type": "linear"
            }
        ]
    },
    "slide_up": {
        "id": "",
        "type": "slide_up",
        "start_time": 0,
        "duration": 500000,
        "material_animation_keyframes": [
            {
                "start_time": 0,
                "end_time": 500000,
                "start_value": 0.0,
                "end_value": 1.0,
                "curve_type": "ease_out"
            }
        ]
    },
    "scale_in": {
        "id": "",
        "type": "scale_in",
        "start_time": 0,
        "duration": 300000,
        "material_animation_keyframes": [
            {
                "start_time": 0,
                "end_time": 300000,
                "start_value": 0.5,
                "end_value": 1.0,
                "curve_type": "elastic"
            }
        ]
    },
    "typewriter": {
        "id": "",
        "type": "typewriter",
        "start_time": 0,
        "duration": 1000000,
        "material_animation_keyframes": [
            {
                "start_time": 0,
                "end_time": 1000000,
                "start_value": 0.0,
                "end_value": 1.0,
                "curve_type": "linear"
            }
        ]
    }
}

# 字幕轨道配置
SUBTITLE_TRACKS = {
    "chinese_track": {
        "attribute": 0,
        "flag": 0,
        "id": "",
        "segments": [],
        "type": "text"
    },
    "english_track": {
        "attribute": 0,
        "flag": 0,
        "id": "",
        "segments": [],
        "type": "text"
    }
}

# 时间转换工具函数
def srt_time_to_microseconds(srt_time: str) -> int:
    """
    将SRT时间格式转换为微秒
    输入格式: "00:00:02,359"
    输出: 微秒数
    """
    try:
        time_part, milliseconds = srt_time.split(',')
        hours, minutes, seconds = map(int, time_part.split(':'))
        total_microseconds = (hours * 3600 + minutes * 60 + seconds) * 1000000 + int(milliseconds) * 1000
        return total_microseconds
    except Exception as e:
        print(f"时间转换错误: {e}")
        return 0

def microseconds_to_srt_time(microseconds: int) -> str:
    """
    将微秒转换为SRT时间格式
    输入: 微秒数
    输出格式: "00:00:02,359"
    """
    try:
        milliseconds = microseconds // 1000
        seconds = milliseconds // 1000
        ms_remainder = milliseconds % 1000

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        sec_remainder = seconds % 60

        return f"{hours:02d}:{minutes:02d}:{sec_remainder:02d},{ms_remainder:03d}"
    except Exception as e:
        print(f"时间转换错误: {e}")
        return "00:00:00,000"

# 字幕生成工具函数
def create_subtitle_material(text: str, material_type: str = "chinese", custom_id: str = None) -> dict:
    """
    创建字幕材料

    Args:
        text: 字幕文本
        material_type: 字幕类型 ("chinese" 或 "english")
        custom_id: 自定义ID

    Returns:
        字幕材料字典
    """
    import uuid

    if material_type == "chinese":
        template = CHINESE_SUBTITLE_MATERIAL_TEMPLATE.copy()
    elif material_type == "english":
        template = ENGLISH_SUBTITLE_MATERIAL_TEMPLATE.copy()
    else:
        template = SUBTITLE_MATERIAL_TEMPLATE.copy()

    material = template.copy()
    material["id"] = custom_id or str(uuid.uuid4())
    material["words"]["text"] = text
    material["font"]["id"] = str(uuid.uuid4())

    return material

def create_subtitle_segment(material_id: str, start_time: str, end_time: str,
                          segment_type: str = "chinese", custom_id: str = None,
                          animation_type: str = "fade_in") -> dict:
    """
    创建字幕片段

    Args:
        material_id: 材料ID
        start_time: 开始时间 (SRT格式)
        end_time: 结束时间 (SRT格式)
        segment_type: 片段类型 ("chinese" 或 "english")
        custom_id: 自定义ID
        animation_type: 动画类型

    Returns:
        字幕片段字典
    """
    import uuid

    if segment_type == "chinese":
        template = CHINESE_SUBTITLE_SEGMENT_TEMPLATE.copy()
    elif segment_type == "english":
        template = ENGLISH_SUBTITLE_SEGMENT_TEMPLATE.copy()
    else:
        template = SUBTITLE_SEGMENT_TEMPLATE.copy()

    segment = template.copy()
    segment["id"] = custom_id or str(uuid.uuid4())
    segment["material_id"] = material_id

    # 时间转换
    start_microseconds = srt_time_to_microseconds(start_time)
    end_microseconds = srt_time_to_microseconds(end_time)
    duration = end_microseconds - start_microseconds

    segment["target_timerange"]["start"] = start_microseconds
    segment["target_timerange"]["duration"] = duration
    segment["source_timerange"]["start"] = 0
    segment["source_timerange"]["duration"] = duration

    # 添加动画效果
    if animation_type in SUBTITLE_ANIMATIONS:
        animation = SUBTITLE_ANIMATIONS[animation_type].copy()
        animation["id"] = str(uuid.uuid4())
        animation["duration"] = min(500000, duration // 2)  # 动画时长不超过字幕时长的一半
        segment["animation"]["animations"][0] = animation

    return segment

def create_subtitle_track(track_type: str = "chinese", custom_id: str = None) -> dict:
    """
    创建字幕轨道

    Args:
        track_type: 轨道类型 ("chinese" 或 "english")
        custom_id: 自定义ID

    Returns:
        字幕轨道字典
    """
    import uuid

    if track_type == "chinese":
        template = SUBTITLE_TRACKS["chinese_track"].copy()
    elif track_type == "english":
        template = SUBTITLE_TRACKS["english_track"].copy()
    else:
        template = SUBTITLE_TRACKS["chinese_track"].copy()

    track = template.copy()
    track["id"] = custom_id or str(uuid.uuid4())

    return track