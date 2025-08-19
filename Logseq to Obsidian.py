# -*- coding: utf-8 -*-
"""
Logseq to Obsidian Migrator (Final Architecture)

This script migrates Logseq-style block references and properties to Obsidian format.

Architecture: Read-Process-Write
1.  Phase 1 (Read-Only): Scan all .md files to build a complete and accurate
    database of block IDs and their corresponding content. This phase does not
    modify any files.
2.  Phase 2 (Process & Write): Re-scan all .md files. For each file, it reads
    the content into memory, performs all transformations (property conversion,
    reference replacement, block wrapping) based on the database from Phase 1,
    and then writes the fully transformed content back to the file in one go.
"""

import os
import re
import shutil
import argparse
import logging
from datetime import datetime
from tqdm import tqdm

# --- Setup Logging ---
log_filename = f"L块-O页面块_migration_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# --- Constants ---
UUID_PATTERN = re.compile(r'id::\s*([a-f0-9\-]{36})')
BLOCK_REF_PATTERN = re.compile(r'\(\(([a-f0-9\-]{36})\)\)')
id_db = {}

def find_markdown_files(directory):
    """Recursively finds all .md files in a directory, excluding backup folders."""
    markdown_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if 'L块-O页面块_backup' not in d]
        for file in files:
            if file.endswith('.md'):
                markdown_files.append(os.path.join(root, file))
    return markdown_files

