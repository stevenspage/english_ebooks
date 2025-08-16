import os
import re
import json
import time

# --- 配置 ---
# ebooks 文件夹的路径
EBOOKS_DIRECTORY = 'ebooks'
# 需要更新的 HTML 文件
HTML_FILE = 'reader_index.html'  # 更新为新的文件名

def update_book_list():
    """
    扫描 ebooks 目录，找到所有 .epub 文件，并更新 index.html 中的书籍列表。
    """
    try:
        # 1. 检查 ebooks 文件夹是否存在
        if not os.path.isdir(EBOOKS_DIRECTORY):
            print(f"错误：文件夹 '{EBOOKS_DIRECTORY}' 不存在。")
            print("请先创建该文件夹并将您的 .epub 文件放入其中。")
            return

        # 2. 获取所有 .epub 文件的文件名和修改时间
        print(f"正在扫描 '{EBOOKS_DIRECTORY}' 文件夹...")
        
        # 获取文件信息（文件名和时间信息）
        book_info = []
        for filename in os.listdir(EBOOKS_DIRECTORY):
            if filename.lower().endswith('.epub'):
                file_path = os.path.join(EBOOKS_DIRECTORY, filename)
                
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

        # 3. 读取 index.html 文件内容
        with open(HTML_FILE, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 4. 生成新的 JavaScript 数据
        # 生成文件列表（保持向后兼容）
        js_book_list = json.dumps(book_files, indent=4, ensure_ascii=False)
        
        # 生成带时间戳的文件信息
        js_book_info = json.dumps(book_info, indent=4, ensure_ascii=False)
        
        # 5. 使用正则表达式替换 HTML 文件中的 bookFiles 数组
        pattern_files = r"(const bookFiles = )(\[.*?\]);"
        replacement_files = r"\g<1>" + js_book_list + ";"
        
        # 替换书籍文件列表
        new_html_content, num_replacements = re.subn(
            pattern_files,
            replacement_files,
            html_content,
            count=1,
            flags=re.DOTALL
        )
        
        if num_replacements == 0:
            print(f"错误：无法在 '{HTML_FILE}' 中找到 'const bookFiles = [...]'。")
            print("请确认该变量存在于您的 HTML 文件中。")
            return
            
        # 添加或更新 bookInfo 数组
        pattern_info = r"(const bookInfo = )(\[.*?\]);"
        replacement_info = r"\g<1>" + js_book_info + ";"
        
        # 如果存在 bookInfo，则替换；否则在 bookFiles 后添加
        info_replacements = re.subn(
            pattern_info,
            replacement_info,
            new_html_content,
            count=1,
            flags=re.DOTALL
        )[1]
        
        if info_replacements > 0:
            new_html_content = re.sub(
                pattern_info,
                replacement_info,
                new_html_content,
                count=1,
                flags=re.DOTALL
            )
        else:
            # 在 bookFiles 后添加 bookInfo
            insert_pattern = r"(const bookFiles = \[.*?\];)"
            insert_replacement = r"\g<1>\n\n    // 文件信息（包含修改时间）- 由脚本自动维护\n    const bookInfo = " + js_book_info + ";"
            new_html_content = re.sub(
                insert_pattern,
                insert_replacement,
                new_html_content,
                count=1,
                flags=re.DOTALL
            )

        # 6. 将更新后的内容写回 index.html 文件
        with open(HTML_FILE, 'w', encoding='utf-8') as f:
            f.write(new_html_content)
        
        print(f"\n成功！'{HTML_FILE}' 中的书籍列表已更新。")
        print("现在您可以在浏览器中刷新 index.html 查看最新的书库。")

    except FileNotFoundError:
        print(f"错误：文件 '{HTML_FILE}' 未找到。请确保脚本与 HTML 文件在同一目录下。")
    except Exception as e:
        print(f"发生未知错误: {e}")

if __name__ == '__main__':
    update_book_list()
