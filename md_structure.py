"""
将书本的目录格式刷新到markdown格式的目录层级
因为不同的书籍目录格式都是正交的，所以直接发送给AI在正则表达式加上内容。注意不要破坏之前的识别方式。
目前的已经比较完备，一般的文档可以直接使用
"""

import re
import logging
import os
from datetime import datetime

class MarkdownProcessor:
    def __init__(self, input_path, output_path):
        """初始化MarkdownProcessor
        
        Args:
            input_path: 输入文件或目录的路径
            output_path: 输出文件或目录的路径
        """
        self.input_path = input_path
        self.output_path = output_path
        
        # 设置日志记录器
        self.logger = logging.getLogger('MarkdownProcessor')
        self.logger.setLevel(logging.INFO)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def process_directory(self, input_dir, output_dir):
        """处理整个文件夹的markdown文件"""
        # 确保输出目录存在
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 获取所有markdown文件
        md_files = [f for f in os.listdir(input_dir) if f.endswith('.md')]
        
        self.logger.info(f"找到 {len(md_files)} 个markdown文件")
        
        # 处理每个文件
        for filename in md_files:
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            
            self.logger.info(f"\n开始处理文件: {filename}")
            try:
                # 读取文件
                with open(input_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 处理内容
                processed_content = self.process_markdown(content)
                
                # 写入新文件
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)
                
                self.logger.info(f"成功处理文件: {filename}")
                
            except Exception as e:
                self.logger.error(f"处理文件 {filename} 时发生错误: {str(e)}")

    def process_markdown(self, content):
        """Process markdown content"""
        self.logger.info("开始处理markdown文件 / Start processing markdown file")
        
        lines = content.split('\n')
        processed_lines = []
        skip_section = False
        current_line_number = 0
        
        # Add table of contents collection list
        table_of_contents = []
        
        stats = {
            'removed_images': 0,
            'removed_sections': 0,
            'modified_headers': 0,
            'converted_to_text': 0
        }
        
        for i, line in enumerate(lines):
            current_line_number += 1
            
            # Skip sections like exercises, references, literature guide and summary
            if any(keyword in line for keyword in [
                '思考题', 'Exercises', 
                '参考文献', 'References',
                '文献导读', 'Literature Guide', 
                '小结', 'Summary'
            ]):
                skip_section = True
                stats['removed_sections'] += 1
                self.logger.info(f"行 {current_line_number}: 开始跳过章节 \"{line.strip()}\" / Line {current_line_number}: Start skipping section \"{line.strip()}\"")
                continue
                
            if skip_section and line.strip().startswith('#'):
                skip_section = False
                self.logger.info(f"行 {current_line_number}: 结束跳过章节")
                
            if skip_section:
                self.logger.debug(f"行 {current_line_number}: 跳过内容 \"{line.strip()}\"")
                continue
                
            # 跳过图片及其多行说明文字
            if '![' in line:
                stats['removed_images'] += 1
                self.logger.info(f"行 {current_line_number}: 删除图片标签 \"{line.strip()}\"")
                continue
            
            # 检查是否处于图片描述区域
            if i > 0:
                # 向上查找最近的非空行
                j = i - 1
                in_image_desc = False
                while j >= 0:
                    if not lines[j].strip():  # 遇到空行
                        break
                    if '![' in lines[j]:  # 找到图片标记
                        in_image_desc = True
                        break
                    j -= 1
                
                if in_image_desc and line.strip():  # 如果是图片描述区域且当前行非空
                    self.logger.info(f"行 {current_line_number}: 删除图片说明文字 \"{line.strip()}\"")
                    continue
                
            # Process headers
            if line.strip().startswith('#') or re.match(r'^\s*(?:第[一二三四五六七八九十]+(?:章|节|部分)|[一二三四五六七八九十]+、|\d+\.|\d+、|\((?:\d+|[一二三四五六七八九十]+)\)|Chapter|Section|Part|\d+\.|[A-Z]\.)', line.strip()):
                original_line = line
                header_content = line.lstrip('#').strip() if line.strip().startswith('#') else line.strip()
                modified = False
                
                # Level 1 header: Match complete "Chapter X" format in both languages
                if re.match(r'^\s*第[一二三四五六七八九十百]+章(?:\s|$)', header_content) or \
                   re.match(r'^\s*CHAPTER\s+\d+(?:\s|$)', header_content, re.IGNORECASE) or \
                   re.match(r'^\s*\d+(?:\s|$)', header_content):
                    line = f"# {header_content}"
                    table_of_contents.append((1, header_content))
                    modified = True
                
                
                # Level 2 header: Match "Section X", "Part X", etc. in both languages
                elif re.match(r'^\s*第[一二三四五六七八九十百]+(?:节|部分)', header_content) or \
                     re.match(r'^\s*绪论', header_content) or \
                     re.match(r'^\s*\d+\.\d+(?![\.\d])', header_content) or \
                     re.match(r'^\s*SECTION\s+\d+(?:\s|$)', header_content, re.IGNORECASE) or \
                     re.match(r'^\s*PART\s+\d+(?:\s|$)', header_content, re.IGNORECASE) or \
                     re.match(r'^\s*\d+\.\d+\s*[^\.0-9]', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                    
                # 二级标题: X.X格式（紧凑格式）
                elif re.match(r'^\s*\d+\.\d+(?![\s\.]*\d)\S', header_content) or \
                   re.match(r'^\s*\d+\.\d+(?![\s\.]*\d)', header_content) or \
                   re.match(r'^\s*\d+\.\d+[^\.]\S+', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                    
                # 二级标题: X. X格式（带空格）
                elif re.match(r'^\s*\d+\s*\.\s*\d+\s+\S', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                    
                # 二级标题: X. X 格式带括号注释
                elif re.match(r'^\s*\d+\.\s*\d+\s+[^\n]*?\([\w\s]+\)', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")
                    
                
                # Level 3 header: Match various formats
                elif re.match(r'^\s*[一二三四五六七八九十百]+、', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+(?![\.\d])', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\s*[^\.0-9]', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\s+[^\n]*', header_content) or \
                     re.match(r'^\s*\d+、\s*\S', header_content):
                    line = f"### {header_content}"
                    table_of_contents.append((3, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改三级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                
                # 四级标题: 带括号的数字、中文数字或X.X.X.X格式
                elif re.match(r'^\s*[\(（]\s*(?:\d+|[一二三四五六七八九十百]+)\s*[\)）]', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\.\d+', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\.\d+\s+[^\n]*?\([\w\s]+\)', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\.\d+\s+\S', header_content) or \
                     re.match(r'^\s*\d+\.\d+\.\d+\.\d+(?![\s\.]*\d)', header_content) or \
                     re.match(r'^\s*[（\(][一二三四五六七八九十百]+[）\)]\s*\S', header_content) or \
                     re.match(r'^\s*\d+[\.．]\s*\S', header_content) or \
                     re.match(r'^\s*\d+\s*\S', header_content) or \
                     re.match(r'^\s*[A-Z]\.\s+', header_content):
                    line = f"#### {header_content}"
                    table_of_contents.append((4, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改四级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                
                # 如果不符合任何标题格式，设置为三级标题
                if not modified:
                    line = f"### {header_content}"
                    table_of_contents.append((3, header_content))
                    stats['modified_headers'] += 1
                    self.logger.info(f"行 {current_line_number}: 将不规范标题设置为三级标题 / Line {current_line_number}: Set non-standard header to level 3")
                    self.logger.info(f"  原文 / Original: {original_line.strip()}")
                    self.logger.info(f"  修改后 / Modified: {line.strip()}")

            
            processed_lines.append(line)
        
        # Record statistics
        self.logger.info("\n处理总结 / Processing Summary:")
        self.logger.info(f"- 删除图片数量 / Removed images: {stats['removed_images']}")
        self.logger.info(f"- 删除章节数量 / Removed sections: {stats['removed_sections']}")
        self.logger.info(f"- 修改标题数量 / Modified headers: {stats['modified_headers']}")
        self.logger.info(f"- 转换为正文数量 / Converted to text: {stats['converted_to_text']}")
        
        # Generate table of contents
        self.logger.info("\n文档目录结构 / Document Structure:")
        for level, title in table_of_contents:
            indent = "  " * (level - 1)
            self.logger.info(f"{indent}{title}")
        
        return '\n'.join(processed_lines)

    def process_file(self, input_path, output_path):
        """处理文件的主函数"""
        try:
            # 读取文件
            self.logger.info(f"开始读取文件: {input_path}")
            with open(input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理内容
            processed_content = self.process_markdown(content)
            
            # 写入新文件
            self.logger.info(f"写入处理后的文件: {output_path}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            self.logger.info("文件处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"处理过程中发生错误: {str(e)}")
            return False

    def process(self):
        """处理文件或目录的主函数"""
        if os.path.isfile(self.input_path):
            # 处理单个文件
            return self.process_file(self.input_path, self.output_path)
        elif os.path.isdir(self.input_path):
            # 处理整个目录
            return self.process_directory(self.input_path, self.output_path)
        else:
            self.logger.error(f"输入路径不存在: {self.input_path}")
            return False

def main():
    # 设置输入文件路径和输出目录
    input_path = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/books_processed2"  # 替换为实际的输入目录路径
    output_path = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/book_processed"  # 替换为实际的输出目录路径
    
    processor = MarkdownProcessor(input_path, output_path)
    processor.process()

if __name__ == "__main__":
    main()
