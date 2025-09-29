
from newapi_client import GeminiClient
from tts_client_new import TTSClient
from draft_gen import DraftGenerator
from dl_splitter_video import VideoDownloader
from srt_generate import SRTGenerator
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


PROJECT_CACHE_DIR = './output/project_cache'

sys_prompt = """
用户输入的是一个 srt 文件，最高指令是 srt 中的时间戳信息是不能变化的 。 
根据故事情节对这个文案进行切割，要求切割的故事是合理的，不能很突兀的就结束，如果最开头或者后面的一段是突然结束的，就可以不需要不完整的部分，输出切割后的每个故事，
保证故事完整，切割时间控制在 一分半以内 ，
然后对一个故事的时间戳做判断，然后对每句话进行翻译，不需要完全遵守原文，英文要保持简洁，可以在不影响故事的情况下去掉原文的一些信息
可以结合原始故事的人物信息，做一些美国文化进行一些翻译，要求要符合场景，特别是人物名称和地点名称方面需要符合美国文化。 
对每个故事生成的标题，需要有足够吸引力，可以是夸张或者设置悬念的方式，纯英文。在标题后增加1个标签，标签是原漫画故事名 ，标题整体长度不超过 90 个字符
生成故事的描述信息，与 标题相同维度。
输出的格式为 纯 json ，不要有任何其他内容。
示例格式

[
  {
    "story_title": "Bart's Inspiration and the Master's Advice #simpsons",
    "start_time": "00:00:00,000",
    "end_time": "01:02:539",
    "dialogue": [
      {
        "index": 0,
        "start": "00:00:00,000",
        "end": "  00:00:02,359",
        "chinese": "心動漫威命狗在春田鎮大火後",
        "english": "After the massive Marvel-themed fire in Springfield, the kids got into drawing."
      }
    ]
  }
]

"""

ai_analysis_dir = "./output/ai_analysis/"
if not os.path.exists(ai_analysis_dir):
    os.makedirs(ai_analysis_dir)

"""
视频段数据结构
"""

class VideoSegment:
    def __init__(self, url: str, segment_index: int, start_time: str, duration: str,
                 org_video_file_path: str, org_audio_file_path: str):
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

"""
dialogue
"""

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
                english=d['english'] if d['english'] else 'God bless you'
            )
            self.dialogue_list.append(dialogue_obj)

    def to_dict(self) -> Dict:
        return {
            'story_title': self.story_title,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'dialogue': [d.to_dict() for d in self.dialogue_list]
        }

