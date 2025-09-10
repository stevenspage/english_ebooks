# ==================== 配置区域 ====================
# 您的API密钥
API_KEY = "7e3c8f9a096d45c29a176cfd29bee1db.n56tQddA2mhejalp"

# 智谱AI智能体配置
AGENT_ID = "general_translation"  # 智能体ID
STRATEGY = "two_step"             # 翻译策略

# 输入输出文件配置
# INPUT_FILE = "book_info.json"           # 输入JSON文件路径（已移除硬编码）

# 第一个翻译字段配置
SOURCE_FIELD_1 = "description"  # 源字段（英文原文）
TARGET_FIELD_1 = "description_zh"     # 目标字段（中文翻译）

# 第二个翻译字段配置
SOURCE_FIELD_2 = "author_bio"             # 源字段（作者简介英文原文）
TARGET_FIELD_2 = "author_bio_zh"          # 目标字段（作者简介中文翻译）

# 输出文件名将直接覆盖原文件
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
                        "text": f"{text}"
                    }
                ]
            }
        ],
        "custom_variables": {
            "source_lang": "auto",
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

def translate_field(text, api_key, field_name):
    """翻译单个字段的函数"""
    if not text or not text.strip():
        return None, f"跳过（无{field_name}原文）"
    
    # 调用翻译函数
    result = translate_english_to_chinese(text, api_key)
    
    if result:
        # 尝试多种可能的响应格式
        translated_text = None
        
        # 格式1: choices -> messages -> content -> text
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            if 'messages' in choice and len(choice['messages']) > 0:
                content = choice['messages'][0]['content']
                if isinstance(content, dict) and 'text' in content:
                    translated_text = content['text']
                elif isinstance(content, list) and len(content) > 0:
                    translated_text = content[0].get('text', '')
                elif isinstance(content, str):
                    translated_text = content
        
        # 格式2: 直接包含翻译结果
        elif 'data' in result and 'choices' in result['data']:
            choices = result['data']['choices']
            if len(choices) > 0 and 'message' in choices[0]:
                translated_text = choices[0]['message'].get('content', '')
        
        # 格式3: 直接包含content
        elif 'content' in result:
            translated_text = result['content']
        
        # 格式4: 包含message字段
        elif 'message' in result:
            translated_text = result['message']
        
        if translated_text and translated_text.strip():
            return translated_text.strip(), "翻译成功"
        else:
            return None, f"无法从响应中提取{field_name}翻译结果"
    else:
        return None, f"API调用错误"

def translate_book(book_data):
    """翻译单本书的函数"""
    book, index, total, api_key = book_data
    book_title = book.get('title', f'书籍{index}')
    
    # 检查两个字段的翻译状态
    field1_has_translation = book.get(TARGET_FIELD_1) and book[TARGET_FIELD_1].strip()
    field2_has_translation = book.get(TARGET_FIELD_2) and book[TARGET_FIELD_2].strip()
    
    # 如果两个字段都已翻译，跳过
    if field1_has_translation and field2_has_translation:
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（两个字段都已有中文翻译）', 'book': book}
    
    # 检查是否有原文需要翻译
    field1_original = book.get(SOURCE_FIELD_1, '')
    field2_original = book.get(SOURCE_FIELD_2, '')
    
    if not field1_original.strip() and not field2_original.strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（无任何原文需要翻译）', 'book': book}
    
    print(f"[{index}/{total}] {book_title} - 正在翻译...")
    
    # 翻译第一个字段
    if field1_original.strip() and not field1_has_translation:
        print(f"  翻译字段1: {SOURCE_FIELD_1} -> {TARGET_FIELD_1}")
        print(f"  原文: {field1_original[:100]}{'...' if len(field1_original) > 100 else ''}")
        
        translated_text, status = translate_field(field1_original, api_key, "描述")
        if translated_text:
            book[TARGET_FIELD_1] = translated_text
            print(f"  ✓ 字段1翻译完成")
            print(f"  译文: {translated_text[:100]}{'...' if len(translated_text) > 100 else ''}")
        else:
            print(f"  ❌ 字段1翻译失败: {status}")
    
    # 翻译第二个字段
    if field2_original.strip() and not field2_has_translation:
        print(f"  翻译字段2: {SOURCE_FIELD_2} -> {TARGET_FIELD_2}")
        print(f"  原文: {field2_original[:100]}{'...' if len(field2_original) > 100 else ''}")
        
        translated_text, status = translate_field(field2_original, api_key, "作者简介")
        if translated_text:
            book[TARGET_FIELD_2] = translated_text
            print(f"  ✓ 字段2翻译完成")
            print(f"  译文: {translated_text[:100]}{'...' if len(translated_text) > 100 else ''}")
        else:
            print(f"  ❌ 字段2翻译失败: {status}")
    
    # 检查翻译结果
    field1_success = book.get(TARGET_FIELD_1) and book[TARGET_FIELD_1].strip()
    field2_success = book.get(TARGET_FIELD_2) and book[TARGET_FIELD_2].strip()
    
    if field1_success or field2_success:
        return {'status': 'success', 'message': f'[{index}/{total}] {book_title} - 翻译完成', 'book': book}
    else:
        return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 翻译失败', 'book': book}

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
        print(f"字段1: {SOURCE_FIELD_1} -> {TARGET_FIELD_1}")
        print(f"字段2: {SOURCE_FIELD_2} -> {TARGET_FIELD_2}")
        
        # 直接使用原文件名，覆盖原文件
        OUTPUT_FILE = INPUT_FILE
        print(f"输出文件: {OUTPUT_FILE} (将覆盖原文件)")
        
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
        books_to_translate.append((book, i, total_books, API_KEY))
    
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
                    if '两个字段都已有中文翻译' in result['message']:
                        skipped_translated += 1
                    elif '无任何原文需要翻译' in result['message']:
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
        print(f"跳过: {skipped_translated + skipped_no_original} 本（两个字段都已有翻译: {skipped_translated} 本，无任何原文: {skipped_no_original} 本）")
        print(f"成功: {translated_books} 本")
        print(f"失败: {failed_books} 本")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()
