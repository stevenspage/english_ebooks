# ==================== 配置区域 ====================
# 您的API密钥
API_KEY = "7e3c8f9a096d45c29a176cfd29bee1db.n56tQddA2mhejalp"

# 智谱AI智能体配置
AGENT_ID = "general_translation"  # 智能体ID
STRATEGY = "two_step"             # 翻译策略

# 输入输出文件配置
# INPUT_FILE = "book_info_goodreads.json"           # 输入JSON文件路径（已移除硬编码）
SOURCE_FIELD = "description_review_original"  # 源字段（英文原文）
TARGET_FIELD = "description_review"     # 目标字段（中文翻译）
# 输出文件名会自动生成为: 原文件名_trans.json
# ================================================

import requests
import json
import time
import threading
import os
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

def list_json_files():
    """
    列出当前目录下的所有JSON文件
    
    Returns:
        list: JSON文件路径列表
    """
    json_files = glob.glob("*.json")
    return sorted(json_files)

def select_input_file():
    """
    让用户选择输入文件
    
    Returns:
        str: 选择的文件路径
    """
    json_files = list_json_files()
    
    if not json_files:
        print("错误: 当前目录下没有找到JSON文件")
        return None
    
    print("当前目录下的JSON文件:")
    for i, file_path in enumerate(json_files, 1):
        print(f"  {i}. {file_path}")
    
    print(f"\n请选择要处理的文件 (1-{len(json_files)})，直接回车选择第一个:")
    
    try:
        user_input = input().strip()
        
        if not user_input:  # 直接回车，选择第一个
            selected_file = json_files[0]
            print(f"已选择: {selected_file}")
            return selected_file
        
        choice = int(user_input)
        if 1 <= choice <= len(json_files):
            selected_file = json_files[choice - 1]
            print(f"已选择: {selected_file}")
            return selected_file
        else:
            print(f"无效选择，请输入 1-{len(json_files)} 之间的数字")
            return None
            
    except ValueError:
        print("无效输入，请输入数字")
        return None

def translate_english_to_chinese(text, api_key):
    """
    使用智谱AI智能体进行英译中翻译
    
    Args:
        text (str): 要翻译的英文文本
        api_key (str): 智谱AI的API密钥
    
    Returns:
        dict: 翻译结果
    """
    
    # API端点
    url = "https://open.bigmodel.cn/api/v1/agents"
    
    # 请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 请求体
    payload = {
        "agent_id": AGENT_ID,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"翻译下列内容，直接返回翻译结果，不要有其他任何内容：\n\n{text}"
                    }
                ]
            }
        ],
        "custom_variables": {
            "source_lang": "en",
            "target_lang": "zh-CN",
            "strategy": STRATEGY
        }
    }
    
    try:
        # 发送请求
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # 检查HTTP错误
        
        # 解析响应
        result = response.json()
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {e}")
        return None

def translate_book(book_data):
    """翻译单本书的函数"""
    book, index, total, api_key, source_field, target_field = book_data
    book_title = book.get('title', f'书籍{index}')
    
    # 检查是否已有中文翻译
    if book.get(target_field) and book[target_field].strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（已有中文翻译）', 'book': book}
    
    # 获取原文描述
    original_desc = book.get(source_field, '')
    if not original_desc or not original_desc.strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（无原文描述）', 'book': book}
    
    print(f"[{index}/{total}] {book_title} - 正在翻译...")
    print(f"  原文: {original_desc[:100]}{'...' if len(original_desc) > 100 else ''}")
    
    # 调用翻译函数
    result = translate_english_to_chinese(original_desc, api_key)
    
    if result:
        # 提取翻译结果
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            if 'messages' in choice and len(choice['messages']) > 0:
                content = choice['messages'][0]['content']
                if isinstance(content, list) and len(content) > 0:
                    translated_text = content[0].get('text', '')
                    book[target_field] = translated_text
                    print(f"  ✓ 翻译完成")
                    print(f"  译文: {translated_text[:100]}{'...' if len(translated_text) > 100 else ''}")
                    return {'status': 'success', 'message': f'[{index}/{total}] {book_title} - 翻译完成', 'book': book}
                else:
                    return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 翻译失败：响应格式错误', 'book': book}
            else:
                return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 翻译失败：无消息内容', 'book': book}
        else:
            return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 翻译失败：无选择结果', 'book': book}
    else:
        return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 翻译失败：API调用错误', 'book': book}

def main():
    # 读取输入文件
    try:
        # 让用户选择输入文件
        INPUT_FILE = select_input_file()
        if not INPUT_FILE:
            return

        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            books = data.get('books', [])
        print(f"成功读取 {len(books)} 本书的信息")
        print(f"源字段: {SOURCE_FIELD}")
        print(f"目标字段: {TARGET_FIELD}")
        
        # 自动生成输出文件名
        base_name = os.path.splitext(INPUT_FILE)[0]  # 去掉扩展名
        OUTPUT_FILE = f"{base_name}_trans.json"
        print(f"输出文件: {OUTPUT_FILE}")
        
    except FileNotFoundError:
        print(f"错误: 找不到 {INPUT_FILE} 文件")
        return
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件格式错误 - {e}")
        return
    
    # 统计信息
    total_books = len(books)
    skipped_translated = 0  # 已有翻译的书籍数量
    skipped_no_original = 0  # 无原文的书籍数量
    translated_books = 0
    failed_books = 0
    
    print("开始批量翻译...")
    print(f"使用并发数: 20")
    print("-" * 50)
    
    # 准备需要翻译的书籍数据
    books_to_translate = []
    for i, book in enumerate(books, 1):
        books_to_translate.append((book, i, total_books, API_KEY, SOURCE_FIELD, TARGET_FIELD))
    
    # 使用线程池执行并发翻译
    with ThreadPoolExecutor(max_workers=20) as executor:
        # 提交所有翻译任务
        future_to_book = {executor.submit(translate_book, book_data): book_data for book_data in books_to_translate}
        
        # 处理完成的任务
        for future in as_completed(future_to_book):
            book_data = future_to_book[future]
            try:
                result = future.result()
                if result['status'] == 'success':
                    translated_books += 1
                elif result['status'] == 'skipped':
                    # 根据跳过原因分别统计
                    if '已有中文翻译' in result['message']:
                        skipped_translated += 1
                    elif '无原文描述' in result['message']:
                        skipped_no_original += 1
                    else:
                        skipped_translated += 1  # 默认归类
                else:
                    failed_books += 1
                
                # 更新原书籍数据
                book_index = book_data[1] - 1
                books[book_index] = result['book']
                
            except Exception as e:
                print(f"处理书籍时出错: {e}")
                failed_books += 1
    
    # 保存结果到新文件
    try:
        # 保持原有的JSON结构，只更新books数组
        data['books'] = books
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("-" * 50)
        print(f"翻译完成！结果已保存到 {OUTPUT_FILE}")
        print(f"总计: {total_books} 本书")
        print(f"跳过: {skipped_translated + skipped_no_original} 本（已有翻译: {skipped_translated} 本，无原文: {skipped_no_original} 本）")
        print(f"成功: {translated_books} 本")
        print(f"失败: {failed_books} 本")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()
