
from newapi_client import GeminiClient
from tts_client_new import TTSClient
from draft_gen import DraftGenerator
from dl_splitter_video import VideoDownloader
from srt_generate import JSONSubtitleGenerator
from data_models import StoryDialogue, StoryContent, VideoSegment, VideoProject
from jy_export import VideoExporter
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging



PROJECT_CACHE_DIR = './output/project_cache'

sys_prompt = """
你是一个专业的视频内容编辑助手。你的任务是接收用户输入的 JSON 数组（包含 index 字段，类似 SRT 格式），然后根据故事情节对内容进行精确切割和优化处理，最终输出为纯 JSON 格式。
核心要求与优化目标：
精确的故事切割 (Precise Story Segmentation):
首要任务是识别和切割出独立的、情节连贯的完整故事单元。每个输出的 JSON 对象应代表一个完整且自洽的短故事或重要的叙事片段。
在切割时，请优先考虑自然的故事转折点、场景变化、人物进场离场或主题切换，确保每个故事都有清晰的开始、发展和结束。避免在故事高潮或关键信息传递中途进行切割。
单个故事的英文翻译总字数应严格控制在 160 到 200 字之间，目标约为 180 字。如果一个自然的故事单元略超出此范围（例如达到 220 字），但在不破坏叙事连贯性的前提下无法合理拆分，则以故事完整性为先；反之，若可以合理拆分，则应进行拆分。
地道的本土化翻译 (Authentic Localization & Adaptation):
将原始文本翻译成简洁、生动、地道的英文。翻译风格必须完全符合美国本土文化、日常表达习惯和视频的目标受众。
不必拘泥于原文的字面意思。在必要时，请进行大胆的意译、改写、润色，甚至重新组织句子结构，以确保翻译内容不仅流畅自然，而且能更好地契合视频的叙事风格、情感表达和幽默感。最重要的是让它听起来像一个美国人在讲故事，而不是直译。
人名、地名、流行语、俚语、文化梗和度量单位等应进行彻底的本地化处理，使其对美国观众而言更具亲和力、理解度和共鸣。
对话合并与优化 (Dialogue Merging & Optimization):
将原始输入的时间连续的小片段（index）智能地合并为逻辑上更长的对话单元 (dialogue 数组中的单个 english 字段)。
合并的目标是为了提高阅读流畅度并服务于每个故事约 180 字的字数控制。合并时无需强求固定数量的 index（例如“大约 5 个 index”不再是硬性要求），而是以形成完整语义的对话、表达一个完整观点或描述一个完整动作的最小单元为准。
dialogue 字段中的 source_indices 数组必须准确引用所有合并进该对话单元的原始 index（重要！保持原始 index 不变）。
吸引力强劲的标题 (Catchy & Engaging Title Generation):
为每个故事生成一个吸引力强、能够概括故事核心内容和亮点的标题 (story_title)。标题应具有传播性，激发观看欲望。
标题应包含原作相关标签（例如 #simpsons, #memorablemoment, #wtfmoments 等，请根据具体内容判断，添加 1-2 个最相关的标签），且总长度不超过 90 个字符。
输入格式：
用户输入是一个包含 index 字段的 JSON 数组（类似 SRT 格式）。
输出格式示例：
[
 {
    "story_title": "Bart's Epic Fail Becomes Victory #simpsons #unexpectedwin",
    "start_index": 1,
    "end_index": 25,
    "dialogue": [
      {
        "english": "So Bart, in his usual fashion, decided to try this absolutely wild stunt, right? Like, a skateboard jump over Principal Skinner's car. What could possibly go wrong?",
        "source_indices": [1, 2, 3, 4]
      },
      {
        "english": "Well, everything, apparently! He totally biffed it, crashed straight into the school's new flagpole, bending it into a pretzel. Skinner was fuming, you could just tell.",
        "source_indices": [5, 6, 7]
      },
      {
        "english": "But here's the kicker: the bent flagpole accidentally pointed directly at a hidden treasure chest buried years ago during a school fair! Bart, the accidental hero, saved the day, even got a medal. Classic Springfield.",
        "source_indices": [8, 9, 10, 11]
      }
    ]
  }
]
"""

