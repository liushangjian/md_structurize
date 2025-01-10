"""
这个是好用的toc识别脚本
使用asyncio包来同时处理一个文件夹中的多本书的内容。
对于每一本书中的chunk按顺序进行处理，当多本书中的一本书处理完之后开始下一本新的书。具体的处理过程无需改变
这个代码中添加最大同时处理的的数量限制，以及再命令行中显示每本书的处理进度
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
                你是一个文本处理专家，我将分段给你输入一本书的内容，从以下文本中识别目录部分，并将其转换为Markdown格式（用#表示层级）的目录。
                你只是处理文本，不要做任何评价或者描述。
                因为输入长度限制，目录可能分布在两次或者多次相邻输入的分段中，请记住上一段的处理方式，保持一致，不要偷懒！！！
                英文书籍的目录请不要翻译成中文

                规则：
                1. 目录识别特征：
                   - 标题编号密集出现的段落
                   - 连续多个X章,X节,或者数字编号12345一二三四五的短文本
                   - 每行都是类似标题的短文本或者连���多个短文本
                   - 句子中可能带有页码（需要删除）
                
                2. 标题层级判断规则：
                   目录部分相邻多个具有并列层级结构的内容需要被识别为同一层级：
                 文字前用于表示章节限定的数字（如1，1.1，1.1.1）或者符号（a,b,c）越多，则标题的级别越低。
                   举例：
                   第一级：
                   - 第X章
                   - 第X部分
                   
                   第二级：
                   - 第X节
                   - X.X（如1.1、2.1等）
                   
                   第三级：
                   - X.X.X（如1.1.1、2.1.1等）
                   - 一、二、三等中文数字编号
                   - 1、2、3等阿拉伯数字编号
                   
                   第四级：
                   - (一)、(二)、(三)等带括号的中文数字
                   - (1)、(2)、(3)等带括号的阿拉伯数字
                   - A、B、C等字母编号
                   
                   第五级：
                   - a)、b)、c)等小写字母编号
                   - 1)、2)、3)等带括号的数字
                   
                   特殊规则：
                   - 删除Box、图、表、注等特殊内容
                   - 保持章节的连续性和层级关系
                   - 确保每个标题都有对应的层级标记
                
                3. 输出要求：
                   - 只输出Markdown格式的目录（只用#的多少来标注层级）
                   - 保持原有的层级关系
                   - 删除包含"思考题"、"参考文献"、"练习题"和"附录"的部分
                   - 删除所有页码
                   - 确保每一行都有标题层级标记
                   - 标题之间用换行分隔
                
                4. 输出的示例
                    # 第一篇 结构生物化学
                    ## 第一章 绪论
                    ### 第一节 生物化学发展简史
                    ### 第二节 生物化学的主要内容及其应用
                    ### 第三节 生物化学学习方法

                    ## 第二章 蛋白质的结构与功能
                    ### 第一节 氨基酸
                    #### 一 氨基酸的结构和分类
                    #### 二 氨基酸的性质
                    #### 三 氨基酸的功能
                以下是要处理的文本内容：
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
                content = content[:20000]  # 限制处理长度
            
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
                      default="/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/books",
                      help='输入文件夹路径')
    parser.add_argument('--output_dir', type=str,
                      default="/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/tocs",
                      help='输出文件夹路径')
    parser.add_argument('--max_concurrent', type=int, default=10,
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