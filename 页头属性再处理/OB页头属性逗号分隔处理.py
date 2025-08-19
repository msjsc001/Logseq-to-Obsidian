# -*- coding: utf-8 -*-

# ========================================================================================
# 用法说明 (新手友好版)
# ========================================================================================
#
# 1. 功能：
#    自动批量处理 Obsidian 的 Markdown (.md) 文件。它会查找页头属性中的 `aliases` 
#    字段，并将任何包含逗号（中文`，`或英文`,`）的别名拆分成多个，最后生成一个
#    干净、标准的列表，且为每一项都加上双引号。
#
# 2. 如何使用：
#    a. 安装依赖库:
#       如果这是您第一次运行此脚本，请先打开终端 (Windows上叫 "命令提示符" 或 
#       "PowerShell", macOS上叫 "终端")，然后输入并执行以下命令：
#       pip install python-frontmatter ruamel.yaml
#
#    b. 放置脚本:
#       将这个 .py 脚本文件，直接复制或移动到您 Obsidian 仓库的【根目录】下。
#
#    c. 运行脚本:
#       直接双击运行这个 .py 文件。
#
# 3. **最重要的一点**：
#    在第一次运行前，强烈建议您【备份整个Obsidian仓库】！
#
# ========================================================================================

import os
import re
import sys
import frontmatter
from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import DoubleQuotedScalarString
from io import StringIO

# --- 全局配置区域 ---

# 脚本将自动处理其所在的目录
try:
    VAULT_PATH = os.path.dirname(os.path.abspath(__file__))
except NameError:
    VAULT_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))

# --- 核心处理函数 ---

def process_markdown_file(file_path):
    """
    处理单个Markdown文件，转换其aliases属性。
    现在能处理列表中多个项目都需要被拆分的情况，并为输出强制添加双引号。
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)

        if 'aliases' not in post.metadata or not isinstance(post.metadata['aliases'], list):
            return False

        original_aliases = post.metadata['aliases']
        new_aliases = []
        was_modified = False

        for item in original_aliases:
            if isinstance(item, str) and ('，' in item or ',' in item):
                was_modified = True
                split_items = [alias.strip() for alias in re.split(r'[，|,]', item) if alias.strip()]
                new_aliases.extend(split_items)
            else:
                new_aliases.append(item)

        if was_modified:
            # --- 新增：将每个别名转换为强制双引号的类型 ---
            quoted_aliases = [DoubleQuotedScalarString(alias) for alias in new_aliases]
            post.metadata['aliases'] = quoted_aliases

            # --- 稳定的文件保存逻辑 ---
            yaml = YAML()
            yaml.default_flow_style = False
            yaml.indent(sequence=4, offset=2)
            string_stream = StringIO()
            yaml.dump(post.metadata, string_stream)
            yaml_string = string_stream.getvalue()

            final_content = f"---\n{yaml_string}---\n\n{post.content}"

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            relative_path = os.path.relpath(file_path, VAULT_PATH)
            print(f"  -> 已修改: {relative_path}")
            return True

    except Exception as e:
        print(f"处理文件 {os.path.basename(file_path)} 时出错: {e}")
    
    return False


def batch_process_vault(path_to_process):
    """
    遍历指定路径下的所有 .md 文件并进行处理。
    """
    if not os.path.isdir(path_to_process):
        print(f"错误：指定的路径 '{path_to_process}' 不是一个有效的目录。")
        return

    print(f"开始扫描并处理路径: {path_to_process}")
    modified_files_count = 0

    for root, dirs, files in os.walk(path_to_process):
        if '.obsidian' in dirs:
            dirs.remove('.obsidian')
        if 'temp_self_test_dir_for_script' in dirs:
            dirs.remove('temp_self_test_dir_for_script')
        
        for filename in files:
            if filename.endswith('.md'):
                file_path = os.path.join(root, filename)
                if process_markdown_file(file_path):
                    modified_files_count += 1
    
    print("\n-----------------------------------------")
    print(f"扫描完成！共修改了 {modified_files_count} 个文件。")
    print("-----------------------------------------")


def self_test():
    """
    创建一个临时目录和一些测试文件来验证脚本逻辑是否正确。
    """
    print("--- 正在运行内部自测试... ---")
    test_dir = os.path.join(VAULT_PATH, "temp_self_test_dir_for_script")
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)

    test_cases = {
        "test_case_1_single_line_chinese_comma.md": """---
aliases:
  - "Aleksandr Lyubishchev，柳比歇夫"
tags: [test, person]
---
# 内容
""",
        "test_case_2_new_user_case.md": """---
aliases:
  - "扩张三角形，Expanding Triangles"
  - "ET，扩三"
tags: [new]
---
"""
    }

    try:
        for filename, content in test_cases.items():
            with open(os.path.join(test_dir, filename), 'w', encoding='utf-8') as f:
                f.write(content)

        for filename in test_cases.keys():
            process_markdown_file(os.path.join(test_dir, filename))

        all_passed = True
        print("--- 验证测试结果... ---")
        
        # 验证第一个文件
        file1_path = os.path.join(test_dir, "test_case_1_single_line_chinese_comma.md")
        with open(file1_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查输出是否包含带引号的字符串
            if '"Aleksandr Lyubishchev"' in content and '"柳比歇夫"' in content:
                 print(f"[通过] {os.path.basename(file1_path)} (格式正确)")
            else:
                 print(f"[失败] {os.path.basename(file1_path)} (引号格式错误)")
                 all_passed = False

        # 验证第二个文件
        file2_path = os.path.join(test_dir, "test_case_2_new_user_case.md")
        with open(file2_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if '"扩张三角形"' in content and '"Expanding Triangles"' in content and '"ET"' in content and '"扩三"' in content:
                 print(f"[通过] {os.path.basename(file2_path)} (格式正确)")
            else:
                 print(f"[失败] {os.path.basename(file2_path)} (引号格式错误)")
                 all_passed = False

        return all_passed

    finally:
        import shutil
        shutil.rmtree(test_dir)
        print("--- 自测试清理完成 ---\n")


if __name__ == "__main__":
    print("="*20 + " OB页头属性批处理脚本 " + "="*20)
    print(f"脚本当前所在目录: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"即将处理的目标仓库: {VAULT_PATH}\n")

    if self_test():
        print("自测试成功！脚本核心功能正常。现在正式开始处理您的仓库文件。\n")
        batch_process_vault(VAULT_PATH)
    else:
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!! 自测试失败！脚本已停止运行，您的文件未被修改。")
        print("!! 请检查您的Python环境或脚本代码。")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    print("\n" + "="*20 + " 所有操作已完成 " + "="*20)
    input("按 Enter 键关闭此窗口...")