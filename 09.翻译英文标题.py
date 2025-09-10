# ==================== 配置区域 ====================
# 您的API密钥
API_KEY = "7e3c8f9a096d45c29a176cfd29bee1db.n56tQddA2mhejalp"

# 字段配置
SOURCE_FIELD = "title"         # 源字段（英文标题）
TARGET_FIELD = "title_zh"              # 目标字段（中文标题）
# 输出文件名将直接覆盖原文件
# ================================================

import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from collections import OrderedDict
import os
import glob

def select_json_file():
    """
    列出当前目录下的所有JSON文件，让用户选择
    """
    # 获取当前目录下所有JSON文件
    json_files = glob.glob("*.json")
    
    if not json_files:
        print("错误: 当前目录下没有找到JSON文件")
        return None
    
    print("发现以下JSON文件:")
    print("-" * 40)
    for i, file in enumerate(json_files, 1):
        print(f"{i}. {file}")
    print("-" * 40)
    
    # 用户选择
    while True:
        try:
            choice = input(f"请选择要处理的文件 (1-{len(json_files)})，回车选择第一个: ").strip()
            
            if not choice:  # 回车直接选择第一个
                selected_file = json_files[0]
                print(f"已选择: {selected_file}")
                return selected_file
            
            choice_num = int(choice)
            if 1 <= choice_num <= len(json_files):
                selected_file = json_files[choice_num - 1]
                print(f"已选择: {selected_file}")
                return selected_file
            else:
                print(f"请输入1到{len(json_files)}之间的数字")
        except ValueError:
            print("请输入有效的数字")
        except KeyboardInterrupt:
            print("\n用户取消操作")
            return None

def translate_english_to_chinese(title, description, api_key):
    """
    使用智谱AI智能体进行英译中翻译，结合书籍描述提供更准确的翻译
    
    Args:
        title (str): 要翻译的英文书名
        description (str): 英文书籍描述和评论
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
    
    # 构建更详细的翻译提示词
    prompt = f"""请将以下英文书名翻译成中文，要求：
1. 直接输出英文书名的翻译结果，禁止输出书籍描述和其他任何内容
2. 结合书籍描述内容，确保翻译的准确性和语境相关性

英文书名：{title}

