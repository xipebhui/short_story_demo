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

    def build_mapping(self, video_dir: str, target_start: str, target_end: str,
                     ring_name: str, base_dir: str = BASE_DIR) -> Dict:
        """
        构建视频到目录的映射关系

        Args:
            video_dir: 视频文件所在目录
            target_start: 目标目录起始名称 (例如: "老号1-1")
            target_end: 目标目录结束名称 (例如: "老号1-50")
            ring_name: 环形系统名称 (用户指定)
            base_dir: 目标目录的基础路径

        Returns:
            Dict: 映射关系
        """
        # 检查环形名称是否已存在
        if ring_name in self.states:
            logger.warning(f"⚠️ 环形系统 '{ring_name}' 已存在，将覆盖原有配置")

        # 解析 target_start 和 target_end
        # 例如: "老号1-1" -> prefix="老号1-", start_num=1
        if '-' not in target_start or '-' not in target_end:
            logger.error(f"❌ 目标目录格式错误，应为 '前缀-数字' 格式 (例如: 老号1-1)")
            return {}

        # 分割最后一个 '-' 来获取前缀和数字
        start_parts = target_start.rsplit('-', 1)
        end_parts = target_end.rsplit('-', 1)

        start_prefix = start_parts[0] + '-'
        end_prefix = end_parts[0] + '-'

        # 验证前缀一致
        if start_prefix != end_prefix:
            logger.error(f"❌ 起始和结束目录的前缀不一致: '{start_prefix}' != '{end_prefix}'")
            return {}

        prefix = start_prefix
        try:
            start_num = int(start_parts[1])
            end_num = int(end_parts[1])
        except ValueError:
            logger.error(f"❌ 无法解析目录编号: {target_start}, {target_end}")
            return {}

        if start_num > end_num:
            logger.error(f"❌ 起始编号 {start_num} 大于结束编号 {end_num}")
            return {}

        logger.info(f"\n🔧 开始构建环形系统: {ring_name}")
        logger.info(f"视频目录: {video_dir}")
        logger.info(f"目标前缀: {prefix}")
        logger.info(f"目标范围: {start_num} - {end_num}")

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
        for i in range(start_num, end_num + 1):
            dir_name = f"{prefix}{i}"
            dir_path = os.path.join(base_dir, dir_name)
            target_dirs.append(dir_path)

        logger.info(f"生成 {len(target_dirs)} 个目标目录路径")
        logger.info(f"  示例: {os.path.basename(target_dirs[0])} ~ {os.path.basename(target_dirs[-1])}")

        # 验证目标目录是否存在
        missing_dirs = [d for d in target_dirs if not os.path.exists(d)]
        if missing_dirs:
            logger.warning(f"⚠️ 警告: {len(missing_dirs)} 个目标目录不存在，将在旋转时创建")
            for d in missing_dirs[:3]:  # 只显示前3个
                logger.warning(f"  - {d}")
            if len(missing_dirs) > 3:
                logger.warning(f"  ... 还有 {len(missing_dirs) - 3} 个")

        num_videos = len(video_files)
        num_dirs = len(target_dirs)

        # 计算窗口大小和映射模式
        if num_videos <= num_dirs:
            # 模式1: 视频数 <= 目录数,每个视频对应多个目录
            window_size = num_dirs // num_videos if num_videos > 0 else 0
            videos_per_dir = 1
            mode = "video_to_dirs"
            max_rotations = num_videos  # 旋转次数 = 视频数
        else:
            # 模式2: 视频数 > 目录数,每个目录对应多个视频
            window_size = 1  # 每个视频只对应1个目录
            videos_per_dir = (num_videos + num_dirs - 1) // num_dirs  # 向上取整
            mode = "dir_to_videos"
            max_rotations = num_dirs  # 旋转次数 = 目录数

        logger.info(f"\n📊 环形窗口配置:")
        logger.info(f"  视频数量: {num_videos}")
        logger.info(f"  目录数量: {num_dirs}")
        if mode == "video_to_dirs":
            logger.info(f"  映射模式: 每个视频对应 {window_size} 个目录")
            logger.info(f"  最大旋转次数: {max_rotations} (旋转完所有视频)")
        else:
            logger.info(f"  映射模式: 每个目录对应约 {videos_per_dir} 个视频")
            logger.info(f"  最大旋转次数: {max_rotations} (旋转完所有目录)")

        # 构建映射关系
        mapping = {
            "ring_name": ring_name,
            "video_dir": video_dir,
            "videos": video_files,
            "base_dir": base_dir,
            "target_prefix": prefix,
            "target_start_num": start_num,
            "target_end_num": end_num,
            "target_start": target_start,
            "target_end": target_end,
            "target_dirs": target_dirs,
            "window_size": window_size,
            "videos_per_dir": videos_per_dir,
            "mode": mode,
            "current_offset": 0,
            "max_rotations": max_rotations,
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
        videos_per_dir = state.get('videos_per_dir', 1)
        mode = state.get('mode', 'video_to_dirs')
        offset = state.get('current_offset', 0)
        rotation_count = state.get('rotation_count', 0)
        max_rotations = state.get('max_rotations', 0)

        logger.info(f"\n📍 环形系统 '{ring_name}' 当前映射 (旋转: {rotation_count}/{max_rotations}):")
        logger.info(f"   模式: {mode}, 偏移: {offset}")

        if mode == "video_to_dirs":
            # 模式1: 每个视频对应多个目录
            # 只显示前5个视频的映射
            display_count = min(5, len(videos))
            for i in range(display_count):
                video = videos[i]
                video_name = os.path.basename(video)
                start_idx = (i * window_size + offset) % len(target_dirs)

                assigned_dirs = []
                for j in range(window_size):
                    dir_idx = (start_idx + j) % len(target_dirs)
                    assigned_dirs.append(os.path.basename(target_dirs[dir_idx]))

                logger.info(f"  视频 {i+1}: {video_name}")
                logger.info(f"    → {', '.join(assigned_dirs)}")

            if len(videos) > display_count:
                logger.info(f"  ... 还有 {len(videos) - display_count} 个视频")
        else:
            # 模式2: 每个目录对应多个视频
            # 只显示前5个目录的映射
            display_count = min(5, len(target_dirs))
            for i in range(display_count):
                dir_idx = (i + offset) % len(target_dirs)
                dir_name = os.path.basename(target_dirs[dir_idx])

                # 计算该目录对应的视频索引范围
                assigned_videos = []
                for j in range(videos_per_dir):
                    video_idx = (dir_idx + j * len(target_dirs)) % len(videos)
                    if video_idx < len(videos):
                        assigned_videos.append(os.path.basename(videos[video_idx]))

                logger.info(f"  目录 {i+1}: {dir_name}")
                logger.info(f"    → {', '.join(assigned_videos[:3])}")  # 只显示前3个视频
                if len(assigned_videos) > 3:
                    logger.info(f"       ... 还有 {len(assigned_videos) - 3} 个视频")

            if len(target_dirs) > display_count:
                logger.info(f"  ... 还有 {len(target_dirs) - display_count} 个目录")

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
        window_size = state.get('window_size', 1)
        videos_per_dir = state.get('videos_per_dir', 1)
        mode = state.get('mode', 'video_to_dirs')
        current_offset = state['current_offset']

        # 1. 清空所有目标目录
        logger.info("\n🧹 清空目标目录...")
        deleted_count = 0
        for target_dir in target_dirs:
            if os.path.exists(target_dir):
                # 只删除视频文件，保留目录结构
                for ext in ['*.mp4', '*.avi', '*.mov', '*.mkv']:
                    for file in Path(target_dir).glob(ext):
                        try:
                            os.remove(file)
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"  ❌ 删除失败 {file}: {e}")
            else:
                # 创建目录
                os.makedirs(target_dir, exist_ok=True)
                logger.info(f"  创建目录: {target_dir}")

        logger.info(f"  删除了 {deleted_count} 个视频文件")

        # 2. 旋转偏移 +1
        new_offset = (current_offset + 1) % len(target_dirs)

        logger.info(f"\n📦 复制视频到新位置 (偏移: {current_offset} → {new_offset})...")

        # 3. 根据模式复制视频
        copy_count = 0
        if mode == "video_to_dirs":
            # 模式1: 每个视频对应多个目录
            for i, video in enumerate(videos):
                if not os.path.exists(video):
                    logger.warning(f"⚠️ 视频不存在: {video}")
                    continue

                video_name = os.path.basename(video)
                start_idx = (i * window_size + new_offset) % len(target_dirs)

                # 复制到对应的目录
                for j in range(window_size):
                    dir_idx = (start_idx + j) % len(target_dirs)
                    target_dir = target_dirs[dir_idx]
                    target_path = os.path.join(target_dir, video_name)

                    try:
                        shutil.copy2(video, target_path)
                        copy_count += 1
                    except Exception as e:
                        logger.error(f"  ❌ 复制失败 {video_name} → {target_dir}: {e}")
        else:
            # 模式2: 每个目录对应多个视频
            for i, target_dir in enumerate(target_dirs):
                dir_idx = (i + new_offset) % len(target_dirs)

                # 计算该目录对应的视频
                for j in range(videos_per_dir):
                    video_idx = (dir_idx + j * len(target_dirs)) % len(videos)
                    if video_idx >= len(videos):
                        break

                    video = videos[video_idx]
                    if not os.path.exists(video):
                        logger.warning(f"⚠️ 视频不存在: {video}")
                        continue

                    video_name = os.path.basename(video)
                    target_path = os.path.join(target_dir, video_name)

                    try:
                        shutil.copy2(video, target_path)
                        copy_count += 1
                    except Exception as e:
                        logger.error(f"  ❌ 复制失败 {video_name} → {target_dir}: {e}")

        logger.info(f"  复制了 {copy_count} 个视频文件")

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

    def delete_ring(self, ring_name: str) -> bool:
        """删除指定的环形系统

        Args:
            ring_name: 环形系统名称

        Returns:
            bool: 是否成功删除
        """
        if ring_name not in self.states:
            logger.error(f"❌ 环形系统 '{ring_name}' 不存在")
            return False

        # 删除环形系统
        del self.states[ring_name]
        self._save_states()

        logger.info(f"✅ 环形系统 '{ring_name}' 已删除")
        return True


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description="视频环形分配器 - 管理多个独立的环形系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:

  1. 构建环形系统:
     python video_rotator.py build --ring-name 老号1 --video_dir E:\\myvideos\\cartoon --target-start 老号1-1 --target-end 老号1-50

     说明: 将视频复制到已存在的 D:\\qiyuan\\素材\\老号1-1, 老号1-2, ..., 老号1-50 目录中
           video_dir 和 target 目录名称可以完全不同

  2. 构建多个环形系统:
     python video_rotator.py build --ring-name 老号1 --video_dir E:\\videos\\set1 --target-start 老号1-1 --target-end 老号1-50
     python video_rotator.py build --ring-name 老号2 --video_dir E:\\videos\\set2 --target-start 老号2-1 --target-end 老号2-50
     python video_rotator.py build --ring-name 新号1 --video_dir F:\\content --target-start 新号1-1 --target-end 新号1-30

  3. 列出所有环形系统:
     python video_rotator.py list

  4. 旋转环形系统:
     python video_rotator.py rotate --name 老号1

  5. 查看环形系统状态:
     python video_rotator.py status --name 老号1
     python video_rotator.py status  # 查看所有

  6. 删除环形系统:
     python video_rotator.py delete --name 老号1

     说明: 只删除配置信息,不会删除目标目录中的视频文件