def create_backup(directory, files):
    """Creates a timestamped backup of all target markdown files."""
    backup_dir = os.path.join(directory, f"L块-O页面块_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        os.makedirs(backup_dir)
        logging.info(f"Creating backup directory: {backup_dir}")
        for file_path in tqdm(files, desc="Backing up files"):
            relative_path = os.path.relpath(file_path, directory)
            backup_file_path = os.path.join(backup_dir, relative_path)
            os.makedirs(os.path.dirname(backup_file_path), exist_ok=True)
            shutil.copy2(file_path, backup_file_path)
        logging.info("Backup created successfully.")
        return True
    except Exception as e:
        logging.error(f"Backup failed: {e}")
        return False

def sanitize_text_for_linking(text):
    """Sanitizes text according to specified rules for safe linking."""
    text = text.replace('**', '★').replace('*', '★')
    text = text.replace(':', '：')
    text = text.replace('?', '？')
    text = text.replace('<', '〈').replace('>', '〉')
    text = text.replace('"', '“')
    text = text.replace('|', '｜')
    text = text.replace('\\', '、')
    text = text.replace('/', '-')
    return text

def convert_logseq_properties_to_yaml(lines):
    """Converts Logseq properties at the start of a file to Obsidian YAML frontmatter."""
    properties = {}
    property_lines_count = 0
    in_properties_block = False
    
    for i, line in enumerate(lines):
        line_stripped = line.strip()
        if '::' in line_stripped and not line_stripped.startswith('- '):
            is_property_line = (i == 0) or (in_properties_block) or (lines[i-1].strip() == '')
            if is_property_line:
                in_properties_block = True
            else:
                break
        elif line_stripped == "" and in_properties_block:
            continue
        elif in_properties_block:
            break
        else:
            return lines, 0

        if in_properties_block:
            key, *value_parts = line_stripped.split('::', 1)
            key = key.strip()
            if not key: continue
            value_str = value_parts[0].strip() if value_parts else ''
            if key == 'alias': key = 'aliases'
            values = [v.strip() for v in value_str.split(',') if v.strip()]
            properties[key] = values
            property_lines_count = i + 1
    
    if not properties:
        return lines, 0

    yaml_lines = ['---\n']
    for key, values in properties.items():
        yaml_lines.append(f'{key}:\n')
        for value in values:
            yaml_lines.append(f'  - "{value}"\n')
    yaml_lines.append('---\n')

    return yaml_lines + lines[property_lines_count:], len(yaml_lines)

def phase_one_build_db(files):
    """Phase 1 (Read-Only): Scans all files to build the UUID->content database."""
    logging.info("\n--- Phase 1: Building database (read-only) ---")
    for file_path in tqdm(files, desc="Phase 1: Building DB"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                match = UUID_PATTERN.search(line)
                if match:
                    uuid_val = match.group(1)
                    page_num = None
                    content_line_index = -1
                    
                    for j in range(i - 1, -1, -1):
                        prev_line = lines[j].strip()
                        if prev_line.startswith('hl-page::'):
                            page_num = prev_line.split('::')[1].strip()
                        elif prev_line.startswith(('ls-type::', 'hl-color::')):
                            continue
                        else:
                            content_line_index = j
                            break
                    
                    if content_line_index != -1:
                        content_text = lines[content_line_index].strip()
                        
                        temp_content = content_text[2:].strip() if content_text.startswith('- ') else content_text
                        if BLOCK_REF_PATTERN.fullmatch(temp_content):
                            continue

                        if content_text.startswith('- '):
                            content_text = content_text[2:].strip()

                        final_content = f"{content_text} page-{page_num}" if page_num else content_text
                        id_db[uuid_val] = sanitize_text_for_linking(final_content)
        except Exception as e:
            logging.error(f"Error building database for file {file_path}: {e}", exc_info=True)

def phase_two_process_and_write(files):
    """Phase 2 (Process & Write): Reads, transforms, and writes each file."""
    logging.info("\n--- Phase 2: Processing and writing files ---")
    for file_path in tqdm(files, desc="Phase 2: Writing files"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines, props_offset = convert_logseq_properties_to_yaml(lines)
            lines_to_process = list(new_lines)
            lines_to_delete = set()
            
            i = 0
            while i < len(lines_to_process):
                line = lines_to_process[i]
                
                lines_to_process[i] = BLOCK_REF_PATTERN.sub(lambda m: f"[[{id_db.get(m.group(1), m.group(0))}]]", line)

                if (i + 1) < len(lines_to_process):
                    next_line = lines_to_process[i+1]
                    id_match = UUID_PATTERN.search(next_line)
                    if id_match:
                        uuid_val = id_match.group(1)
                        if uuid_val in id_db:
                            original_content_line = lines_to_process[i]
                            prefix_match = re.match(r'^(\s*-\s*)', original_content_line)
                            prefix = prefix_match.group(1) if prefix_match else ""
                            
                            new_content_line = f"{prefix}[[{id_db[uuid_val]}]]\n"
                            lines_to_process[i] = new_content_line
                            
                            lines_to_delete.add(i + 1)
                            j = i + 2
                            while j < len(lines_to_process) and lines_to_process[j].strip().startswith(('ls-type::', 'hl-page::', 'hl-color::')):
                                lines_to_delete.add(j)
                                j += 1
                i += 1
            
            final_lines = [line for idx, line in enumerate(lines_to_process) if idx not in lines_to_delete]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(final_lines)
        except Exception as e:
            logging.error(f"Error processing file {file_path}: {e}", exc_info=True)

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Logseq to Obsidian Migrator.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('directory', nargs='?', default='.', help='Root directory of the Logseq vault (default: current dir).')
    parser.add_argument('--no-backup', action='store_true', help='Skip the backup process (DANGEROUS).')
    args = parser.parse_args()

    target_dir = args.directory
    
    logging.info("=============================================")
    logging.info(" Logseq to Obsidian Migration Tool")
    logging.info(f" Target Directory: {os.path.abspath(target_dir)}")
    logging.info("=============================================")

    markdown_files = find_markdown_files(target_dir)
    if not markdown_files:
        logging.warning("No .md files found in the target directory. Exiting.")
        return
        
    logging.info(f"Found {len(markdown_files)} markdown files.")

    if not args.no_backup:
        if not create_backup(target_dir, markdown_files):
            logging.error("Backup failed. Aborting migration.")
            return
    else:
        logging.info("Skipping backup as per --no-backup flag.")

    phase_one_build_db(markdown_files)
    logging.info(f"\nDatabase build complete. Found {len(id_db)} unique block IDs.")
    
    phase_two_process_and_write(markdown_files)
    
    logging.info("\nMigration complete! All steps executed.")
    logging.info(f"Log file saved to: {log_filename}")

if __name__ == '__main__':
    main()
