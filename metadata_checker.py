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

def check_exiftool_availability():
    """Checks if ExifTool is installed and in PATH. Exits script if not found."""
    if shutil.which("exiftool") is None:
        print("Error: ExifTool not found. Please ensure it's installed and in your system PATH.")
        print("You can download it from https://exiftool.org/")
        exit(1) # Exit script with an error code
    print("ExifTool found, proceeding with metadata check...\n")

def get_file_metadata_status(file_path):
    """
    Checks a single file for the configured metadata tags using ExifTool.
    Returns a dictionary: {'found_count': int, 'missing_tags': list, 'error_message': str|None}
    """
    exiftool_cli_tags = [f"-{tag_key}" for tag_key in TAGS_TO_CHECK_CONFIG.keys()]
    human_readable_target_tags = list(TAGS_TO_CHECK_CONFIG.values())
    
    present_tags_in_output = []
    error_msg = None

    try:
        command = ['exiftool'] + exiftool_cli_tags + [file_path]
        process = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,  # Crucial: handle non-zero exit codes manually
            encoding='utf-8'
        )

        # Analyze ExifTool's output
        stdout_lines = process.stdout.strip().split('\n') if process.stdout else []
        stderr_content = process.stderr.strip() if process.stderr else ""

        # Check for tags in stdout
        for line in stdout_lines:
            if not line.strip(): # Skip empty lines
                continue
            for hr_tag in human_readable_target_tags:
                if line.strip().startswith(hr_tag + ':'):
                    present_tags_in_output.append(hr_tag)
                    break # Found one of our target tags on this line

        # Determine if there was a significant error reported by ExifTool
        if process.returncode != 0:
            # ExifTool returns 1 if some files could not be processed (e.g. file not found by exiftool, corrupted)
            # or if some tags were not found (though it might still output other found tags).
            # We are interested in errors that prevent reading any metadata.
            if "Error: File not found" in stderr_content:
                error_msg = f"ExifTool error: File not found by ExifTool."
            elif stderr_content and not any(hr_tag in process.stdout for hr_tag in human_readable_target_tags):
                # If stderr has content AND no target tags were found in stdout, consider it an error.
                # Filter out common "1 image files read" if it's the only stderr.
                if not (stderr_content.lower().startswith("1 image files read") and len(stderr_content.splitlines()) == 1):
                    error_msg = f"ExifTool processing error: {stderr_content.splitlines()[0] if stderr_content else 'Unknown error'}"
            # If returncode is non-zero but tags were found, or stderr is just informational,
            # it's likely just that some requested tags are missing, not a processing error.

    except FileNotFoundError: # Raised if 'exiftool' command itself is not found
        error_msg = "Critical: ExifTool command not found during execution. Ensure PATH is correct."
        # This should ideally be caught by the initial check_exiftool_availability()
    except Exception as e: # Catch any other unexpected Python errors
        error_msg = f"Unexpected Python error: {str(e)}"

    # Remove duplicates from present_tags_in_output before counting
    unique_present_tags = sorted(list(set(present_tags_in_output)))
    found_count = len(unique_present_tags)
    
    missing_tags_list = [tag for tag in human_readable_target_tags if tag not in unique_present_tags]
    
    # If a critical error occurred and no tags were found, ensure found_count reflects this.
    if error_msg and not unique_present_tags:
        found_count = 0 # No tags considered found if a critical error prevented reading.

    return {
        'found_count': found_count,
        'missing_tags': missing_tags_list,
        'error_message': error_msg
    }

def main():
    check_exiftool_availability()

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