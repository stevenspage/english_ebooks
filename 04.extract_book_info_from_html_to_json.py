#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从HTML文件中提取图书信息并保存为JSON
"""

import re
import json
import os
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

def extract_author_and_title_from_filename(filename):
    """从文件名中提取作者和纯书名"""
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
        return name_without_ext, ""

def extract_books_from_index_html(html_content):
    """从index.html提取图书信息（仅提取description_review和pages）"""
    soup = BeautifulSoup(html_content, 'html.parser')
    books = []
    
    # 查找所有图书列表项
    book_items = soup.find_all('li')
    
    for item in book_items:
        try:
            # 提取页数
            page_match = re.search(r'\((\d+)页\)', item.get_text())
            if not page_match:
                continue
            pages = int(page_match.group(1))
            
            # 提取链接和文件名
            link = item.find('a')
            if not link:
                continue
                
            href = link.get('href')
            if not href or 'book=' not in href:
                continue
                
            # 解码文件路径
            file_path = unquote(href.split('book=')[1])
            filename = os.path.basename(file_path)
            
            # 提取描述和书评
            blockquote = item.find('blockquote', class_='book-review')
            description_review = ""
            if blockquote:
                paragraphs = blockquote.find_all('p')
                for p in paragraphs:
                    text = p.get_text().strip()
                    if text and not text.startswith('书评:'):
                        description_review += text + " "
                description_review = description_review.strip()
            
            book_info = {
                "filename": filename,
                "pages": pages,
                "description_review": description_review
            }
            
            books.append(book_info)
            
        except Exception as e:
            print(f"处理图书项时出错: {e}")
            continue
    
    return books

def extract_books_from_reader_index(html_content):
    """从reader_index.html提取图书信息"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 查找JavaScript代码中的bookFiles和bookInfo
    scripts = soup.find_all('script')
    
    book_files = []
    book_info = []
    
    for script in scripts:
        if script.string:
            script_text = script.string
            
            # 提取bookFiles数组
            files_match = re.search(r'const bookFiles = \[(.*?)\];', script_text, re.DOTALL)
            if files_match:
                files_text = files_match.group(1)
                # 解析文件名
                files = re.findall(r'"([^"]+\.epub)"', files_text)
                book_files = files
            
            # 提取bookInfo数组
            info_match = re.search(r'const bookInfo = \[(.*?)\];', script_text, re.DOTALL)
            if info_match:
                info_text = info_match.group(1)
                # 解析bookInfo
                info_entries = re.findall(r'\{[^}]+\}', info_text)
                for entry in info_entries:
                    filename_match = re.search(r'"filename":\s*"([^"]+)"', entry)
                    add_time_match = re.search(r'"addTime":\s*([\d.]+)', entry)
                    add_time_iso_match = re.search(r'"addTimeISO":\s*"([^"]+)"', entry)
                    
                    if filename_match and add_time_match:
                        book_info.append({
                            "filename": filename_match.group(1),
                            "addTime": float(add_time_match.group(1)),
                            "addTimeISO": add_time_iso_match.group(1) if add_time_iso_match else None
                        })
    
    return book_files, book_info

def merge_book_info(books_from_index, book_files, book_info):
    """合并两个来源的图书信息，使用模糊匹配"""
    # 创建文件名到bookInfo的映射
    info_map = {info["filename"]: info for info in book_info}
    
    # 创建文件名到index信息的映射
    index_map = {book["filename"]: book for book in books_from_index}
    
    # 构建完整的图书信息
    final_books = []
    
    # 统计匹配信息
    exact_matches = 0
    fuzzy_matches = 0
    no_matches = 0
    
    for filename in book_files:
        # 从文件名提取作者和纯书名
        original_title, author = extract_author_and_title_from_filename(filename)
        
        book_data = {
            "filename": filename,
            "original_title": original_title,  # 纯书名（去掉作者名）
            "title_zh": "",  # 暂时不提取中文标题
            "author": author,  # 从文件名提取的作者名
            "pages": None,  # 将从index.html获取
            "format": "EPUB",
            "addTime": None,  # 将从reader_index.html获取
            "addTimeISO": None,
            "publishYear": None,  # 暂时不提取
            "filePath": f"./ebooks/{filename}",
            "coverPath": f"./covers/{filename.replace('.epub', '.jpeg')}",
            "description_review": ""  # 将从index.html获取
        }
        
        # 尝试精确匹配
        if filename in index_map:
            book_data["pages"] = index_map[filename]["pages"]
            book_data["description_review"] = index_map[filename]["description_review"]
            exact_matches += 1
        else:
            # 尝试模糊匹配
            best_match_filename, similarity = find_best_match(filename, list(index_map.keys()))
            if best_match_filename:
                book_data["pages"] = index_map[best_match_filename]["pages"]
                book_data["description_review"] = index_map[best_match_filename]["description_review"]
                fuzzy_matches += 1
                print(f"模糊匹配: '{filename}' -> '{best_match_filename}' (相似度: {similarity:.3f})")
            else:
                no_matches += 1
                print(f"未找到匹配: '{filename}'")
        
        # 添加从reader_index.html提取的信息
        if filename in info_map:
            book_data["addTime"] = info_map[filename]["addTime"]
            book_data["addTimeISO"] = info_map[filename]["addTimeISO"]
        
        final_books.append(book_data)
    
    # 打印匹配统计信息
    print(f"\n匹配统计:")
    print(f"- 精确匹配: {exact_matches}")
    print(f"- 模糊匹配: {fuzzy_matches}")
    print(f"- 无匹配: {no_matches}")
    print(f"- 总匹配率: {((exact_matches + fuzzy_matches) / len(book_files) * 100):.1f}%")
    
    return final_books

def main():
    """主函数"""
    try:
        # 读取HTML文件
        print("正在读取HTML文件...")
        
        with open('index.html', 'r', encoding='utf-8') as f:
            index_content = f.read()
        
        with open('reader_index.html', 'r', encoding='utf-8') as f:
            reader_content = f.read()
        
        # 提取图书信息
        print("正在从index.html提取图书信息...")
        books_from_index = extract_books_from_index_html(index_content)
        
        print("正在从reader_index.html提取图书信息...")
        book_files, book_info = extract_books_from_reader_index(reader_content)
        
        # 合并信息
        print("正在合并图书信息（使用模糊匹配）...")
        final_books = merge_book_info(books_from_index, book_files, book_info)
        
        # 构建最终的JSON结构
        result = {
            "totalBooks": len(final_books),
            "lastUpdated": datetime.now().isoformat() + "Z",
            "books": final_books
        }
        
        # 保存为JSON文件
        print("正在保存为JSON文件...")
        with open('book_info.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"成功提取 {len(final_books)} 本图书信息，已保存到 book_info.json")
        
        # 显示一些统计信息
        print(f"\n统计信息:")
        print(f"- 总图书数量: {len(final_books)}")
        print(f"- 有页数信息的图书: {len([b for b in final_books if b['pages']])}")
        print(f"- 有描述信息的图书: {len([b for b in final_books if b['description_review']])}")
        print(f"- 有时间信息的图书: {len([b for b in final_books if b['addTime']])}")
        print(f"- 有作者信息的图书: {len([b for b in final_books if b['author']])}")
        
    except FileNotFoundError as e:
        print(f"错误: 找不到文件 {e}")
    except Exception as e:
        print(f"处理过程中出错: {e}")

if __name__ == "__main__":
    main()
