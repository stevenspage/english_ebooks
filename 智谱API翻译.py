import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

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
        "agent_id": "social_literature_translation_agent",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ]
            }
        ],
        "custom_variables": {
            "source_lang": "en",
            "target_lang": "zh-CN"
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
    book, index, total, api_key = book_data
    book_title = book.get('title', f'书籍{index}')
    
    # 检查是否已有中文翻译
    if book.get('description_review') and book['description_review'].strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（已有中文翻译）', 'book': book}
    
    # 获取原文描述
    original_desc = book.get('description_review_original', '')
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
                    book['description_review'] = translated_text
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
    # 您的API密钥
    API_KEY = "7e3c8f9a096d45c29a176cfd29bee1db.n56tQddA2mhejalp"
    
    # 读取book_info.json文件
    try:
        with open('book_info.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            books = data.get('books', [])
        print(f"成功读取 {len(books)} 本书的信息")
    except FileNotFoundError:
        print("错误: 找不到 book_info.json 文件")
        return
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件格式错误 - {e}")
        return
    
    # 统计信息
    total_books = len(books)
    skipped_books = 0
    translated_books = 0
    failed_books = 0
    
    print("开始批量翻译...")
    print(f"使用并发数: 5")
    print("-" * 50)
    
    # 准备需要翻译的书籍数据
    books_to_translate = []
    for i, book in enumerate(books, 1):
        books_to_translate.append((book, i, total_books, API_KEY))
    
    # 使用线程池执行并发翻译
    with ThreadPoolExecutor(max_workers=5) as executor:
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
                    skipped_books += 1
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
        with open('book_info_trans.json', 'w', encoding='utf-8') as f:
            json.dump({'totalBooks': total_books, 'lastUpdated': data.get('lastUpdated'), 'books': books}, f, ensure_ascii=False, indent=2)
        print("-" * 50)
        print("翻译完成！结果已保存到 book_info_trans.json")
        print(f"总计: {total_books} 本书")
        print(f"跳过: {skipped_books} 本（已有翻译或无原文）")
        print(f"成功: {translated_books} 本")
        print(f"失败: {failed_books} 本")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()
