#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从book_title_zh.json读取中文标题并写入book_info.json中
通过匹配title字段来更新title_zh字段
逻辑：先读取book_info.json找出缺失title_zh的书籍，再去book_title_zh.json中寻找
"""

import json
import os
from typing import Dict, List

def load_json_file(file_path: str) -> dict:
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {file_path}")
        return {}
    except json.JSONDecodeError as e:
        print(f"错误：JSON文件格式错误 {file_path}: {e}")
        return {}

def save_json_file(file_path: str, data: dict) -> bool:
    """保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"错误：保存文件失败 {file_path}: {e}")
        return False

def find_missing_title_zh_books(book_info: dict) -> List[Dict]:
    """找出缺失title_zh字段的书籍"""
    missing_books = []
    for book in book_info.get('books', []):
        title_zh = book.get('title_zh', '')
        # 检查title_zh是否为空或不存在
        if not title_zh or title_zh.strip() == '':
            missing_books.append(book)
    return missing_books

def create_title_mapping(zh_titles: List[Dict]) -> Dict[str, str]:
    """创建title到title_zh的映射"""
    mapping = {}
    for item in zh_titles:
        title = item.get('title', '')
        title_zh = item.get('title_zh', '')
        if title and title_zh:
            mapping[title] = title_zh
    return mapping

def update_missing_books(book_info: dict, title_mapping: Dict[str, str]) -> tuple[int, int]:
    """更新缺失title_zh的书籍"""
    updated_count = 0
    total_missing = 0
    
    for book in book_info.get('books', []):
        title_zh = book.get('title_zh', '')
        # 只更新缺失title_zh的书籍
        if not title_zh or title_zh.strip() == '':
            total_missing += 1
            title = book.get('title', '')
            if title in title_mapping:
                book['title_zh'] = title_mapping[title]
                updated_count += 1
                print(f"✓ 更新: {title} -> {title_mapping[title]}")
            else:
                print(f"✗ 未找到: {title}")
    
    return updated_count, total_missing

def main():
    """主函数"""
    print("开始更新图书中文标题...")
    
    # 文件路径
    zh_title_file = "book_title_zh.json"
    book_info_file = "book_info.json"
    
    # 检查文件是否存在
    if not os.path.exists(book_info_file):
        print(f"错误：找不到文件 {book_info_file}")
        return
    
    if not os.path.exists(zh_title_file):
        print(f"错误：找不到文件 {zh_title_file}")
        return
    
    # 第一步：加载图书信息数据
    print(f"正在加载 {book_info_file}...")
    book_info = load_json_file(book_info_file)
    if not book_info:
        print("无法加载图书信息数据")
        return
    
    # 第二步：找出缺失title_zh的书籍
    print("正在检查缺失中文标题的书籍...")
    missing_books = find_missing_title_zh_books(book_info)
    total_books = len(book_info.get('books', []))
    
    if not missing_books:
        print("所有书籍都已经有中文标题了，无需更新！")
        return
    
    print(f"找到 {len(missing_books)} 本缺失中文标题的书籍")
    print(f"总共 {total_books} 本书")
    
    # 第三步：加载中文标题数据
    print(f"正在加载 {zh_title_file}...")
    zh_titles = load_json_file(zh_title_file)
    if not zh_titles:
        print("无法加载中文标题数据")
        return
    
    # 第四步：创建标题映射
    print("正在创建标题映射...")
    title_mapping = create_title_mapping(zh_titles)
    print(f"找到 {len(title_mapping)} 个中文标题")
    
    # 第五步：更新缺失的书籍
    print("正在更新缺失中文标题的书籍...")
    updated_count, total_missing = update_missing_books(book_info, title_mapping)
    
    # 第六步：保存更新后的数据
    if updated_count > 0:
        print(f"正在保存更新后的数据到 {book_info_file}...")
        if save_json_file(book_info_file, book_info):
            print(f"更新完成！")
            print(f"成功更新 {updated_count} 本书的中文标题")
            print(f"仍有 {total_missing - updated_count} 本书未找到中文标题")
        else:
            print("保存失败！")
    else:
        print("没有需要更新的书籍")

if __name__ == "__main__":
    main()
