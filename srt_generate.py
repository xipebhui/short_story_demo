# 配置选项
ENABLE_CACHE_CHECK = True  # 是否启用缓存检测，True=检测已存在文件并跳过，False=总是重新处理
SRT_OUTPUT_DIR = "./output/srt_files"
import sys
import os
import logging
import whisper


class SRTGenerator:
    def __init__(self, output_dir=SRT_OUTPUT_DIR):
        self.output_dir = output_dir
        self._setup_logging()
        self.logger.info(f"SRTGenerator initialized with output directory: {output_dir}")

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

    def transcribe(self, audio_path: str, max_duration: float = 3.0):
        self.logger.info(f"开始转录音频文件: {audio_path}")
        self.logger.info(f"缓存检测: {'启用' if ENABLE_CACHE_CHECK else '禁用'}")

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 生成SRT文件路径
        filename = os.path.basename(audio_path).rsplit(".", 1)[0] + ".srt"
        srt_output = os.path.join(self.output_dir, filename)

        # 检查是否存在缓存文件
        if ENABLE_CACHE_CHECK and os.path.exists(srt_output):
            self.logger.info(f"发现缓存文件，跳过转录: {srt_output}")
            return srt_output

        # 加载模型  small medium
        model = whisper.load_model("medium")
        self.logger.info("Whisper 模型已加载")

        self.logger.info("正在转录音频，请稍候...")
        result = model.transcribe(audio_path, task="transcribe", language=None, verbose=True)

        # 合并短段落
        merged_segments = []
        for seg in result["segments"]:
            if not merged_segments:
                merged_segments.append(seg)
            else:
                last = merged_segments[-1]
                # 判断是否时间连续
                if abs(last["end"] - seg["start"]) < 1e-3:
                    # 如果拼接后时长不超过 max_duration，则合并
                    if (seg["end"] - last["start"]) <= max_duration:
                        last["end"] = seg["end"]
                        last["text"] += " " + seg["text"].strip()
                    else:
                        # 否则单独成段
                        merged_segments.append(seg)
                else:
                    merged_segments.append(seg)

        # 写入SRT文件
        with open(srt_output, "w", encoding="utf-8") as f:
            for i, segment in enumerate(merged_segments, start=1):
                start = segment["start"]
                end = segment["end"]
                text = segment["text"].strip()

                f.write(f"{i}\n")
                f.write(f"{self._format_time(start)} --> {self._format_time(end)}\n")
                f.write(f"{text}\n\n")

        self.logger.info(f"SRT 字幕已保存：{srt_output}")
        return srt_output

    def _format_time(self, seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python srt_generate.py your_audio_file.mp3")
    else:
        generator = SRTGenerator()
        generator.transcribe(sys.argv[1])