ai_analysis_dir = "./output/ai_analysis/"
if not os.path.exists(ai_analysis_dir):
    os.makedirs(ai_analysis_dir)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

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
        self.srt_generator = JSONSubtitleGenerator(output_dir="./output")

        # 初始化草稿生成器
        self.draft_generator = DraftGenerator()

        # 初始化视频导出器
        self.video_exporter = VideoExporter()

    def generate(self, url: str) -> Optional[VideoProject]:
        logging.info(f"🎬 开始处理视频URL: {url}")

        try:
            # 第一步：下载视频和切割
            logging.info("📥 第一步：下载并切割视频...")
            video_segments_data = self.video_downloader.process_video(url)
            if not video_segments_data:
                logging.info("❌ 视频下载失败")
                return None

            # 创建视频项目对象
            video_project = VideoProject(url)

            # 第二步：为每个视频段生成SRT文件
            logging.info(f"🎵 第二步：为 {len(video_segments_data)} 个视频段生成SRT文件...")
            for i, segment_data in enumerate(video_segments_data):
                logging.info(f"\n处理视频段 {i+1}/{len(video_segments_data)}")

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
                srt_file_path, sotry_num = self.generate_srt_for_segment(video_segment)
                if srt_file_path:
                    video_segment.srt_file_path = srt_file_path

                    # 第三步：分析SRT文件生成故事
                    logging.info(f"📖 第三步：分析SRT文件生成故事...")
                    stories = self.ai_analysis_story(srt_file_path, sotry_num)
                    if stories:
                        video_segment.stories = stories

                        # 第四步：为每个故事生成语音和草稿
                        logging.info(f"🎤 第四步：为 {len(stories)} 个故事生成语音和草稿...")
                        for story_idx, story in enumerate(stories):
                            self.process_story_for_segment(story, story_idx, video_segment)

                            # 处理完每个故事后立即更新缓存
                            self.save_project_to_cache(video_project)

                video_project.add_segment(video_segment)

            # 保存最终项目结果
            cache_file = self.save_project_to_cache(video_project)

            logging.info(f"✅ 视频处理完成！共处理 {len(video_project.segments)} 个视频段")
            return video_project

        except Exception as e:
            logging.info(f"❌ 处理失败: {e}")
            import traceback
            traceback.logging.info_exc()
            return None

    def generate_srt_for_segment(self, video_segment: VideoSegment):
        """为视频段生成SRT文件"""
        try:
            logging.info(f"🎵 为视频段 {video_segment.segment_index} 生成SRT文件...")

            
            # 使用音频文件路径生成SRT
            srt_file_path , story_num = self.srt_generator.transcribe(video_segment.org_audio_file_path)

            if srt_file_path and os.path.exists(srt_file_path):
                logging.info(f"✅ SRT文件生成成功: {srt_file_path}")
                return srt_file_path, story_num
            else:
                logging.info(f"❌ SRT文件生成失败")
                return None

        except Exception as e:
            logging.info(f"❌ SRT文件生成异常: {e}")
            return None

    def process_story_for_segment(self, story: StoryContent, story_idx: int, video_segment: VideoSegment):
        video_id = video_segment.url.split("/")[-1].split("?")[0]
        """为视频段中的故事生成语音和草稿"""
        try:
            logging.info(f"🎤 处理视频段 {video_id}:{video_segment.segment_index} 的故事 {story_idx + 1}: {story.story_title}")

            # 创建输出目录
            base_filename = f"{video_id}_segment_{video_segment.segment_index}"
            output_dir = f"./output/tmp_voice/{base_filename}"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            # 生成语音
            processed_story = self.process_single_story_audio(story, story_idx, output_dir)

            # 生成草稿文件
            draft_file = self.generate_draft_file(processed_story, story_idx, video_segment.org_video_file_path, video_id)

            # 导出草稿为视频
            if draft_file:
                exported_video_path = self.export_draft_video(draft_file)
                if exported_video_path:
                    # 保存导出视频路径到 story 对象
                    processed_story.exported_video_path = exported_video_path

            logging.info(f"✅ 故事处理完成: {story.story_title}")

        except Exception as e:
            logging.info(f"❌ 故事处理失败: {e}")

    def save_project_to_cache(self, video_project: VideoProject) -> str:
        """保存视频项目到缓存文件"""
        try:
            # 生成缓存文件路径
            url_safe = video_project.url.split("/")[-1].split("?")[0]
            cache_file = f"{PROJECT_CACHE_DIR}/{url_safe}_{int(video_project.project_created_time.timestamp())}.json"

            # 保存到文件
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(video_project.to_dict(), f, ensure_ascii=False, indent=2)

            logging.info(f"💾 项目已缓存到: {cache_file}")
            return cache_file

        except Exception as e:
            logging.info(f"❌ 项目缓存失败: {e}")
            return None

    def ai_analysis_story(self, srt_file, story_num: int) -> List[StoryContent]:
        """
        AI分析故事方法 - 先检查缓存，没有缓存则调用AI生成
        """
        # 生成缓存文件路径
        base_filename = os.path.splitext(os.path.basename(srt_file))[0]
        cache_file = os.path.join(ai_analysis_dir, f"{base_filename}.json")

        # 1. 先检查缓存文件是否存在
        if os.path.exists(cache_file):
            logging.info(f"💾 发现缓存文件，加载中: {cache_file}")
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    analysis_result = f.read()

                # 解析并返回对象
                stories = self.parse_analysis_result_obj(analysis_result, srt_file)
                if stories:
                    logging.info(f"✅ 从缓存加载了 {len(stories)} 个故事")
                    return stories
                else:
                    logging.info("⚠️ 缓存文件损坏，将重新生成")
            except Exception as e:
                logging.info(f"⚠️ 缓存文件读取失败: {e}，将重新生成")

        # 2. 没有缓存或缓存损坏，调用AI生成
        logging.info("🤖 正在调用AI分析...")

        # 加载srt文件
        with open(srt_file, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
            # 🔑 保留 time 字段，但为AI输入创建一个简化版本（只保留 index 和 text）
            ai_input_data = []
            for item in data:
                ai_input_data.append({
                    'index': item['index'],
                    'text': item['text']
                })
        input_date = json.dumps(ai_input_data)

        text = f"生成故事片段为: {story_num} 个 \n {input_date}"

        # 调用AI分析
        analysis_result = self.client.analyze_text(text, sys_prompt)

        if not analysis_result:
            logging.info("❌ AI分析返回空结果")
            return []

        # 清理结果格式
        if analysis_result.startswith('`'):
            analysis_result = analysis_result.replace('`', '').replace('json', '')

        # 3. 缓存AI分析结果
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(analysis_result)
            logging.info(f"💾 AI分析结果已缓存到: {cache_file}")
        except Exception as e:
            logging.info(f"⚠️ 缓存失败: {e}")

        # 4. 解析并返回对象
        stories = self.parse_analysis_result_obj(analysis_result,srt_file)
        if stories:
            logging.info(f"✅ AI分析完成，获取到 {len(stories)} 个故事")
        else:
            logging.info("❌ AI分析结果解析失败")

        return stories

    def parse_analysis_result_obj(self, analysis_result: str, srt_file: str) -> List[StoryContent]:
        """解析AI分析结果为对象 - 支持 source_indices 格式"""
        try:
            # 1. 加载 SRT JSON 创建索引映射
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_data = json.load(f)

            # 创建 index → srt_item 的映射
            srt_map = {item['index']: item for item in srt_data}
            logging.info(f"📖 加载了 {len(srt_map)} 条 SRT 记录")

            # 2. 清理可能的markdown格式
            clean_result = analysis_result.strip()
            if clean_result.startswith('json'):
                clean_result = clean_result[4:].strip()
            if clean_result.startswith('```'):
                clean_result = clean_result.replace('```', '')

            # 3. 解析JSON
            stories_data = json.loads(clean_result)

            # 4. 转换为对象
            stories = []
            for story_data in stories_data:
                # 处理每个 dialogue
                dialogue_list = []
                for idx, dialogue_data in enumerate(story_data['dialogue']):
                    # 🔑 根据 source_indices 还原 video_segments
                    video_segments = []
                    source_indices = dialogue_data.get('source_indices', [])

                    if source_indices:
                        # 新格式：使用 source_indices
                        logging.info(f"  🔗 处理 dialogue {idx}，source_indices: {source_indices}")
                        for srt_idx in source_indices:
                            if srt_idx in srt_map:
                                time_str = srt_map[srt_idx]['time']  # "00:00:00,000 --> 00:00:02,000"
                                if ' --> ' in time_str:
                                    start, end = time_str.split(' --> ')
                                    video_segments.append({
                                        'start': start.strip(),
                                        'end': end.strip()
                                    })
                                else:
                                    logging.warning(f"  ⚠️ SRT index {srt_idx} 时间格式异常: {time_str}")
                            else:
                                logging.warning(f"  ⚠️ SRT index {srt_idx} 不存在")
                    else:
                        # 兼容旧格式：使用 start/end 字段
                        if 'start' in dialogue_data and 'end' in dialogue_data:
                            logging.info(f"  📌 使用旧格式 start/end")
                            video_segments.append({
                                'start': dialogue_data['start'],
                                'end': dialogue_data['end']
                            })
                        else:
                            logging.warning(f"  ⚠️ dialogue {idx} 缺少 source_indices 和 start/end")

                    # 创建 dialogue 字典（用于 StoryContent 初始化）
                    dialogue_dict = {
                        'index': idx,
                        'video_segments': video_segments,
                        'chinese': dialogue_data.get('chinese', ''),
                        'english': dialogue_data.get('english', 'God bless you')
                    }
                    dialogue_list.append(dialogue_dict)

                # 创建 StoryContent（会自动转换为 StoryDialogue 对象）
                story = StoryContent(
                    story_title=story_data['story_title'],
                    start_index=story_data.get('start_index', 0),
                    end_index=story_data.get('end_index', 0),
                    dialogue=dialogue_list
                )
                stories.append(story)

            logging.info(f"✅ 成功解析 {len(stories)} 个故事")
            return stories

        except Exception as e:
            logging.error(f"❌ 解析对象失败: {e}")
            import traceback
            traceback.print_exc()
            return []

    def process_single_story_audio(self, story: StoryContent, story_idx: int, output_dir: str) -> StoryContent:
        """为单个故事生成语音 - 带缓存逻辑"""
        logging.info(f"🎵 开始为故事生成语音: {story.story_title}")

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
                    logging.info(f"  💾 发现缓存音频: {audio_filename}")

                    # 检查文件大小是否正常（大于1KB）
                    if os.path.getsize(audio_path) > 1024:
                        # 更新对象中的路径信息
                        dialogue.audio_path = audio_path

                        # 检查字幕文件是否存在
                        if os.path.exists(srt_path):
                            dialogue.srt_path = srt_path
                        else:
                            dialogue.srt_path = None

                        logging.info(f"  ✅ 使用缓存音频: {audio_filename}")
                        continue
                    else:
                        logging.info(f"  ⚠️ 缓存文件损坏（太小），将重新生成")
                        # 删除损坏的文件
                        try:
                            os.remove(audio_path)
                        except:
                            pass

                # 2. 生成新的语音文件
                logging.info(f"  🎤 生成对话 {dialogue.index}: {dialogue.english[:50]}...")

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

                    logging.info(f"  ✅ 语音生成完成: {audio_filename}")
                else:
                    logging.info(f"  ❌ 语音文件生成异常")
                    dialogue.audio_path = None
                    dialogue.srt_path = None

            except Exception as e:
                logging.info(f"  ❌ 生成语音失败: {e}")
                dialogue.audio_path = None
                dialogue.srt_path = None

        logging.info(f"✅ 故事 '{story.story_title}' 语音处理完成!")
        return story

    def generate_draft_file(self, story: 'StoryContent', story_idx: int, video_path: str = None, video_id: str = None) -> str:
        """为单个故事生成草稿文件"""
        try:
            logging.info(f"📝 开始为故事生成草稿: {story.story_title}")

            # 使用 DraftGenerator 的 generate_from_story 方法
            if not os.path.exists(video_path):
                logging.info(f"❌ 视频文件不存在: {video_path}")
                return None
            
            draft_file = self.draft_generator.generate_from_story(
                story=story,
                video_path=video_path,
                story_idx=story_idx,
                video_id=video_id
            )

            logging.info(f"✅ 草稿文件生成完成: {draft_file}")
            return draft_file

        except Exception as e:
            logging.info(f"❌ 生成草稿文件失败: {e}")
            import traceback
            traceback.logging.info_exc()
            return None

    def export_draft_video(self, draft_file: str) -> Optional[str]:
        """导出草稿为视频"""
        try:
            # 获取草稿的绝对路径
            draft_abs_path = os.path.abspath(draft_file)
            draft_floder = os.path.dirname(draft_abs_path)
            logging.info(f"📹 开始导出草稿: {draft_floder}")

            # 调用导出方法
            exported_video_path = self.video_exporter.export_video(draft_floder)

            if exported_video_path:
                logging.info(f"✅ 视频导出成功: {exported_video_path}")
                return exported_video_path
            else:
                logging.info(f"❌ 视频导出失败")
                return None

        except Exception as e:
            logging.info(f"❌ 导出视频异常: {e}")
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

            logging.info(f"💾 结果已缓存到: {cache_file}")
            return cache_file

        except Exception as e:
            logging.info(f"❌ 缓存失败: {e}")
            return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.info("Usage: python short_story_generator.py <video_url> [max_duration_minutes] [output_dir]")
        logging.info("Example: python short_story_generator.py 'https://www.bilibili.com/video/BV1abc123def' 10 './output/org_materials'")
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
        logging.info(f"\n🎉 处理完成！项目包含 {len(result.segments)} 个视频段")
        for i, segment in enumerate(result.segments, 1):
            logging.info(f"段 {i}: {len(segment.stories)} 个故事，SRT文件: {segment.srt_file_path}")
    else:
        logging.info("❌ 处理失败")
        sys.exit(1)

