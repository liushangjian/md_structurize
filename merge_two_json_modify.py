"""
我希望合并这两个文档的信息。合并逻辑：
读取两个文档，对于书籍的每一个chunk（subsection+内容），为它提供10个toc的chunk （chapter+section）。
调用gpt-4o-mini判断书籍的内容属于哪一个toc chunk。合并两个chunk的内容。
提供10个toc chunk的逻辑是，gpt-4o-mini对一个内容块做出判断之后。根据它判断的chunk提供-2个chunk到+7个chunk给下一个文本块进行选择。
如果gpt-4o-mini对下一个内容块选择的toc在上一个内容块之前，则在命令行显示错误，程序停止。

窗口将始终包含7个TOC条目
窗口的起始位置是上一次匹配位置的前一个位置
如果到达列表开头或结尾，窗口会自动调整大小以适应可用的TOC条目
每次匹配后会更新当前位置，用于下一次窗口的计算
这种方式可以帮助模型在相邻的内容区域内进行匹配，提高匹配的准确性。
"""
import json
from typing import List, Dict, Optional
import sys
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import logging
from datetime import datetime
import argparse
from tqdm import tqdm
import time

class TocChunk:
    def __init__(self, chapter: str, section: str):
        self.chapter = chapter
        self.section = section
    
    def __str__(self):
        return f"{self.chapter} - {self.section}"

class ContentChunk:
    def __init__(self, subsection: str, content: str):
        self.subsection = subsection
        self.content = content

def load_toc(file_path: str) -> List[TocChunk]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"TOC data type: {type(data)}")
        
        # 检查数据结构
        if isinstance(data, dict) and 'sections' in data:
            sections = data['sections']
        else:
            sections = data
            
        chunks = []
        for section in sections:
            # 添加调试信息
            print(f"Processing TOC section: {section}")
            chapter = section.get('Chapter', '')
            section_title = section.get('Section', '')
            chunks.append(TocChunk(chapter, section_title))
        
        print(f"Loaded {len(chunks)} TOC chunks")
        return chunks

def load_content(file_path: str) -> List[ContentChunk]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print(f"Content data type: {type(data)}")
        
        # 检查数据结构并统一处理为列表
        if isinstance(data, dict):
            if 'Subsections' in data:  # 处理包含 Subsections 的情况
                sections = data['Subsections']
            elif 'sections' in data:
                sections = data['sections']
            else:
                sections = [data]
        else:
            sections = data
            
        chunks = []
        for item in sections:
            if isinstance(item, dict):
                subsection = item.get('Subsection')
                content = item.get('Content')
                if subsection and content:  # 确保两个字段都不为空
                    chunks.append(ContentChunk(subsection, content))
                    
        print(f"Loaded {len(chunks)} content chunks")
        return chunks

### 这个地方实际调节了误差的范围，只有前后n个标题会被输送给gpt。
def get_toc_window(toc_chunks: List[TocChunk], current_index: int, window_size: int = 8) -> List[TocChunk]:
    """
    Get a window of TOC chunks centered around the current index.
    Window includes [current_index-1, current_index, current_index+1, ..., current_index+4]
    """
    start_idx = max(0, current_index - 2)  # 从当前位置前一个开始
    end_idx = min(len(toc_chunks), start_idx + window_size)  # 向后取6个位置
    return toc_chunks[start_idx:end_idx]

