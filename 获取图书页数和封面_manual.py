import requests

def is_probable_same_author(input_author, result_authors):
    """
    判断输入作者名与结果作者列表中是否有可能是同一个人。
    忽略顺序、去除点号、匹配两个以上相同单词，判断可能性。
    """
    if not result_authors:
        return False

    input_parts = set(input_author.lower().replace('.', '').split())
    for candidate in result_authors:
        candidate_parts = set(candidate.lower().replace('.', '').split())
        if len(input_parts & candidate_parts) >= 2:
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

def get_book_pages_and_covers(title, author):
    """
    查询 Google Books API，返回页数、匹配作者名。
    并使用 ISBN 去 Open Library 获取有效封面链接。
    """
    query = f"{title} {author}"
    url = f"https://www.googleapis.com/books/v1/volumes?q={requests.utils.quote(query)}"

    response = requests.get(url)
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
            print(f"✅ 匹配书名: {title_result}")
            print(f"📖 页数: {page_count if page_count else '未知'}")
            print(f"👤 匹配的作者名（API返回）: {', '.join(result_authors)}")

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
                # 生成Open Library封面链接
                cover_sizes = {'小尺寸': 'S', '中尺寸': 'M', '大尺寸': 'L'}
                for size_name, size_code in cover_sizes.items():
                    cover_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-{size_code}.jpg"
                    if is_valid_cover(cover_url):
                        print(f"🖼️ {size_name}封面链接: {cover_url}")
                    else:
                        print(f"🚫 {size_name}封面无效")
            else:
                print("❗️未找到ISBN，无法生成封面链接")

            return page_count

    print("❗️未找到匹配的作者/书籍")
    return None

# 示例用法
if __name__ == "__main__":
    print("📚 图书信息查询工具")
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
        get_book_pages_and_covers(title_input, author_input)
        
        print("\n" + "-" * 30)
        print("✅ 查询完成，请继续输入下一本书的信息...")
