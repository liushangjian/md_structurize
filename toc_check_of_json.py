import json
from deep_translator import GoogleTranslator
import time
import os
import random
from datetime import datetime

def process_single_book(json_file: str, folder_path: str, output_file, samples_per_file=5, chunks_per_sample=5):
    """处理单本书籍"""
    try:
        file_path = os.path.join(folder_path, json_file)
        output_file.write(f"\n# {json_file}\n\n")
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.loads(file.read())
        
        # 创建目录列表
        toc = []
        for item in data:
            if all(key in item for key in ['Chapter', 'Section', 'Subsection']):
                toc.append((item['Chapter'], item['Section'], item['Subsection']))
        
        # 排序目录
        toc = sorted(list(set(toc)))
        
        if len(toc) == 0:
            output_file.write("该文件没有有效的目录结构\n\n")
            return
        
        translator = GoogleTranslator(source='en', target='zh-CN')
        
        # 随机选择起始点
        max_start = max(0, len(toc) - chunks_per_sample)
        start_points = sorted(random.sample(range(max_start + 1), min(samples_per_file, max_start + 1)))
        
        # 处理每个采样点
        for sample_idx, start_point in enumerate(start_points, 1):
            output_file.write(f"## 采样 {sample_idx}\n")
            output_file.write(f"起始索引: {start_point}\n\n")
            
            # 处理这个采样点后的chunks_per_sample个条目
            end_point = min(start_point + chunks_per_sample, len(toc))
            for i in range(start_point, end_point):
                chapter, section, subsection = toc[i]
                try:
                    output_file.write(f"### 条目 {i-start_point+1}\n")
                    
                    # 写入原文
                    output_file.write("原文：\n")
                    output_file.write(f"{chapter}\n")
                    if section:
                        output_file.write(f"  └─{section}\n")
                    if subsection:
                        output_file.write(f"    └─{subsection}\n")
                    output_file.write("\n")
                    
                    # 翻译并写入译文
                    chapter_zh = translator.translate(chapter) if chapter else ""
                    section_zh = translator.translate(section) if section else ""
                    subsection_zh = translator.translate(subsection) if subsection else ""
                    
                    output_file.write("翻译：\n")
                    output_file.write(f"{chapter_zh}\n")
                    if section_zh:
                        output_file.write(f"  └─{section_zh}\n")
                    if subsection_zh:
                        output_file.write(f"    └─{subsection_zh}\n")
                    output_file.write("\n")
                    
                    # 延迟以避免触发API限制
                    time.sleep(0.1)
                    
                except Exception as e:
                    print(f"翻译出错: {e}")
            
            output_file.write("---\n\n")  # 添加分隔线
                    
    except Exception as e:
        print(f"处理文件 {json_file} 时发生错误: {e}")

def extract_and_translate_toc_samples(folder_path: str, output_md_path: str, samples_per_file=5, chunks_per_sample=5):
    """主函数 - 同步处理所有书籍"""
    try:
        # 获取文件夹中的所有JSON文件
        json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]
        
        if not json_files:
            print("错误：未找到JSON文件！")
            return
            
        with open(output_md_path, 'w', encoding='utf-8') as output_file:
            # 写入头部信息
            output_file.write(f"# 目录翻译采样结果\n\n")
            output_file.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 顺序处理每个文件
            for json_file in json_files:
                process_single_book(json_file, folder_path, output_file, samples_per_file, chunks_per_sample)
                
        print(f"\n处理完成! 输出文件已保存到: {output_md_path}")
                
    except Exception as e:
        print(f"程序出错: {e}")

def main():
    folder_path = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/test_merge9"
    output_md_path = f"toc_translation_samples_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    extract_and_translate_toc_samples(folder_path, output_md_path)

if __name__ == "__main__":
    main()