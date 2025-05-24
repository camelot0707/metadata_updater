import os
import subprocess
import shutil

if shutil.which("exiftool") is None:
    exit("Error: ExifTool not found. Please copy the .exe found at https://exiftool.org/ into the same directory as this script.")
else:
    print("ExifTool found, proceeding...")

def check_metadata(file_path):
    """Check if DateTimeOriginal, CreateDate, and ModifyDate exist in the file's metadata."""
    try:
        # Run exiftool to get the three fields
        result = subprocess.run(
            ['exiftool', '-DateTimeOriginal', '-CreateDate', '-ModifyDate', file_path],
            capture_output=True, text=True, check=True
        )
        output = result.stdout
        missing = []
        for tag in ['Date/Time Original', 'Create Date', 'Modify Date']:
            if tag not in output:
                missing.append(tag)
        if missing:
            print(f"{os.path.basename(file_path)}: Missing {', '.join(missing)}")
        else:
            print(f"{os.path.basename(file_path)}: All fields present")
    except Exception as e:
        print(f"Error checking {file_path}: {e}")

def main():
    folder = input("Enter folder path to check: ").strip()
    if not os.path.isdir(folder):
        print("Invalid folder path.")
        return

    print("Checking JPEG files for metadata fields...")
    for filename in os.listdir(folder):
        if filename.lower().endswith(('.jpg', '.jpeg')):
            check_metadata(os.path.join(folder, filename))

if __name__ == "__main__":
    main()