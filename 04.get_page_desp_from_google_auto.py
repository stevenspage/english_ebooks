import requests
import json
import time
import re
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

def is_probable_same_author(input_author, result_authors):
    """
    判断输入作者名与结果作者列表中是否有可能是同一个人。
    智能匹配，处理缩写、全称、标点符号等差异。
    """
    if not result_authors:
        return False

    # 去除所有标点符号（包括逗号、点号、连字符、括号等）
    input_parts = set(re.sub(r'[^\w\s]', '', input_author.lower()).split())
    
    for candidate in result_authors:
        candidate_parts = set(re.sub(r'[^\w\s]', '', candidate.lower()).split())
        
        # 计算匹配的单词数量
        common_words = input_parts & candidate_parts
        
        # 策略1：如果有2个以上相同单词，直接匹配
        if len(common_words) >= 2:
            return True
        
        # 策略2：如果只有1个相同单词，检查是否是姓氏匹配
        if len(common_words) == 1:
            # 检查是否是常见的姓氏匹配
            common_surname = list(common_words)[0]
            if is_likely_surname(common_surname):
                # 进一步检查名字部分是否有相关性
                if has_name_correlation(input_parts, candidate_parts):
                    return True
        
        # 策略3：检查缩写匹配（如 Timothy G vs Tim）
        if has_abbreviation_match(input_parts, candidate_parts):
            return True
    
    return False

def is_likely_surname(word):
    """
    判断一个单词是否可能是姓氏
    """
    # 常见的英语姓氏
    common_surnames = {
        'collins', 'smith', 'jones', 'williams', 'brown', 'davis', 'miller',
        'wilson', 'moore', 'taylor', 'anderson', 'thomas', 'jackson', 'white',
        'harris', 'martin', 'thompson', 'garcia', 'martinez', 'robinson',
        'clark', 'rodriguez', 'lewis', 'lee', 'walker', 'hall', 'allen',
        'young', 'king', 'wright', 'lopez', 'hill', 'scott', 'green',
        'adams', 'baker', 'gonzalez', 'nelson', 'carter', 'mitchell',
        'perez', 'roberts', 'turner', 'phillips', 'campbell', 'parker',
        'evans', 'edwards', 'collins', 'stewart', 'sanchez', 'morris',
        'rogers', 'reed', 'cook', 'morgan', 'bell', 'murphy', 'bailey',
        'rivera', 'cooper', 'richardson', 'cox', 'howard', 'ward', 'torres',
        'peterson', 'gray', 'ramirez', 'james', 'watson', 'brooks', 'kelly',
        'sanders', 'price', 'bennett', 'wood', 'barnes', 'ross', 'henderson',
        'coleman', 'jenkins', 'perry', 'powell', 'long', 'patterson', 'hughes',
        'flores', 'washington', 'butler', 'simmons', 'foster', 'gonzales',
        'bryant', 'alexander', 'russell', 'griffin', 'diaz', 'hayes'
    }
    return word in common_surnames

def has_name_correlation(input_parts, candidate_parts):
    """
    检查名字部分是否有相关性（如 Timothy vs Tim）
    """
    # 常见的名字缩写对应关系
    name_variations = {
        'timothy': ['tim'],
        'thomas': ['tom', 'thom'],
        'william': ['will', 'bill', 'billy'],
        'robert': ['rob', 'bob', 'bobby'],
        'michael': ['mike', 'mick'],
        'christopher': ['chris'],
        'nicholas': ['nick'],
        'daniel': ['dan', 'danny'],
        'matthew': ['matt'],
        'andrew': ['andy', 'drew'],
        'joseph': ['joe', 'joey'],
        'david': ['dave', 'davey'],
        'richard': ['rick', 'dick', 'richie'],
        'charles': ['charlie', 'chuck'],
        'james': ['jim', 'jimmy'],
        'john': ['johnny', 'jack'],
        'steven': ['steve'],
        'kevin': ['kev'],
        'brian': ['bri'],
        'jason': ['jay'],
        'justin': ['just'],
        'brandon': ['brand'],
        'ryan': ['ry'],
        'gary': ['gar'],
        'nathan': ['nate'],
        'adam': ['ad'],
        'mark': ['marky'],
        'donald': ['don', 'donny'],
        'steven': ['steve'],
        'paul': ['paulie'],
        'kenneth': ['ken', 'kenny'],
        'ronald': ['ron', 'ronnie'],
        'anthony': ['tony', 'ant'],
        'kevin': ['kev'],
        'jason': ['jay'],
        'matthew': ['matt'],
        'gary': ['gar'],
        'timothy': ['tim']
    }
    
    # 检查是否有名字变体匹配
    for input_part in input_parts:
        for candidate_part in candidate_parts:
            # 检查是否是变体关系
            if input_part in name_variations and candidate_part in name_variations[input_part]:
                return True
            if candidate_part in name_variations and input_part in name_variations[candidate_part]:
                return True
    
    return False

