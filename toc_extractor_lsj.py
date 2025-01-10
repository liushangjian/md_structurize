import asyncio
import aiofiles
from typing import List
import glob
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
from openai import OpenAI


class TOCExtractor:
    def __init__(self, input_path, output_dir, api_key):
        self.input_path = input_path
        self.output_dir = output_dir
        self.client = OpenAI(api_key=api_key)
        
        # Create logs directory if it doesn't exist
        self.logs_dir = os.path.join(os.path.dirname(output_dir), 'logs')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # 设置日志
        self.setup_logging()
        
    def setup_logging(self):
        """设置日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(self.logs_dir, f'toc_extraction_{timestamp}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def generate_response(self, prompt):
        """
        调用GPT-4生成响应
        这个地方是整本书的框架，所以对识别要求要高一些，而且一共就20000字符，所以用gpt-4也不会有很高的成本
        """
        try:
            response = self.client.chat.completions.create(
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
            
    def extract_toc(self, content):
        """从文档中提取目录并转换为Markdown格式"""
        words = content.split()
        chunk_size = 4000   ## 分成2000字符一个chunk，避免达到输入和输出的限制
        toc_parts = []
        
        # 按字符长度分割
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            prompt = """
            你是一个文本处理专家，我将分段给你输入一本书的内容，从以下文本中识别目录部分，并将其转换为Markdown格式（用#表示层级）的目录。
            你只是处理文本，不要做任何评价或者描述。
            因为输入长度限制，目录可能分布在两次或者多次相邻输入的分段中，请记住上一段的处理方式，保持一致，不要偷懒！！！
            英文书籍的目录请不要翻译成中文
            
            规则：
            1. 目录识别特征：
               - 标题编号密集出现的段落
               - 连续多个X章,X节,或者数字编号12345一二三四五的短文本
               - 每行都是类似标题的短文本或者连续多个短文本
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
               - 删除Box、图、表、注解等特殊内容
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
            """以上是要处理的文本内容"""
            try:
                response = self.generate_response(prompt)
                toc_parts.append(response.strip())
            except Exception as e:
                self.logger.error(f"目录提取失败: {str(e)}")
                continue
        
        # 合并所有部分
        full_toc = '\n'.join(toc_parts)
        return full_toc
    
    async def process_file(self):
        """异步处理文件并保存目录"""
        try:
            # 读取输入文件
            self.logger.info(f"开始读取文件: {self.input_path}")
            async with aiofiles.open(self.input_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                content = content[:20000]  # 只处理前20000字符
            
            # 提取目录
            self.logger.info("开始提取目录")
            toc = self.extract_toc(content)
            
            # 保存目录
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
async def process_book(input_path: str, output_dir: str, api_key: str) -> None:
    """异步处理单本书籍"""
    try:
        extractor = TOCExtractor(input_path, output_dir, api_key)
        await extractor.process_file()  # 注意：需要将 process_file 方法改为异步
    except Exception as e:
        logging.error(f"处理文件 {input_path} 时出错: {str(e)}")

async def process_books_directory(input_dir: str, output_dir: str, api_key: str, max_concurrent: int = 50) -> None:
    """
    异步处理目录中的所有书籍
    :param input_dir: 输入目录路径
    :param output_dir: 输出目录路径
    :param api_key: OpenAI API密钥
    :param max_concurrent: 最大并发数
    """
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有.md文件
    md_files = glob.glob(os.path.join(input_dir, "*.md"))
    
    if not md_files:
        logging.warning(f"在目录 {input_dir} 中未找到.md文件")
        return
    
    # 创建信号量来限制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(file_path: str) -> None:
        async with semaphore:
            await process_book(file_path, output_dir, api_key)
    
    # 创建所有任务
    tasks = [process_with_semaphore(file_path) for file_path in md_files]
    
    # 使用进度条显示处理进度
    total_files = len(md_files)
    completed = 0
    
    for task in asyncio.as_completed(tasks):
        try:
            await task
            completed += 1
            print(f"进度: {completed}/{total_files} ({(completed/total_files)*100:.2f}%)")
        except Exception as e:
            logging.error(f"任务执行失败: {str(e)}")

if __name__ == "__main__":
    load_dotenv()  # 加载 .env 文件中的环境变量
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    api_key = os.getenv("OPENAI_API_KEY")
    
    # 配置参数
    input_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/all_textbooks_md"
    output_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/toc_of_chinese"
    logs_dir = os.path.join(os.path.dirname(output_dir), 'logs')
    
    # Create logs directory if it doesn't exist
    os.makedirs(logs_dir, exist_ok=True)
    
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(logs_dir, 'batch_processing.log'), encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    # 运行异步处理
    try:
        asyncio.run(process_books_directory(input_dir, output_dir, api_key))
        print("所有文件处理完成！")
    except Exception as e:
        logging.error(f"批处理过程中发生错误: {str(e)}")

