#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSON文件差异比较工具
支持忽略排序，比较两个JSON文件的结构和内容差异
"""

import json
import os
import sys
from typing import Dict, List, Any, Tuple
from collections import OrderedDict
import argparse


def normalize_json_data(data: Any) -> Any:
    """
    标准化JSON数据，用于比较时忽略排序
    """
    if isinstance(data, dict):
        # 对字典按键排序，然后递归处理值
        sorted_dict = OrderedDict()
        for key in sorted(data.keys()):
            sorted_dict[key] = normalize_json_data(data[key])
        return sorted_dict
    elif isinstance(data, list):
        # 对列表中的每个元素进行标准化
        return [normalize_json_data(item) for item in data]
    else:
        # 基本类型直接返回
        return data


def deep_compare(obj1: Any, obj2: Any, path: str = "") -> List[Dict]:
    """
    深度比较两个对象，返回结构化的差异列表
    """
    differences = []
    
    if type(obj1) != type(obj2):
        differences.append({
            'type': 'type_change',
            'path': path,
            'old_type': type(obj1).__name__,
            'new_type': type(obj2).__name__,
            'old_value': str(obj1),
            'new_value': str(obj2)
        })
        return differences
    
    if isinstance(obj1, dict):
        # 比较字典
        all_keys = set(obj1.keys()) | set(obj2.keys())
        for key in sorted(all_keys):
            new_path = f"{path}.{key}" if path else key
            if key not in obj1:
                differences.append({
                    'type': 'key_added',
                    'path': new_path,
                    'key': key,
                    'value': obj2[key]
                })
            elif key not in obj2:
                differences.append({
                    'type': 'key_removed',
                    'path': new_path,
                    'key': key,
                    'value': obj1[key]
                })
            else:
                differences.extend(deep_compare(obj1[key], obj2[key], new_path))
    
    elif isinstance(obj1, list):
        # 列表比较：当元素为包含 original_title 的字典时，按 original_title 作为键进行无序比较
        can_key_by_title = (
            all(isinstance(it, dict) for it in obj1) and
            all(isinstance(it, dict) for it in obj2) and
            len(obj1) > 0 and len(obj2) > 0 and
            'original_title' in obj1[0] and 'original_title' in obj2[0]
        )

        if can_key_by_title:
            # 构建以 original_title 为键的映射
            def build_map(items):
                title_to_items = {}
                for idx, it in enumerate(items):
                    title = str(it.get('original_title', '')).strip()
                    # 处理可能的重复标题：使用列表存放
                    title_to_items.setdefault(title, []).append((idx, it))
                return title_to_items

            map1 = build_map(obj1)
            map2 = build_map(obj2)

            titles_all = set(map1.keys()) | set(map2.keys())
            for title in sorted(titles_all):
                new_path = f"{path}['{title}']" if path else f"['{title}']"
                if title not in map1:
                    differences.append({
                        'type': 'book_missing',
                        'path': new_path,
                        'title': title,
                        'side': 'first'
                    })
                    continue
                if title not in map2:
                    differences.append({
                        'type': 'book_missing',
                        'path': new_path,
                        'title': title,
                        'side': 'second'
                    })
                    continue

                list1 = map1[title]
                list2 = map2[title]
                if len(list1) != len(list2):
                    differences.append({
                        'type': 'book_count_mismatch',
                        'path': new_path,
                        'title': title,
                        'old_count': len(list1),
                        'new_count': len(list2)
                    })
                    # 尽量继续比较成对的项
                pair_count = min(len(list1), len(list2))
                for pair_index in range(pair_count):
                    idx1, item1 = list1[pair_index]
                    idx2, item2 = list2[pair_index]
                    pair_path = f"{new_path}[{pair_index}]"
                    differences.extend(deep_compare(item1, item2, pair_path))

            # 列表总体长度差异提示（辅助信息）
            if len(obj1) != len(obj2):
                differences.append({
                    'type': 'list_length_mismatch',
                    'path': path,
                    'old_length': len(obj1),
                    'new_length': len(obj2)
                })
        else:
            # 默认：按位置比较
            if len(obj1) != len(obj2):
                differences.append({
                    'type': 'list_length_mismatch',
                    'path': path,
                    'old_length': len(obj1),
                    'new_length': len(obj2)
                })
            else:
                for i, (item1, item2) in enumerate(zip(obj1, obj2)):
                    new_path = f"{path}[{i}]"
                    differences.extend(deep_compare(item1, item2, new_path))
    
    else:
        # 比较基本类型
        if obj1 != obj2:
            differences.append({
                'type': 'value_changed',
                'path': path,
                'old_value': obj1,
                'new_value': obj2
            })
    
    return differences


def load_json_file(file_path: str) -> Dict:
    """
    加载JSON文件
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"错误：无法解析JSON文件 '{file_path}': {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"错误：文件 '{file_path}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"错误：读取文件 '{file_path}' 时出错: {e}")
        sys.exit(1)


