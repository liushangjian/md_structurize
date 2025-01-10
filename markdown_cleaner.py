import os
import logging
import asyncio
import aiohttp
from openai import AsyncOpenAI
from datetime import datetime
from pathlib import Path
from typing import List, Tuple
import glob
import aiofiles

class MarkdownCleaner:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    async def generate_response(self, prompt: str) -> str:
        """异步调用GPT-4o-mini生成响应"""
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

    async def clean_markdown(self, content: str) -> str:
        """异步清理Markdown文档，对每本书的chunks按顺序处理"""
        # 将内容分成较小的块进行处理
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in content.split('\n'):
            line_length = len(line)
            if current_length + line_length > 4000:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # 顺序处理每个块
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            prompt = """You are a professional document processing assistant. Please process the text according to the following rules and return only the processed text without any explanations:

1. Remove the following content:
   - All images and image descriptions (lines containing ![])
   - Acknowledgments section
   - Preface/Foreword
   - References/Bibliography section
   - Review questions， exercises, concept check questions
   - All content before the table of contents
   - Content outside the main text (e.g., appendices, indices)
   - Further reading sections
   - Headers without accompanying text
   - Table of contents

2. Retain the following content:
   - All chapter and section headings (in markdown format)
   - Main body text
   - Mathematical equations
   - Code blocks
   - Essential tables and figures

3. Processing rules:
   - Maintain the hierarchical structure of headings
   - Preserve the original formatting of the main text
   - Remove excessive blank lines (keep maximum one blank line)
   - Ensure textual coherence and flow
   - Maintain academic writing style and terminology

Please process the following text:

"""
            prompt += chunk
            
            try:
                self.logger.info(f"正在处理第 {i+1}/{len(chunks)} 个文本块")
                response = await self.generate_response(prompt)
                processed_chunks.append(response.strip())
            except Exception as e:
                self.logger.error(f"处理第 {i+1} 个文本块时失败: {str(e)}")
                processed_chunks.append(chunk)  # 如果处理失败，保留原文
        
        return '\n'.join(processed_chunks)

async def clean_markdown_file(input_path: str, output_dir: str, api_key: str) -> bool:
    """异步处理单个Markdown文件"""
    try:
        cleaner = MarkdownCleaner(api_key)
        
        # 异步读取输入文件
        async with aiofiles.open(input_path, 'r', encoding='utf-8') as f:
            content = await f.read()
        
        # 清理文档
        cleaned_content = await cleaner.clean_markdown(content)
        
        # 保存处理后的文件
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(
            output_dir, 
            f'cleaned_{timestamp}_{os.path.basename(input_path)}'
        )
        
        # 异步写入文件
        async with aiofiles.open(output_path, 'w', encoding='utf-8') as f:
            await f.write(cleaned_content)
        
        cleaner.logger.info(f"文件已清理并保存到: {output_path}")
        return True
        
    except Exception as e:
        logging.error(f"处理文件时发生错误: {str(e)}")
        return False

async def process_book(input_path: str, output_dir: str, api_key: str) -> Tuple[str, bool]:
    """异步处理单本书籍"""
    try:
        success = await clean_markdown_file(input_path, output_dir, api_key)
        return input_path, success
    except Exception as e:
        logging.error(f"处理文件 {input_path} 时出错: {str(e)}")
        return input_path, False

async def process_books_directory(
    input_dir: str,
    output_dir: str,
    api_key: str,
    max_concurrent: int = 50
) -> None:
    """
    异步处理目录中的所有书籍，每次最多同时处理max_concurrent本书
    :param input_dir: 输入目录路径
    :param output_dir: 输出目录路径
    :param api_key: OpenAI API密钥
    :param max_concurrent: 最大并发书籍数
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有markdown文件
    md_files = []
    for ext in ['*.md', '*.markdown']:
        md_files.extend(glob.glob(os.path.join(input_dir, "**", ext), recursive=True))
    
    if not md_files:
        logging.warning(f"在目录 {input_dir} 中未找到Markdown文件")
        return
    
    # 创建信号量来限制并发书籍数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(file_path: str) -> Tuple[str, bool]:
        async with semaphore:
            return await process_book(file_path, output_dir, api_key)
    
    # 创建所有任务
    tasks = [process_with_semaphore(file_path) for file_path in md_files]
    
    # 使用进度条显示处理进度
    total_files = len(md_files)
    completed = 0
    success_count = 0
    failed_files = []
    
    for task in asyncio.as_completed(tasks):
        try:
            file_path, success = await task
            completed += 1
            if success:
                success_count += 1
            else:
                failed_files.append(file_path)
            
            print(f"进度: {completed}/{total_files} ({(completed/total_files)*100:.2f}%)")
        except Exception as e:
            logging.error(f"任务执行失败: {str(e)}")
    
    # 打印最终处理结果
    print(f"\n处理完成:")
    print(f"成功: {success_count}/{total_files} 个文件")
    if failed_files:
        print("\n处理失败的文件:")
        for file in failed_files:
            print(f"- {file}")

async def main():
    """主函数"""
    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 配置参数
    input_dir = "md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_output"
    output_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_after_gpt"
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(output_dir, 'batch_processing.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 运行异步处理
    try:
        await process_books_directory(input_dir, output_dir, api_key)
        print("所有文件处理完成！")
    except Exception as e:
        logging.error(f"批处理过程中发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 