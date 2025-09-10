#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进版：从 book_info.json 生成 README.md 文件的脚本
读取中文书名、英文书名、页数、链接、图书描述和书评信息
"""

import json
import os
from urllib.parse import quote
import re

def load_book_info(json_file):
    """加载图书信息JSON文件"""
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"错误：找不到文件 {json_file}")
        return None
    except json.JSONDecodeError:
        print(f"错误：{json_file} 不是有效的JSON文件")
        return None

def generate_book_link(book_info):
    """生成图书链接"""
    filename = book_info.get('filename', '')
    if not filename:
        return ""
    
    # 构建相对路径
    relative_path = f"./ebooks/{filename}"
    # URL编码
    encoded_path = quote(relative_path)
    # 构建完整链接
    base_url = "https://stevenspage.github.io/english_ebooks/reader.html?book="
    return f"{base_url}{encoded_path}"

def format_book_title(book_info):
    """格式化图书标题（中文+英文+作者+年份）"""
    title_zh = book_info.get('title_zh', '').strip()
    title = book_info.get('title', '').strip()
    author = book_info.get('author', '').strip()
    publish_year = book_info.get('publishYear', '')
    
    # 如果中文标题为空，尝试从文件名中提取
    if not title_zh and title:
        # 检查是否有中文内容
        if re.search(r'[\u4e00-\u9fff]', title):
            title_zh = title
            title = ""
    
    # 格式化标题
    if title_zh and title:
        if publish_year:
            return f"《{title_zh}》({title}) - {author}, {publish_year}"
        else:
            return f"《{title_zh}》({title}) - {author}"
    elif title_zh:
        if publish_year:
            return f"《{title_zh}》 - {author}, {publish_year}"
        else:
            return f"《{title_zh}》 - {author}"
    elif title:
        if publish_year:
            return f"{title} - {author}, {publish_year}"
        else:
            return f"{title} - {author}"
    else:
        if publish_year:
            return f"未知标题 - {author}, {publish_year}"
        else:
            return f"未知标题 - {author}"



def generate_readme_content(books_data):
    """生成README内容"""
    header = '''<p align="right" style="font-size: 1em; color: #0366d6; font-weight: bold;">Ebooks from Roy, curated by Steven</p>

<div align="center">
  <h1>📚 英文电子书合集</h1>
  <p>
    <strong>一份精心整理的英文原版电子书收藏，助您提升英语阅读能力，领略文学魅力。</strong>
  </p>
  <p align="center" style="margin: 20px 0;">
    <a href="https://stevenspage.github.io/english_ebooks/" style="
      display: inline-block;
      padding: 8px 16px;
      margin: 0 8px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-weight: 500;
      transition: transform 0.2s ease;
    font-size: 0.75em;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
      📖 进入主页
    </a>
    <a href="https://github.com/stevenspage/english_ebooks" style="
      display: inline-block;
      padding: 8px 16px;
      margin: 0 8px;
      background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
      color: white;
      text-decoration: none;
      border-radius: 6px;
      font-weight: 500;
      transition: transform 0.2s ease;
    font-size: 0.75em;
    " onmouseover="this.style.transform='translateY(-2px)'" onmouseout="this.style.transform='translateY(0)'">
    🧑‍💻 Github地址
    </a>
  </p>
</div>

 ⚠️ **在线预览电子书需要在科学环境下**

---

## 📖 电子书列表

'''
    
    content = header
    
    # 按添加时间排序（最新的在前）
    sorted_books = sorted(books_data.get('books', []), 
                         key=lambda x: x.get('addTime', 0), reverse=True)
    
    book_counter = 0  # 用于重新编号显示的图书
    for book in sorted_books:
        pages = book.get('pages', 0)
        title = format_book_title(book)
        link = generate_book_link(book)
        
        # 获取描述信息 - 只读取 description_zh 字段
        description_zh = book.get('description_zh', '').strip()
        
        # 如果没有描述，跳过这本书
        if not description_zh:
            continue
        
        book_counter += 1  # 只有有描述的图书才计数
    
    # 根据总编号数动态确定空格策略
    if book_counter < 100:
        # 两位数总编号：一位数用2个空格，两位数用1个空格
        space_strategy = lambda x: "  " if x < 10 else " "
    else:
        # 三位数总编号：一位数用3个空格，两位数用2个空格，三位数用1个空格
        space_strategy = lambda x: "   " if x < 10 else ("  " if x < 100 else " ")
    
    # 重新遍历图书生成内容
    book_counter = 0
    for book in sorted_books:
        pages = book.get('pages', 0)
        title = format_book_title(book)
        link = generate_book_link(book)
        
        # 获取描述信息 - 只读取 description_zh 字段
        description_zh = book.get('description_zh', '').strip()
        
        # 如果没有描述，跳过这本书
        if not description_zh:
            continue
        
        book_counter += 1  # 只有有描述的图书才计数
        
        # 生成图书条目 - 使用动态空格策略
        spaces = space_strategy(book_counter)
        
        # 添加Goodreads评分信息
        goodreads_rating = book.get('goodreads_rating', 0)
        goodreads_rating_count = book.get('goodreads_rating_count', 0)
        rating_info = ""
        if goodreads_rating > 0 and goodreads_rating_count > 0:
            # 将评分人数转换为万为单位
            rating_count_wan = goodreads_rating_count / 10000
            if rating_count_wan >= 1:
                rating_display = f"{rating_count_wan:.1f}万人评分"
            else:
                rating_display = f"{goodreads_rating_count}人评分"
            
            rating_info = f"  | ⭐Goodreads：{goodreads_rating}分 ({rating_display})"
        
        book_entry = f"{book_counter}.{spaces}**({pages}页) [{title}]({link})**{rating_info}\n"
        
        # 添加图书类型信息
        genre_list = book.get('genre', [])
        if genre_list:
            genre_str = " · ".join(genre_list)
            book_entry += f"    <br>📚 类型：{genre_str}\n"
        
        # 完整输出描述，不截断，并处理换行符
        # 将换行符替换为换行符+引用标记，保持Markdown格式
        formatted_description_zh = description_zh.replace('\n', '\n    > ')
        book_entry += f"    > {formatted_description_zh}\n"
        
        # 添加作者简介（中文）
        author_bio_zh = book.get('author_bio_zh', '').strip()
        if author_bio_zh:
            # 处理换行符，保持Markdown格式，并在作者简介前添加空行
            formatted_author_bio = author_bio_zh.replace('\n', '\n    > ')
            book_entry += f"\n    > **作者简介**: {formatted_author_bio}\n"
        
        # 添加分隔行
        book_entry += "\n"
        content += book_entry
    
    # 添加统计信息
    total_books = books_data.get('total_books', 0)
    displayed_books = book_counter  # 实际显示的图书数量
    last_updated = books_data.get('last_updated', '')
    
    footer = f"""
---

## 📊 统计信息

- **总图书数量**: {total_books} 本
- **显示图书数量**: {displayed_books} 本
- **最后更新**: {last_updated}
- **数据来源**: book_info.json
"""
    
    content += footer
    return content

def main():
    """主函数"""
    json_file = "book_info.json"
    output_file = "README.md"
    
    print("正在加载图书信息...")
    books_data = load_book_info(json_file)
    
    if not books_data:
        print("无法加载图书信息，程序退出")
        return
    
    print(f"成功加载 {books_data.get('total_books', 0)} 本图书")
    
    print("正在生成README内容...")
    readme_content = generate_readme_content(books_data)
    
    print(f"正在保存到 {output_file}...")
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"✅ 成功生成 {output_file}")
        print(f"📊 包含 {books_data.get('total_books', 0)} 本图书")
        print(f"📅 最后更新: {books_data.get('last_updated', 'N/A')}")
    except Exception as e:
        print(f"❌ 保存文件时出错: {e}")

if __name__ == "__main__":
    main()
