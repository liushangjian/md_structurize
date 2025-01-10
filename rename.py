import os
import re

# Define the directory containing the files
directory = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/english_book/test_merge9/good_json'

# Iterate over all files in the directory
for filename in os.listdir(directory):
    # Construct the full file path
    old_file_path = os.path.join(directory, filename)
    
    # Check if it is a file (not a directory)
    if os.path.isfile(old_file_path):
        # 只保留最后一部分文件名，添加'toc_'前缀
        new_filename = filename.split('_')[-1]
        new_file_path = os.path.join(directory, new_filename)
        
        # 重命名文件
        os.rename(old_file_path, new_file_path)
        print(f"Renamed '{filename}' to '{new_filename}'")
