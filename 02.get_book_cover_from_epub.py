#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EPUB封面提取脚本
从epub文件中提取封面图片并保存到covers文件夹
"""

import os
import zipfile
import xml.etree.ElementTree as ET
import shutil
from pathlib import Path
import mimetypes
from PIL import Image
import io

def extract_epub_cover(epub_path, output_dir, skip_existing=True):
    """
    从epub文件中提取封面图片
    
    Args:
        epub_path: epub文件路径
        output_dir: 输出目录路径
        skip_existing: 是否跳过已存在的封面文件
    
    Returns:
        str: 'skipped' 跳过, 'success' 新提取, 'fail' 失败
    """
    # 检查是否已经存在封面文件
    if skip_existing:
        epub_name = os.path.splitext(os.path.basename(epub_path))[0]
        existing_covers = []
        for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            cover_path = os.path.join(output_dir, f"{epub_name}{ext}")
            if os.path.exists(cover_path):
                existing_covers.append(cover_path)
        if existing_covers:
            cover_filename = os.path.basename(existing_covers[0])
            print(f"⏭️  跳过已存在的封面: {cover_filename}")
            return 'skipped'
    
    try:
        with zipfile.ZipFile(epub_path, 'r') as epub_zip:
            opf_file = None
            for file_info in epub_zip.filelist:
                if file_info.filename.endswith('.opf'):
                    opf_file = file_info.filename
                    break
            if opf_file:
                try:
                    opf_content = epub_zip.read(opf_file).decode('utf-8')
                    cover_image = extract_cover_from_opf(epub_zip, opf_content, opf_file)
                    if cover_image:
                        if save_cover_image(cover_image, epub_path, output_dir):
                            return 'success'
                        else:
                            return 'fail'
                except Exception as e:
                    print(f"从OPF提取封面失败: {e}")
            cover_image = find_cover_by_filename(epub_zip)
            if cover_image:
                if save_cover_image(cover_image, epub_path, output_dir):
                    return 'success'
                else:
                    return 'fail'
            cover_image = find_cover_in_images(epub_zip)
            if cover_image:
                if save_cover_image(cover_image, epub_path, output_dir):
                    return 'success'
                else:
                    return 'fail'
            print(f"❌ 无法从 {os.path.basename(epub_path)} 提取封面")
            return 'fail'
    except Exception as e:
        print(f"❌ 处理 {os.path.basename(epub_path)} 时出错: {e}")
        return 'fail'

def extract_cover_from_opf(epub_zip, opf_content, opf_file):
    """
    从OPF文件中提取封面图片路径
    """
    try:
        # 解析OPF文件
        root = ET.fromstring(opf_content)
        
        # 查找封面相关的元数据
        cover_id = None
        for meta in root.findall('.//{*}meta'):
            if meta.get('name') == 'cover' or meta.get('content') == 'cover':
                cover_id = meta.get('content') or meta.get('id')
                break
        
        if cover_id:
            # 查找对应的文件
            for item in root.findall('.//{*}item'):
                if item.get('id') == cover_id:
                    href = item.get('href')
                    if href:
                        # 尝试多种路径组合
                        possible_paths = []
                        
                        # 1. 直接使用href
                        possible_paths.append(href)
                        
                        # 2. 相对于OPF文件的路径
                        opf_dir = os.path.dirname(opf_file) if '/' in opf_file else ''
                        if opf_dir:
                            possible_paths.append(os.path.join(opf_dir, href))
                        
                        # 3. 尝试在OEBPS目录下查找
                        if not href.startswith('OEBPS/'):
                            possible_paths.append(f"OEBPS/{href}")
                        
                        # 4. 尝试在根目录下查找
                        possible_paths.append(f"/{href}")
                        
                        # 尝试读取每个可能的路径
                        for path in possible_paths:
                            try:
                                # 标准化路径分隔符
                                normalized_path = path.replace('\\', '/')
                                return epub_zip.read(normalized_path)
                            except:
                                continue
        
        # 如果没有找到明确的封面，尝试查找第一个图片文件
        for item in root.findall('.//{*}item'):
            media_type = item.get('media-type', '')
            if media_type.startswith('image/'):
                href = item.get('href')
                if href:
                    # 尝试多种路径组合
                    possible_paths = []
                    
                    # 1. 直接使用href
                    possible_paths.append(href)
                    
                    # 2. 相对于OPF文件的路径
                    opf_dir = os.path.dirname(opf_file) if '/' in opf_file else ''
                    if opf_dir:
                        possible_paths.append(os.path.join(opf_dir, href))
                    
                    # 3. 尝试在OEBPS目录下查找
                    if not href.startswith('OEBPS/'):
                        possible_paths.append(f"OEBPS/{href}")
                    
                    # 4. 尝试在根目录下查找
                    possible_paths.append(f"/{href}")
                    
                    # 尝试读取每个可能的路径
                    for path in possible_paths:
                        try:
                            # 标准化路径分隔符
                            normalized_path = path.replace('\\', '/')
                            return epub_zip.read(normalized_path)
                        except:
                            continue
                        
    except Exception as e:
        print(f"解析OPF文件失败: {e}")
    
    return None

def find_cover_by_filename(epub_zip):
    """
    通过文件名查找封面图片
    """
    cover_keywords = ['cover', 'front', 'title', 'book']
    
    for file_info in epub_zip.filelist:
        filename = file_info.filename.lower()
        if any(keyword in filename for keyword in cover_keywords):
            if is_image_file(filename):
                try:
                    return epub_zip.read(file_info.filename)
                except:
                    pass
    
    return None

def find_cover_in_images(epub_zip):
    """
    在images目录中查找图片文件
    """
    image_files = []
    
    for file_info in epub_zip.filelist:
        filename = file_info.filename.lower()
        if 'images' in filename and is_image_file(filename):
            image_files.append(file_info)
    
    if image_files:
        # 按文件名排序，优先选择可能包含"cover"的文件
        image_files.sort(key=lambda x: ('cover' not in x.filename.lower(), x.filename))
        try:
            return epub_zip.read(image_files[0].filename)
        except:
            pass
    
    return None

def is_image_file(filename):
    """
    判断文件是否为图片文件
    """
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'}
    return any(filename.endswith(ext) for ext in image_extensions)

def save_cover_image(image_data, epub_path, output_dir):
    """
    保存封面图片
    """
    try:
        # 获取epub文件名（不含扩展名）
        epub_name = os.path.splitext(os.path.basename(epub_path))[0]
        
        # 尝试确定图片格式
        image = Image.open(io.BytesIO(image_data))
        format_name = image.format.lower() if image.format else 'jpg'
        
        # 生成输出文件名
        output_filename = f"{epub_name}.{format_name}"
        output_path = os.path.join(output_dir, output_filename)
        
        # 保存图片
        image.save(output_path, format=format_name.upper())
        print(f"✅ 成功提取封面: {output_filename}")
        return True
        
    except Exception as e:
        print(f"保存封面图片失败: {e}")
        return False

def main():
    """
    主函数
    """
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='EPUB封面提取工具')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制重新提取已存在的封面')
    parser.add_argument('--ebooks-dir', '-e', default='ebooks',
                       help='epub文件目录 (默认: ebooks)')
    parser.add_argument('--output-dir', '-o', default='covers',
                       help='输出目录 (默认: covers)')
    
    args = parser.parse_args()
    
    # 设置路径
    ebooks_dir = args.ebooks_dir
    covers_dir = args.output_dir
    skip_existing = not args.force
    
    # 检查ebooks目录是否存在
    if not os.path.exists(ebooks_dir):
        print(f"❌ ebooks目录不存在: {ebooks_dir}")
        return
    
    # 创建covers目录（如果不存在）
    os.makedirs(covers_dir, exist_ok=True)
    print(f"📁 输出目录: {covers_dir}")
    
    if skip_existing:
        print("🔄 模式: 跳过已存在的封面")
    else:
        print("🔄 模式: 强制重新提取所有封面")
    
    # 查找所有epub文件
    epub_files = []
    epub_names = set()
    for file in os.listdir(ebooks_dir):
        if file.lower().endswith('.epub'):
            epub_files.append(os.path.join(ebooks_dir, file))
            epub_names.add(os.path.splitext(file)[0])

    if not epub_files:
        print("❌ 在ebooks目录中未找到epub文件")
        return

    print(f"📚 找到 {len(epub_files)} 个epub文件")

    # 删除covers目录下无对应epub的封面图片
    removed_count = 0
    for cover_file in os.listdir(covers_dir):
        cover_path = os.path.join(covers_dir, cover_file)
        if not os.path.isfile(cover_path):
            continue
        cover_name, cover_ext = os.path.splitext(cover_file)
        if cover_ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            continue
        if cover_name not in epub_names:
            try:
                os.remove(cover_path)
                print(f"🗑️  删除无对应epub的封面: {cover_file}")
                removed_count += 1
            except Exception as e:
                print(f"⚠️  删除封面失败: {cover_file}，原因: {e}")
    if removed_count > 0:
        print(f"🧹 共删除 {removed_count} 个无对应epub的封面文件")
    
    # 统计已存在的封面
    if skip_existing:
        existing_count = 0
        for epub_file in epub_files:
            epub_name = os.path.splitext(os.path.basename(epub_file))[0]
            for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                if os.path.exists(os.path.join(covers_dir, f"{epub_name}{ext}")):
                    existing_count += 1
                    break
        
        if existing_count > 0:
            print(f"📋 发现 {existing_count} 个已存在的封面")
    
    # 处理每个epub文件
    success_count = 0
    skipped_count = 0
    fail_count = 0
    for epub_file in epub_files:
        print(f"\n📖 处理: {os.path.basename(epub_file)}")
        result = extract_epub_cover(epub_file, covers_dir, skip_existing)
        if result == 'skipped':
            skipped_count += 1
        elif result == 'success':
            success_count += 1
        else:
            fail_count += 1

    print(f"\n🎉 完成！")
    if skip_existing:
        print(f"📊 统计: 删除{removed_count}个，跳过 {skipped_count} 个，新提取 {success_count} 个，失败 {fail_count} 个，总计 {skipped_count + success_count + fail_count}/{len(epub_files)}")
    else:
        print(f"📊 统计: 成功提取 {success_count} 个，失败 {fail_count} 个，总计 {success_count + fail_count}/{len(epub_files)}")
    print(f"📁 封面文件保存在: {os.path.abspath(covers_dir)}")
if __name__ == "__main__":
    main()