def has_abbreviation_match(input_parts, candidate_parts):
    """
    检查是否有缩写匹配（如 G vs George）
    """
    # 检查单字母是否可能是名字缩写
    for part in input_parts:
        if len(part) == 1 and part.isalpha():
            # 检查这个字母是否在候选名字中出现
            for candidate_part in candidate_parts:
                if candidate_part.startswith(part.lower()):
                    return True
    
    for part in candidate_parts:
        if len(part) == 1 and part.isalpha():
            # 检查这个字母是否在输入名字中出现
            for input_part in input_parts:
                if input_part.startswith(part.lower()):
                    return True
    
    return False

def is_valid_cover(url):
    """
    验证封面链接是否有效：
    - 响应为 200
    - 返回类型为 image/jpeg
    - 内容大小超过 5KB（避免默认黑图或占位图）
    """
    try:
        r = requests.get(url, timeout=5)
        content_type = r.headers.get("Content-Type", "")
        return (
            r.status_code == 200 and
            content_type == "image/jpeg" and
            len(r.content) > 5000
        )
    except Exception:
        return False

def get_book_info(title, author):
    """
    查询 Google Books API，返回页数、匹配作者名、图书描述、出版信息等。
    并使用 ISBN 去 Open Library 获取有效封面链接。
    """
    query = f"{title} {author}"
    url = f"https://www.googleapis.com/books/v1/volumes?q={requests.utils.quote(query)}"

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print("❌ 查询失败")
            return None

        data = response.json()

        for item in data.get("items", []):
            volume_info = item.get("volumeInfo", {})
            result_authors = volume_info.get("authors", [])

            if is_probable_same_author(author, result_authors):
                page_count = volume_info.get("pageCount")
                title_result = volume_info.get("title", "未知标题")
                description = volume_info.get("description", "")
                published_date = volume_info.get("publishedDate", "")
                publisher = volume_info.get("publisher", "")
                categories = volume_info.get("categories", [])
                language = volume_info.get("language", "")
                
                print(f"✅ 匹配书名: {title_result}")
                print(f"📖 页数: {page_count if page_count else '未知'}")
                print(f"👤 匹配的作者名（API返回）: {', '.join(result_authors)}")
                
                if published_date:
                    print(f"📅 出版日期: {published_date}")
                if publisher:
                    print(f"🏢 出版社: {publisher}")
                if language:
                    print(f"🌐 语言: {language}")
                if categories:
                    print(f"📚 分类: {', '.join(categories)}")
                
                if description:
                    # 截取描述的前200个字符，避免输出过长
                    desc_preview = description[:200] + "..." if len(description) > 200 else description
                    print(f"📝 图书描述: {desc_preview}")
                else:
                    print("📝 图书描述: 暂无描述")

                # 尝试获取ISBN
                isbn_13 = isbn_10 = None
                for identifier in volume_info.get("industryIdentifiers", []):
                    if identifier.get("type") == "ISBN_13":
                        isbn_13 = identifier.get("identifier")
                    elif identifier.get("type") == "ISBN_10":
                        isbn_10 = identifier.get("identifier")

                isbn = isbn_13 or isbn_10
                if isbn:
                    print(f"🔖 ISBN号: {isbn}")
                else:
                    print("❗️未找到ISBN，无法获取 Open Library 封面")

                # 如果页数未知，尝试通过 selfLink 获取更详细信息
                if not page_count:
                    self_link = item.get("selfLink", "")
                    volume_id = item.get("id", "")
                    
                    if self_link and volume_id:
                        print(f"🔍 页数未知，尝试通过 selfLink 获取详细信息...")
                        print(f"🔗 Self Link: {self_link}")
                        
                        try:
                            # 通过 selfLink 再次查询
                            detail_response = requests.get(self_link, timeout=10)
                            if detail_response.status_code == 200:
                                detail_data = detail_response.json()
                                detail_volume_info = detail_data.get("volumeInfo", {})
                                detail_page_count = detail_volume_info.get("pageCount")
                                
                                if detail_page_count:
                                    print(f"✅ 通过 selfLink 获取到页数: {detail_page_count}")
                                    page_count = detail_page_count
                                else:
                                    print(f"❌ 通过 selfLink 仍未获取到页数")
                            else:
                                print(f"❌ selfLink 查询失败，状态码: {detail_response.status_code}")
                        except Exception as e:
                            print(f"❌ selfLink 查询出错: {str(e)}")
                    else:
                        print(f"❌ 无法获取 selfLink 或 Volume ID")
                
                # 提取出版年份
                publish_year = None
                if published_date:
                    # 尝试从出版日期中提取年份
                    year_match = re.search(r'(\d{4})', published_date)
                    if year_match:
                        publish_year = int(year_match.group(1))
                        print(f"📅 提取到出版年份: {publish_year}")
                
                # 返回包含所有信息的字典
                return {
                    'pages': page_count if page_count else None,
                    'publishYear': publish_year,
                    'description_review_original': description if description else "",
                    'genre': categories if categories else [],
                    'isbn': isbn if isbn else None
                }

        # 分析未找到匹配的原因
        print("❗️未找到匹配的作者/书籍")
        print("🔍 失败原因分析:")
        
        # 检查是否有返回结果但作者不匹配
        if data.get("items"):
            print("   • 有返回结果，但作者名不匹配")
            print("   • 建议检查作者名拼写或格式")
        else:
            print("   • Google Books API 中无此书籍数据")
            print("   • 可能原因：新书、小众书籍、地区限制等")
        
        return None
        
    except Exception as e:
        print(f"❌ 查询出错: {str(e)}")
        return None

