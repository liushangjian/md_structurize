import os
import json
import shutil
from datetime import datetime

def fix_json_files(directory_path, create_backup=True):
    """
    处理指定目录下所有JSON文件的末尾格式
    
    Args:
        directory_path (str): JSON文件所在的目录路径
        create_backup (bool): 是否创建备份文件
    """
    # 确保目录存在
    if not os.path.exists(directory_path):
        print(f"目录不存在: {directory_path}")
        return

    # 创建备份目录
    if create_backup:
        backup_dir = os.path.join(directory_path, f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_dir, exist_ok=True)

    # 获取所有JSON文件
    json_files = [f for f in os.listdir(directory_path) if f.endswith('.json')]
    
    modified_count = 0
    error_count = 0
    
    for filename in json_files:
        file_path = os.path.join(directory_path, filename)
        print(f"处理文件: {filename}")
        
        try:
            # 创建备份
            if create_backup:
                backup_path = os.path.join(backup_dir, filename)
                shutil.copy2(file_path, backup_path)
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 检查文件格式
            if not content.startswith('['):
                print(f"警告: 文件 {filename} 不是以 '[' 开始")
                continue
            
            # 如果文件末尾有逗号，删除它并添加换行和方括号
            if content.endswith(','):
                # 删除末尾的逗号
                content = content[:-1].rstrip() + '\n]'
                
                # 验证JSON格式
                try:
                    json.loads(content)
                except json.JSONDecodeError:
                    print(f"错误: 修改后的 {filename} 不是有效的JSON格式")
                    continue
                
                # 写回文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"成功修改: {filename}")
                modified_count += 1
            else:
                print(f"文件 {filename} 不需要修改")
                
        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")
            error_count += 1
    
    # 输出统计信息
    print("\n处理完成:")
    print(f"总文件数: {len(json_files)}")
    print(f"修改文件数: {modified_count}")
    print(f"错误文件数: {error_count}")
    if create_backup:
        print(f"备份目录: {backup_dir}")

if __name__ == "__main__":
    # 指定要处理的目录路径
    directory = "/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/test_merge8"  # 替换为你的实际目录路径
    fix_json_files(directory, create_backup=True)