class ShortStoryGenerator:
    def __init__(self, max_duration_minutes: int = 10, output_dir: str = "./output/org_materials"):
        self.client = GeminiClient()
        self.tts_client = TTSClient()
        self.max_duration_minutes = max_duration_minutes
        self.output_dir = output_dir

        # 初始化下载器和SRT生成器
        self.video_downloader = VideoDownloader(
            max_duration_minutes=max_duration_minutes,
            output_dir=output_dir
        )
        self.srt_generator = SRTGenerator(output_dir="./output")

        # 初始化草稿生成器
        self.draft_generator = DraftGenerator()

    def generate(self, url: str) -> Optional[VideoProject]:
        print(f"🎬 开始处理视频URL: {url}")

        try:
            # 第一步：下载视频和切割
            print("📥 第一步：下载并切割视频...")
            video_segments_data = self.video_downloader.process_video(url)
            if not video_segments_data:
                print("❌ 视频下载失败")
                return None

            # 创建视频项目对象
            video_project = VideoProject(url)

            # 第二步：为每个视频段生成SRT文件
            print(f"🎵 第二步：为 {len(video_segments_data)} 个视频段生成SRT文件...")
            for i, segment_data in enumerate(video_segments_data):
                print(f"\n处理视频段 {i+1}/{len(video_segments_data)}")

                # 创建VideoSegment对象
                video_segment = VideoSegment(
                    url=url,
                    segment_index=segment_data['segment_index'],
                    start_time=segment_data['start_time'],
                    duration=segment_data['duration'],
                    org_video_file_path=segment_data['org_video_file_path'],
                    org_audio_file_path=segment_data['org_audio_file_path']
                )

                # 生成SRT文件
                srt_file_path = self.generate_srt_for_segment(video_segment)
                if srt_file_path:
                    video_segment.srt_file_path = srt_file_path

                    # 第三步：分析SRT文件生成故事
                    print(f"📖 第三步：分析SRT文件生成故事...")
                    stories = self.ai_analysis_story(srt_file_path)
                    if stories:
                        video_segment.stories = stories

                        # 第四步：为每个故事生成语音和草稿
                        print(f"🎤 第四步：为 {len(stories)} 个故事生成语音和草稿...")
                        for story_idx, story in enumerate(stories):
                            self.process_story_for_segment(story, story_idx, video_segment)

                video_project.add_segment(video_segment)

            # 保存项目结果
            self.save_project_to_cache(video_project)

            print(f"✅ 视频处理完成！共处理 {len(video_project.segments)} 个视频段")
            return video_project

        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def generate_srt_for_segment(self, video_segment: VideoSegment) -> Optional[str]:
        """为视频段生成SRT文件"""
        try:
            print(f"🎵 为视频段 {video_segment.segment_index} 生成SRT文件...")

            # 使用音频文件路径生成SRT
            srt_file_path = self.srt_generator.transcribe(video_segment.org_audio_file_path)

            if srt_file_path and os.path.exists(srt_file_path):
                print(f"✅ SRT文件生成成功: {srt_file_path}")
                return srt_file_path
            else:
                print(f"❌ SRT文件生成失败")
                return None

        except Exception as e:
            print(f"❌ SRT文件生成异常: {e}")
            return None

    def process_story_for_segment(self, story: StoryContent, story_idx: int, video_segment: VideoSegment):
        video_id = video_segment.url.split("/")[-1].split("?")[0]
        """为视频段中的故事生成语音和草稿"""
        try:
            print(f"🎤 处理视频段 {video_id}:{video_segment.segment_index} 的故事 {story_idx + 1}: {story.story_title}")

            # 创建输出目录
            base_filename = f"{video_id}_segment_{video_segment.segment_index}"
            output_dir = f"./output/tmp_voice/{base_filename}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 生成语音
            processed_story = self.process_single_story_audio(story, story_idx, output_dir)

            # 生成草稿文件
            self.generate_draft_file(processed_story, story_idx, video_segment.org_video_file_path, video_id)

            print(f"✅ 故事处理完成: {story.story_title}")

        except Exception as e:
            print(f"❌ 故事处理失败: {e}")

    def save_project_to_cache(self, video_project: VideoProject) -> str:
        """保存视频项目到缓存文件"""
        try:
            # 生成缓存文件路径
            url_safe = video_project.url.split("/")[-1].split("?")[0]
            cache_file = f"{PROJECT_CACHE_DIR}/{url_safe}_{int(video_project.project_created_time.timestamp())}.json"

            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(video_project.to_dict(), f, ensure_ascii=False, indent=2)

            print(f"💾 项目已缓存到: {cache_file}")
            return cache_file

        except Exception as e:
            print(f"❌ 项目缓存失败: {e}")
            return None

    def ai_analysis_story(self, srt_file) -> List[StoryContent]:
        """
        AI分析故事方法 - 先检查缓存，没有缓存则调用AI生成
        """
        # 生成缓存文件路径
        base_filename = os.path.splitext(os.path.basename(srt_file))[0]
        cache_file = os.path.join(ai_analysis_dir, f"{base_filename}.json")

        # 1. 先检查缓存文件是否存在
        if os.path.exists(cache_file):
            print(f"💾 发现缓存文件，加载中: {cache_file}")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    analysis_result = f.read()

                # 解析并返回对象
                stories = self.parse_analysis_result_obj(analysis_result)
                if stories:
                    print(f"✅ 从缓存加载了 {len(stories)} 个故事")
                    return stories
                else:
                    print("⚠️ 缓存文件损坏，将重新生成")
            except Exception as e:
                print(f"⚠️ 缓存文件读取失败: {e}，将重新生成")

        # 2. 没有缓存或缓存损坏，调用AI生成
        print("🤖 正在调用AI分析...")

        # 加载srt文件
        with open(srt_file, "r", encoding="utf-8") as f:
            text = f.read()

        # 调用AI分析
        analysis_result = self.client.analyze_text(text, sys_prompt)

        if not analysis_result:
            print("❌ AI分析返回空结果")
            return []

        # 清理结果格式
        if analysis_result.startswith('`'):
            analysis_result = analysis_result.replace('`', '').replace('json', '')

        # 3. 缓存AI分析结果
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(analysis_result)
            print(f"💾 AI分析结果已缓存到: {cache_file}")
        except Exception as e:
            print(f"⚠️ 缓存失败: {e}")

        # 4. 解析并返回对象
        stories = self.parse_analysis_result_obj(analysis_result)
        if stories:
            print(f"✅ AI分析完成，获取到 {len(stories)} 个故事")
        else:
            print("❌ AI分析结果解析失败")

        return stories

    def parse_analysis_result_obj(self, analysis_result: str) -> List[StoryContent]:
        """解析AI分析结果为对象"""
        try:
            # 清理可能的markdown格式
            clean_result = analysis_result.strip()
            if clean_result.startswith('json'):
                clean_result = clean_result[4:].strip()

            # 解析JSON
            stories_data = json.loads(clean_result)

            # 转换为对象
            stories = []
            for story_data in stories_data:
                story = StoryContent(
                    story_title=story_data['story_title'],
                    start_time=story_data['start_time'],
                    end_time=story_data['end_time'],
                    dialogue=story_data['dialogue']
                )
                stories.append(story)

            print(f"✅ 成功解析 {len(stories)} 个故事")
            return stories

        except Exception as e:
            print(f"❌ 解析对象失败: {e}")
            return []

    def process_single_story_audio(self, story: StoryContent, story_idx: int, output_dir: str) -> StoryContent:
        """为单个故事生成语音 - 带缓存逻辑"""
        print(f"🎵 开始为故事生成语音: {story.story_title}")

        # 为每个对话生成语音
        for dialogue in story.dialogue_list:
            try:
                # 生成音频文件路径
                audio_filename = f"story_{story_idx + 1}_dialogue_{dialogue.index}.mp3"
                audio_path = os.path.join(output_dir, audio_filename)
                srt_filename = f"story_{story_idx + 1}_dialogue_{dialogue.index}.srt"
                srt_path = os.path.join(output_dir, srt_filename)

                # 1. 检查语音文件是否已存在
                if os.path.exists(audio_path):
                    print(f"  💾 发现缓存音频: {audio_filename}")

                    # 检查文件大小是否正常（大于1KB）
                    if os.path.getsize(audio_path) > 1024:
                        # 更新对象中的路径信息
                        dialogue.audio_path = audio_path

                        # 检查字幕文件是否存在
                        if os.path.exists(srt_path):
                            dialogue.srt_path = srt_path
                        else:
                            dialogue.srt_path = None

                        print(f"  ✅ 使用缓存音频: {audio_filename}")
                        continue
                    else:
                        print(f"  ⚠️ 缓存文件损坏（太小），将重新生成")
                        # 删除损坏的文件
                        try:
                            os.remove(audio_path)
                        except:
                            pass

                # 2. 生成新的语音文件
                print(f"  🎤 生成对话 {dialogue.index}: {dialogue.english[:50]}...")

                # 调用TTS生成语音
                generated_srt_path = self.tts_client.generate_and_save_audio(
                    text=dialogue.english,
                    output_file=audio_path,
                    voice="zh-HK-HiuGaaiNeural"
                )

                # 3. 验证生成的文件
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1024:
                    # 更新对象中的路径信息
                    dialogue.audio_path = audio_path
                    dialogue.srt_path = generated_srt_path if generated_srt_path else None

                    print(f"  ✅ 语音生成完成: {audio_filename}")
                else:
                    print(f"  ❌ 语音文件生成异常")
                    dialogue.audio_path = None
                    dialogue.srt_path = None

            except Exception as e:
                print(f"  ❌ 生成语音失败: {e}")
                dialogue.audio_path = None
                dialogue.srt_path = None

        print(f"✅ 故事 '{story.story_title}' 语音处理完成!")
        return story

    def generate_draft_file(self, story: 'StoryContent', story_idx: int, video_path: str = None, video_id: str = None) -> str:
        """为单个故事生成草稿文件"""
        try:
            print(f"📝 开始为故事生成草稿: {story.story_title}")

            # 使用 DraftGenerator 的 generate_from_story 方法
            if not os.path.exists(video_path):
                print(f"❌ 视频文件不存在: {video_path}")
                return None
            
            draft_file = self.draft_generator.generate_from_story(
                story=story,
                video_path=video_path,
                story_idx=story_idx,
                video_id=video_id
            )

            print(f"✅ 草稿文件生成完成: {draft_file}")
            return draft_file

        except Exception as e:
            print(f"❌ 生成草稿文件失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def save_stories_to_cache(self, stories: List[StoryContent], srt_file: str) -> str:
        """将处理结果缓存到本地文件"""
        try:
            # 生成缓存文件路径
            base_filename = os.path.splitext(os.path.basename(srt_file))[0]
            cache_file = f"./output/{base_filename}_processed_stories.json"

            # 转换为可序列化的字典格式
            cache_data = {
                'source_file': srt_file,
                'processed_time': datetime.now().isoformat(),
                'stories': [story.to_dict() for story in stories]
            }

            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"💾 结果已缓存到: {cache_file}")
            return cache_file

        except Exception as e:
            print(f"❌ 缓存失败: {e}")
            return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python short_story_generator.py <video_url> [max_duration_minutes] [output_dir]")
        print("Example: python short_story_generator.py 'https://www.bilibili.com/video/BV1abc123def' 10 './output/org_materials'")
        sys.exit(1)

    video_url = sys.argv[1]
    max_duration_minutes = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "./output/org_materials"

    generator = ShortStoryGenerator(
        max_duration_minutes=max_duration_minutes,
        output_dir=output_dir
    )
    result = generator.generate(video_url)

    if result:
        print(f"\n🎉 处理完成！项目包含 {len(result.segments)} 个视频段")
        for i, segment in enumerate(result.segments, 1):
            print(f"段 {i}: {len(segment.stories)} 个故事，SRT文件: {segment.srt_file_path}")
    else:
        print("❌ 处理失败")
        sys.exit(1)

