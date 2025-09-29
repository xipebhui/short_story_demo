#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的视频导出模块
只负责调用剪映导出API
"""

import os
import shutil
import requests
import logging
from typing import Optional

# 常量：导出视频的目标移动路径
EXPORT_VIDEO_TARGET_DIR = "./output/exported_videos"

# 配置日志格式，包含行号
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


class VideoExporter:
    """视频导出器类"""

    def __init__(self, export_url: Optional[str] = None, target_dir: str = EXPORT_VIDEO_TARGET_DIR):
        """
        初始化视频导出器

        Args:
            export_url: 导出服务URL，如果不提供则从环境变量读取
            target_dir: 导出视频的目标目录
        """
        self.export_url = export_url or os.getenv("EXPORT_VIDEO_URL", "http://localhost:51053")
        self.target_dir = target_dir
        self.logger = logging.getLogger(__name__)

        # 确保目标目录存在
        self._ensure_target_dir()
        self.logger.info(f"VideoExporter initialized with target directory: {self.target_dir}")

    def _ensure_target_dir(self):
        """确保目标目录存在"""
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir, exist_ok=True)
            self.logger.info(f"Created target directory: {self.target_dir}")

    def _move_video_to_target(self, source_path: str) -> str:
        """
        将导出的视频移动到目标目录

        Args:
            source_path: 源视频文件路径

        Returns:
            移动后的视频文件路径
        """
        if not os.path.exists(source_path):
            self.logger.error(f"源视频文件不存在: {source_path}")
            return source_path

        # 生成目标文件路径
        filename = os.path.basename(source_path)
        target_path = os.path.join(self.target_dir, filename)

        # 如果目标文件已存在，生成唯一文件名
        counter = 1
        base_name, ext = os.path.splitext(filename)
        while os.path.exists(target_path):
            new_filename = f"{base_name}_{counter}{ext}"
            target_path = os.path.join(self.target_dir, new_filename)
            counter += 1

        try:
            # 移动文件
            shutil.move(source_path, target_path)
            self.logger.info(f"视频文件已移动到: {target_path}")
            return target_path
        except Exception as e:
            self.logger.error(f"移动视频文件失败: {e}")
            return source_path

    def export_video(self, draft_name: str, draft_path: Optional[str] = None, move_to_target: bool = True) -> Optional[str]:
        """
        导出剪映草稿为视频

        Args:
            draft_name: 草稿文件夹名称
            draft_path: 草稿完整路径，如果提供则优先使用
            move_to_target: 是否将导出的视频移动到目标目录

        Returns:
            成功返回视频文件路径，失败返回None
        """
        # 构建完整的API地址
        api_endpoint = f"{self.export_url}/api/export_draft"

        # 准备请求数据
        request_data = {
            "draft_name": draft_name
        }

        # 如果提供了完整路径，添加到请求数据中
        if draft_path:
            request_data["draft_path"] = draft_path

        try:
            self.logger.info(f"正在导出草稿: {draft_name}")
            self.logger.info("注意：视频导出可能需要较长时间（最长30分钟），请耐心等待...")
            self.logger.debug(f"API地址: {api_endpoint}")

            # 发送请求
            response = requests.post(
                api_endpoint,
                json=request_data,
                timeout=3600  # 30分钟超时
            )

            # 处理响应
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    output_path = result.get("output_path")
                    self.logger.info(f"视频导出成功: {output_path}")

                    # 如果需要移动到目标目录
                    if move_to_target:
                        output_path = self._move_video_to_target(output_path)

                    return output_path
                else:
                    self.logger.error(f"导出失败: {result}")
                    return None
            else:
                # 错误响应
                try:
                    error_detail = response.json().get("detail", "Unknown error")
                except:
                    error_detail = f"HTTP {response.status_code}"
                self.logger.error(f"导出API返回错误: {error_detail}")
                return None

        except requests.exceptions.Timeout:
            self.logger.error("导出请求超时（30分钟）")
            return None
        except requests.exceptions.ConnectionError:
            self.logger.error(f"无法连接到导出服务: {api_endpoint}")
            return None
        except Exception as e:
            self.logger.error(f"导出过程中发生错误: {e}")
            return None

    def test_export_service(self) -> bool:
        """
        测试导出服务是否可用

        Returns:
            服务可用返回True，否则返回False
        """
        test_endpoint = f"{self.export_url}/api/test"

        try:
            self.logger.info(f"测试导出服务: {test_endpoint}")
            response = requests.get(test_endpoint, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "success":
                    self.logger.info("导出服务测试成功")
                    return True
        except Exception as e:
            self.logger.error(f"导出服务测试失败: {e}")

        self.logger.error("导出服务不可用")
        return False


if __name__ == "__main__":
    # 测试代码
    import sys

    if len(sys.argv) < 2:
        print("用法: python jy_export.py <draft_name> [target_dir]")
        print("示例: python jy_export.py 'my_draft' './custom_output'")
        sys.exit(1)

    draft_name = sys.argv[1]
    target_dir = sys.argv[2] if len(sys.argv) > 2 else EXPORT_VIDEO_TARGET_DIR

    # 创建视频导出器
    exporter = VideoExporter(target_dir=target_dir)

    # 测试服务
    if exporter.test_export_service():
        # 导出视频
        video_path = exporter.export_video(draft_name=draft_name)
        if video_path:
            print(f"[OK] 视频导出成功: {video_path}")
        else:
            print(f"[ERROR] 视频导出失败")
            sys.exit(1)
    else:
        print("[ERROR] 导出服务不可用")
        sys.exit(1)