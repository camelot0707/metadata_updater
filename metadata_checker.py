import os
import subprocess
import shutil

# --- Constants ---
# Tags as ExifTool expects them on the command line and their human-readable form for output/checking
TAGS_TO_CHECK_CONFIG = {
    "DateTimeOriginal": "Date/Time Original",
    "CreateDate": "Create Date",
    "ModifyDate": "Modify Date"
}
EXIFTOOL_EXECUTABLE = None # Will store the full path to exiftool.exe

def find_and_set_exiftool_path():
    """
    Finds ExifTool executable and sets the global EXIFTOOL_EXECUTABLE path.
    Search order:
    1. Script's directory.
    2. Recursively in subfolders of the script's parent directory.
    3. System PATH.
    Exits script if not found.
    """
    global EXIFTOOL_EXECUTABLE
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    exiftool_name = "exiftool.exe" if os.name == 'nt' else "exiftool"

    # 1. Check script's directory
    local_path = os.path.join(script_dir, exiftool_name)
    if os.path.isfile(local_path) and os.access(local_path, os.X_OK):
        EXIFTOOL_EXECUTABLE = local_path
        print(f"ExifTool found in script directory: {EXIFTOOL_EXECUTABLE}")
        return

    # 2. Check subfolders of the script's parent directory
    parent_dir = os.path.dirname(script_dir) # e.g., metadata_updater directory
    print(f"Searching for {exiftool_name} in subfolders of: {parent_dir}...")
    for root, _, files in os.walk(parent_dir):
        if exiftool_name in files:
            found_path = os.path.join(root, exiftool_name)
            if os.access(found_path, os.X_OK):
                EXIFTOOL_EXECUTABLE = found_path
                print(f"ExifTool found in subfolder: {EXIFTOOL_EXECUTABLE}")
                return

    # 3. Check system PATH
    path_from_which = shutil.which(exiftool_name)
    if path_from_which:
        EXIFTOOL_EXECUTABLE = path_from_which
        print(f"ExifTool found in system PATH: {EXIFTOOL_EXECUTABLE}")
        return

    print(f"Error: {exiftool_name} not found.")
    print("Please ensure exiftool.exe is in the script's directory, a subfolder of the project, or in your system PATH.")
    print("You can download it from https://exiftool.org/")
    exit(1)

def get_file_metadata_status(file_path):
    """
    Checks a single file for the configured metadata tags using ExifTool.
    Returns a dictionary: {'found_count': int, 'missing_tags': list, 'error_message': str|None}
    """
    if EXIFTOOL_EXECUTABLE is None:
        # This should not happen if find_and_set_exiftool_path() is called first
        return {'found_count': 0, 'missing_tags': list(TAGS_TO_CHECK_CONFIG.values()), 'error_message': "Critical: ExifTool executable path not set."}

    exiftool_cli_tags = [f"-{tag_key}" for tag_key in TAGS_TO_CHECK_CONFIG.keys()]
    human_readable_target_tags = list(TAGS_TO_CHECK_CONFIG.values())
    
    present_tags_in_output = []
    error_msg = None

    try:
        # Use the full path to exiftool and -S for simple output
        command = [EXIFTOOL_EXECUTABLE] + exiftool_cli_tags + ['-S', file_path] 
        
        # Set the current working directory for the subprocess to ExifTool's directory
        exiftool_dir = os.path.dirname(EXIFTOOL_EXECUTABLE)
        
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            encoding='utf-8',
            cwd=exiftool_dir # Crucial for standalone Windows ExifTool to find its DLLs
        )

        stdout_lines = process.stdout.strip().split('\n') if process.stdout else []
        stderr_content = process.stderr.strip() if process.stderr else ""

        for line in stdout_lines:
            if not line.strip():
                continue
            # With -S, output is "TagName: Value"
            tag_name_from_output = line.split(':', 1)[0].strip()
            if tag_name_from_output in TAGS_TO_CHECK_CONFIG:
                 present_tags_in_output.append(TAGS_TO_CHECK_CONFIG[tag_name_from_output])

        if process.returncode != 0:
            if "perl5" in stderr_content and ".dll" in stderr_content:
                 error_msg = f"ExifTool runtime error (likely Perl DLL issue): {stderr_content.splitlines()[0] if stderr_content else 'Unknown Perl DLL error'}"
            elif "Error: File not found" in stderr_content or "Error: File not found" in process.stdout:
                error_msg = f"ExifTool error: File not found by ExifTool."
            elif stderr_content and not any(hr_tag in process.stdout for hr_tag in human_readable_target_tags):
                if not (stderr_content.lower().startswith("1 image files read") and len(stderr_content.splitlines()) == 1):
                    error_msg = f"ExifTool processing error: {stderr_content.splitlines()[0] if stderr_content else 'Unknown error'}"
        
        if "perl5" in stderr_content and ".dll" in stderr_content: # Prioritize this error
            error_msg = f"ExifTool runtime error: {stderr_content.splitlines()[0] if stderr_content else 'Unknown Perl DLL error'}"

    except FileNotFoundError: 
        error_msg = "Critical: ExifTool command could not be executed. Ensure EXIFTOOL_EXECUTABLE path is correct."
    except Exception as e:
        error_msg = f"Unexpected Python error: {str(e)}"

    unique_present_tags = sorted(list(set(present_tags_in_output)))
    found_count = len(unique_present_tags)
    missing_tags_list = [tag for tag in human_readable_target_tags if tag not in unique_present_tags]
    
    if error_msg and not unique_present_tags:
        found_count = 0

    return {
        'found_count': found_count,
        'missing_tags': missing_tags_list,
        'error_message': error_msg
    }