书籍描述：{description}"""
    
    # 请求体
    payload = {
        "agent_id": "general_translation",  # 使用通用的翻译智能体
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
        ],
        "custom_variables": {
            "source_lang": "auto",
            "target_lang": "zh-CN",
            "strategy": "two_step"  # 添加翻译策略
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
        print(f"  [ERROR] 请求错误: {e}")
        print(f"  [ERROR] 请求URL: {url}")
        return None
    except json.JSONDecodeError as e:
        print(f"  [ERROR] JSON解析错误: {e}")
        print(f"  [ERROR] 响应内容: {response.text}")
        return None

def translate_book_title(book_data):
    """翻译单本书标题的函数"""
    book, index, total, api_key, source_field, target_field = book_data
    book_title = book.get('title', f'书籍{index}')
    
    # 检查是否已有中文标题
    if book.get(target_field) and book[target_field].strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（已有中文标题）', 'book': book}
    
    # 获取英文标题
    title = book.get(source_field, '')
    if not title or not title.strip():
        return {'status': 'skipped', 'message': f'[{index}/{total}] {book_title} - 跳过（无英文标题）', 'book': book}
    
    # 获取英文描述
    description = book.get('description', '')
    
    print(f"[{index}/{total}] {book_title} - 正在翻译标题...")
    print(f"  英文标题: {title}")
    if description:
        print(f"  英文描述: {description[:100]}...")
    
    # 调用翻译函数，传入标题和描述
    result = translate_english_to_chinese(title, description, api_key)
    
    if result:
        # 尝试多种可能的响应格式
        translated_text = None
        
        # 格式1: choices -> messages -> content -> text (列表格式)
        if 'choices' in result and len(result['choices']) > 0:
            choice = result['choices'][0]
            
            if 'messages' in choice and len(choice['messages']) > 0:
                content = choice['messages'][0]['content']
                
                if isinstance(content, list) and len(content) > 0:
                    translated_text = content[0].get('text', '')
                elif isinstance(content, dict) and 'text' in content:
                    translated_text = content['text']
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
        
        # 格式5: 检查是否有其他可能的字段
        else:
            # 尝试查找任何包含文本的字段
            for key, value in result.items():
                if isinstance(value, str) and value.strip():
                    if len(value) > 10:  # 假设翻译结果应该有一定长度
                        translated_text = value
                        break
        
        if translated_text and translated_text.strip():
            # 直接更新原书籍数据，添加翻译结果
            book[target_field] = translated_text.strip()
            
            print(f"  ✓ 标题翻译完成")
            print(f"  中文标题: {translated_text.strip()}")
            return {'status': 'success', 'message': f'[{index}/{total}] {book_title} - 标题翻译完成', 'book': book}
        else:
            print(f"  [ERROR] 无法从任何格式中提取翻译结果")
            print(f"  [ERROR] 完整API响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 标题翻译失败：无法提取翻译结果', 'book': book}
    else:
        print(f"  [ERROR] API调用返回None")
        return {'status': 'failed', 'message': f'[{index}/{total}] {book_title} - 标题翻译失败：API调用错误', 'book': book}

def main():
    # 选择要处理的JSON文件
    input_file = select_json_file()
    if not input_file:
        return
    
    # 读取输入文件
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            books = data.get('books', [])
        print(f"成功读取 {len(books)} 本书的信息")
        print(f"源字段: {SOURCE_FIELD}")
        print(f"目标字段: {TARGET_FIELD}")
        
        # 直接使用原文件名，覆盖原文件
        output_file = input_file
        print(f"输出文件: {output_file} (将覆盖原文件)")
        
    except FileNotFoundError:
        print(f"错误: 找不到 {input_file} 文件")
        return
    except json.JSONDecodeError as e:
        print(f"错误: JSON文件格式错误 - {e}")
        return
    
    # 统计信息
    total_books = len(books)
    skipped_translated = 0  # 已有中文标题的书籍数量
    skipped_no_original = 0  # 无英文标题的书籍数量
    translated_books = 0
    failed_books = 0
    
    print("开始批量翻译英文标题...")
    print(f"使用并发数: 20")
    print("-" * 50)
    
    # 准备需要翻译的书籍数据
    books_to_translate = []
    for i, book in enumerate(books, 1):
        books_to_translate.append((book, i, total_books, API_KEY, SOURCE_FIELD, TARGET_FIELD))
    
    # 使用线程池执行并发翻译
    with ThreadPoolExecutor(max_workers=20) as executor:
        # 提交所有翻译任务
        future_to_book = {executor.submit(translate_book_title, book_data): book_data for book_data in books_to_translate}
        
        # 处理完成的任务
        for future in as_completed(future_to_book):
            book_data = future_to_book[future]
            try:
                result = future.result()
                if result['status'] == 'success':
                    translated_books += 1
                    print(f"  [SUCCESS] {result['message']}")
                elif result['status'] == 'skipped':
                    print(f"  [SKIPPED] {result['message']}")
                    # 根据跳过原因分别统计
                    if '已有中文标题' in result['message']:
                        skipped_translated += 1
                    elif '无英文标题' in result['message']:
                        skipped_no_original += 1
                    else:
                        skipped_translated += 1  # 默认归类
                else:
                    print(f"  [FAILED] {result['message']}")
                    failed_books += 1
                
                # 更新原书籍数据
                book_index = book_data[1] - 1
                books[book_index] = result['book']
                
                # 只有成功翻译的书籍才添加延迟避免API限制
                if result['status'] == 'success':
                    time.sleep(1)
                
            except Exception as e:
                print(f"  [ERROR] 处理书籍时出错: {e}")
                print(f"  [ERROR] 书籍数据: {book_data}")
                import traceback
                print(f"  [ERROR] 详细错误信息: {traceback.format_exc()}")
                failed_books += 1
    
    # 保存结果到新文件
    try:
        # 直接更新原数据结构中的books数组
        data['books'] = books
        
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("-" * 50)
        print(f"标题翻译完成！结果已保存到 {output_file}")
        print(f"总计: {total_books} 本书")
        print(f"跳过: {skipped_translated + skipped_no_original} 本（已有中文标题: {skipped_translated} 本，无英文标题: {skipped_no_original} 本）")
        print(f"成功: {translated_books} 本")
        print(f"失败: {failed_books} 本")
    except Exception as e:
        print(f"保存文件时出错: {e}")

if __name__ == "__main__":
    main()