def get_json_files() -> List[str]:
    """
    获取当前目录下的所有JSON文件
    """
    json_files = []
    for file in os.listdir('.'):
        if file.endswith('.json') and os.path.isfile(file):
            json_files.append(file)
    return sorted(json_files)


def select_json_files() -> Tuple[str, str]:
    """
    让用户选择要比较的两个JSON文件
    """
    json_files = get_json_files()
    
    if len(json_files) < 2:
        print("错误：当前目录中JSON文件数量不足（需要至少2个）")
        sys.exit(1)
    
    print("发现以下JSON文件：")
    for i, file in enumerate(json_files, 1):
        file_size = os.path.getsize(file)
        print(f"{i}. {file} ({file_size:,} bytes)")
    
    if len(json_files) == 2:
        print(f"\n自动选择文件进行比较：")
        print(f"文件1: {json_files[0]}")
        print(f"文件2: {json_files[1]}")
        return json_files[0], json_files[1]
    
    print("\n请选择要比较的两个文件：")
    
    while True:
        try:
            choice1 = int(input(f"选择第一个文件 (1-{len(json_files)}): ")) - 1
            if 0 <= choice1 < len(json_files):
                break
            else:
                print("请输入有效的数字")
        except ValueError:
            print("请输入有效的数字")
    
    while True:
        try:
            choice2 = int(input(f"选择第二个文件 (1-{len(json_files)}): ")) - 1
            if 0 <= choice2 < len(json_files):
                if choice2 == choice1:
                    print("不能选择相同的文件，请重新选择")
                    continue
                break
            else:
                print("请输入有效的数字")
        except ValueError:
            print("请输入有效的数字")
    
    return json_files[choice1], json_files[choice2]


def parse_book_info(path, data1, data2):
    """从路径中解析出书籍信息"""
    result = {
        'book_title': None,
        'field_name': path.split('.')[-1] if '.' in path else path,
        'is_metadata': False
    }
    
    # 检查是否是metadata路径
    if path in ['last_updated', 'total_books']:
        result['is_metadata'] = True
        return result
    
    # 解析书籍标题
    if "books['" in path and "']" in path:
        try:
            # 提取标题
            start = path.find("books['") + 7
            end = path.find("']", start)
            if start < end:
                result['book_title'] = path[start:end]
        except (ValueError, IndexError):
            pass
    
    return result

def format_book_info(info):
    """格式化书籍信息显示"""
    if info['is_metadata']:
        return f"📋 {info['field_name']}"
    elif info['book_title']:
        return f"📚 《{info['book_title']}》"
    else:
        return "📚 未知书籍"