工作原理:
  - 假设有 10 个视频, 20 个目录
  - 窗口大小 = 目录数 / 视频数 = 20 / 10 = 2
  - 每个视频对应 2 个目录
  - 旋转时,窗口整体向前移动 +1
  - 最大旋转次数 = 10 次 (视频数量)
  - 旋转 10 次后,每个目录都存储过每个视频

状态保存:
  - 所有环形系统的状态保存在: ./output/video_rotator_state.json
  - 支持多个独立的环形系统并存
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # build 命令
    build_parser = subparsers.add_parser(
        'build',
        help='构建环形映射关系',
        description='创建一个新的环形系统,将视频文件映射到目录窗口',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python video_rotator.py build --ring-name 老号1 --video_dir E:\\myvideos\\cartoon --target-start 老号1-1 --target-end 老号1-50

  会创建环形系统 "老号1":
  - 扫描 E:\\myvideos\\cartoon 下的所有视频文件
  - 映射到已存在的目录: D:\\qiyuan\\素材\\老号1-1, 老号1-2, ..., 老号1-50
  - 计算窗口大小并建立映射关系
  - 注意: video_dir 和目标目录名称可以完全不同
  - 注意: 目标目录应该已经存在,脚本不会创建目录
        """
    )
    build_parser.add_argument('--ring-name', required=True,
                             help='环形系统名称 (用户自定义,例如: 老号1)')
    build_parser.add_argument('--video_dir', required=True,
                             help='视频文件所在目录 (任意目录,与目标目录名称无关)')
    build_parser.add_argument('--target-start', type=str, required=True,
                             help='目标目录起始名称 (例如: 老号1-1)')
    build_parser.add_argument('--target-end', type=str, required=True,
                             help='目标目录结束名称 (例如: 老号1-50)')
    build_parser.add_argument('--base-dir', default=BASE_DIR,
                             help=f'目标目录的基础路径 (默认: {BASE_DIR})')

    # rotate 命令
    rotate_parser = subparsers.add_parser(
        'rotate',
        help='旋转指定环形系统的视频',
        description='清空目标目录并按环形窗口+1的方式重新分配视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python video_rotator.py rotate --name 老号1

  执行操作:
  1. 清空所有目标目录中的视频文件
  2. 将窗口偏移 +1
  3. 根据新的窗口位置复制视频到对应目录
  4. 更新旋转计数
        """
    )
    rotate_parser.add_argument('--name', required=True,
                              help='环形系统名称 (使用 list 命令查看所有环形系统)')

    # status 命令
    status_parser = subparsers.add_parser(
        'status',
        help='查看环形系统状态',
        description='显示环形系统的详细状态信息',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 查看指定环形系统状态
  python video_rotator.py status --name 老号1

  # 查看所有环形系统状态
  python video_rotator.py status
        """
    )
    status_parser.add_argument('--name',
                              help='环形系统名称 (可选，不指定则显示所有环形系统的状态)')

    # list 命令
    subparsers.add_parser(
        'list',
        help='列出所有环形系统',
        description='显示当前配置的所有环形系统名称',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python video_rotator.py list

  输出示例:
  📋 所有环形系统 (共 3 个):
    1. 老号1
    2. 老号2
    3. 新号1
        """
    )

    # delete 命令
    delete_parser = subparsers.add_parser(
        'delete',
        help='删除指定环形系统',
        description='删除环形系统的配置信息 (不删除目标目录中的视频文件)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python video_rotator.py delete --name 老号1

  注意:
  - 只删除环形系统的配置信息
  - 不会删除目标目录中的视频文件
  - 删除后可以重新构建同名的环形系统
        """
    )
    delete_parser.add_argument('--name', required=True,
                              help='要删除的环形系统名称')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    rotator = VideoRotator()

    if args.command == 'build':
        logger.info(f"\n🔧 构建环形系统")
        logger.info(f"  环形名称: {args.ring_name}")
        logger.info(f"  视频目录: {args.video_dir}")
        logger.info(f"  目标范围: {args.target_start} - {args.target_end}")
        logger.info(f"  基础目录: {args.base_dir}")

        rotator.build_mapping(
            video_dir=args.video_dir,
            target_start=args.target_start,
            target_end=args.target_end,
            ring_name=args.ring_name,
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

    elif args.command == 'delete':
        success = rotator.delete_ring(args.name)
        if not success:
            exit(1)


if __name__ == "__main__":
    main()
