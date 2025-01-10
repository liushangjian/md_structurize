"""
这个是好用的toc识别脚本
使用asyncio包来同时处理一个文件夹中的多本书的内容。
对于每一本书中的chunk按顺序进行处理，当多本书中的一本书处理完之后开始下一本新的书。具体的处理过程无需改变
这个代码中添加最大同时处理的的数量限制，以及再命令行中显示每本书的处理进度



这个英文版本保留了原始prompt的所有关键功能，但调整了表达方式和示例以更好地适应英文书籍的常见格式。
"""
import os
import logging
from openai import AsyncOpenAI
from datetime import datetime
from dotenv import load_dotenv
import asyncio
from typing import List
import glob
from tqdm import tqdm
import argparse
import aiofiles

class TOCExtractor:
    def __init__(self, input_path, output_dir, api_key):
        self.input_path = input_path
        self.output_dir = output_dir
        self.client = AsyncOpenAI(api_key=api_key)
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.output_dir, f'toc_extraction_{timestamp}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    async def generate_response(self, prompt):
        """异步调用GPT-4生成响应"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",     
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"API调用失败: {str(e)}")
            
    async def extract_toc(self, content):
        """从文档中提取目录"""
        words = content.split()
        chunk_size = 4000
        toc_parts = []
        chunks = [content[i:i + chunk_size] for i in range(0, len(content), chunk_size)]
        
        # 使用tqdm显示chunk处理进度
        with tqdm(total=len(chunks), desc=f"处理 {os.path.basename(self.input_path)}", 
                 position=1, leave=False) as pbar:
            # 按顺序处理每个chunk
            for chunk in chunks:
                prompt = """
                You are a text processing expert. I will provide you with book content in segments. Your task is to identify the table of contents from the text and convert it into a Markdown format (using # for hierarchy levels).
                Process the text only, without making any evaluations or descriptions.
                Due to input length limitations, the table of contents may be spread across two or more adjacent segments. Please maintain consistency with the previous segment's processing style, don't be lazy!!!

                Rules:
                1. Table of Contents Recognition Features:
                   - Paragraphs with dense title numbering
                   - Multiple consecutive chapters, sections, or numerical sequences (1,2,3,4,5)
                   - Multiple consecutive short texts that resemble titles
                   - Lines may contain page numbers (to be removed)
                
                2. Title Hierarchy Rules:
                    Adjacent content with parallel hierarchical structure should be recognized at the same level:
                  The more numbers (like 1, 1.11) or symbols (a,b,c) preceding the text, the lower the title level.
                    Examples:
                    First level:
                   - Chapter X
                   - Part X
                   
                    Second level:
                   - Section X
                   - X.X (like 1.1, 2.1, etc.) 
                   - CONCEPT X.X
                   
                    Special rules:
                   - Maintain chapter continuity and hierarchical relationships
                   - Ensure each title has corresponding level markers
                
                3. Output Requirements:
                  - Output only in Markdown format using # for chapters and ## for sections, remove all other information
                  - Preserve original hierarchical relationships
                  - Remove sections containing "Review Questions", "References", "Exercises", and "Appendix"
                  - Remove all page numbers
                  - Ensure each line has a title level marker
                  - Separate titles with line breaks
                
                4. Output Example:
                    # Chapter One: Introduction
                    ##  Historical Development
                    ##  Main Contents and Applications
                    ##  Study Methods

                    # Chapter Two: Structure and Function
                    ##  Basic Components

                Here is the text to process:
                """ + chunk
                try:
                    response = await self.generate_response(prompt)
                    toc_parts.append(response.strip())
                except Exception as e:
                    self.logger.error(f"目录提取失败: {str(e)}")
                finally:
                    pbar.update(1)
        
        full_toc = '\n'.join(toc_parts)
        return full_toc
            
    async def process_file(self):
        """异步处理单个文件"""
        try:
            self.logger.info(f"开始读取文件: {self.input_path}")
            async with aiofiles.open(self.input_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                content = content[:40000]  # 限制处理长度
            
            self.logger.info("开始提取目录")
            toc = await self.extract_toc(content)
            
            if toc:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.basename(self.input_path)
                output_path = os.path.join(
                    self.output_dir, 
                    f'toc_{timestamp}_{filename}'
                )
                
                async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
                    await f.write(toc)
                    
                self.logger.info(f"目录已保存到: {output_path}")
            else:
                self.logger.warning("未能提取到目录")
                
        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")

async def process_books(input_dir: str, output_dir: str, api_key: str, max_concurrent: int = 10):
    """异步处理文件夹中的所有书籍，限制最大并发数"""
    # 获取所有.md文件
    book_files = glob.glob(os.path.join(input_dir, "*.md"))
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建信号量来限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(book_path):
        async with semaphore:
            extractor = TOCExtractor(book_path, output_dir, api_key)
            await extractor.process_file()
    
    # 创建总进度条
    with tqdm(total=len(book_files), desc="总体进度", position=0) as pbar:
        # 创建所有任务
        tasks = []
        for book_path in book_files:
            task = asyncio.create_task(process_with_semaphore(book_path))
            task.add_done_callback(lambda _: pbar.update(1))
            tasks.append(task)
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='处理多本书的目录提取')
    parser.add_argument('--input_dir', type=str, 
                      default="/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/1toc_md/good_toc",
                      help='输入文件夹路径')
    parser.add_argument('--output_dir', type=str,
                      default="/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/2toc_md",
                      help='输出文件夹路径')
    parser.add_argument('--max_concurrent', type=int, default=25,
                      help='最大并发处理数量')
    
    args = parser.parse_args()
    
    # 设置路径和API密钥
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 运行异步处理
    asyncio.run(process_books(
        args.input_dir,
        args.output_dir,
        api_key,
        args.max_concurrent
    ))