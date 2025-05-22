
import os
import re
import shutil
import subprocess
import tempfile

def run_exiftool(files, commands):
    """Run exiftool commands on a batch of files using a temp file list"""
    if not files:
        return
        
    # Create a temporary file listing all files to process
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write('\n'.join(files))
        temp_filename = f.name
    
    # Run exiftool with the file list
    try:
        cmd = ['exiftool', '-@', temp_filename] + commands
        subprocess.run(cmd, check=True)
        print(f"Updated metadata for {len(files)} files")
    except subprocess.CalledProcessError as e:
        print(f"Error running ExifTool: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

def main():
    # Get source and destination folders
    src_dir = input("Enter source folder: ").strip()
    dst_dir = input("Enter destination folder: ").strip()
    
    # Create temporary directory for processing
    temp_dir = os.path.join(dst_dir, "_temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Lists to track files
    process_files = []  # Files in temp dir that need metadata updates
    skipped_files = []  # Files that didn't match the pattern
    
    print("\nSTEP 1: Copying files to temporary directory...")
    
    # Copy files to temp dir with original names
    for filename in os.listdir(src_dir):
        # Look for files matching pattern IMG-YYYYMMDD-WA####.jpg
        match = re.match(r"IMG-(\d{8})-WA\d+\.jpe?g", filename, re.IGNORECASE)
        
        if match:
            src_path = os.path.join(src_dir, filename)
            temp_path = os.path.join(temp_dir, filename)
            
            # Copy file to temp dir
            shutil.copy2(src_path, temp_path)
            process_files.append(temp_path)
            print(f"Copied: {filename}")
        else:
            skipped_files.append(filename)
            print(f"Skipped: {filename} (doesn't match pattern)")
    
    print(f"\nSTEP 2: Updating metadata for {len(process_files)} files...")
    
    # Process metadata for all copied files in batches based on date
    # Group files by date for batch processing
    date_groups = {}
    for temp_path in process_files:
        filename = os.path.basename(temp_path)
        match = re.match(r"IMG-(\d{8})-WA\d+\.jpe?g", filename, re.IGNORECASE)
        if match:
            date_part = match.group(1)
            if date_part not in date_groups:
                date_groups[date_part] = []
            date_groups[date_part].append(temp_path)
    
    # Process each date group with a single ExifTool command
    for date_part, files in date_groups.items():
        year = date_part[:4]
        month = date_part[4:6]
        day = date_part[6:8]
        
        # Format date for metadata
        date_value = f"{year}:{month}:{day} 20:00:00"
        
        print(f"Updating metadata for date: {date_part} ({len(files)} files)")
        
        # Update metadata for all files with this date
        commands = [
            f"-DateTimeOriginal={date_value}",
            f"-CreateDate={date_value}",
            f"-ModifyDate={date_value}",
            "-overwrite_original"
        ]
        
        run_exiftool(files, commands)
    
    print("\nSTEP 3: Renaming and moving files to destination...")
    
    # Rename and move files to final destination
    for temp_path in process_files:
        filename = os.path.basename(temp_path)
        match = re.match(r"IMG-(\d{8})-WA\d+\.jpe?g", filename, re.IGNORECASE)
        
        if match:
            date_part = match.group(1)
            
            # Create new filename: YYYYMMDD.jpg
            ## new_name = f"{date_part}.jpg"
            ## dst_path = os.path.join(dst_dir, new_name)
            
            # Handle duplicate filenames
            counter = 1
            while os.path.exists(dst_path):
                new_name = f"{date_part}_{counter}.jpg"
                dst_path = os.path.join(dst_dir, new_name)
                counter += 1
            
            # Move and rename the file
            shutil.move(temp_path, dst_path)
            #print(f"Renamed and moved: {filename} → {new_name}")
            print(f"Moved {filename}")
            
    
    # Clean up temp directory
    try:
        os.rmdir(temp_dir)
        print(f"Removed temporary directory: {temp_dir}")
    except OSError:
        print(f"Note: Temporary directory not empty, skipping removal: {temp_dir}")
    
    # Show summary
    print(f"\nSummary: {len(process_files)} files processed, {len(skipped_files)} files skipped")
    # List skipped files at the end for review
    for filename in skipped_files:
        print(f"  Skipped: {filename} (doesn't match pattern)")
            
if __name__ == "__main__":
    main()
