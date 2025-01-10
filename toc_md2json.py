"""
将md文件转化为json。{chapter section}格式
"""
import re
import json
import os
from pathlib import Path

def parse_md_to_json(md_file_path):
    with open(md_file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # 初始化结果字典
    result = {
        "Book": str(md_file_path),
        "sections": []
    }
    
    # 当前章节和小节
    current_chapter = ""
    current_section = ""
    
    # 按行分割内容
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 匹配章节（以单个#开头）
        chapter_match = re.match(r'^# (.+)$', line)
        if chapter_match:
            current_chapter = chapter_match.group(1)
            continue
            
        # 匹配小节（以##开头）
        section_match = re.match(r'^## (.+)$', line)
        if section_match:
            current_section = section_match.group(1)
            # 如果没有子节，则在这里添加记录
            result["sections"].append({
                "Chapter": current_chapter,
                "Section": current_section,
                "Subsection": None,
                "Content": None
            })
    
    return result

def process_folder(input_folder, output_folder):
    # 创建输出文件夹（如果不存在）
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # 处理输入文件夹中的所有md文件
    for file_path in Path(input_folder).glob('*.md'):
        # 解析MD文件
        result = parse_md_to_json(file_path)
        
        # 生成输出文件名
        output_file = Path(output_folder) / f"{file_path.stem}.json"
        
        # 保存JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Processed {file_path.name} -> {output_file.name}")

if __name__ == "__main__":
    # 设置输入和输出文件夹路径
    input_folder = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/1toc_md/good_toc_md"
    output_folder = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/toc_json"
    
    # 处理文件夹
    process_folder(input_folder, output_folder)