def display_differences(differences, data1, data2):
    """显示差异，重点突出书籍信息，并按特定顺序列出"""
    # 按类型分组
    added_books = []
    removed_books = []
    title_count_mismatch = []
    book_field_changes = []
    metadata_changes = []
    other_diffs = []

    for diff in differences:
        if diff['type'] == 'book_missing':
            # side == 'first' -> 旧文件缺少 -> 新增书籍
            if diff.get('side') == 'first':
                added_books.append(diff)
            else:
                removed_books.append(diff)
        elif diff['type'] == 'book_count_mismatch':
            title_count_mismatch.append(diff)
        elif 'books[' in diff['path']:
            book_field_changes.append(diff)
        elif diff['path'] in ['last_updated', 'total_books']:
            metadata_changes.append(diff)
        else:
            other_diffs.append(diff)

    total = len(differences)
    print(f"\n📊 总共发现 {total} 个差异")
    print("=" * 60)
    
    # 创建输出内容列表
    output_lines = []
    output_lines.append("JSON文件差异比较报告")
    output_lines.append("=" * 60)
    output_lines.append(f"比较时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    output_lines.append(f"总差异数: {total}")
    output_lines.append("=" * 60)
    output_lines.append("")

    # 定义一个通用的函数来格式化和打印差异部分
    def print_section(title, diffs, is_book_list=False, is_missing=False, is_count_mismatch=False):
        if not diffs:
            return
        
        section_header = f"\n{title} ({len(diffs)}个):"
        print(section_header)
        print("-" * 50)
        output_lines.append(section_header)
        output_lines.append("-" * 50)

        for i, diff in enumerate(diffs, 1):
            if is_book_list:
                # 解析书籍信息
                info = parse_book_info(diff['path'], data1, data2)
                book_display = format_book_info(info)
                book_line = f"{i:3d}. {book_display}"
                field_line = f"     📍 字段: {info['field_name']}"
                print(book_line)
                print(field_line)
                output_lines.append(book_line)
                output_lines.append(field_line)
                
                # 显示差异详情
                if diff['type'] == 'value_changed':
                    old_line = f"     🔄 旧值: {diff['old_value']}"
                    new_line = f"     ✨ 新值: {diff['new_value']}"
                    print(old_line)
                    print(new_line)
                    output_lines.extend([old_line, new_line])
                elif diff['type'] == 'book_missing':
                    side = "第一文件" if diff['side'] == 'first' else "第二文件"
                    missing_line = f"     ❌ {side}缺少该书籍"
                    print(missing_line)
                    output_lines.append(missing_line)
                elif diff['type'] == 'book_count_mismatch':
                    count_line = f"     ⚠️  相同标题出现次数不同 - {diff['old_count']} vs {diff['new_count']}"
                    print(count_line)
                    output_lines.append(count_line)
                elif diff['type'] == 'type_change':
                    type_line = f"     🔀 类型: {diff['old_type']} → {diff['new_type']}"
                    old_line = f"     🔄 旧值: {diff['old_value']}"
                    new_line = f"     ✨ 新值: {diff['new_value']}"
                    print(type_line)
                    print(old_line)
                    print(new_line)
                    output_lines.extend([type_line, old_line, new_line])
                else:
                    # 其他类型的差异
                    diff_line = f"     💫 详情: {diff['type']}"
                    print(diff_line)
                    output_lines.append(diff_line)
            elif is_missing:
                # 直接显示缺失书籍标题
                title = diff.get('title') or parse_book_info(diff['path'], data1, data2).get('book_title') or '未知书籍'
                which = '新增于新文件' if diff.get('side') == 'first' else '仅存在于旧文件'
                line = f"{i:3d}. 📚 《{title}》  — {which}"
                print(line)
                output_lines.append(line)
            elif is_count_mismatch:
                title = diff.get('title') or parse_book_info(diff['path'], data1, data2).get('book_title') or '未知书籍'
                line = f"{i:3d}. 📚 《{title}》  — 次数不同: {diff.get('old_count')} vs {diff.get('new_count')}"
                print(line)
                output_lines.append(line)
            else:
                # 元数据或其他差异
                if diff['type'] == 'value_changed':
                    diff_line = f"{i:3d}. 📋 {diff['path']}: {diff['old_value']} → {diff['new_value']}"
                else:
                    diff_line = f"{i:3d}. 📋 {diff['path']}: {diff['type']}"
                print(diff_line)
                output_lines.append(diff_line)
            
            print()
            output_lines.append("")

    # 按照新的顺序显示
    # 1. 新增书籍（新文件有、旧文件无）
    print_section("✨ 新增书籍", added_books, is_missing=True)

    # 2. 删除书籍（旧文件有、新文件无）
    print_section("🗑️ 删除书籍", removed_books, is_missing=True)

    # 3. 同名出现次数不同
    print_section("⚠️ 同名书籍次数不同", title_count_mismatch, is_count_mismatch=True)

    # 4. 书籍字段变更
    print_section("📚 书籍字段变更", book_field_changes, is_book_list=True)

    # 5. 元数据变更
    print_section("📋 元数据变更", metadata_changes)

    # 6. 其他差异
    print_section("🔧 其他差异", other_diffs)
    
    return output_lines

def compare_json_files(file1: str, file2: str, output_file: str = None) -> None:
    """
    比较两个JSON文件
    """
    print(f"\n正在比较文件：")
    print(f"文件1: {file1}")
    print(f"文件2: {file2}")
    print("-" * 50)
    
    # 加载JSON文件
    data1 = load_json_file(file1)
    data2 = load_json_file(file2)

    # 按文件修改时间判断新旧
    try:
        mtime1 = os.path.getmtime(file1)
        mtime2 = os.path.getmtime(file2)
    except Exception:
        mtime1 = mtime2 = None

    # old -> 修改时间更早的文件；new -> 修改时间更晚的文件
    if mtime1 is not None and mtime2 is not None and mtime1 <= mtime2:
        old_file_path, new_file_path = file1, file2
        old_data, new_data = data1, data2
        old_mtime, new_mtime = mtime1, mtime2
    elif mtime1 is not None and mtime2 is not None:
        old_file_path, new_file_path = file2, file1
        old_data, new_data = data2, data1
        old_mtime, new_mtime = mtime2, mtime1
    else:
        # 回退：无法获取mtime时，保持传入顺序
        old_file_path, new_file_path = file1, file2
        old_data, new_data = data1, data2
        old_mtime = new_mtime = None
    
    # 标准化数据（忽略排序），并以旧→新顺序比较
    normalized_data1 = normalize_json_data(old_data)
    normalized_data2 = normalize_json_data(new_data)
    
    # 比较数据
    differences = deep_compare(normalized_data1, normalized_data2)
    
    if not differences:
        result_msg = "✅ 两个JSON文件完全相同（忽略排序）"
        print(result_msg)
        return
    
    # 显示差异
    output_lines = display_differences(differences, old_data, new_data)

    # 在报告开头插入文件角色说明
    mapping_lines = [
        "文件角色：",
    ]
    if old_mtime is not None and new_mtime is not None:
        from datetime import datetime as _dt
        mapping_lines.append(
            f"旧文件: {old_file_path} (修改时间: {_dt.fromtimestamp(old_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
        )
        mapping_lines.append(
            f"新文件: {new_file_path} (修改时间: {_dt.fromtimestamp(new_mtime).strftime('%Y-%m-%d %H:%M:%S')})"
        )
    else:
        mapping_lines.append(f"旧文件: {old_file_path}")
        mapping_lines.append(f"新文件: {new_file_path}")

    # 将文件角色说明插入到标题之后
    # 期望 output_lines[0] 为标题行
    insert_pos = 1 if len(output_lines) > 0 else 0
    output_lines[insert_pos:insert_pos] = mapping_lines + [""]
    
    # 显示基本统计信息
    stats_msg = "\n文件统计信息："
    print(stats_msg)
    output_lines.append(stats_msg)
    
    file1_stats = f"旧文件 ({old_file_path}):"
    print(file1_stats)
    output_lines.append(file1_stats)
    
    file1_size = f"  - 文件大小: {os.path.getsize(file1):,} bytes"
    print(file1_size)
    output_lines.append(file1_size)
    
    if isinstance(old_data, dict) and 'total_books' in old_data:
        file1_books = f"  - 书籍总数: {old_data.get('total_books', 'N/A')}"
        print(file1_books)
        output_lines.append(file1_books)
    
    if isinstance(old_data, dict) and 'last_updated' in old_data:
        file1_updated = f"  - 最后更新: {old_data.get('last_updated', 'N/A')}"
        print(file1_updated)
        output_lines.append(file1_updated)
    
    file2_stats = f"新文件 ({new_file_path}):"
    print(file2_stats)
    output_lines.append(file2_stats)
    
    file2_size = f"  - 文件大小: {os.path.getsize(file2):,} bytes"
    print(file2_size)
    output_lines.append(file2_size)
    
    if isinstance(new_data, dict) and 'total_books' in new_data:
        file2_books = f"  - 书籍总数: {new_data.get('total_books', 'N/A')}"
        print(file2_books)
        output_lines.append(file2_books)
    
    if isinstance(new_data, dict) and 'last_updated' in new_data:
        file2_updated = f"  - 最后更新: {new_data.get('last_updated', 'N/A')}"
        print(file2_updated)
        output_lines.append(file2_updated)
    
    # 保存报告到文件
    if output_file:
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"\n📄 比较报告已保存到: {output_file}")
        except Exception as e:
            print(f"\n❌ 保存报告文件失败: {e}")
    else:
        # 自动生成报告文件名
        timestamp = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
        auto_output_file = f"书籍信息比较报告_{timestamp}.txt"
        try:
            with open(auto_output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
            print(f"\n📄 比较报告已自动保存到: {auto_output_file}")
        except Exception as e:
            print(f"\n❌ 保存报告文件失败: {e}")


def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(description='比较两个JSON文件的差异（忽略排序）')
    parser.add_argument('file1', nargs='?', help='第一个JSON文件路径')
    parser.add_argument('file2', nargs='?', help='第二个JSON文件路径')
    parser.add_argument('-o', '--output', help='输出报告文件路径（可选）')
    
    args = parser.parse_args()
    
    if args.file1 and args.file2:
        # 命令行参数模式
        if not os.path.exists(args.file1):
            print(f"错误：文件 '{args.file1}' 不存在")
            sys.exit(1)
        if not os.path.exists(args.file2):
            print(f"错误：文件 '{args.file2}' 不存在")
            sys.exit(1)
        compare_json_files(args.file1, args.file2, args.output)
    else:
        # 交互模式
        file1, file2 = select_json_files()
        compare_json_files(file1, file2, args.output)


if __name__ == "__main__":
    main()