class ContentMatcher:
    def __init__(self, api_key):
        self.client = AsyncOpenAI(api_key=api_key)
        self.setup_logging()
    
    def setup_logging(self):
        """设置日志"""
        # Create logs directory if it doesn't exist
        log_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/logs'
        os.makedirs(log_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f'content_matching_{timestamp}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    async def match_content_to_toc(self, content: ContentChunk, content_list: List[ContentChunk], current_index: int, toc_options: List[TocChunk]) -> List[TocChunk]:
        """
        匹配内容到目录项，使用三个相邻的文本块进行验证
        返回三个文本块对应的TOC条目列表
        """
        # 获取相邻的三个文本块，每个块限制300字符
        chunks = []
        chunk_texts = []  # 存储文本块的标题和内容
        
            
        # 添加当前块
        chunks.append(content)
        chunk_texts.append(f"以下是第一个文本块：{content.subsection}\n内容：{content.content[:200]}")
        
        # 添加后一个块（如果存在）
        if current_index < len(content_list) - 1:
            chunks.append(content_list[current_index + 1])
            chunk_texts.append(f"第一块结束，以下是第二个文本块：{content_list[current_index + 1].subsection}\n内容：{content_list[current_index + 1].content[:200]}")
            
        # 构建TOC选项字符串
        toc_options_str = "\n".join([f"{i}. {toc.chapter} - {toc.section}" 
                                   for i, toc in enumerate(toc_options, 1)])
        
        prompt = "你是一个文本分类专家。请为以下两个文本块从目录选项中选择最合适的一个。\n" + \
                 "请按顺序返回两个块对应的选项序号，用逗号分隔（如：1,2）。不要有任何解释。\n\n" + \
                 "请注意：\n" + \
                 "chapter,section,subsection之前的标识符，他们是有规律的。比如subsection2.2.2代表第2章，2.2节。\n" + \
                 "请主要按照section与（content和subsection）的相似度来判断，如果相似度很高，则返回section的序号。\n" + \
                 "请注意，这2个文本块是存在先后顺序的，第二个块的chapter,section的序号必须大于或等于第一个块的序号。举例：1,2或者3,3是允许的。\n" + \
                 "请注意，两个文本块的chapter,section的序号间隔不要太大，比如1,4或者2,5是不允许的。\n" + \
                 "如果某个文本块内容能够匹配多个章节，就给出所有选择中的第二个结果。\n" + \
                 "如果你认为文本块内容无法匹配任何一个章节，给出所有选择中的第二个结果。\n\n" + \
                 "目录选项：\n" + \
                 toc_options_str + "\n\n" + \
                 "文本块：\n" + \
                 "\n\n".join(chunk_texts) + "\n\n" + \
                 "请返回每个块对应的选项序号（用逗号分隔）："

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=15,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0
            )
            
            # 处理返回的序号列表
            try:
                indices = [int(idx.strip()) - 1 for idx in response.choices[0].message.content.strip().split(',')]
                results = []
                for idx in indices:
                    if 0 <= idx < len(toc_options):
                        results.append(toc_options[idx])
                    else:
                        results.append(toc_options[0])  # 对于无效索引使用第一个选项
                return results
            except ValueError:
                self.logger.error("GPT返回了无效的序号格式")
                return [toc_options[0]] * len(chunks)  # 返回相同数量的默认选项
                
        except Exception as e:
            self.logger.error(f"API调用失败: {str(e)}")
            return [toc_options[0]] * len(chunks)  # 返回相同数量的默认选项

