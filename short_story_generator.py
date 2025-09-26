

from newapi_client import GeminiClient
from tts_client_new import TTSClient
import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Optional


sys_prompt = """
用户输入的是一个 srt 文件，最高指令是 srt 中的时间戳信息是不能变化的 。 
根据故事情节对这个文案进行切割，要求切割的故事是合理的，不能很突兀的就结束，输出切割后的每个故事，
拆分的时间可以稍微长一点，首先是保证故事完整，其次时间控制在 1min 到 2min 以内 ，
然后对一个故事的时间戳做判断，然后对每句话进行翻译，不需要完全遵守原文，
可以结合美国文化进行一些翻译，要求要符合场景。 输出的格式为 纯 json 格式，不要有任何其他内容。
示例格式

[
  {
    "story_title": "巴特的靈感與大師的指點 (Bart's Inspiration and the Master's Advice)",
    "start_time": "00:00:00,000",
    "end_time": "01:02:539",
    "dialogue": [
      {
        "index": 0,
        "timestamp": "00:00:00,000 --> 00:00:02,359",
        "chinese": "心動漫威命狗在春田鎮大火後",
        "english": "After the massive Marvel-themed fire in Springfield, the kids got into drawing."
      }
    ]
  }
]
"""

class StoryAnalysisResult:
    """故事分析结果对象"""
    
    def __init__(self, stories_data: List[Dict], source_file: str):
        self.stories_data = stories_data
        self.source_file = source_file
        self.timestamp = datetime.now().isoformat()
        self.audio_path = None
        self.subtitle_path = None
        self.output_dir = "output/tmp"
        
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)
    
    def extract_english_text(self) -> str:
        """提取所有英文对话文本"""
        all_text = []
        for story in self.stories_data:
            if 'dialogue' in story:
                for dialogue in story['dialogue']:
                    if 'english' in dialogue:
                        all_text.append(dialogue['english'])
        return " ".join(all_text)
    
    def generate_audio(self, tts_client: TTSClient, voice: str = "en-US-BrianNeural") -> bool:
        """生成音频文件"""
        english_text = self.extract_english_text()
        if not english_text:
            print("⚠️ No English text found for audio generation")
            return False
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_filename = f"story_audio_{timestamp}.mp3"
        self.audio_path = os.path.join(self.output_dir, audio_filename)
        
        try:
            # 使用TTS生成音频
            subtitle_file = tts_client.generate_and_save_audio(
                english_text,
                self.audio_path,
                voice=voice
            )
            
            if subtitle_file:
                self.subtitle_path = subtitle_file
                print(f"✅ Audio saved to {self.audio_path}")
                print(f"✅ Subtitle saved to {subtitle_file}")
            else:
                print(f"✅ Audio saved to {self.audio_path}")
                
            return True
            
        except Exception as e:
            print(f"❌ Audio generation failed: {e}")
            return False
    
    def save_to_json(self) -> str:
        """保存对象为JSON文件"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"story_analysis_{timestamp}.json"
        json_path = os.path.join(self.output_dir, json_filename)
        
        # 构建要保存的数据
        save_data = {
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "audio_path": self.audio_path,
            "subtitle_path": self.subtitle_path,
            "stories_count": len(self.stories_data),
            "stories_data": self.stories_data,
            "english_text_preview": self.extract_english_text()[:200] + "..." if len(self.extract_english_text()) > 200 else self.extract_english_text()
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Analysis result saved to {json_path}")
        return json_path
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            "timestamp": self.timestamp,
            "source_file": self.source_file,
            "audio_path": self.audio_path,
            "subtitle_path": self.subtitle_path,
            "stories_count": len(self.stories_data),
            "stories_data": self.stories_data
        }

class ShortStoryGenerator:
    def __init__(self):
        self.client = GeminiClient()
        self.tts_client = TTSClient()

    def generate(self, srt_file) -> Optional[StoryAnalysisResult]:
        print(f"📖 开始处理文件: {srt_file}")
        
        # 加载srt文件
        with open(srt_file, "r", encoding="utf-8") as f:
            text = f.read()
        
        # 获取分析结果
        print("🤖 正在调用AI分析...")
        analysis_result = self.client.analyze_text(text, sys_prompt)
        
        if not analysis_result:
            print("❌ API返回空结果")
            return None
            
        try:
            # 尝试解析JSON字符串
            if isinstance(analysis_result, str):
                parsed_result = json.loads(analysis_result)
            else:
                parsed_result = analysis_result
            
            # 验证解析结果格式
            if not isinstance(parsed_result, list):
                print("❌ 解析结果格式错误，期望列表格式")
                return None
                
            print(f"✅ AI分析完成，共解析出 {len(parsed_result)} 个故事")
            
            # 创建结果对象
            result = StoryAnalysisResult(parsed_result, srt_file)
            
            # 生成音频文件
            print("🎵 正在生成音频...")
            if result.generate_audio(self.tts_client):
                print("✅ 音频生成成功")
            else:
                print("⚠️ 音频生成失败或跳过")
            
            # 保存结果对象为JSON
            print("💾 正在保存结果...")
            json_path = result.save_to_json()
            
            print("🎉 处理完成！")
            print(f"📁 输出目录: {result.output_dir}")
            print(f"🎵 音频文件: {result.audio_path}")
            print(f"📝 字幕文件: {result.subtitle_path}")
            print(f"📄 结果文件: {json_path}")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON解析失败: {e}")
            print(f"原始返回内容: {analysis_result}")
            # 保存原始内容用于调试
            with open("analysis_raw.txt", "w", encoding="utf-8") as f:
                f.write(str(analysis_result))
            print("原始内容已保存到 analysis_raw.txt")
            return None
        except Exception as e:
            print(f"❌ 处理过程中发生错误: {e}")
            return None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python short_story_generator.py <srt_file>")
        sys.exit(1)
    
    srt_file = sys.argv[1]
    generator = ShortStoryGenerator()
    result = generator.generate(srt_file)
    
    if result:
        print(f"\n📊 处理结果摘要:")
        print(f"   故事数量: {len(result.stories_data)}")
        print(f"   英文文本长度: {len(result.extract_english_text())} 字符")
        print(f"   输出目录: {result.output_dir}")
    else:
        print("❌ 处理失败")
        sys.exit(1)