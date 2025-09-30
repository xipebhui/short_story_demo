
from newapi_client import GeminiClient
from tts_client_new import TTSClient
from draft_gen import DraftGenerator
from dl_splitter_video import VideoDownloader
from srt_generate import JSONSubtitleGenerator
from data_models import StoryDialogue, StoryContent, VideoSegment, VideoProject
from jy_export import VideoExporter
from spliter_export_video import VideoSplitter
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import logging



PROJECT_CACHE_DIR = './output/project_cache'

sys_prompt = """
角色
你是一位顶级的 YouTube 故事解说频道（Recap Channel）的剧本作家。你擅长观看一段连续的画面（漫画、动画），然后用极具吸引力、节奏感十足的旁-白，把这个故事讲述给观众听。
核心思维
Index = 画面帧: index 序列就是你正在观看的无声影片。你的所有创作都必须围绕这些画面展开。
Text = 画面参考: 原始的中文 text 只是帮助你理解画面内容的辅助线索，它不是你需要翻译的原文。
你的任务 = 讲述故事: 你的工作是创作一段全新的英文旁白，引导观众理解并沉浸在这些连续画面所构成的故事中。
最高指令：声画同步 (Narration-to-Visual Sync)
这是你唯一且不可违背的铁律。你创作的每一句旁白，都必须与它所对应的画面序列（source_indices）在内容、节奏和情绪上完美契合。
工作流程
第一步：看懂故事 (Analyze the Visuals)
快速浏览全部的 index 和 text，在脑中构建出整个故事的视觉流程。理解故事的起因、转折和结局，推测故事来源，替换为欧美本土化的人物和地点。
第二步：创作旁白剧本 (Write the Narration)
忘记原始文本的束缚。用你自己的语言，构思一段引人入胜的英文旁白来讲述这个故事。
你可以自由地：
结构重组法
非线性叙事：把原本顺序 A→B→C 的剧情，调整为 C→A→B，制造悬念或反转。
倒叙/插叙：先告诉观众“结局”，再一步步解开谜团。
碎片化讲述：像在拼拼图一样，分散线索，让观众跟着你推理。
👉 例子：一部爱情故事，原版是“相遇→误会→分开→重逢”，你可以解说成“他们重逢了，但你绝对想不到，之前经历过什么”。
角色视角法
用不同角色的视角重构剧情。
“主角并不是故事的主角”：比如从配角/反派的角度解说，整个剧情会变得完全不同。
对比不同角色的欲望和矛盾，把故事变成立体冲突。
悬念制造
先抛问题，再解答：
“你能想象吗？这对恋人重逢的时候，竟然已经互相欺骗了三年。”
每隔一段给观众留“钩子”，比如：“可就在他们以为一切结束时，一个细节彻底改变了命运。”
大胆二次创作
魔改剧情：保持故事骨架，但加上你的解说风格，例如讽刺、搞笑、阴谋论式解读。
脑洞延伸：比如“如果结局不是这样，会怎样？”、“其实还有一个隐藏人物”。
用“旁白调侃”来增加娱乐性：
“这男主真是实力作死，换我早就凉透了。”
节奏控制
解说不要平铺直叙，要有快有慢。
快节奏：剧情高潮、冲突。
慢节奏：营造氛围、留悬念。
可以用“短句+停顿”增加张力。
例：
“他们相遇了。——可惜，只是表面上的。”
情绪渲染
语气要比故事本身“更夸张”一些。
根据剧情切换不同语气：紧张、冷静、讽刺、感慨。
你可以尝试给观众“代入感”，比如说：
“如果是你，你会怎么选？相信爱情，还是选择背叛？”
适合“剧情打乱”的特别技巧
反转叙事：先说“结局”，再解释为什么会这样。
错位解读：把后面的情节当成“前因”，把前面的情节当成“结果”。
平行时空解说：像在说“假如这是另一个世界”的版本。
第三步：同步旁白与画面 (Sync Script to Visuals)
将你创作好的旁白剧本，切分成一句句自然的句子。
将每一句旁白，精确地分配给它所描述的、最合适的画面序列（source_indices）。确保旁白的时长感和画面的时长感相匹配。
用户输入：
用户会输入故事的旁白和目标切割的故事个数
输出格式要求
最终输出必须是纯粹的、格式正确的JSON数组。绝对禁止包含任何解释性文字、注释或标题，输出格式标题标需要添加一个故事来源的标签 比如 辛普森一家 就是  #simpsons, 标题整体长度不超过 50 个字。
输出格式示例 (请严格遵守)
code
JSON
download
content_copy
expand_less
[
{
"story_title": "This Guy Faked a Miracle, and It Actually Worked?! #StoryRecap",
"start_index": 1,
"end_index": 25,
"dialogue": [
{
"chinese": 来认识一下麦克斯，一个如此迫切地想要拯救他垂死的小镇的人，他决定做一件不可思议的事情：假装一个奇迹
"english": "Meet Max, a man so desperate to save his dying town, he decided to do the unthinkable: fake a miracle.",
"source_indices": [ 1, 2, 3 ]
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

        # 初始化视频切割器
        self.video_splitter = VideoSplitter()

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

            # 切割导出的视频
            if cache_file:
                logging.info(f"✂️ 开始切割导出的视频...")
                self.video_splitter.process(cache_file)

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

