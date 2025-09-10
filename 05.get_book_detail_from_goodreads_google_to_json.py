#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
双数据源图书信息批量查询工具
支持 Google Books API 和 Goodreads 两种数据源
"""

# ==================== 用户配置区域 ====================
# 用户可以通过修改这里的值来选择使用哪种方法获取图书信息
# 可选值: "google" 或 "goodreads"
BOOK_INFO_SOURCE = "goodreads"  # 默认使用Google Books API

# 并发线程数配置（可根据网络情况调整）
# Google Books API 建议: 5-10
# Goodreads 建议: 2-3
MAX_WORKERS = 2

# 是否显示详细调试信息
DEBUG_MODE = False
# =====================================================

import requests
import json
import time
import re
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from bs4 import BeautifulSoup

def filter_version_notes(text):
    """
    如果开头第一句话包含ISBN，则删除第一句话
    
    Args:
        text (str): 原始文本
        
    Returns:
        str: 过滤后的文本
    """
    if not text:
        return text
    
    # 按句子分割（以句号、问号、感叹号分割）
    sentences = re.split(r'[.!?]+', text)
    
    if len(sentences) == 0:
        return text
    
    # 检查第一句话是否包含ISBN
    first_sentence = sentences[0].strip()
    if 'ISBN' in first_sentence.upper():
        # 删除第一句话，保留其余句子
        remaining_sentences = sentences[1:]
        result = '. '.join(sentence.strip() for sentence in remaining_sentences if sentence.strip())
        if result and not result.endswith('.'):
            result += '.'
        return result.strip()
    
    # 如果第一句话不包含ISBN，返回原文本
    return text

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

# ==================== Google Books API 函数 ====================

def get_book_info_google(title, author):
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
                # 过滤版本说明句子
                description = filter_version_notes(description)
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
                    'description': description if description else "",
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

# ==================== Goodreads 函数 ====================

def debug_print(message):
    """
    调试信息打印函数
    """
    if DEBUG_MODE:
        print(f"🐛 DEBUG: {message}")

def get_goodreads_headers():
    """
    获取Goodreads请求头
    """
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
    }

def find_matching_book_by_author_goodreads(search_url, target_author):
    """
    从Goodreads搜索结果中找到匹配指定作者的书
    
    Args:
        search_url (str): Goodreads搜索URL
        target_author (str): 目标作者名
        
    Returns:
        str: 匹配的书籍详情页面URL，如果没找到返回None
    """
    try:
        print(f"正在搜索匹配作者 '{target_author}' 的书籍...")
        debug_print(f"搜索URL: {search_url}")
        
        # 发送请求
        response = requests.get(search_url, headers=get_goodreads_headers(), timeout=60)
        response.raise_for_status()
        
        print(f"成功获取搜索结果页面，状态码: {response.status_code}")
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找所有搜索结果
        search_results = soup.find_all('tr', {'itemscope': True, 'itemtype': 'http://schema.org/Book'})
        
        print(f"找到 {len(search_results)} 个搜索结果")
        
        # 遍历搜索结果，查找匹配的作者
        for i, result in enumerate(search_results):
            # 提取作者名称
            author_link = result.find('a', class_='authorName')
            if author_link:
                author_span = author_link.find('span', {'itemprop': 'name'})
                if author_span:
                    author_name = author_span.get_text(strip=True)
                    print(f"结果 {i+1}: 作者 = {author_name}")
                    
                    # 检查是否匹配目标作者
                    if is_probable_same_author(target_author, [author_name]):
                        # 提取书籍链接
                        book_link = result.find('a', {'itemprop': 'url'})
                        if book_link:
                            href = book_link.get('href')
                            if href:
                                # 去除查询参数
                                clean_href = href.split('?')[0]
                                book_url = 'https://www.goodreads.com' + clean_href
                                print(f"找到匹配的书籍: {book_url}")
                                return book_url
            else:
                # 备用方法：直接查找itemprop="name"的span
                author_span = result.find('span', {'itemprop': 'name'}, class_=None)
                if author_span and author_span.parent and author_span.parent.get('class') == ['authorName']:
                    author_name = author_span.get_text(strip=True)
                    print(f"结果 {i+1}: 作者 = {author_name} (备用方法)")
                    
                    # 检查是否匹配目标作者
                    if is_probable_same_author(target_author, [author_name]):
                        # 提取书籍链接
                        book_link = result.find('a', {'itemprop': 'url'})
                        if book_link:
                            href = book_link.get('href')
                            if href:
                                # 去除查询参数
                                clean_href = href.split('?')[0]
                                book_url = 'https://www.goodreads.com' + clean_href
                                print(f"找到匹配的书籍: {book_url}")
                                return book_url
        
        print(f"未找到作者 '{target_author}' 的匹配书籍")
        return None
        
    except requests.exceptions.RequestException as e:
        print(f"搜索请求错误: {e}")
        return None
    except Exception as e:
        print(f"搜索解析错误: {e}")
        return None

def extract_goodreads_detailed_info(book_url):
    """
    从Goodreads书籍详情页面提取所有详细信息
    
    Args:
        book_url (str): 书籍详情页面URL
        
    Returns:
        dict: 包含所有详细信息的字典
    """
    try:
        print(f"正在访问书籍详情页面提取所有信息: {book_url}")
        
        # 发送请求
        response = requests.get(book_url, headers=get_goodreads_headers(), timeout=60)
        response.raise_for_status()
        
        print(f"成功获取书籍详情页面，状态码: {response.status_code}")
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        detailed_info = {}
        
        # 1. 提取详细评分信息
        print("提取评分信息...")
        rating_stats = soup.find('a', class_='RatingStatistics')
        if rating_stats:
            # 提取平均评分
            rating_value = rating_stats.find('div', class_='RatingStatistics__rating')
            if rating_value:
                try:
                    detailed_info['avg_rating'] = float(rating_value.get_text(strip=True))
                    print(f"平均评分: {detailed_info['avg_rating']}")
                except ValueError:
                    pass
            
            # 提取评分数量和评论数量
            meta_div = rating_stats.find('div', class_='RatingStatistics__meta')
            if meta_div:
                # 提取评分数量
                ratings_span = meta_div.find('span', {'data-testid': 'ratingsCount'})
                if ratings_span:
                    ratings_text = ratings_span.get_text(strip=True)
                    ratings_match = re.search(r'([\d,]+)\s*ratings', ratings_text)
                    if ratings_match:
                        detailed_info['rating_count'] = int(ratings_match.group(1).replace(',', ''))
                        print(f"评分数量: {detailed_info['rating_count']}")
                
                # 提取评论数量
                reviews_span = meta_div.find('span', {'data-testid': 'reviewsCount'})
                if reviews_span:
                    reviews_text = reviews_span.get_text(strip=True)
                    reviews_match = re.search(r'([\d,]+)\s*reviews', reviews_text)
                    if reviews_match:
                        detailed_info['review_count'] = int(reviews_match.group(1).replace(',', ''))
                        print(f"评论数量: {detailed_info['review_count']}")
        
        # 2. 提取作者信息
        print("提取作者信息...")
        author_link = soup.find('a', class_='authorName')
        if author_link:
            author_span = author_link.find('span', {'itemprop': 'name'})
            if author_span:
                detailed_info['author'] = author_span.get_text(strip=True)
                print(f"作者: {detailed_info['author']}")
        
        # 备用方法：从JSON-LD提取作者
        if not detailed_info.get('author'):
            json_script = soup.find('script', type='application/ld+json')
            if json_script:
                try:
                    json_data = json.loads(json_script.string)
                    if 'author' in json_data and isinstance(json_data['author'], list) and len(json_data['author']) > 0:
                        author_name = json_data['author'][0].get('name', '')
                        if author_name:
                            detailed_info['author'] = author_name
                            print(f"从JSON-LD提取作者: {author_name}")
                except (json.JSONDecodeError, KeyError, ValueError):
                    pass
        
        # 3. 提取书籍描述和作者介绍（按顺序）
        print("提取书籍描述和作者介绍...")
        
        # 查找包含Formatted span的div
        formatted_divs = soup.find_all('div', class_='DetailsLayoutRightParagraph__widthConstrained')
        print(f"找到 {len(formatted_divs)} 个 DetailsLayoutRightParagraph__widthConstrained div")
        
        # 初始化字段
        detailed_info['description'] = ""
        detailed_info['author_bio'] = ""
        detailed_info['pages'] = ""
        detailed_info['first_published_year'] = ""
        detailed_info['isbn13'] = ""
        
        # 第一个是书籍描述
        if len(formatted_divs) >= 1:
            description_span = formatted_divs[0].find('span', class_='Formatted')
            if description_span:
                description = description_span.get_text(strip=True)
                # 清理HTML标签和特殊字符
                description = description.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                description = re.sub(r'\n+', '\n', description).strip()
                
                # 过滤版本说明句子
                description = filter_version_notes(description)
                
                if description and len(description) > 50:
                    detailed_info['description'] = description
                    print(f"书籍描述: {description[:100]}...")
                else:
                    print("书籍描述: 未找到有效内容")
            else:
                print("书籍描述: 未找到Formatted span")
        else:
            print("书籍描述: 未找到DetailsLayoutRightParagraph__widthConstrained div")
        
        # 第二个是作者介绍
        if len(formatted_divs) >= 2:
            author_bio_span = formatted_divs[1].find('span', class_='Formatted')
            if author_bio_span:
                author_bio = author_bio_span.get_text(strip=True)
                # 清理HTML标签和特殊字符
                author_bio = author_bio.replace('<br>', '\n').replace('<br/>', '\n').replace('<br />', '\n')
                author_bio = re.sub(r'\n+', '\n', author_bio).strip()
                if author_bio and len(author_bio) > 50:
                    detailed_info['author_bio'] = author_bio
                    print(f"作者介绍: {author_bio[:100]}...")
                else:
                    print("作者介绍: 未找到有效内容")
            else:
                print("作者介绍: 未找到Formatted span")
        else:
            print("作者介绍: 未找到第二个DetailsLayoutRightParagraph__widthConstrained div")
        
        # 4. 提取页数和首次出版年份
        print("提取页数和首次出版年份...")
        featured_details = soup.find('div', class_='FeaturedDetails')
        if featured_details:
            # 提取页数
            pages_element = featured_details.find('p', {'data-testid': 'pagesFormat'})
            if pages_element:
                pages_text = pages_element.get_text(strip=True)
                # 提取数字部分
                pages_match = re.search(r'(\d+)', pages_text)
                if pages_match:
                    detailed_info['pages'] = int(pages_match.group(1))
                    print(f"页数: {detailed_info['pages']}")
                else:
                    print("页数: 未找到数字")
            else:
                print("页数: 未找到pagesFormat元素")
            
            # 提取首次出版年份
            publication_element = featured_details.find('p', {'data-testid': 'publicationInfo'})
            if publication_element:
                publication_text = publication_element.get_text(strip=True)
                # 提取年份
                year_match = re.search(r'(\d{4})', publication_text)
                if year_match:
                    detailed_info['first_published_year'] = int(year_match.group(1))
                    print(f"首次出版年份: {detailed_info['first_published_year']}")
                else:
                    print("首次出版年份: 未找到年份")
            else:
                print("首次出版年份: 未找到publicationInfo元素")
        else:
            print("页数和首次出版年份: 未找到FeaturedDetails元素")
        
        # 5. 提取ISBN 13
        print("提取ISBN 13...")
        
        # 方法1：从JSON-LD中提取
        json_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_scripts:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and data.get('@type') == 'Book':
                    isbn = data.get('isbn')
                    if isbn and len(isbn) == 13 and (isbn.startswith('978') or isbn.startswith('979')):
                        detailed_info['isbn13'] = isbn
                        print(f"ISBN 13 (JSON-LD): {detailed_info['isbn13']}")
                        break
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        
        # 方法2：如果JSON-LD中没有找到，尝试从EditionDetails中提取
        if not detailed_info['isbn13']:
            edition_details = soup.find('div', class_='EditionDetails')
            if edition_details:
                # 查找ISBN相关的DescListItem
                desc_items = edition_details.find_all('div', class_='DescListItem')
                for item in desc_items:
                    dt = item.find('dt')
                    if dt and dt.get_text(strip=True) == 'ISBN':
                        dd = item.find('dd')
                        if dd:
                            # 查找包含ISBN的文本内容
                            content_container = dd.find('div', {'data-testid': 'contentContainer'})
                            if content_container:
                                isbn_text = content_container.get_text(strip=True)
                                # 提取ISBN 13（13位数字，通常以978或979开头）
                                isbn13_match = re.search(r'(\d{13})', isbn_text)
                                if isbn13_match:
                                    detailed_info['isbn13'] = isbn13_match.group(1)
                                    print(f"ISBN 13 (EditionDetails): {detailed_info['isbn13']}")
                                else:
                                    print("ISBN 13: 未找到13位数字")
                            else:
                                print("ISBN 13: 未找到contentContainer")
                        else:
                            print("ISBN 13: 未找到dd元素")
                        break
                else:
                    print("ISBN 13: 未找到ISBN相关的DescListItem")
            else:
                print("ISBN 13: 未找到EditionDetails元素")
        
        # 如果仍然没有找到，输出提示
        if not detailed_info['isbn13']:
            print("ISBN 13: 未找到ISBN 13信息")
        
        # 6. 提取书籍类型（Genres）
        print("提取书籍类型...")
        genres_div = soup.find('div', {'data-testid': 'genresList'})
        if genres_div:
            # 查找所有genre按钮
            genre_buttons = genres_div.find_all('a', class_='Button--tag')
            genres = []
            for button in genre_buttons:
                label_item = button.find('span', class_='Button__labelItem')
                if label_item:
                    genre_text = label_item.get_text(strip=True)
                    if genre_text and genre_text != '...more':  # 排除"更多"按钮
                        genres.append(genre_text)
            
            if genres:
                detailed_info['genres'] = genres
                print(f"书籍类型: {', '.join(genres)}")
            else:
                print("书籍类型: 未找到有效的类型")
        else:
            print("书籍类型: 未找到genresList元素")
        
        return detailed_info if detailed_info else None
        
    except requests.exceptions.RequestException as e:
        print(f"请求书籍详情页面错误: {e}")
        return None
    except Exception as e:
        print(f"解析书籍详情页面错误: {e}")
        return None

def get_book_info_goodreads(title, author):
    """
    从Goodreads获取图书信息
    """
    try:
        # 构建搜索URL
        search_url = f"https://www.goodreads.com/search?utf8=%E2%9C%93&q={requests.utils.quote(title)}&search_type=books&search%5Bfield%5D=title"
        
        print(f"🔍 正在Goodreads搜索: {title} - {author}")
        
        # 从搜索结果中找到匹配作者名的书籍
        book_url = find_matching_book_by_author_goodreads(search_url, author)
        
        if not book_url:
            print("❌ 未在Goodreads找到匹配的书籍")
            return None
        
        # 提取详细信息
        detailed_info = extract_goodreads_detailed_info(book_url)
        
        if not detailed_info:
            print("❌ 无法从Goodreads提取详细信息")
            return None
        
        # 转换为统一格式
        result = {
            'pages': detailed_info.get('pages'),
            'publishYear': detailed_info.get('first_published_year'),
            'description': detailed_info.get('description', ''),
            'genre': detailed_info.get('genres', []),  # 使用Goodreads提取的genres
            'isbn': detailed_info.get('isbn13'),
            # Goodreads额外信息
            'goodreads_rating': detailed_info.get('avg_rating'),
            'goodreads_rating_count': detailed_info.get('rating_count'),
            'goodreads_review_count': detailed_info.get('review_count'),
            'author_bio': detailed_info.get('author_bio', '')
        }
        
        # 显示提取的信息
        print(f"✅ 匹配书名: {title}")
        print(f"📖 页数: {result['pages'] if result['pages'] else '未知'}")
        print(f"👤 作者: {detailed_info.get('author', author)}")
        print(f"📅 出版年份: {result['publishYear'] if result['publishYear'] else '未知'}")
        print(f"🔖 ISBN: {result['isbn'] if result['isbn'] else '未知'}")
        
        # 显示分类信息
        if result['genre']:
            print(f"🏷️ 分类: {', '.join(result['genre'])}")
        else:
            print("🏷️ 分类: 暂无分类")
        
        # 显示Goodreads评分信息
        if result['goodreads_rating']:
            print(f"⭐ Goodreads评分: {result['goodreads_rating']}")
        if result['goodreads_rating_count']:
            print(f"📊 评分数量: {result['goodreads_rating_count']:,}")
        if result['goodreads_review_count']:
            print(f"💬 评论数量: {result['goodreads_review_count']:,}")
        
        if result['description']:
            desc_preview = result['description'][:200] + "..." if len(result['description']) > 200 else result['description']
            print(f"📝 图书描述: {desc_preview}")
        else:
            print("📝 图书描述: 暂无描述")
            
        if result['author_bio']:
            bio_preview = result['author_bio'][:100] + "..." if len(result['author_bio']) > 100 else result['author_bio']
            print(f"👨‍💼 作者介绍: {bio_preview}")
        else:
            print("👨‍💼 作者介绍: 暂无介绍")
        
        return result
        
    except Exception as e:
        print(f"❌ Goodreads查询出错: {str(e)}")
        return None

# ==================== 统一接口函数 ====================

def get_book_info(title, author):
    """
    统一的图书信息获取接口，根据配置选择数据源
    """
    if BOOK_INFO_SOURCE == "google":
        return get_book_info_google(title, author)
    elif BOOK_INFO_SOURCE == "goodreads":
        return get_book_info_goodreads(title, author)
    else:
        print(f"❌ 未知的数据源: {BOOK_INFO_SOURCE}")
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
        data['last_updated'] = datetime.utcnow().isoformat() + 'Z'
        
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
        if book_info.get('description'):
            book['description'] = book_info['description']
            print(f"📝 已更新图书介绍")
        
        # 更新分类信息
        if book_info.get('genre'):
            book['genre'] = book_info['genre']
            print(f"🏷️ 已更新分类信息: {', '.join(book_info['genre'])}")
        
        # 更新ISBN信息
        if book_info.get('isbn'):
            book['isbn'] = book_info['isbn']
            print(f"🔖 已更新ISBN: {book_info['isbn']}")
        
        # 更新Goodreads额外信息
        if book_info.get('goodreads_rating') is not None:
            book['goodreads_rating'] = book_info['goodreads_rating']
            print(f"⭐ 已更新Goodreads评分: {book_info['goodreads_rating']}")
        
        if book_info.get('goodreads_rating_count') is not None:
            book['goodreads_rating_count'] = book_info['goodreads_rating_count']
            print(f"📊 已更新评分数量: {book_info['goodreads_rating_count']:,}")
        
        if book_info.get('goodreads_review_count') is not None:
            book['goodreads_review_count'] = book_info['goodreads_review_count']
            print(f"💬 已更新评论数量: {book_info['goodreads_review_count']:,}")
        
        if book_info.get('author_bio'):
            book['author_bio'] = book_info['author_bio']
            print(f"👨‍💼 已更新作者介绍")
        
        return True
    return False

def process_single_book(args):
    """
    处理单本书籍的函数，用于并发执行
    """
    i, book, total_books = args
    title = book.get('title', '')
    author = book.get('author', '')
    
    if not title or not author:
        return {
            'type': 'incomplete',
            'index': i+1,
            'title': title,
            'author': author,
            'filename': book.get('filename', '未知文件名')
        }
    
    # 检查书籍是否已经有完整信息，如果有则跳过
    has_pages = book.get('pages') is not None and book.get('pages') > 0
    has_year = book.get('publishYear') is not None and book.get('publishYear') > 0
    has_description = book.get('description') and len(book.get('description', '').strip()) > 0
    has_genre = book.get('genre') and len(book.get('genre', [])) > 0
    has_isbn = book.get('isbn') and len(book.get('isbn', '').strip()) > 0
    
    # 如果书籍已经有足够的信息，则跳过
    if has_pages and has_year and has_description and has_genre and has_isbn:
        return {
            'type': 'skipped',
            'index': i+1,
            'title': title,
            'author': author,
            'reason': '已有完整信息'
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
    print(f"🔧 当前数据源: {BOOK_INFO_SOURCE.upper()}")
    if BOOK_INFO_SOURCE == "google":
        print("📖 使用 Google Books API")
    elif BOOK_INFO_SOURCE == "goodreads":
        print("📖 使用 Goodreads 网站")
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
    
    # 使用配置的并发数量
    max_workers = MAX_WORKERS
    print(f"🚀 使用 {max_workers} 个并发线程")
    print("=" * 60)
    
    # 记录匹配结果
    matched_books = []
    unmatched_books = []
    incomplete_books = []
    skipped_books = []
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
                    if 'description' not in book or not book['description']:
                        book['description'] = ""
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
                    if 'description' not in book or not book['description']:
                        book['description'] = ""
                    if 'genre' not in book or not book['genre']:
                        book['genre'] = []
                    if 'isbn' not in book or book['isbn'] is None:
                        book['isbn'] = None
                    print(f"   📝 已添加默认键值")
            
            elif result['type'] == 'skipped':
                skipped_books.append(result)
                print(f"⏭️ [{result['index']}/{len(books)}] 跳过已有完整信息: {result['title']}")
            
            # 显示进度
            progress_rate = (completed_count / len(books)) * 100
            print(f"📊 进度: [{completed_count}/{len(books)}] {progress_rate:.1f}% | ✅ {len(matched_books)} | ❌ {len(unmatched_books)} | ⚠️ {len(incomplete_books)} | ⏭️ {len(skipped_books)}")
    
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
    print(f"   ⏭️ 跳过已有: {len(skipped_books)}")
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
        rating_updated = 0
        rating_count_updated = 0
        review_count_updated = 0
        author_bio_updated = 0
        
        for book in matched_books:
            info = book['info']
            if info.get('pages') is not None:
                pages_updated += 1
            if info.get('publishYear') is not None:
                year_updated += 1
            if info.get('description'):
                desc_updated += 1
            if info.get('genre'):
                genre_updated += 1
            if info.get('isbn'):
                isbn_updated += 1
            if info.get('goodreads_rating') is not None:
                rating_updated += 1
            if info.get('goodreads_rating_count') is not None:
                rating_count_updated += 1
            if info.get('goodreads_review_count') is not None:
                review_count_updated += 1
            if info.get('author_bio'):
                author_bio_updated += 1
        
        print(f"   📖 页数信息: {pages_updated} 本")
        print(f"   📅 出版年份: {year_updated} 本")
        print(f"   📝 图书介绍: {desc_updated} 本")
        print(f"   🏷️ 分类信息: {genre_updated} 本")
        print(f"   🔖 ISBN信息: {isbn_updated} 本")
        print(f"   ⭐ Goodreads评分: {rating_updated} 本")
        print(f"   📊 评分数量: {rating_count_updated} 本")
        print(f"   💬 评论数量: {review_count_updated} 本")
        print(f"   👨‍💼 作者介绍: {author_bio_updated} 本")
        
        # 计算信息完整度
        total_possible_updates = len(matched_books) * 9  # 每本书最多9种信息（5个基础 + 4个Goodreads额外）
        actual_updates = pages_updated + year_updated + desc_updated + genre_updated + isbn_updated + rating_updated + rating_count_updated + review_count_updated + author_bio_updated
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
        books_with_desc = [book for book in matched_books if book['info'].get('description')]
        books_without_desc = [book for book in matched_books if not book['info'].get('description')]
        
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
            if info.get('description'):
                print(f"      📝 有介绍")
            if info.get('genre'):
                print(f"      🏷️ 分类: {', '.join(info['genre'])}")
            if info.get('isbn'):
                print(f"      🔖 ISBN: {info['isbn']}")
            if info.get('goodreads_rating'):
                print(f"      ⭐ 评分: {info['goodreads_rating']}")
            if info.get('goodreads_rating_count'):
                print(f"      📊 评分数: {info['goodreads_rating_count']:,}")
            if info.get('goodreads_review_count'):
                print(f"      💬 评论数: {info['goodreads_review_count']:,}")
            if info.get('author_bio'):
                print(f"      👨‍💼 有作者介绍")
            print()
        
        print("-" * 60)
    
    # 打印未匹配的图书清单
    if unmatched_books:
        print(f"\n❌ 未匹配的图书清单:")
        print("-" * 60)
        for book in unmatched_books:
            print(f"  {book['index']:2d}. {book['title']} - {book['author']}")
        print("-" * 60)
    
    # 打印跳过的图书清单
    if skipped_books:
        print(f"\n⏭️ 跳过的图书清单（已有完整信息）:")
        print("-" * 60)
        for book in skipped_books:
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
    
    if skipped_books:
        print(f"\n⏭️ 跳过了 {len(skipped_books)} 本已有完整信息的书籍，节省了查询时间")

if __name__ == "__main__":
    # ==================== 使用说明 ====================
    # 要切换数据源，请修改文件顶部的用户配置区域：
    # 1. BOOK_INFO_SOURCE: "google" 或 "goodreads"
    # 2. MAX_WORKERS: 并发线程数（Google建议5-10，Goodreads建议2-3）
    # 3. DEBUG_MODE: True/False 是否显示调试信息
    # ================================================
    
    print("🚀 启动图书信息批量查询工具...")
    main()
