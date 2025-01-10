import re
import logging
import os
from datetime import datetime

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
            if line.strip().startswith('#'):
                original_line = line
                header_content = line.lstrip('#').strip()
                modified = False
                
                # Level 1 header: Match complete "Chapter X" format in both languages
                if re.match(r'^\s*第[一二三四五六七八九十]+章(?:\s|$)', header_content) or \
                   re.match(r'^\s*CHAPTER\s+\d+(?:\s|$)', header_content, re.IGNORECASE):
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
                elif re.match(r'^\s*\d+\.\s*\d+\s+[^\n]*?\([\w\s]+\)', header_content):
                    line = f"## {header_content}"
                    table_of_contents.append((2, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改二级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")
                    
                
                # Level 3 header: Match various formats
                elif re.match(r'^\s*[一二三四五六七八九十]+、', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+(?![\s\.]*\d)', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+(?![\.\d])', header_content) or \
                   re.match(r'^\s*\d+\.\d+\.\d+\s+[^\n]*', header_content) or \
                   re.match(r'^\s*\d+、\s*\S', header_content):
                    line = f"### {header_content}"
                    table_of_contents.append((3, header_content))
                    modified = True
                    self.logger.info(f"行 {current_line_number}: 修改三级标题")
                    self.logger.info(f"  原文: {original_line.strip()}")
                    self.logger.info(f"  修改后: {line.strip()}")

                
                # 四级标题: 带括号的数字、中文数字或X.X.X.X格式
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

def main():
    """
    处理指定目录下的所有markdown文件
    Process all markdown files in the specified directory
    """
    # 设置输入和输出目录
    input_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book"
    output_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_output"
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(output_dir, 'batch_processing.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    
    # 获取所有markdown文件
    md_files = []
    for root, _, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    
    logger.info(f"找到 {len(md_files)} 个markdown文件 / Found {len(md_files)} markdown files")
    
    # 处理每个文件
    success_count = 0
    failure_count = 0
    
    for file_path in md_files:
        try:
            logger.info(f"\n开始处理文件 / Start processing file: {file_path}")
            processor = MarkdownProcessor(file_path, output_dir)
            if processor.process_file():
                success_count += 1
            else:
                failure_count += 1
        except Exception as e:
            logger.error(f"处理文件时发生错误 / Error processing file {file_path}: {str(e)}")
            failure_count += 1
    
    # 输出处理总结
    logger.info("\n批量处理完成 / Batch processing completed:")
    logger.info(f"成功处理文件数 / Successfully processed: {success_count}")
    logger.info(f"处理失败文件数 / Failed to process: {failure_count}")
    logger.info(f"总文件数 / Total files: {len(md_files)}")

if __name__ == "__main__":
    main()
