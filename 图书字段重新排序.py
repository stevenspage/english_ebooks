#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调整JSON字段顺序的脚本
将最后四个字段按照指定顺序重新排列：
1. description
2. author_bio
3. description_zh
4. author_bio_zh
"""

import json
import sys
from typing import Dict, Any, OrderedDict

def reorder_book_fields(book: Dict[str, Any]) -> Dict[str, Any]:
    """
    重新排序单本书的字段，将最后四个字段按照指定顺序排列
    """
    # 定义新的字段顺序
    field_order = [
        "description",
        "author_bio", 
        "description_zh",
        "author_bio_zh"
    ]
    
    # 创建新的有序字典
    reordered_book = OrderedDict()
    
    # 首先添加除了最后四个字段之外的所有字段
    for key, value in book.items():
        if key not in field_order:
            reordered_book[key] = value
    
    # 然后按照指定顺序添加最后四个字段
    for field in field_order:
        if field in book:
            reordered_book[field] = book[field]
    
    return reordered_book

def main():
    """主函数"""
    input_file = "book_info.json"
    output_file = "book_info_reorder.json"
    
    try:
        # 读取原始JSON文件
        print(f"正在读取文件: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"找到 {data.get('total_books', 0)} 本书")
        
        # 重新排序每本书的字段
        if 'books' in data:
            print("正在重新排序字段...")
            reordered_books = []
            
            for i, book in enumerate(data['books']):
                reordered_book = reorder_book_fields(book)
                reordered_books.append(reordered_book)
                
                # 显示进度
                if (i + 1) % 10 == 0 or i == len(data['books']) - 1:
                    print(f"已处理: {i + 1}/{len(data['books'])} 本书")
            
            # 更新数据
            data['books'] = reordered_books
        
        # 保存重新排序后的JSON文件
        print(f"正在保存到文件: {output_file}")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("字段重新排序完成！")
        print(f"输出文件: {output_file}")
        
        # 显示第一本书的字段顺序作为示例
        if data.get('books'):
            print("\n第一本书的字段顺序示例:")
            for i, (key, value) in enumerate(data['books'][0].items(), 1):
                print(f"{i:2d}. {key}")
                if i >= 20:  # 只显示前20个字段
                    print("    ...")
                    break
        
    except FileNotFoundError:
        print(f"错误: 找不到文件 {input_file}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON解析失败 - {e}")
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
