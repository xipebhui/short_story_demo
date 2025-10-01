#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
视频环形分配器 - 将视频文件按环形窗口分配到目录中
支持多个独立的环形系统
"""

import os
import json
import shutil
import logging
import argparse
from typing import List, Dict
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# 状态文件路径
STATE_FILE = "./output/video_rotator_state.json"

# 基础目录
BASE_DIR = r'D:\qiyuan\素材'


class VideoRotator:
    """视频环形分配器 - 支持多个独立环形系统"""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.states = self._load_states()

    def _load_states(self) -> Dict:
        """加载所有环形系统的状态"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    states = json.load(f)
                logger.info(f"📂 加载状态文件: {self.state_file}")
                logger.info(f"   共有 {len(states)} 个环形系统")
                return states
            except Exception as e:
                logger.error(f"❌ 加载状态文件失败: {e}")
                return {}
        return {}

    def _save_states(self):
        """保存所有环形系统的状态"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)

            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.states, f, ensure_ascii=False, indent=2)
            logger.info(f"💾 状态已保存到: {self.state_file}")
        except Exception as e:
            logger.error(f"❌ 保存状态文件失败: {e}")

    def build_mapping(self, video_dir: str, target_start: int, target_end: int,
                     base_dir: str = BASE_DIR) -> Dict:
        """
        构建视频到目录的映射关系

        Args:
            video_dir: 视频文件所在目录
            target_start: 目标目录起始编号
            target_end: 目标目录结束编号
            base_dir: 目标目录的基础路径

        Returns:
            Dict: 映射关系
        """
        # 环形名称 = 视频目录的 basename
        ring_name = os.path.basename(video_dir.rstrip(os.sep))

        logger.info(f"\n🔧 开始构建环形系统: {ring_name}")
        logger.info(f"视频目录: {video_dir}")
        logger.info(f"目标范围: {target_start} - {target_end}")

        # 获取所有视频文件
        video_files = []
        if os.path.exists(video_dir):
            for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                video_files.extend(Path(video_dir).glob(ext))
        else:
            logger.error(f"❌ 视频目录不存在: {video_dir}")
            return {}

        video_files = sorted([str(f) for f in video_files])

        if not video_files:
            logger.error(f"❌ 在 {video_dir} 中没有找到视频文件")
            return {}

        logger.info(f"找到 {len(video_files)} 个视频文件")

        # 生成目标目录列表: 老号1-1, 老号1-2, ..., 老号1-50
        target_dirs = []
        for i in range(target_start, target_end + 1):
            # 从视频目录名中提取号码前缀 (例如 "老号1" 从 "老号1视频目录")
            # 简化处理: 直接使用 ring_name 作为前缀
            dir_name = f"{ring_name}-{i}"
            dir_path = os.path.join(base_dir, dir_name)
            target_dirs.append(dir_path)

        logger.info(f"生成 {len(target_dirs)} 个目标目录")
        logger.info(f"  示例: {os.path.basename(target_dirs[0])} ~ {os.path.basename(target_dirs[-1])}")

        num_videos = len(video_files)
        num_dirs = len(target_dirs)

        # 计算每个视频对应的目录数量（窗口大小）
        window_size = num_dirs // num_videos if num_videos > 0 else 0

        logger.info(f"\n📊 环形窗口配置:")
        logger.info(f"  视频数量: {num_videos}")
        logger.info(f"  目录数量: {num_dirs}")
        logger.info(f"  窗口大小: {window_size} (每个视频对应 {window_size} 个目录)")
        logger.info(f"  最大旋转次数: {num_videos}")

        # 构建映射关系
        mapping = {
            "ring_name": ring_name,
            "video_dir": video_dir,
            "videos": video_files,
            "base_dir": base_dir,
            "target_start": target_start,
            "target_end": target_end,
            "target_dirs": target_dirs,
            "window_size": window_size,
            "current_offset": 0,
            "max_rotations": num_videos,
            "rotation_count": 0
        }

        # 保存到 states 字典中
        self.states[ring_name] = mapping
        self._save_states()

        logger.info(f"\n✅ 环形系统 '{ring_name}' 构建完成！")
        self._print_current_mapping(ring_name)

        return mapping

    def _print_current_mapping(self, ring_name: str):
        """打印当前环形系统的映射关系"""
        if ring_name not in self.states:
            logger.warning(f"⚠️ 环形系统 '{ring_name}' 不存在")
            return

        state = self.states[ring_name]
        videos = state.get('videos', [])
        target_dirs = state.get('target_dirs', [])
        window_size = state.get('window_size', 0)
        offset = state.get('current_offset', 0)
        rotation_count = state.get('rotation_count', 0)
        max_rotations = state.get('max_rotations', 0)

        logger.info(f"\n📍 环形系统 '{ring_name}' 当前映射 (旋转: {rotation_count}/{max_rotations}):")

        for i, video in enumerate(videos):
            video_name = os.path.basename(video)
            # 计算当前视频对应的目录索引（考虑偏移）
            start_idx = (i * window_size + offset) % len(target_dirs)

            assigned_dirs = []
            for j in range(window_size):
                dir_idx = (start_idx + j) % len(target_dirs)
                assigned_dirs.append(os.path.basename(target_dirs[dir_idx]))

            logger.info(f"  视频 {i+1}: {video_name}")
            logger.info(f"    → {', '.join(assigned_dirs)}")

    def rotate(self, ring_name: str) -> bool:
        """
        旋转指定环形系统的窗口 +1，清空目录并移动新视频

        Args:
            ring_name: 环形系统名称

        Returns:
            bool: 是否成功旋转
        """
        if ring_name not in self.states:
            logger.error(f"❌ 环形系统 '{ring_name}' 不存在，请先运行 build")
            return False

        state = self.states[ring_name]
        rotation_count = state.get('rotation_count', 0)
        max_rotations = state.get('max_rotations', 0)

        if rotation_count >= max_rotations:
            logger.warning(f"⚠️ 环形系统 '{ring_name}' 已达到最大旋转次数 ({max_rotations})")
            logger.warning(f"   所有目录都已存储过所有视频")
            return False

        logger.info(f"\n🔄 旋转环形系统 '{ring_name}' (第 {rotation_count + 1}/{max_rotations} 次)...")

        videos = state['videos']
        target_dirs = state['target_dirs']
        window_size = state['window_size']
        current_offset = state['current_offset']

        # 1. 清空所有目标目录
        logger.info("\n🧹 清空目标目录...")
        for target_dir in target_dirs:
            if os.path.exists(target_dir):
                # 只删除视频文件，保留目录结构
                for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                    for file in Path(target_dir).glob(ext):
                        try:
                            os.remove(file)
                            logger.info(f"  删除: {file}")
                        except Exception as e:
                            logger.error(f"  ❌ 删除失败 {file}: {e}")
            else:
                # 创建目录
                os.makedirs(target_dir, exist_ok=True)
                logger.info(f"  创建目录: {target_dir}")

        # 2. 旋转偏移 +1
        new_offset = (current_offset + 1) % len(target_dirs)

        logger.info(f"\n📦 复制视频到新位置 (偏移: {current_offset} → {new_offset})...")

        # 3. 根据新的偏移复制视频
        for i, video in enumerate(videos):
            if not os.path.exists(video):
                logger.warning(f"⚠️ 视频不存在: {video}")
                continue

            video_name = os.path.basename(video)

            # 计算当前视频对应的目录索引
            start_idx = (i * window_size + new_offset) % len(target_dirs)

            # 复制到对应的目录
            for j in range(window_size):
                dir_idx = (start_idx + j) % len(target_dirs)
                target_dir = target_dirs[dir_idx]
                target_path = os.path.join(target_dir, video_name)

                try:
                    shutil.copy2(video, target_path)
                    logger.info(f"  ✓ {video_name} → {os.path.basename(target_dir)}/")
                except Exception as e:
                    logger.error(f"  ❌ 复制失败 {video_name} → {target_dir}: {e}")

        # 4. 更新状态
        state['current_offset'] = new_offset
        state['rotation_count'] = rotation_count + 1
        self.states[ring_name] = state
        self._save_states()

        logger.info(f"\n✅ 旋转完成！")
        self._print_current_mapping(ring_name)

        return True

    def get_status(self, ring_name: str = None) -> Dict:
        """获取环形系统的状态

        Args:
            ring_name: 环形系统名称，如果为 None 则返回所有环形系统的状态

        Returns:
            Dict: 状态信息
        """
        if ring_name:
            # 返回指定环形系统的状态
            if ring_name not in self.states:
                return {
                    "initialized": False,
                    "message": f"环形系统 '{ring_name}' 不存在"
                }

            state = self.states[ring_name]
            return {
                "initialized": True,
                "ring_name": ring_name,
                "video_count": len(state.get('videos', [])),
                "dir_count": len(state.get('target_dirs', [])),
                "window_size": state.get('window_size', 0),
                "rotation_count": state.get('rotation_count', 0),
                "max_rotations": state.get('max_rotations', 0),
                "can_rotate": state.get('rotation_count', 0) < state.get('max_rotations', 0)
            }
        else:
            # 返回所有环形系统的状态
            if not self.states:
                return {
                    "initialized": False,
                    "message": "没有任何环形系统，请先运行 build"
                }

            all_status = {}
            for name, state in self.states.items():
                all_status[name] = {
                    "video_count": len(state.get('videos', [])),
                    "dir_count": len(state.get('target_dirs', [])),
                    "window_size": state.get('window_size', 0),
                    "rotation_count": state.get('rotation_count', 0),
                    "max_rotations": state.get('max_rotations', 0),
                    "can_rotate": state.get('rotation_count', 0) < state.get('max_rotations', 0)
                }
            return {
                "initialized": True,
                "ring_count": len(self.states),
                "rings": all_status
            }

    def list_rings(self) -> List[str]:
        """列出所有环形系统的名称

        Returns:
            List[str]: 环形系统名称列表
        """
        return list(self.states.keys())


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(description="视频环形分配器 - 管理多个独立的环形系统")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # build 命令
    build_parser = subparsers.add_parser('build', help='构建环形映射关系')
    build_parser.add_argument('--video_dir', required=True, help='视频文件所在目录')
    build_parser.add_argument('--target-start', type=int, required=True, help='目标目录起始编号')
    build_parser.add_argument('--target-end', type=int, required=True, help='目标目录结束编号')
    build_parser.add_argument('--base-dir', default=BASE_DIR, help=f'目标目录的基础路径 (默认: {BASE_DIR})')

    # rotate 命令
    rotate_parser = subparsers.add_parser('rotate', help='旋转指定环形系统的视频')
    rotate_parser.add_argument('--name', required=True, help='环形系统名称')

    # status 命令
    status_parser = subparsers.add_parser('status', help='查看环形系统状态')
    status_parser.add_argument('--name', help='环形系统名称 (可选，不指定则显示所有)')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有环形系统')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    rotator = VideoRotator()

    if args.command == 'build':
        logger.info(f"\n🔧 构建环形系统")
        logger.info(f"  视频目录: {args.video_dir}")
        logger.info(f"  目标范围: {args.target_start} - {args.target_end}")
        logger.info(f"  基础目录: {args.base_dir}")

        rotator.build_mapping(
            video_dir=args.video_dir,
            target_start=args.target_start,
            target_end=args.target_end,
            base_dir=args.base_dir
        )

    elif args.command == 'rotate':
        success = rotator.rotate(args.name)
        if not success:
            logger.error(f"❌ 旋转失败")
            exit(1)

    elif args.command == 'status':
        status = rotator.get_status(args.name)

        if not status.get('initialized', False):
            logger.warning(f"⚠️ {status.get('message', '未知错误')}")
            return

        if args.name:
            # 显示指定环形系统的状态
            logger.info(f"\n📊 环形系统 '{args.name}' 状态:")
            logger.info(f"  视频数量: {status['video_count']}")
            logger.info(f"  目录数量: {status['dir_count']}")
            logger.info(f"  窗口大小: {status['window_size']}")
            logger.info(f"  旋转次数: {status['rotation_count']}/{status['max_rotations']}")
            logger.info(f"  可旋转: {'是' if status['can_rotate'] else '否'}")
        else:
            # 显示所有环形系统的状态
            logger.info(f"\n📊 所有环形系统状态 (共 {status['ring_count']} 个):")
            for ring_name, ring_status in status['rings'].items():
                logger.info(f"\n  环形系统: {ring_name}")
                logger.info(f"    视频数量: {ring_status['video_count']}")
                logger.info(f"    目录数量: {ring_status['dir_count']}")
                logger.info(f"    窗口大小: {ring_status['window_size']}")
                logger.info(f"    旋转次数: {ring_status['rotation_count']}/{ring_status['max_rotations']}")
                logger.info(f"    可旋转: {'是' if ring_status['can_rotate'] else '否'}")

    elif args.command == 'list':
        rings = rotator.list_rings()
        if not rings:
            logger.info("📭 没有任何环形系统")
        else:
            logger.info(f"\n📋 所有环形系统 (共 {len(rings)} 个):")
            for i, ring_name in enumerate(rings, 1):
                logger.info(f"  {i}. {ring_name}")


if __name__ == "__main__":
    main()
