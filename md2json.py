"""
将markdown文件转换为json文件
保留文档中的层级信息
"""
import re
import json
import os

def split_and_parse_markdown(file_path, max_chars=100000):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    book_name = os.path.basename(file_path)
    
    # 分割内容，保留标题层级信息
    sections = re.split(r'(?=^#\s|^##\s|^###\s)', content, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]
    
    current_chapter = None
    current_section = None
    current_part = 1
    current_chars = 0
    current_subsections = []
    all_json_structures = []
    
    for section in sections:
        # 检查标题级别和内容
        header_match = re.match(r'^(#{1,3})\s+(.+?)\n([\s\S]*)', section)
        if not header_match:
            continue
            
        level = len(header_match.group(1))
        title = header_match.group(2).strip()
        content = re.sub(r'^#{4,}\s+.*$', '', header_match.group(3), flags=re.MULTILINE).strip()
        
        # 更新章节信息
        if level == 1:
            current_chapter = title
        elif level == 2:
            current_section = title
        elif level == 3:
            subsection = {
                "Chapter": current_chapter,
                "Section": current_section,
                "Subsection": title,
                "Content": content
            }
        
            
            # 检查是否需要创建新文件
            section_chars = len(json.dumps(subsection, ensure_ascii=False))
            if current_chars + section_chars > max_chars and current_subsections:
                # 保存当前部分
                json_structure = {
                    "Book": f"{book_name}_part{current_part}",
                    "Subsections": current_subsections
                }
                all_json_structures.append(json_structure)
                
                # 重置计数器和列表，开始新的部分
                current_part += 1
                current_chars = 0
                current_subsections = []
                print(f"Starting part {current_part} of {book_name}")
            
            current_subsections.append(subsection)
            current_chars += section_chars
    
    # 保存最后一部分
    if current_subsections:
        json_structure = {
            "Book": f"{book_name}_part{current_part}",
            "Subsections": current_subsections
        }
        all_json_structures.append(json_structure)
    
    return all_json_structures

def save_split_json(json_structures, output_dir, original_filename):
    base_name = os.path.splitext(original_filename)[0]
    
    for i, json_structure in enumerate(json_structures, 1):
        output_filename = f"{base_name}_part{i}.json"
        output_path = os.path.join(output_dir, output_filename)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(json_structure, f, ensure_ascii=False, indent=2)
            print(f"Successfully saved part {i} to {output_filename}")
        except Exception as e:
            print(f"Error saving {output_filename}: {str(e)}")

def merge_json_parts(output_dir, base_filename):
    """
    合并同一个文件的所有部分为一个完整的JSON文件
    """
    base_name = os.path.splitext(base_filename)[0]
    merged_subsections = []
    part_files = []
    
    # 收集所有相关的部分文件
    for filename in os.listdir(output_dir):
        if filename.startswith(base_name) and '_part' in filename:
            part_files.append(filename)
    
    # 按照部分号排序
    part_files.sort(key=lambda x: int(re.search(r'part(\d+)', x).group(1)))
    
    # 合并所有部分
    for part_file in part_files:
        part_path = os.path.join(output_dir, part_file)
        try:
            with open(part_path, 'r', encoding='utf-8') as f:
                part_data = json.load(f)
                merged_subsections.extend(part_data['Subsections'])
            # 删除部分文件
            os.remove(part_path)
        except Exception as e:
            print(f"Error processing part file {part_file}: {str(e)}")
    
    # 创建最终的合并文件
    merged_structure = {
        "Book": base_filename,
        "Subsections": merged_subsections
    }
    
    # 保存合并后的文件
    output_path = os.path.join(output_dir, base_filename.replace('.md', '.json'))
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(merged_structure, f, ensure_ascii=False, indent=2)
        print(f"Successfully merged all parts into {output_path}")
    except Exception as e:
        print(f"Error saving merged file: {str(e)}")

def process_directory(input_dir, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    for filename in os.listdir(input_dir):
        if filename.endswith('.md'):
            input_path = os.path.join(input_dir, filename)
            
            try:
                print(f"Processing {filename}")
                # 1. 首先分割处理
                json_structures = split_and_parse_markdown(input_path)
                # 2. 保存各个部分
                save_split_json(json_structures, output_dir, filename)
                print(f"Successfully processed {filename} into {len(json_structures)} parts")
                # 3. 合并所有部分
                merge_json_parts(output_dir, filename)
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

# 设置输入输出目录
input_directory = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/books_processed2"
output_directory = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/books_json"

# 处理整个目录
process_directory(input_directory, output_directory)