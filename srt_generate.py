# 配置选项
ENABLE_CACHE_CHECK = True  # 是否启用缓存检测，True=检测已存在文件并跳过，False=总是重新处理
JSON_OUTPUT_DIR = "./output/json_files"
STORY_DURATIME_SECONDS = 120 

import sys
import os
import json
import logging
import whisper


class JSONSubtitleGenerator:
    def __init__(self, output_dir=JSON_OUTPUT_DIR):
        self.output_dir = output_dir
        self._setup_logging()
        self.logger.info(f"JSONSubtitleGenerator initialized with output directory: {output_dir}")

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.logger = logging.getLogger(__name__)

    def transcribe(self, audio_path: str, max_duration: float = 3.0):
        self.logger.info(f"开始转录音频文件: {audio_path}")
        self.logger.info(f"缓存检测: {'启用' if ENABLE_CACHE_CHECK else '禁用'}")

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 生成JSON文件路径
        filename = os.path.basename(audio_path).rsplit(".", 1)[0] + ".json"
        json_output = os.path.join(self.output_dir, filename)
        
        # 检查是否存在缓存文件
        if ENABLE_CACHE_CHECK and os.path.exists(json_output):
            self.logger.info(f"发现缓存文件，跳过转录: {json_output}")
            with open(json_output, "r", encoding="utf-8") as f:
                data = json.load(f)
            end_time = data[-1]['time'].split(' --> ')[1].split(',')[0]
            end_seconds = self._format_time_to_seconds(end_time)
            story_num = round(end_seconds / STORY_DURATIME_SECONDS)
            return json_output, story_num

        # 加载模型 medium small
        model = whisper.load_model("small",device="cuda")
        self.logger.info("Whisper 模型已加载")

        self.logger.info("正在转录音频，请稍候...")
        result = model.transcribe(audio_path, task="transcribe", language=None, verbose=True)

        story_end_time = 0
        # 合并短段落
        merged_segments = []
        for seg in result["segments"]:
            if not merged_segments:
                merged_segments.append(seg)
            else:
                last = merged_segments[-1]
                if abs(last["end"] - seg["start"]) < 1e-3:
                    if (seg["end"] - last["start"]) <= max_duration:
                        last["end"] = seg["end"]
                        logging.info(f"current end time is {last['end']}")
                        story_end_time = last['end'] if last['end'] > story_end_time else story_end_time
                        last["text"] += " " + seg["text"].strip()
                    else:
                        merged_segments.append(seg)
                else:
                    merged_segments.append(seg)

        # 生成 JSON 格式数据
        json_data = []
        for i, segment in enumerate(merged_segments, start=1):
            json_data.append({
                "index": i,
                "time": f"{self._format_time(segment['start'])} --> {self._format_time(segment['end'])}",
                "text": segment["text"].strip()
            })
        story_num = round(story_end_time / STORY_DURATIME_SECONDS)
        # 写入 JSON 文件
        with open(json_output, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"字幕 JSON 已保存：{json_output}")
        return json_output, story_num

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    def _format_time_to_seconds(self, time: str) -> float:
        h, m, s = time.split(':')
        return int(h) * 3600 + int(m) * 60 + int(s)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python srt_generate.py your_audio_file.mp3")
    else:
        generator = JSONSubtitleGenerator()
        generator.transcribe(sys.argv[1])
