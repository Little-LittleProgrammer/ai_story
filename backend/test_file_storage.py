#!/usr/bin/env python
"""
测试日期分层文件存储功能
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

# 配置 Django 设置
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

import django
django.setup()

from core.utils.file_storage import DateBasedFileStorage, image_storage, video_storage


def test_basic_storage():
    """测试基本存储功能"""
    print("=" * 60)
    print("测试 1: 基本文件存储")
    print("=" * 60)

    storage = DateBasedFileStorage('storage/test')

    # 测试数据
    test_content = b"This is a test image content"

    # 保存第一个文件
    full_path1, rel_path1 = storage.save_file('test.png', test_content)
    print(f"✓ 保存文件 1:")
    print(f"  完整路径: {full_path1}")
    print(f"  相对路径: {rel_path1}")
    print(f"  文件存在: {full_path1.exists()}")

    # 保存相同文件名 (应该添加后缀 _1)
    full_path2, rel_path2 = storage.save_file('test.png', test_content)
    print(f"\n✓ 保存文件 2 (相同文件名):")
    print(f"  完整路径: {full_path2}")
    print(f"  相对路径: {rel_path2}")
    print(f"  文件存在: {full_path2.exists()}")

    # 再保存一次 (应该添加后缀 _2)
    full_path3, rel_path3 = storage.save_file('test.png', test_content)
    print(f"\n✓ 保存文件 3 (相同文件名):")
    print(f"  完整路径: {full_path3}")
    print(f"  相对路径: {rel_path3}")
    print(f"  文件存在: {full_path3.exists()}")

    # 验证路径不同
    assert str(full_path1) != str(full_path2) != str(full_path3), "路径应该不同"
    print("\n✓ 所有文件路径都不同")


def test_date_structure():
    """测试日期目录结构"""
    print("\n" + "=" * 60)
    print("测试 2: 日期目录结构")
    print("=" * 60)

    storage = DateBasedFileStorage('storage/test')

    # 今天
    today = datetime.now()
    full_path_today, rel_path_today = storage.save_file('today.png', b"today")
    print(f"✓ 今天的文件:")
    print(f"  相对路径: {rel_path_today}")
    print(f"  预期包含: {today.strftime('%Y-%m-%d')}")
    assert today.strftime('%Y-%m-%d') in rel_path_today

    # 昨天
    yesterday = today - timedelta(days=1)
    full_path_yesterday, rel_path_yesterday = storage.get_unique_filepath('yesterday.png', date=yesterday)
    print(f"\n✓ 昨天的文件路径 (未实际保存):")
    print(f"  相对路径: {rel_path_yesterday}")
    print(f"  预期包含: {yesterday.strftime('%Y-%m-%d')}")
    assert yesterday.strftime('%Y-%m-%d') in rel_path_yesterday

    # 明天
    tomorrow = today + timedelta(days=1)
    full_path_tomorrow, rel_path_tomorrow = storage.get_unique_filepath('tomorrow.png', date=tomorrow)
    print(f"\n✓ 明天的文件路径 (未实际保存):")
    print(f"  相对路径: {rel_path_tomorrow}")
    print(f"  预期包含: {tomorrow.strftime('%Y-%m-%d')}")
    assert tomorrow.strftime('%Y-%m-%d') in rel_path_tomorrow


def test_global_instances():
    """测试全局实例"""
    print("\n" + "=" * 60)
    print("测试 3: 全局存储实例")
    print("=" * 60)

    # 测试图片存储
    img_content = b"Image content"
    full_path, rel_path = image_storage.save_file('global_test.png', img_content)
    print(f"✓ 图片存储 (image_storage):")
    print(f"  基础目录: {image_storage.base_dir}")
    print(f"  相对路径: {rel_path}")
    print(f"  包含 'image': {'image' in str(rel_path)}")

    # 测试视频存储
    video_content = b"Video content"
    full_path, rel_path = video_storage.save_file('global_test.mp4', video_content)
    print(f"\n✓ 视频存储 (video_storage):")
    print(f"  基础目录: {video_storage.base_dir}")
    print(f"  相对路径: {rel_path}")
    print(f"  包含 'video': {'video' in str(rel_path)}")


def test_file_extensions():
    """测试各种文件扩展名"""
    print("\n" + "=" * 60)
    print("测试 4: 不同文件扩展名")
    print("=" * 60)

    storage = DateBasedFileStorage('storage/test')
    test_content = b"test"

    extensions = ['.png', '.jpg', '.gif', '.webp', '.mp4', '.avi', '.mov']

    for ext in extensions:
        filename = f"test{ext}"
        full_path, rel_path = storage.save_file(filename, test_content)
        print(f"✓ {ext:6s} -> {rel_path}")
        assert ext in rel_path, f"扩展名 {ext} 应该保留"


def test_duplicate_handling():
    """测试重复文件处理"""
    print("\n" + "=" * 60)
    print("测试 5: 大量重复文件处理")
    print("=" * 60)

    storage = DateBasedFileStorage('storage/test')
    test_content = b"duplicate test"

    # 保存 10 个同名文件
    paths = []
    for i in range(10):
        full_path, rel_path = storage.save_file('duplicate.png', test_content)
        paths.append(rel_path)

    print(f"✓ 保存了 10 个同名文件:")
    for i, path in enumerate(paths):
        print(f"  {i+1:2d}. {path}")

    # 验证所有路径都不同
    assert len(set(paths)) == 10, "所有路径应该都不同"
    print("\n✓ 所有路径都是唯一的")


def cleanup_test_files():
    """清理测试文件"""
    print("\n" + "=" * 60)
    print("清理测试文件")
    print("=" * 60)

    import shutil
    test_dir = Path('storage/test')
    if test_dir.exists():
        shutil.rmtree(test_dir)
        print(f"✓ 已删除测试目录: {test_dir}")
    else:
        print(f"  测试目录不存在: {test_dir}")


if __name__ == '__main__':
    try:
        test_basic_storage()
        test_date_structure()
        test_global_instances()
        test_file_extensions()
        test_duplicate_handling()

        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)

        # 自动清理测试文件
        cleanup_test_files()

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
