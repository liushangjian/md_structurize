"""
这个文档包含两个步骤：
第一步：调用gpt-4o-mini完成以下任务：
1，在文档的前20000字符中识别出目录
2，将目录的层级转化为markdown标题的层级
3，将识别到的目录输出到一个markdown文档
因为模型的输入和输出长度的限制，我希望能够将这个文本拆分成5000词的chunk并拼接多段的输出来获取完整的目录。
第二步：调用gpt-4o-mini实现以下任务。
1，将HeadingRearranger类识别出目录作为新文件的目录输入给gpt-4o-mini
2，让gpt-4o-mini根据目录对markdown文本标题等级进行重新排列。
3，如果gpt-4o-mini遇到没有出现在目录中的标题，则设置为更低级的标题。
4，将正文标题层级重新排列后的运行结果输出成一个markdown文件。
"""
import os
import logging
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import json

class TOCExtractor:
    def __init__(self, input_path, output_dir, api_key):
        self.input_path = input_path
        self.output_dir = output_dir
        self.client = OpenAI(api_key=api_key)
        
        # 设置日志
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
        
    def generate_response(self, prompt):
        """
        调用GPT-4o-mini生成响应
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
              
    def generate_response2(self, prompt):
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
        chunk_size = 5000   ## 分成2000字符一个chunk，避免达到输入和输出的限制
        toc_parts = []
        
        # 按字符长度分割
        for i in range(0, len(content), chunk_size):
            chunk = content[i:i + chunk_size]
            prompt = """
            你是一个文本处理专家，我将分段给你输入一本书的内容，从以下文本中识别目录部分，并将其转换为Markdown格式（用#表示层级）的目录。
            你只是处理文本，不要做任何评价或者描述。
            因为输入长度限制，目录可能分布在两次或者多次相邻输入的分段中，请记住上一段的处理方式，保持一致，不要偷懒！！！

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
            
    def toc_from_file(self):
        """处理文件并保存目录"""
        try:
            # 读取输入文件
            self.logger.info(f"开始读取文件: {self.input_path}")
            with open(self.input_path, 'r', encoding='utf-8') as f:
                content = f.read()[:20000]  # 只处理前20000字符
            
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
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(toc)
                    
                self.logger.info(f"目录已保存到: {output_path}")
            else:
                self.logger.warning("未能提取到目录")
                
        except Exception as e:
            self.logger.error(f"处理失败: {str(e)}")
        return toc


"""
下面开始处理文档
"""

    
def process_markdown_file(input_path, output_dir, api_key):
    """
    处理Markdown文件：提取目录并重新排列标题层级
    :param input_path: 输入文件路径
    :param output_dir: 输出文件路径
    :param api_key: OpenAI API密钥
    """
    try:
        # 创建提取器实例 - 只传入 api_key
        extractor = TOCExtractor(input_path,output_dir,api_key)  # 修改这里，只传入 api_key
        
        # 读取输入文件
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 首先提取目录结构
        toc_content = extractor.toc_from_file()
        extractor.logger.info("目录提取完成")
        
        # 将内容分成较小的块进行处理
        lines = content.split('\n')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in lines:
            line_length = len(line)
            if current_length + line_length > 4000:
                chunks.append('\n'.join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += line_length
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        # 处理每个文本块
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            prompt = f"""系统：你是一个专业的文档处理助手。我在prompt中给出了一本书的目录结构，请参考目录结构按照以下规则处理这本书中的文本，只返回处理后的文本内容，不要添加任何解释或总结。
这本书很长，因此我拆分成多段提供给你。在处理不同段的时候，你的处理逻辑是不变的。

以下是目录结构：
{toc_content}
以上是目录结构：

处理规则：
1. 标题层级规则：
   - 仔细分析目录中的标题格式和层级关系，整本书的目录格式是一致的，请保持一致。
   - 例如：如果目录中"第X章"使用一级标题(#)，那么正文中所有"第X章"也应使用一级标题
   - 例如：如果目录中"X.X节"使用二级标题(##)，那么正文中所有"X.X节"也应使用二级标题
   - 保持与目录中相同标题格式的一致性
   - 标题的限定越多，层级越低。比如：2.2是二级标题，那么2.2.1应使用三级标题。

2. 未出现在目录中的标题处理：
   - 识别目录中最低层级的标题格式
   - 将未在目录中出现的标题设置为比目录最低层级更低一级
   - 相似格式的未知标题应保持相同的层级
   - 例如：如果目录最低层级是四级标题(####)，则未知标题应使用五级标题(#####)

3. 标题格式识别规则：
   - 数字编号：1、2、3等
   - 中文数字：一、二、三等
   - 字母编号：A、B、C或a、b、c等
   - 组合编号：1.1、1.2或(1)、(2)等
   - 特殊标记：第X章、第X节等

4. 删除内容（保持不变）：
   - 所有图片及图片描述（包含![]的行）
   - 致谢/acknowledgments部分
   - 前言
   - 参考文献/references
   - 思考题以及课后习题
   - 网络资源
   - 连续多个没有文字描述的标题

5. 保持其他内容不变：
   - 正文内容
   - 数学公式
   - 表格
   - 代码块

以下是需要处理的文本内容：

{chunk}

以上是需要处理的文本内容：
"""
            
            try:
                extractor.logger.info(f"正在处理第 {i+1}/{len(chunks)} 个文本块")
                response = extractor.generate_response2(prompt)
                processed_chunks.append(response.strip())
            except Exception as e:
                extractor.logger.error(f"处理第 {i+1} 个文本块时失败: {str(e)}")
                processed_chunks.append(chunk)  # 如果处理失败，保留原文
        
        # 合并处理后的文本块
        final_content = '\n'.join(processed_chunks)
        
     #   # 在文件开头添加目录
     #   final_content = f"{toc_content}\n\n{'='*50}\n\n{processed_content}" #感觉添加目录没什么意义
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_dir), exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path2 = os.path.join(output_dir, f'wholebook_rearranged_{timestamp}_{os.path.basename(input_path)}')
        # 写入处理后的文件
        with open(output_path2, 'w', encoding='utf-8') as f:
            f.write(final_content)
        
        extractor.logger.info("文件处理完成")
        extractor.logger.info(f"处理完成的文件已保存到: {output_path2}")
        return True, toc_content
        
    except Exception as e:
        logging.error(f"处理文件时发生错误: {str(e)}")
        return False, ""



if __name__ == "__main__":
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    # 配置参数
    input_path = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/assets/普通生物学_test.md"
    output_dir = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/markdown_output"
    #output_path = os.path.join(output_dir, f'rearranged_{os.path.basename(input_path)}')

    # 处理文件
    success, toc_structure = process_markdown_file(input_path, output_dir, api_key)
    
    if success:
        print("文档处理完成")
        #print("提取的目录结构：")
        #print(json.dumps(toc_structure, ensure_ascii=False, indent=2))
    else:
        print("文档处理失败") 