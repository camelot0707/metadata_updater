import os
import re
import shutil
from datetime import datetime

# Supported file extensions
PHOTO_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.3gp', '.webm', '.mkv'}

# List of (regex pattern, how to format the output) as (pattern, group order, is_short_year)
PATTERNS = [
    # YYYYMMDD_HHMMSS or YYYYMMDD-HHMMSS
    (re.compile(r'(\d{4})(\d{2})(\d{2})[-_T]?(\d{2})(\d{2})(\d{2})', re.I),
     ['1', '2', '3', '4', '5', '6'], False),
    # YYYY-MM-DD_HH-MM-SS or YYYY.MM.DD_HH.MM.SS or YYYY_MM_DD_HH_MM_SS
    (re.compile(r'(\d{4})[-_.](\d{2})[-_.](\d{2})[- T_\.]*(\d{2})[-_.](\d{2})[-_.](\d{2})', re.I),
     ['1', '2', '3', '4', '5', '6'], False),
    # YYYY-MM-DDThhmmssZ
    (re.compile(r'(\d{4})-(\d{2})-(\d{2})T(\d{2})(\d{2})(\d{2})Z', re.I),
     ['1', '2', '3', '4', '5', '6'], False),
    # YYYYMMDDHHMMSS (no separator at all)
    (re.compile(r'(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})', re.I),
     ['1', '2', '3', '4', '5', '6'], False),
    # DD-MM-YYYY_HHMMSS or DD.MM.YYYY_HHMMSS
    (re.compile(r'(\d{2})[-_.](\d{2})[-_.](\d{4})[-_ ]?(\d{2})(\d{2})(\d{2})', re.I),
     ['3', '2', '1', '4', '5', '6'], False),
    # MMDDYYYY_HHMMSS or MM-DD-YYYY_HHMMSS
    (re.compile(r'(\d{2})(\d{2})(\d{4})[-_ ]?(\d{2})(\d{2})(\d{2})', re.I),
     ['3', '1', '2', '4', '5', '6'], False),
    # YYMMDDhhmmss or YYMMDD_hhmmss
    (re.compile(r'(\d{2})(\d{2})(\d{2})[_\-]?(\d{2})(\d{2})(\d{2})', re.I),
     ['1', '2', '3', '4', '5', '6'], True),  # Year is 2-digit
]

def get_datetime_from_filename(filename):
    basename = os.path.splitext(filename)[0]
    for pattern, order, is_short_year in PATTERNS:
        match = pattern.search(basename)
        if match:
            try:
                elements = []
                for i in order:
                    group_value = match.group(int(i))
                    # Handle 2-digit year by prepending "20"
                    if is_short_year and i == '1' and len(group_value) == 2:
                        elements.append(f"20{group_value}")
                    else:
                        elements.append(group_value)
                
                # Validate date before returning
                year, month, day = int(elements[0]), int(elements[1]), int(elements[2])
                hour, minute, second = int(elements[3]), int(elements[4]), int(elements[5])
                
                # Check if date is valid
                datetime(year, month, day, hour, minute, second)
                
                return f"{''.join(elements[:3])}_{''.join(elements[3:])}"
            except (ValueError, IndexError):
                # Skip invalid dates or indices
                continue
    return None

def is_supported_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in PHOTO_EXTENSIONS or ext in VIDEO_EXTENSIONS

def main():
    src_dir = input("Enter the source folder path: ").strip()
    dst_dir = input("Enter the destination folder path: ").strip()
    
    if not os.path.isdir(src_dir):
        print(f"Source directory '{src_dir}' does not exist.")
        return
    if not os.path.isdir(dst_dir):
        create_dir = input(f"Destination directory '{dst_dir}' does not exist. Create it? (y/n): ")
        if create_dir.lower() == 'y':
            try:
                os.makedirs(dst_dir)
                print(f"Created directory: {dst_dir}")
            except OSError as e:
                print(f"Error creating directory: {e}")
                return
        else:
            return

    # Track rename operations and conflicts
    processed_count = 0
    skipped_count = 0
    conflict_count = 0
    
    for root, _, files in os.walk(src_dir):
        for filename in files:
            if not is_supported_file(filename):
                print(f"Skipped (unsupported extension): {filename}")
                skipped_count += 1
                continue
                
            src_path = os.path.join(root, filename)
            relative_path = os.path.relpath(root, src_dir)
            
            dt_val = get_datetime_from_filename(filename)
            if dt_val:
                ext = os.path.splitext(filename)[1].lower()
                new_name = f"{dt_val}{ext}"
                
                # Create subdirectory structure in destination if processing recursively
                if relative_path != '.':
                    dst_subdir = os.path.join(dst_dir, relative_path)
                    if not os.path.exists(dst_subdir):
                        os.makedirs(dst_subdir)
                    dst_path = os.path.join(dst_subdir, new_name)
                else:
                    dst_path = os.path.join(dst_dir, new_name)
                
                # Handle file conflicts by adding a suffix
                if os.path.exists(dst_path):
                    conflict_count += 1
                    base, ext = os.path.splitext(new_name)
                    counter = 1
                    while os.path.exists(os.path.join(dst_dir, f"{base}_{counter}{ext}")):
                        counter += 1
                    new_name = f"{base}_{counter}{ext}"
                    dst_path = os.path.join(dst_dir, new_name)
                
                try:
                    shutil.copy2(src_path, dst_path)
                    print(f"Copied and renamed: {filename} -> {new_name}")
                    processed_count += 1
                except (IOError, OSError) as e:
                    print(f"Error copying file {filename}: {e}")
            else:
                print(f"Skipped (no recognizable date): {filename}")
                skipped_count += 1

    print(f"\nSummary:")
    print(f"- Files processed: {processed_count}")
    print(f"- Files skipped: {skipped_count}")
    print(f"- Filename conflicts resolved: {conflict_count}")

if __name__ == "__main__":
    main()