async def process_single_book(toc_path: str, content_path: str, output_dir: str):
    """
    处理单本书的合并任务
    """
    try:
        print(f"\nProcessing book: {os.path.basename(toc_path)}")
        start_time = time.time()
        
        # 加载文档
        toc_chunks = load_toc(toc_path)
        if not toc_chunks:
            raise ValueError(f"No TOC chunks loaded from {toc_path}")
            
        content_chunks = load_content(content_path)
        if not content_chunks:
            raise ValueError(f"No content chunks loaded from {content_path}")
        
        # 创建 matcher 实例
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        matcher = ContentMatcher(api_key)
        
        merged_results = []
        current_toc_index = 0
        
        # 处理每个内容块
        for i, content_chunk in enumerate(tqdm(content_chunks, 
                                desc=f"Processing {os.path.basename(content_path)}", 
                                unit="chunks")):
            try:
                # 获取相关的 TOC 选项窗口
                toc_window = get_toc_window(toc_chunks, current_toc_index)
                if not toc_window:
                    raise ValueError(f"Empty TOC window at index {current_toc_index}")
                
                # 使用 GPT 匹配最合适的 TOC 条目
                matched_tocs = await matcher.match_content_to_toc(content_chunk, content_chunks, i, toc_window)
                if not matched_tocs:
                    raise ValueError("No matching TOC entries returned from GPT")
                
                matched_toc = matched_tocs[0]  # 使用第一个匹配结果
                
                # 更新当前TOC索引
                try:
                    matched_index = toc_chunks.index(matched_toc)
                    current_toc_index = matched_index
                except ValueError as e:
                    print(f"Warning: Could not find matched TOC in chunks: {str(e)}")
                    continue
                
                # 创建合并后的数据结构
                merged_chunk = {
                    "Chapter": matched_toc.chapter,
                    "Section": matched_toc.section,
                    "Subsection": content_chunk.subsection,
                    "Content": content_chunk.content
                }
                merged_results.append(merged_chunk)
                
            except Exception as chunk_error:
                print(f"Error processing chunk {i}: {str(chunk_error)}")
                continue
            
            # 添加小延迟以避免API限制
            await asyncio.sleep(0.1)
        
        if not merged_results:
            raise ValueError("No results were successfully merged")
            
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"merged_{timestamp}_{os.path.basename(toc_path)}"
        output_path = os.path.join(output_dir, output_filename)
        
        # 保存结果
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(merged_results, f, ensure_ascii=False, indent=2)
        
        elapsed_time = time.time() - start_time
        print(f"Completed {os.path.basename(toc_path)} in {elapsed_time:.2f} seconds")
        
        return output_path
        
    except Exception as e:
        print(f"Error processing {os.path.basename(toc_path)}: {str(e)}")
        print(f"Full error: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

async def process_all_books(toc_dir: str, content_dir: str, output_dir: str):
    """
    并行处理所有书籍，限制最大并发数为10
    """
    try:
        # 获取匹配的文件对
        file_pairs = get_matching_files(toc_dir, content_dir)
        if not file_pairs:
            raise ValueError("No matching file pairs found")
            
        total_files = len(file_pairs)
        print(f"\nFound {total_files} matching file pairs")
        print("Starting parallel processing with max 10 concurrent tasks...")
        
        # 创建信号量限制并发数
        semaphore = asyncio.Semaphore(20)
        
        async def process_with_semaphore(toc_path, content_path):
            async with semaphore:
                return await process_single_book(toc_path, content_path, output_dir)
        
        # 创建所有书籍的任务
        tasks = []
        for toc_path, content_path in file_pairs:
            task = process_with_semaphore(toc_path, content_path)
            tasks.append(task)
        
        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计处理结果并输出详细信息
        successful = 0
        failed = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed += 1
                print(f"Failed processing book {i+1}: {str(result)}")
            elif result is None:
                failed += 1
                print(f"Failed processing book {i+1}: Unknown error")
            else:
                successful += 1
        
        print(f"\nProcessing completed:")
        print(f"Successfully processed: {successful} books")
        print(f"Failed: {failed} books")
        
    except Exception as e:
        print(f"Error in process_all_books: {str(e)}")
        print(f"Full error: {type(e).__name__}: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

def get_matching_files(toc_dir: str, content_dir: str) -> List[tuple]:
    """
    获取匹配的TOC和content文件对
    返回格式: [(toc_path, content_path), ...]
    """
    toc_files = {os.path.splitext(f)[0]: os.path.join(toc_dir, f) 
                 for f in os.listdir(toc_dir) 
                 if f.endswith('.json')}
    
    content_files = {os.path.splitext(f)[0]: os.path.join(content_dir, f) 
                    for f in os.listdir(content_dir) 
                    if f.endswith('.json')}
    
    # 找到共同的文件名（不包含扩展名）
    common_names = set(toc_files.keys()) & set(content_files.keys())
    
    # 创建匹配的文件对
    file_pairs = [(toc_files[name], content_files[name]) for name in common_names]
    
    return file_pairs

def main():
    # 确保在开始时加载环境变量
    load_dotenv()
    
    # 验证 API key 是否存在
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment variables")
        print("Please make sure you have set the OPENAI_API_KEY in your .env file")
        sys.exit(1)
    
    start_time = time.time()
    
    # 设置目录路径
    toc_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/目录有问题/new_toc_json'
    content_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/JSON_book/allbooks'
    output_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/目录有问题/merged_two_json' #修改过的代码
    
    # 验证目录是否存在
    for directory in [toc_dir, content_dir]:
        if not os.path.exists(directory):
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    print("\nStarting batch processing...")
    print(f"TOC Directory: {toc_dir}")
    print(f"Content Directory: {content_dir}")
    print(f"Output Directory: {output_dir}")
    
    try:
        # 使用 asyncio 运行异步函数
        asyncio.run(process_all_books(toc_dir, content_dir, output_dir))
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        sys.exit(1)
    
    # 显示总运行时间
    total_time = time.time() - start_time
    print(f"\nAll processing completed!")
    print(f"Total execution time: {total_time:.2f} seconds")

if __name__ == "__main__":
    main()