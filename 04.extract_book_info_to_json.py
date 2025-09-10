#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从ebooks文件夹中的epub文件提取图书信息并保存为JSON
"""

import re
import json
import os
import time
import zipfile
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import unquote
from difflib import SequenceMatcher

def calculate_similarity(str1, str2):
    """计算两个字符串的相似度（0-1之间）"""
    if not str1 or not str2:
        return 0.0
    
    # 标准化字符串：转小写，去掉扩展名，去掉多余空格
    def normalize_filename(filename):
        # 去掉扩展名
        name = re.sub(r'\.(epub|pdf|mobi)$', '', filename, flags=re.IGNORECASE)
        # 转小写，去掉多余空格
        return re.sub(r'\s+', ' ', name.lower().strip())
    
    norm1 = normalize_filename(str1)
    norm2 = normalize_filename(str2)
    
    # 使用SequenceMatcher计算相似度
    similarity = SequenceMatcher(None, norm1, norm2).ratio()
    
    # 对于中文文件名，进行额外的相似度调整
    # 如果两个文件名都包含中文，且核心书名相同，提高相似度
    if similarity >= 0.6:  # 基础相似度达到60%时
        # 提取核心书名（去掉括号内容）
        def extract_core_title(filename):
            # 去掉所有括号及其内容
            core = re.sub(r'\([^)]*\)', '', filename)
            # 去掉连字符和多余空格
            core = re.sub(r'[-_\s]+', ' ', core).strip()
            return core
        
        core1 = extract_core_title(norm1)
        core2 = extract_core_title(norm2)
        
        # 如果核心书名相似，提高相似度
        core_similarity = SequenceMatcher(None, core1, core2).ratio()
        if core_similarity >= 0.8:  # 核心书名相似度很高
            # 提高最终相似度
            similarity = min(1.0, similarity + 0.1)
    
    return similarity

def find_best_match(target_filename, candidate_filenames, threshold=0.7):
    """找到最佳匹配的文件名"""
    if not candidate_filenames:
        return None, 0.0
    
    best_match = None
    best_similarity = 0.0
    
    for candidate in candidate_filenames:
        similarity = calculate_similarity(target_filename, candidate)
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = candidate
    
    # 只有当相似度超过阈值时才返回匹配结果
    if best_similarity >= threshold:
        return best_match, best_similarity
    
    return None, 0.0

def extract_author_from_epub(epub_path):
    """从epub文件中提取作者信息"""
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub:
            # 查找OPF文件
            opf_files = [f for f in epub.namelist() if f.endswith('.opf')]
            if not opf_files:
                return ""
            
            # 读取第一个OPF文件
            opf_content = epub.read(opf_files[0]).decode('utf-8', errors='ignore')
            
            # 使用xml.etree.ElementTree解析OPF文件（与附件脚本一致）
            import xml.etree.ElementTree as ET
            root = ET.fromstring(opf_content)
            
            # 定义命名空间（与附件脚本一致）
            namespaces = {
                'dc': 'http://purl.org/dc/elements/1.1/',
                'opf': 'http://www.idpf.org/2007/opf'
            }
            
            # 提取作者（与附件脚本逻辑完全一致）
            author_elements = root.findall('.//dc:creator', namespaces)
            authors = [author.text for author in author_elements if author.text]
            
            # 如果没有找到作者，尝试其他可能的标签
            if not authors:
                # 尝试dc:contributor
                contributor_elements = root.findall('.//dc:contributor', namespaces)
                authors = [contributor.text for contributor in contributor_elements if contributor.text]
            
            # 如果仍然没有作者，返回空字符串（与附件脚本的'未知'不同，因为这是备选方案）
            if not authors:
                return ""
            
            # 返回所有作者，用逗号分隔
            return ', '.join(authors)
            
    except Exception as e:
        print(f"从epub文件提取作者信息时出错 {epub_path}: {e}")
        return ""

def extract_author_and_title_from_filename(filename):
    """从文件名中提取作者和纯书名，如果提取不到作者则从epub文件提取"""
    # 去掉.epub扩展名
    name_without_ext = filename.replace('.epub', '')
    
    # 常见的作者名模式：在括号中的名字
    author_match = re.search(r'\(([^)]+)\)', name_without_ext)
    
    if author_match:
        author = author_match.group(1).strip()
        # 去掉作者名部分，得到纯书名
        title = name_without_ext.replace(f'({author})', '').strip()
        # 清理多余的括号和空格
        title = re.sub(r'\s*\([^)]*\)\s*', '', title).strip()
        return title, author
    else:
        # 如果没有找到作者名，整个文件名就是书名
        title = name_without_ext
        
        # 尝试从epub文件中提取作者信息
        epub_path = os.path.join('ebooks', filename)
        if os.path.exists(epub_path):
            author = extract_author_from_epub(epub_path)
            if author:
                print(f"从epub文件提取到作者信息: {filename} -> {author}")
            return title, author
        else:
            return title, ""

def scan_ebooks_directory():
    """直接从ebooks文件夹扫描epub文件，获取文件信息"""
    ebooks_directory = 'ebooks'
    
    # 检查ebooks文件夹是否存在
    if not os.path.isdir(ebooks_directory):
        print(f"错误：文件夹 '{ebooks_directory}' 不存在。")
        return [], []
    
    print(f"正在扫描 '{ebooks_directory}' 文件夹...")
    
    # 获取文件信息（文件名和时间信息）
    book_info = []
    for filename in os.listdir(ebooks_directory):
        if filename.lower().endswith('.epub'):
            file_path = os.path.join(ebooks_directory, filename)
            
            # 获取文件的各种时间
            stat_info = os.stat(file_path)
            
            # 尝试获取创建时间（Windows系统）
            try:
                if hasattr(stat_info, 'st_birthtime'):
                    # macOS/BSD 系统
                    create_time = stat_info.st_birthtime
                elif hasattr(stat_info, 'st_ctime') and os.name == 'nt':
                    # Windows 系统，st_ctime 通常是创建时间
                    create_time = stat_info.st_ctime
                else:
                    # Linux 系统，使用 stat 的 st_ctime（状态改变时间）
                    create_time = stat_info.st_ctime
            except:
                create_time = stat_info.st_mtime  # fallback 到修改时间
            
            book_info.append({
                'filename': filename,
                'addTime': create_time,  # 使用创建时间作为添加时间
                'addTimeISO': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(create_time))
            })
    
    # 按添加时间（创建时间）排序（最新的在前）
    book_info.sort(key=lambda x: x['addTime'], reverse=True)
    
    # 提取文件名列表用于兼容性
    book_files = [info['filename'] for info in book_info]
    
    if not book_files:
        print("未在 ebooks 文件夹中找到任何 .epub 文件。")
    else:
        print(f"找到了 {len(book_files)} 本书: {', '.join(book_files[:5])}{'...' if len(book_files) > 5 else ''}")
    
    return book_files, book_info

def build_book_info(book_files, book_info):
    """构建图书信息，从文件名和文件系统获取数据"""
    # 创建文件名到bookInfo的映射
    info_map = {info["filename"]: info for info in book_info}
    
    # 构建完整的图书信息
    final_books = []
    
    for filename in book_files:
        # 从文件名提取作者和纯书名
        title, author = extract_author_and_title_from_filename(filename)
        
        book_data = {
            "filename": filename,
            "title": title,  # 纯书名（去掉作者名）
            "title_zh": "",  # 暂时不提取中文标题
            "author": author,  # 从文件名提取的作者名
            "pages": None,  # 不再从index.html获取
            "format": "EPUB",
            "addTime": None,  # 将从reader_index.html获取
            "addTimeISO": None,
            "publishYear": None,  # 暂时不提取
            "filePath": f"./ebooks/{filename}",
            "coverPath": f"./covers/{filename.replace('.epub', '.jpeg')}",
            "description": ""  # 不再从index.html获取
        }
        
        # 添加从reader_index.html提取的信息
        if filename in info_map:
            book_data["addTime"] = info_map[filename]["addTime"]
            book_data["addTimeISO"] = info_map[filename]["addTimeISO"]
        
        final_books.append(book_data)
    
    return final_books

def load_existing_book_info():
    """加载现有的book_info.json文件"""
    try:
        if os.path.exists('book_info.json'):
            with open('book_info.json', 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                print(f"发现现有book_info.json文件，包含 {len(existing_data.get('books', []))} 本图书")
                return existing_data
        else:
            print("未发现现有book_info.json文件，将创建新文件")
            return None
    except Exception as e:
        print(f"读取现有文件时出错: {e}，将创建新文件")
        return None

def merge_book_info(existing_books, new_books):
    """合并现有图书信息和新提取的图书信息"""
    if not existing_books:
        return new_books
    
    # 创建现有图书的映射（以文件名为键）
    existing_map = {book['filename']: book for book in existing_books}
    
    merged_books = []
    matched_existing_files = set()  # 记录已匹配的现有文件
    
    for new_book in new_books:
        filename = new_book['filename']
        
        if filename in existing_map:
            # 情况1：精确匹配成功
            existing_book = existing_map[filename]
            merged_book = existing_book.copy()
            
            # 更新可能变化的信息
            merged_book.update({
                'title': new_book['title'],
                'author': new_book['author'],
                'addTime': new_book['addTime'],
                'addTimeISO': new_book['addTimeISO'],
                'filePath': new_book['filePath'],
                'coverPath': new_book['coverPath']
            })
            
            # 保留现有信息（如果新信息为空）
            if not merged_book.get('title_zh') and new_book.get('title_zh'):
                merged_book['title_zh'] = new_book['title_zh']
            if not merged_book.get('pages') and new_book.get('pages'):
                merged_book['pages'] = new_book['pages']
            if not merged_book.get('description') and new_book.get('description'):
                merged_book['description'] = new_book['description']
            if not merged_book.get('publishYear') and new_book.get('publishYear'):
                merged_book['publishYear'] = new_book['publishYear']
            
            print(f"更新图书: {filename}")
            matched_existing_files.add(filename)
            
        else:
            # 情况2：精确匹配失败，尝试智能匹配
            best_match, similarity = find_best_match(filename, list(existing_map.keys()), threshold=0.7)
            
            if best_match and best_match not in matched_existing_files:
                # 智能匹配成功
                existing_book = existing_map[best_match]
                merged_book = existing_book.copy()
                
                # 更新文件名（记录变更）
                old_filename = best_match
                merged_book['filename'] = filename
                merged_book['old_filename'] = old_filename  # 记录原文件名
                
                # 更新其他信息
                merged_book.update({
                    'title': new_book['title'],
                    'author': new_book['author'],
                    'addTime': new_book['addTime'],
                    'addTimeISO': new_book['addTimeISO'],
                    'filePath': new_book['filePath'],
                    'coverPath': new_book['coverPath']
                })
                
                # 保留现有信息（如果新信息为空）
                if not merged_book.get('title_zh') and new_book.get('title_zh'):
                    merged_book['title_zh'] = new_book['title_zh']
                if not merged_book.get('pages') and new_book.get('pages'):
                    merged_book['pages'] = new_book['pages']
                if not merged_book.get('description') and new_book.get('description'):
                    merged_book['description'] = new_book['description']
                if not merged_book.get('publishYear') and new_book.get('publishYear'):
                    merged_book['publishYear'] = new_book['publishYear']
                
                print(f"检测到文件名变更: '{old_filename}' → '{filename}' (相似度: {similarity:.2f})")
                matched_existing_files.add(best_match)
                
            else:
                # 情况3：智能匹配也失败，作为新书处理
                merged_book = new_book
                if best_match and best_match in matched_existing_files:
                    print(f"添加新图书: {filename} (注意：可能与现有图书 '{best_match}' 重复)")
                else:
                    print(f"添加新图书: {filename}")
        
        merged_books.append(merged_book)
    
    # 检查是否有被删除的图书（在现有文件中但不在新文件列表中，且未被匹配）
    new_filenames = {book['filename'] for book in new_books}
    removed_books = [book for book in existing_books 
                     if book['filename'] not in new_filenames 
                     and book['filename'] not in matched_existing_files]
    
    if removed_books:
        print(f"\n发现 {len(removed_books)} 本图书可能已被删除:")
        for book in removed_books:
            print(f"  - {book['filename']}")
        
        # 询问是否保留已删除的图书
        keep_removed = input("\n是否保留这些已删除的图书信息？(y/n): ").lower().strip()
        if keep_removed == 'y':
            merged_books.extend(removed_books)
            print("已保留被删除的图书信息")
        else:
            print("已移除被删除的图书信息")
    
    return merged_books

def main():
    """主函数"""
    try:
        # 加载现有的book_info.json文件
        existing_data = load_existing_book_info()
        
        # 直接从ebooks文件夹扫描epub文件
        print("正在扫描ebooks文件夹...")
        book_files, book_info = scan_ebooks_directory()
        
        if not book_files:
            print("未找到任何epub文件，程序退出。")
            return
        
        # 构建图书信息
        print("正在构建图书信息...")
        new_books = build_book_info(book_files, book_info)
        
        # 合并现有信息和新信息
        print("正在合并图书信息...")
        final_books = merge_book_info(
            existing_data['books'] if existing_data else [], 
            new_books
        )
        
        # 构建最终的JSON结构
        result = {
            "total_books": len(final_books),
            "last_updated": datetime.now().isoformat() + "Z",
            "books": final_books
        }
        
        # 保存为JSON文件
        print("正在保存为JSON文件...")
        with open('book_info.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"成功更新图书信息，共 {len(final_books)} 本图书，已保存到 book_info.json")
        
        # 显示一些统计信息
        print(f"\n统计信息:")
        print(f"- 总图书数量: {len(final_books)}")
        print(f"- 有页数信息的图书: {len([b for b in final_books if b['pages']])}")
        print(f"- 有描述信息的图书: {len([b for b in final_books if b['description']])}")
        print(f"- 有时间信息的图书: {len([b for b in final_books if b['addTime']])}")
        print(f"- 有作者信息的图书: {len([b for b in final_books if b['author']])}")
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 {e}")
    except Exception as e:
        print(f"处理过程中出错: {e}")

if __name__ == "__main__":
    main()
