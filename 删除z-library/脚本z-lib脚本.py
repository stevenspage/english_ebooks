import os
import re

def remove_zlibrary_from_filename(directory):
    """
    批量删除文件名中的 (Z-Library) 部分
    """
    # 遍历目录中的所有文件
    for filename in os.listdir(directory):
        # 匹配文件名中的 (Z-Library) 部分（包括括号）
        new_filename = re.sub(r'\s*\(Z-Library\)', '', filename)
        
        # 如果文件名有变化，则重命名
        if new_filename != filename:
            old_path = os.path.join(directory, filename)
            new_path = os.path.join(directory, new_filename)
            
            try:
                os.rename(old_path, new_path)
                print(f'Renamed: "{filename}" -> "{new_filename}"')
            except Exception as e:
                print(f'Error renaming "{filename}": {e}')

if __name__ == '__main__':
    # 指定要处理的目录（当前目录）
    target_directory = '.'
    remove_zlibrary_from_filename(target_directory)