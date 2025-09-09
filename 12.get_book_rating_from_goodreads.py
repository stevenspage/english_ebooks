#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从Goodreads搜索结果页面提取第一个结果的信息
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re

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

def extract_first_result_from_goodreads(url):
    """
    从Goodreads搜索结果页面提取第一个结果的信息
    
    Args:
        url (str): Goodreads搜索结果页面URL
        
    Returns:
        dict: 包含第一个结果信息的字典
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        print(f"正在访问URL: {url}")
        
        # 发送请求
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()
        
        print(f"成功获取页面，状态码: {response.status_code}")
        
        # 解析HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 查找第一个搜索结果
        # 根据HTML结构，第一个结果在第一个包含itemscope itemtype="http://schema.org/Book"的tr标签中
        first_result = soup.find('tr', {'itemscope': True, 'itemtype': 'http://schema.org/Book'})
        
        if not first_result:
            print("未找到搜索结果")
            return None
            
        print("找到第一个搜索结果，开始提取信息...")
        
        # 提取书籍信息
        result_info = {}
        
        # 1. 书籍标题
        title_element = first_result.find('span', {'itemprop': 'name'}, role='heading')
        if title_element:
            result_info['title'] = title_element.get_text(strip=True)
            print(f"标题: {result_info['title']}")
        
        # 3. 书籍链接
        book_link = first_result.find('a', class_='bookTitle')
        if book_link:
            href = book_link.get('href')
            if href:
                # 去除查询参数（?后面的部分）
                clean_href = href.split('?')[0]
                result_info['book_url'] = 'https://www.goodreads.com' + clean_href
                print(f"书籍链接: {result_info['book_url']}")
        
        # 4. 封面图片
        cover_img = first_result.find('img', class_='bookCover')
        if cover_img:
            result_info['cover_image'] = cover_img.get('src')
            print(f"封面图片: {result_info['cover_image']}")
        
        # 5. 评分信息
        rating_text = first_result.find('span', class_='minirating')
        if rating_text:
            rating_text_content = rating_text.get_text(strip=True)
            # 使用正则表达式提取评分和评价数量
            rating_match = re.search(r'(\d+\.\d+)\s+avg rating.*?(\d+(?:,\d+)*)\s+ratings', rating_text_content)
            if rating_match:
                result_info['avg_rating'] = float(rating_match.group(1))
                result_info['rating_count'] = int(rating_match.group(2).replace(',', ''))
                print(f"平均评分: {result_info['avg_rating']}")
                print(f"评价数量: {result_info['rating_count']}")
        
        # 6. 作者名称
        author_link = first_result.find('a', class_='authorName')
        if author_link:
            author_span = author_link.find('span', {'itemprop': 'name'})
            if author_span:
                result_info['author'] = author_span.get_text(strip=True)
                print(f"作者: {result_info['author']}")
        else:
            # 备用方法：直接查找itemprop="name"的span
            author_span = first_result.find('span', {'itemprop': 'name'}, class_=None)
            if author_span and author_span.parent and author_span.parent.get('class') == ['authorName']:
                result_info['author'] = author_span.get_text(strip=True)
                print(f"作者 (备用方法): {result_info['author']}")
        
        # 7. 出版年份
        published_text = first_result.find('span', class_='greyText smallText uitext')
        if published_text:
            published_content = published_text.get_text()
            year_match = re.search(r'published\s+(\d{4})', published_content)
            if year_match:
                result_info['published_year'] = int(year_match.group(1))
                print(f"出版年份: {result_info['published_year']}")
        
        
        return result_info
        
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
        return None
    except Exception as e:
        print(f"解析错误: {e}")
        return None



def extract_all_detailed_info(book_url):
    """
    一次性从书籍详情页面提取所有详细信息
    
    Args:
        book_url (str): 书籍详情页面URL
        
    Returns:
        dict: 包含所有详细信息的字典
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        print(f"正在访问书籍详情页面提取所有信息: {book_url}")
        
        # 发送请求
        response = requests.get(book_url, headers=headers, timeout=60)
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
        detailed_info['genres'] = []
        
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
                    detailed_info['pages'] = pages_match.group(1)
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
                    detailed_info['first_published_year'] = year_match.group(1)
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


def find_matching_book_by_author(search_url, target_author):
    """
    从搜索结果中找到匹配指定作者的书
    
    Args:
        search_url (str): Goodreads搜索URL
        target_author (str): 目标作者名
        
    Returns:
        str: 匹配的书籍详情页面URL，如果没找到返回None
    """
    try:
        # 设置请求头，模拟浏览器访问
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        print(f"正在搜索匹配作者 '{target_author}' 的书籍...")
        print(f"搜索URL: {search_url}")
        
        # 发送请求
        response = requests.get(search_url, headers=headers, timeout=60)
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
                    if author_name.lower() == target_author.lower():
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
                    if author_name.lower() == target_author.lower():
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


def main():
    """主函数"""
    # 硬编码的书名和作者名
    book_title = "The Great Gatsby"
    author_name = "F. Scott Fitzgerald"
    
    # 构建搜索URL
    search_url = f"https://www.goodreads.com/search?utf8=%E2%9C%93&q={book_title}&search_type=books&search%5Bfield%5D=title"
    
    print("=" * 50)
    print(f"搜索书籍: {book_title}")
    print(f"目标作者: {author_name}")
    print("=" * 50)
    
    # 从搜索结果中找到匹配作者名的书籍
    book_url = find_matching_book_by_author(search_url, author_name)
    
    if not book_url:
        print("未找到匹配的书籍，程序结束")
        return
    
    print("=" * 50)
    print("开始提取书籍详细信息...")
    print("=" * 50)
    
    # 直接使用找到的书籍URL提取详细信息
    detailed_info = extract_all_detailed_info(book_url)
    
    if detailed_info:
        print("=" * 50)
        print("提取完成！结果如下：")
        print("=" * 50)
        
        # 美化输出
        for key, value in detailed_info.items():
            if key == 'description' and len(str(value)) > 100:
                print(f"{key}: {str(value)[:100]}...")
            elif key == 'author_bio' and len(str(value)) > 100:
                print(f"{key}: {str(value)[:100]}...")
            else:
                print(f"{key}: {value}")
        
        print("=" * 50)
        
        # 保存为JSON文件
        output_file = "first_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_info, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {output_file}")
        
    else:
        print("提取失败！")

if __name__ == "__main__":
    main()
