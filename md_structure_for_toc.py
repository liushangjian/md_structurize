"""
这个代码将AI识别的目录结构统一刷成markdown标题格式，方便之后处理成json

"""

import re
import logging
import os
from datetime import datetime
from tqdm import tqdm

class MarkdownProcessor:
    def __init__(self, input_path, output_dir):
        """
        初始化处理器
        :param input_path: 输入文件的完整路径
        :param output_dir: 输出目录的路径
        """
        self.input_path = input_path
        self.output_dir = output_dir
        
        # 设置日志
        self.setup_logging()
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成输出文件名
        input_filename = os.path.basename(input_path)
        self.output_path = os.path.join(
            output_dir, 
            f"processed_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{input_filename}"
        )

    def setup_logging(self):
        """设置日志配置"""
        log_filename = f"markdown_processing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        log_path = os.path.join(self.output_dir, log_filename)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_path, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

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
                if re.match(r'^\s*第[一二三四五六七八九十]+章(?:\s|$)', header_content) or \
                   re.match(r'^\s*第[一二三四五六七八九十]+章\s+\S+', header_content) or \
                   re.match(r'^\s*第\d+章(?:\s|$)', header_content) or \
                   re.match(r'^\s*第\d+章\s+\S+', header_content) or \
                   re.match(r'^\s*CHAPTER\s+\d+(?:\s|$)', header_content, re.IGNORECASE) or \
                   re.match(r'^\s*\d+(?:\s|$)', header_content):
                    line = f"# {header_content}"
                    table_of_contents.append((1, header_content))
                    modified = True
                
                
                # Level 2 header: Match "Section X", "Part X", etc. in both languages
                elif re.match(r'^\s*第[一二三四五六七八九十]+(?:节|部分)', header_content) or \
                     re.match(r'^\s*绪论', header_content) or \
                     re.match(r'^\s*\d+\.\d+(?![\.\d])', header_content) or \
                     re.match(r'^\s*SECTION\s+\d+(?:\s|$)', header_content, re.IGNORECASE) or \
                     re.match(r'^\s*PART\s+\d+(?:\s|$)', header_content, re.IGNORECASE):
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
                elif re.match(r'^\s*[一二三四五六七八九十]+、', header_content) or \
                    re.match(r'^\s*\d+\.\s*\d+\s+[^\n]*?\([\w\s]+\)', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")
                    
                
                # Level 3 header: Match various formats
                elif re.match(r'^\s*\d+\.\d+\.\d+(?![\s\.]*\d)', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+(?![\.\d])', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\s+[^\n]*', header_content) or \
                   re.match(r'^\s*\d+、\s*\S', header_content):
                    line = f"### {header_content}"
                    table_of_contents.append((3, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改三级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                
                # 四级标题: 带括号的数字、中文字或X.X.X.X格式
                elif re.match(r'^\s*[\(（]\s*(?:\d+|[一二三四五六七八九十]+)\s*[\)）]', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\.\d+', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\.\d+\s+[^\n]*?\([\w\s]+\)', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\.\d+\s+\S', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\.\d+(?![\s\.]*\d)', header_content) or \
                   re.match(r'^\s*[（\(][一二三四五六七八九十]+[）\)]\s*\S', header_content) or \
                   re.match(r'^\s*\d+[\.．]\s*\S', header_content) or \
                   re.match(r'^\s*\d+\s*\S', header_content) or \
                   re.match(r'^\s*[A-Z]\.\s+', header_content):
                    line = f"#### {header_content}"
                    table_of_contents.append((4, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改四级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                
                # 如果不符合任何标题格式，跳过这一行
                if not modified:
                    self.logger.info(f"行 {current_line_number}: 删除不规范标题 / Line {current_line_number}: Removing non-standard header")
                    self.logger.info(f"  删除内容 / Removed content: {original_line.strip()}")
                    stats['removed_headers'] = stats.get('removed_headers', 0) + 1
                    continue

            
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
    def process_file(self):
        """处理文件的主函数"""
        try:
            # 读取文件
            self.logger.info(f"开始读取文件: {self.input_path}")
            with open(self.input_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 处理内容
            processed_content = self.process_markdown(content)
            
            # 写入新文件
            self.logger.info(f"写入处理后的文件: {self.output_path}")
            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)
            
            self.logger.info("文件处理完成")
            return True
            
        except Exception as e:
            self.logger.error(f"处理过程中发生错误: {str(e)}")
            return False

def process_directory(input_dir, output_dir):
    """处理目录中的所有markdown文件"""
    # 获取所有.md文件（包括子文件夹中的文件）
    md_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    if not md_files:
        print(f"在目录 {input_dir} 中未找到.md文件")
        return
        
    print(f"找到 {len(md_files)} 个.md文件")
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 使用tqdm显示处理进度
    success_count = 0
    with tqdm(total=len(md_files), desc="处理进度") as pbar:
        for md_file in md_files:
            # 保持输入文件的相对路径结构
            rel_path = os.path.relpath(md_file, input_dir)
            output_subdir = os.path.dirname(os.path.join(output_dir, rel_path))
            os.makedirs(output_subdir, exist_ok=True)
            
            # 处理文件
            processor = MarkdownProcessor(md_file, output_subdir)
            if processor.process_file():
                success_count += 1
            
            pbar.update(1)
    
    print(f"\n处理完成: 成功 {success_count}/{len(md_files)} 个文件")

def main():
    # 设置输入目录和输出目录
    input_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/tocs"
    output_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/update_toc"
    
    process_directory(input_dir, output_dir)

if __name__ == "__main__":
    main()
