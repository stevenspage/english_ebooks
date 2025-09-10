import requests

# Hardcover GraphQL 端点
url = "https://api.hardcover.app/v1/graphql"

# API Token
headers = {
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJIYXJkY292ZXIiLCJ2ZXJzaW9uIjoiOCIsImp0aSI6ImQzYTZmZWM2LTFhZTctNDU4OS1iYmM1LTJmNjkyN2IwNDk1NyIsImFwcGxpY2F0aW9uSWQiOjIsInN1YiI6IjQzNjY4IiwiYXVkIjoiMSIsImlkIjoiNDM2NjgiLCJsb2dnZWRJbiI6dHJ1ZSwiaWF0IjoxNzU1NjA4MDUxLCJleHAiOjE3ODcxNDQwNTEsImh0dHBzOi8vaGFzdXJhLmlvL2p3dC9jbGFpbXMiOnsieC1oYXN1cmEtYWxsb3dlZC1yb2xlcyI6WyJ1c2VyIl0sIngtaGFzdXJhLWRlZmF1bHQtcm9sZSI6InVzZXIiLCJ4LWhhc3VyYS1yb2xlIjoidXNlciIsIlgtaGFzdXJhLXVzZXItaWQiOiI0MzY2OCJ9LCJ1c2VyIjp7ImlkIjoiNDM2NjgiLCJ1c2VyIjp7ImlkIjo0MzY2OH19.1n5zBanc2T8Nms4P8PKKc25Gii_JBxXtNGQgwqJ4tUE",
    "Content-Type": "application/json"
}

def main():
    print("检查Hardcover API中体裁信息的存储结构")
    print("=" * 60)
    
    # 测试1: 检查books表的字段
    print("\n📚 测试1: 检查books表的字段")
    books_fields_query = """
    query {
      __type(name: "books") {
        fields {
          name
          type {
            name
            kind
          }
        }
      }
    }
    """
    
    response = requests.post(url, headers=headers, json={"query": books_fields_query})
    if response.status_code == 200:
        data = response.json()
        if "errors" not in data and "data" in data:
            fields = data["data"]["__type"]["fields"]
            print("✅ books表的字段:")
            for field in fields:
                print(f"  - {field['name']}: {field['type']['name']} ({field['type']['kind']})")
        else:
            print(f"❌ 查询失败: {data}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
    
    print("\n" + "="*60)
    
    # 测试2: 检查editions表的字段
    print("\n📖 测试2: 检查editions表的字段")
    editions_fields_query = """
    query {
      __type(name: "editions") {
        fields {
          name
          type {
            name
            kind
          }
        }
      }
    }
    """
    
    response = requests.post(url, headers=headers, json={"query": editions_fields_query})
    if response.status_code == 200:
        data = response.json()
        if "errors" not in data and "data" in data:
            fields = data["data"]["__type"]["fields"]
            print("✅ editions表的字段:")
            for field in fields:
                print(f"  - {field['name']}: {field['type']['name']} ({field['type']['kind']})")
        else:
            print(f"❌ 查询失败: {data}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
    
    print("\n" + "="*60)
    
    # 测试3: 检查是否有专门的genres表
    print("\n🏷️ 测试3: 检查是否有genres表")
    genres_query = """
    query {
      __type(name: "genres") {
        fields {
          name
          type {
            name
            kind
          }
        }
      }
    }
    """
    
    response = requests.post(url, headers=headers, json={"query": genres_query})
    if response.status_code == 200:
        data = response.json()
        if "errors" not in data and "data" in data:
            fields = data["data"]["__type"]["fields"]
            print("✅ genres表存在，字段:")
            for field in fields:
                print(f"  - {field['name']}: {field['type']['name']} ({field['type']['kind']})")
        else:
            print("❌ genres表不存在")
    else:
        print(f"❌ HTTP错误: {response.status_code}")
    
    print("\n" + "="*60)
    
    # 测试4: 尝试获取一些实际数据看看结构
    print("\n🔍 测试4: 获取实际数据查看结构")
    sample_query = """
    query {
      books(limit: 1) {
        id
        title
        editions(limit: 1) {
          id
          language_id
        }
      }
    }
    """
    
    response = requests.post(url, headers=headers, json={"query": sample_query})
    if response.status_code == 200:
        data = response.json()
        if "errors" not in data and "data" in data:
            print("✅ 实际数据结构:")
            import json
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ 查询失败: {data}")
    else:
        print(f"❌ HTTP错误: {response.status_code}")

if __name__ == "__main__":
    main()