def main():
    find_and_set_exiftool_path() # Find and set ExifTool path at the start
    print("ExifTool check passed, proceeding with metadata check...\n" if EXIFTOOL_EXECUTABLE else "")


    folder_path = input("Enter folder path to check for JPEGs: ").strip()
    if not os.path.isdir(folder_path):
        print(f"Error: Folder not found at '{folder_path}'")
        return

    print(f"\nChecking JPEG files in '{folder_path}' for metadata fields: {', '.join(TAGS_TO_CHECK_CONFIG.values())}...")
    
    stats = {
        "total_files_scanned": 0,
        "files_with_errors": 0,
        "tags_found_counts": {i: 0 for i in range(len(TAGS_TO_CHECK_CONFIG) + 1)} # Counts for 0, 1, 2, 3 tags
    }

    jpeg_files_found = 0
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            jpeg_files_found +=1
            stats["total_files_scanned"] += 1
            file_path = os.path.join(folder_path, filename)
            
            status = get_file_metadata_status(file_path)
            
            if status['error_message']:
                print(f"-> {filename}: ERROR - {status['error_message']}")
                stats["files_with_errors"] += 1
            else:
                found_count = status['found_count']
                stats["tags_found_counts"][found_count] += 1
                if status['missing_tags']:
                    print(f"-> {filename}: Found {found_count}/{len(TAGS_TO_CHECK_CONFIG)} tags. Missing: {', '.join(status['missing_tags'])}")
                else:
                    print(f"-> {filename}: All {len(TAGS_TO_CHECK_CONFIG)} required tags present.")
    
    if jpeg_files_found == 0:
        print("\nNo JPEG files found in the specified directory.")
        return

    print("\n--- Metadata Check Summary ---")
    print(f"Total JPEG files scanned: {stats['total_files_scanned']}")
    print(f"Files with all {len(TAGS_TO_CHECK_CONFIG)} required tags: {stats['tags_found_counts'][len(TAGS_TO_CHECK_CONFIG)]}")
    for i in range(len(TAGS_TO_CHECK_CONFIG) -1, -1, -1): # Print for 2, 1, 0 tags found
        print(f"Files with exactly {i} required tag(s): {stats['tags_found_counts'][i]}")
    if stats["files_with_errors"] > 0:
        print(f"Files that encountered processing errors: {stats['files_with_errors']}")
    
    # For very large numbers of files, ExifTool's -stay_open option can significantly speed up processing.
    # This script calls ExifTool once per file for simplicity.

if __name__ == "__main__":
    main()