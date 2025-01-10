import os
import shutil

# 定义源目录和目标目录
source_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/md_processed2'
target_dir = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/合并的质量不好/books_processed2'

# 要复制的文件列表
files_to_copy = [
    '12 微生物学-沈萍,陈向东（8）.md',
    '14 生物信息学  陈铭（4）.md',
    '38 Lewin基因（12）.md',
    '4 基础生物化学原理.md',
    'Brock 微生物生物学（11上）.md',
    'Brock 微生物生物学（11下）.md',
    'Fundamentals of Biostatistics（5）中文版.md',
    'Weaver-分子生物学（4中文）.md',
    '动物生理学 陈守良（4）.md',
    '国际命名法规.md',
    '基础生命科学（2）.md',
    '武维华（3）.md',
    '生物信息学基础教程 张洛欣.md'
]

# 确保目标目录存在
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

# 复制文件
for filename in files_to_copy:
    source_path = os.path.join(source_dir, filename)
    target_path = os.path.join(target_dir, filename)
    
    try:
        if os.path.exists(source_path):
            shutil.copy2(source_path, target_path)
            print(f"成功复制: {filename}")
        else:
            print(f"文件不存在: {filename}")
    except Exception as e:
        print(f"复制 {filename} 时出错: {str(e)}")

print("复制完成！")