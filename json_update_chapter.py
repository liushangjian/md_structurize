"""
更新JSON文件中的章节信息,利用已经识别好的目录。已经识别好的目录具有很高的信噪比，用这个文件来更新对整本书分块识别产生的JSON文件
JSON文件只需要更新chapter和section两个部分即可
"""
import json

# Load the JSON data from the files with error handling
try:
    with open('md_processing/github_code/CrossModalRetrieval-RAG/all_books/toc_json/processed_20241210_131731_1 普通生物学（5）.json', 'r', encoding='utf-8') as file1:
        toc_data = json.load(file1)
except FileNotFoundError:
    raise FileNotFoundError("The file for toc_data was not found. Please check the file path.")
except json.JSONDecodeError:
    raise ValueError("The file for toc_data does not contain valid JSON.")

with open('md_processing/github_code/CrossModalRetrieval-RAG/all_books/JSON_book/chinese_book/1 普通生物学（5）.json', 'r', encoding='utf-8') as file2:
    content_data = json.load(file2)

# Check if toc_data is a list and not empty
if not isinstance(toc_data, list) or not toc_data:
    raise ValueError("toc_data is not a list or is empty")

# Initialize the merged data list
merged_data = []

# Initialize indices for both lists
toc_index = 0
content_index = 0

# Iterate through both lists
while toc_index < len(toc_data) and content_index < len(content_data):
    toc_entry = toc_data[toc_index]
    content_entry = content_data[content_index]

    # Check if the chapter and section match
    if toc_entry['Chapter'] == content_entry['Chapter'] and toc_entry['Section'] == content_entry['Section']:
        # If they match, merge the entries
        merged_entry = {
            "Chapter": toc_entry['Chapter'],
            "Section": toc_entry['Section'],
            "Subsection": content_entry['Subsection'],
            "Content": content_entry['Content']
        }
        merged_data.append(merged_entry)
        # Move to the next entries in both lists
        toc_index += 1
        content_index += 1
    else:
        # If they don't match, decide based on the rules
        # Here, we assume content belongs to the last matched chapter/section
        if content_entry['Chapter'] is None:
            content_entry['Chapter'] = toc_entry['Chapter']
        if content_entry['Section'] is None:
            content_entry['Section'] = toc_entry['Section']
        
        # Add the content entry to the merged data
        merged_data.append(content_entry)
        # Move to the next content entry
        content_index += 1

# Handle any remaining entries in the content data
while content_index < len(content_data):
    content_entry = content_data[content_index]
    if content_entry['Chapter'] is None:
        content_entry['Chapter'] = toc_data[-1]['Chapter']
    if content_entry['Section'] is None:
        content_entry['Section'] = toc_data[-1]['Section']
    merged_data.append(content_entry)
    content_index += 1

# Save the merged data to a new JSON file
output_path = '/home/azureuser/md_processing/github_code/CrossModalRetrieval-RAG/all_books/json_refine/merged_data.json'
with open(output_path, 'w', encoding='utf-8') as outfile:
    json.dump(merged_data, outfile, ensure_ascii=False, indent=4)