def load_book_info():
    """
    从book_info.json加载书籍信息
    """
    try:
        with open('book_info.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data
    except Exception as e:
        print(f"❌ 读取book_info.json失败: {str(e)}")
        return None

def save_book_info(data):
    """
    保存书籍信息到book_info.json
    """
    try:
        # 更新最后更新时间
        data['lastUpdated'] = datetime.utcnow().isoformat() + 'Z'
        
        with open('book_info.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("✅ 书籍信息已保存到 book_info.json")
        return True
    except Exception as e:
        print(f"❌ 保存book_info.json失败: {str(e)}")
        return False

def update_book_info(books, book_index, book_info):
    """
    更新指定书籍的信息
    """
    if book_info and book_index < len(books):
        book = books[book_index]
        
        # 更新页数
        if book_info.get('pages') is not None:
            book['pages'] = book_info['pages']
            print(f"📖 已更新页数: {book_info['pages']}")
        
        # 更新出版年份
        if book_info.get('publishYear') is not None:
            book['publishYear'] = book_info['publishYear']
            print(f"📅 已更新出版年份: {book_info['publishYear']}")
        
        # 更新图书介绍
        if book_info.get('description_review_original'):
            book['description_review_original'] = book_info['description_review_original']
            print(f"📝 已更新图书介绍")
        
        # 更新分类信息
        if book_info.get('genre'):
            book['genre'] = book_info['genre']
            print(f"🏷️ 已更新分类信息: {', '.join(book_info['genre'])}")
        
        # 更新ISBN信息
        if book_info.get('isbn'):
            book['isbn'] = book_info['isbn']
            print(f"🔖 已更新ISBN: {book_info['isbn']}")
        
        return True
    return False

def process_single_book(args):
    """
    处理单本书籍的函数，用于并发执行
    """
    i, book, total_books = args
    title = book.get('original_title', '')
    author = book.get('author', '')
    
    if not title or not author:
        return {
            'type': 'incomplete',
            'index': i+1,
            'title': title,
            'author': author,
            'filename': book.get('filename', '未知文件名')
        }
    
    print(f"🔍 [{i+1}/{total_books}] 正在查询：{title} - {author}")
    
    # 执行查询
    result = get_book_info(title, author)
    
    if result is not None:
        return {
            'type': 'matched',
            'index': i+1,
            'title': title,
            'author': author,
            'info': result
        }
    else:
        return {
            'type': 'unmatched',
            'index': i+1,
            'title': title,
            'author': author
        }

def main():
    """
    主函数：从book_info.json读取所有书籍信息并并发查询
    """
    print("📚 图书信息批量查询工具（并发加速版）")
    print("=" * 60)
    
    # 加载书籍信息
    data = load_book_info()
    if not data:
        print("❌ 没有找到书籍信息")
        return
    
    books = data.get('books', [])
    if not books:
        print("❌ 没有找到书籍信息")
        return
    
    print(f"📖 共找到 {len(books)} 本书籍")
    
    # 使用默认并发数量
    max_workers = 5
    print(f"🚀 使用 {max_workers} 个并发线程")
    print("=" * 60)
    
    # 记录匹配结果
    matched_books = []
    unmatched_books = []
    incomplete_books = []
    updated_count = 0
    
    # 准备任务参数
    task_args = [(i, book, len(books)) for i, book in enumerate(books)]
    
    # 使用线程池执行并发查询
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_book = {executor.submit(process_single_book, args): args for args in task_args}
        
        # 处理完成的任务
        completed_count = 0
        for future in as_completed(future_to_book):
            completed_count += 1
            result = future.result()
            
            if result['type'] == 'matched':
                matched_books.append(result)
                print(f"🎉 [{result['index']}/{len(books)}] 匹配成功: {result['title']}")
                
                # 更新书籍信息
                book_index = result['index'] - 1
                if update_book_info(books, book_index, result['info']):
                    updated_count += 1
                    
            elif result['type'] == 'unmatched':
                unmatched_books.append(result)
                print(f"❌ [{result['index']}/{len(books)}] 匹配失败: {result['title']}")
                
                # 为未匹配的图书添加默认键值
                book_index = result['index'] - 1
                if book_index < len(books):
                    book = books[book_index]
                    # 设置默认值
                    if 'pages' not in book or book['pages'] is None:
                        book['pages'] = None
                    if 'publishYear' not in book or book['publishYear'] is None:
                        book['publishYear'] = None
                    if 'description_review_original' not in book or not book['description_review_original']:
                        book['description_review_original'] = ""
                    if 'genre' not in book or not book['genre']:
                        book['genre'] = []
                    if 'isbn' not in book or book['isbn'] is None:
                        book['isbn'] = None
                    print(f"   📝 已添加默认键值")
                
            elif result['type'] == 'incomplete':
                incomplete_books.append(result)
                print(f"⚠️ [{result['index']}/{len(books)}] 信息不完整: {result['title']}")
                
                # 为信息不完整的图书添加默认键值
                book_index = result['index'] - 1
                if book_index < len(books):
                    book = books[book_index]
                    # 设置默认值
                    if 'pages' not in book or book['pages'] is None:
                        book['pages'] = None
                    if 'publishYear' not in book or book['publishYear'] is None:
                        book['publishYear'] = None
                    if 'description_review_original' not in book or not book['description_review_original']:
                        book['description_review_original'] = ""
                    if 'genre' not in book or not book['genre']:
                        book['genre'] = []
                    if 'isbn' not in book or book['isbn'] is None:
                        book['isbn'] = None
                    print(f"   📝 已添加默认键值")
            
            # 显示进度
            progress_rate = (completed_count / len(books)) * 100
            print(f"📊 进度: [{completed_count}/{len(books)}] {progress_rate:.1f}% | ✅ {len(matched_books)} | ❌ {len(unmatched_books)} | ⚠️ {len(incomplete_books)}")
    
    end_time = time.time()
    total_time = end_time - start_time
    
    print(f"\n⏱️ 并发查询完成，总耗时: {total_time:.2f} 秒")
    print(f"🚀 平均每本书耗时: {total_time/len(books):.2f} 秒")
    
    # 保存更新后的信息
    if updated_count > 0:
        print(f"\n💾 正在保存更新后的信息...")
        if save_book_info(data):
            print(f"✅ 成功保存了 {updated_count} 本书的更新信息")
        else:
            print("❌ 保存失败")
    else:
        print(f"\n💾 没有需要保存的更新信息")
    
    # 打印最终统计信息
    print(f"\n🎉 批量查询完成！")
    print("=" * 60)
    print(f"📊 统计信息:")
    print(f"   📖 总书籍数: {len(books)}")
    print(f"   ✅ 成功匹配: {len(matched_books)}")
    print(f"   ❌ 未匹配: {len(unmatched_books)}")
    print(f"   ⚠️ 信息不完整: {len(incomplete_books)}")
    print(f"   📈 匹配率: {(len(matched_books)/len(books)*100):.1f}%")
    print(f"   💾 信息更新: {updated_count} 本")
    
    # 详细统计写入的信息类型
    if updated_count > 0:
        print(f"\n📝 写入信息详细统计:")
        
        # 统计各类型信息的更新数量
        pages_updated = 0
        year_updated = 0
        desc_updated = 0
        genre_updated = 0
        isbn_updated = 0
        
        for book in matched_books:
            info = book['info']
            if info.get('pages') is not None:
                pages_updated += 1
            if info.get('publishYear') is not None:
                year_updated += 1
            if info.get('description_review_original'):
                desc_updated += 1
            if info.get('genre'):
                genre_updated += 1
            if info.get('isbn'):
                isbn_updated += 1
        
        print(f"   📖 页数信息: {pages_updated} 本")
        print(f"   📅 出版年份: {year_updated} 本")
        print(f"   📝 图书介绍: {desc_updated} 本")
        print(f"   🏷️ 分类信息: {genre_updated} 本")
        print(f"   🔖 ISBN信息: {isbn_updated} 本")
        
        # 计算信息完整度
        total_possible_updates = len(matched_books) * 5  # 每本书最多5种信息
        actual_updates = pages_updated + year_updated + desc_updated + genre_updated + isbn_updated
        update_completeness = (actual_updates / total_possible_updates * 100) if total_possible_updates > 0 else 0
        
        print(f"   📊 信息完整度: {update_completeness:.1f}% ({actual_updates}/{total_possible_updates})")
    else:
        print(f"\n📝 本次查询没有写入任何新信息")
    
    # 页数信息统计
    if matched_books:
        books_with_pages = [book for book in matched_books if book['info'].get('pages')]
        books_without_pages = [book for book in matched_books if not book['info'].get('pages')]
        
        print(f"\n📖 页数信息统计:")
        print(f"   📊 有页数信息: {len(books_with_pages)} 本")
        print(f"   ❓ 无页数信息: {len(books_without_pages)} 本")
        print(f"   📈 页数完整率: {(len(books_with_pages)/len(matched_books)*100):.1f}%")
    
    # 出版年份信息统计
    if matched_books:
        books_with_year = [book for book in matched_books if book['info'].get('publishYear')]
        books_without_year = [book for book in matched_books if not book['info'].get('publishYear')]
        
        print(f"\n📅 出版年份信息统计:")
        print(f"   📊 有年份信息: {len(books_with_year)} 本")
        print(f"   ❓ 无年份信息: {len(books_without_year)} 本")
        print(f"   📈 年份完整率: {(len(books_with_year)/len(matched_books)*100):.1f}%")
    
    # 图书介绍信息统计
    if matched_books:
        books_with_desc = [book for book in matched_books if book['info'].get('description_review_original')]
        books_without_desc = [book for book in matched_books if not book['info'].get('description_review_original')]
        
        print(f"\n📝 图书介绍信息统计:")
        print(f"   📊 有介绍信息: {len(books_with_desc)} 本")
        print(f"   ❓ 无介绍信息: {len(books_without_desc)} 本")
        print(f"   📈 介绍完整率: {(len(books_with_desc)/len(matched_books)*100):.1f}%")
    
    # 打印已匹配的图书清单
    if matched_books:
        print(f"\n✅ 已匹配的图书清单:")
        print("-" * 60)
        
        for book in matched_books:
            info = book['info']
            print(f"  {book['index']:2d}. {book['title']} - {book['author']}")
            if info.get('pages'):
                print(f"      📖 页数: {info['pages']}")
            if info.get('publishYear'):
                print(f"      📅 年份: {info['publishYear']}")
            if info.get('description_review_original'):
                print(f"      📝 有介绍")
            if info.get('genre'):
                print(f"      🏷️ 分类: {', '.join(info['genre'])}")
            if info.get('isbn'):
                print(f"      🔖 ISBN: {info['isbn']}")
            print()
        
        print("-" * 60)
    
    # 打印未匹配的图书清单
    if unmatched_books:
        print(f"\n❌ 未匹配的图书清单:")
        print("-" * 60)
        for book in unmatched_books:
            print(f"  {book['index']:2d}. {book['title']} - {book['author']}")
        print("-" * 60)
    
    # 打印信息不完整的图书清单
    if incomplete_books:
        print(f"\n⚠️ 信息不完整的图书清单:")
        print("-" * 60)
        for book in incomplete_books:
            print(f"  {book['index']:2d}. {book['filename']}")
            print(f"     书名: '{book['title']}' | 作者: '{book['author']}'")
        print("-" * 60)
        
    # 总结
    if not unmatched_books and not incomplete_books:
        print(f"\n🎊 太棒了！所有书籍都成功匹配了！")
    elif not unmatched_books:
        print(f"\n🎉 所有可处理的书籍都成功匹配了！")
    else:
        print(f"\n📝 部分书籍需要进一步处理")

# 示例用法（保留原有功能）
def interactive_mode():
    """
    交互式模式：手动输入书名和作者
    """
    print("📚 图书信息查询工具（交互式模式）")
    print("=" * 50)
    
    while True:
        print("\n" + "=" * 50)
        title_input = input("请输入书名（输入 'quit' 或 'exit' 退出）：").strip()
        
        # 检查退出条件
        if title_input.lower() in ['quit', 'exit', '退出', 'q']:
            print("👋 感谢使用，再见！")
            break
            
        if not title_input:
            print("❌ 书名不能为空，请重新输入")
            continue
            
        author_input = input("请输入作者名：").strip()
        
        if not author_input:
            print("❌ 作者名不能为空，请重新输入")
            continue
        
        print(f"\n🔍 正在查询：{title_input} - {author_input}")
        print("-" * 30)
        
        # 执行查询
        result = get_book_info(title_input, author_input)
        
        if result:
            print(f"\n📊 查询结果:")
            if result.get('pages'):
                print(f"📖 页数: {result['pages']}")
            if result.get('publishYear'):
                print(f"📅 出版年份: {result['publishYear']}")
            if result.get('description_review_original'):
                print(f"📝 图书介绍: {result['description_review_original'][:100]}...")
            if result.get('genre'):
                print(f"🏷️ 分类: {', '.join(result['genre'])}")
            if result.get('isbn'):
                print(f"🔖 ISBN: {result['isbn']}")
        
        print("\n" + "-" * 30)
        print("✅ 查询完成，请继续输入下一本书的信息...")

if __name__ == "__main__":
    # 暂时绕过交互模式选择，直接运行批量查询模式
    # print("请选择运行模式：")
    # print("1. 批量查询模式（从book_info.json读取）")
    # print("2. 交互式模式（手动输入）")
    # 
    # choice = input("请输入选择 (1 或 2): ").strip()
    # 
    # if choice == "1":
    #     main()
    # elif choice == "2":
    #     interactive_mode()
    # else:
    #     print("❌ 无效选择，默认运行批量查询模式")
    #     main()
    
    # 直接运行批量查询模式
    print("🚀 自动运行批量查询模式...")
    main()
