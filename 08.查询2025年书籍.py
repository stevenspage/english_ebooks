import requests
import json

def get_books_by_year(year, limit=10):
    """
    使用 Open Library API 获取指定年份出版的图书数据。
    
    :param year: 要查询的年份 (int)
    :param limit: 返回结果的数量 (int)
    :return: 图书数据列表 (list of dicts) or None
    """
    # 构建 API URL
    url = f"https://openlibrary.org/search.json?q=first_publish_year:{year}&limit={limit}"
    
    try:
        # 发送 GET 请求
        response = requests.get(url)
        # 如果请求成功 (状态码 200)
        response.raise_for_status()
        
        # 解析 JSON 响应
        data = response.json()
        
        # 提取图书列表
        books = data.get("docs", [])
        
        # 精简并打印信息，并添加序号
        for idx, book in enumerate(books, 1):
            title = book.get("title", "N/A")
            # 作者可能是一个列表
            authors = ", ".join(book.get("author_name", ["N/A"]))
            first_publish_year = book.get("first_publish_year", "N/A")
            isbn_list = book.get("isbn", [])
            first_isbn = isbn_list[0] if isbn_list else "N/A"
            
            print(f"[{idx}] 书名: {title}")
            print(f"作者: {authors}")
            print(f"首次出版年份: {first_publish_year}")
            print(f"ISBN: {first_isbn}")
            print("-" * 20)
            
        return books

    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
    except json.JSONDecodeError:
        print("解析JSON响应失败")
        return None

# --- 调用函数 ---
if __name__ == "__main__":
    print("正在查询 2025 年出版的图书 (最多10本)...")
    get_books_by_year(2025, limit=20)
    
    # 你也可以试试其他年份
    # print("\n正在查询 2023 年出版的关于 'Python' 的图书 (最多5本)...")
    # url_python = "https://openlibrary.org/search.json?q=python+first_publish_year:2023&limit=5"
    # ... (可以仿照上面的函数写一个更通用的查询)