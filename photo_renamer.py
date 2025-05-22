
import os
import re
import shutil

# Define the pattern for the source filenames
pattern = re.compile(r"IMG_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})\.jpg", re.IGNORECASE)

# Prompt user for source and destination folder paths
src_dir = input("Enter the source folder path: ").strip()
dst_dir = input("Enter the destination folder path: ").strip()

if not os.path.isdir(src_dir):
    print(f"Source directory '{src_dir}' does not exist.")
    exit(1)
if not os.path.isdir(dst_dir):
    print(f"Destination directory '{dst_dir}' does not exist.")
    exit(1)

for filename in os.listdir(src_dir):
    match = pattern.match(filename)
    src_file = os.path.join(src_dir, filename)
    if match and os.path.isfile(src_file):
        year, month, day = match.group(1), match.group(2), match.group(3)
        hour, minute, second = match.group(4), match.group(5), match.group(6)
        new_filename = f"{year}-{month}-{day}_{hour}-{minute}-{second}.jpg"
        dst_file = os.path.join(dst_dir, new_filename)
        shutil.copy2(src_file, dst_file)
        print(f"Copied and renamed: {filename} -> {new_filename}")
    else:
        print(f"Skipped: {filename} (pattern not matched or not a file)")

