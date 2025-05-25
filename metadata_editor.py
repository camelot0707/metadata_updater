import os
import re
import shutil
import subprocess
import tempfile
import json
from datetime import datetime, timedelta

# --- Configuration ---
EXIFTOOL_EXECUTABLE = None # Will store the full path to exiftool.exe
DATE_FORMATS_FILE_PATHS = [
    os.path.join("Insights", "date_formats_source.json"), # Primary location
    "date_formats_source.json" # Fallback location
]
SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.heic', '.heif', '.tiff', '.tif', '.mp4', '.mov', '.arw', '.cr2', '.nef', '.orf', '.raf', '.rw2', '.srw')
DEFAULT_TIME_IF_ONLY_DATE_FOUND = "20:00:00"

# --- ExifTool Check ---
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
    local_path_script_dir = os.path.join(script_dir, exiftool_name)
    if os.path.isfile(local_path_script_dir) and os.access(local_path_script_dir, os.X_OK):
        EXIFTOOL_EXECUTABLE = local_path_script_dir
        print(f"ExifTool found in script directory: {EXIFTOOL_EXECUTABLE}")
        return

    # 2. Check subfolders of the script's parent directory
    parent_dir = os.path.dirname(script_dir)
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

find_and_set_exiftool_path() # Call the function to set the path

# --- Date Format Parsing Logic ---
DATE_COMPONENT_REGEX_MAP = {
    # Order matters for tokens that are substrings of others (e.g., YYYY before YY)
    "YYYY": r"(?P<year>\d{4})",
    "YY": r"(?P<shortyear>\d{2})",
    "MM": r"(?P<month>\d{2})", # Expects 2 digits
    "M": r"(?P<month>\d{1,2})", # Allows 1 or 2 digits
    "DDD": r"(?P<dayofyear>\d{3})", # For 3-digit day of year
    "DD": r"(?P<day>\d{2})",   # Expects 2 digits
    "D": r"(?P<day>\d{1,2})",  # Allows 1 or 2 digits
    "HH": r"(?P<hour>\d{2})",  # 24-hour for main time
    "hh": r"(?P<hour12>\d{2})", # 12-hour for main time (used with AMPM)
    "mm": r"(?P<minute>\d{2})", # lowercase 'mm' for main time minutes
    "SS": r"(?P<second>\d{2})", # uppercase 'SS' for main time seconds
    "fff": r"(?P<millisecond>\d{3})",
    "AMPM": r"(?P<ampm>[APap][Mm])", # Case insensitive AM/PM
    "Z": r"(?P<zulu>Z)",
    # New tokens for Timezone Offsets
    "TZ_SIGN": r"(?P<offset_sign>[+-])",    # Token for + or -
    "TZ_HH": r"(?P<offset_hh>\d{2})",        # Token for timezone offset hours
    "TZ_MM": r"(?P<offset_mm>\d{2})",        # Token for timezone offset minutes
}
# Sort keys by length descending to match longer tokens first
# This will be automatically recalculated based on the updated DATE_COMPONENT_REGEX_MAP
SORTED_DATE_TOKENS = sorted(DATE_COMPONENT_REGEX_MAP.keys(), key=len, reverse=True)

def compile_pattern_from_format_string(format_entry):
    """
    Converts a format_string from JSON into a compiled regex pattern.
    Example format_string: "YYYY-MM-DD_HHMMSS"
    """
    format_str = format_entry.get("format_string", "")
    regex_str_parts = []
    i = 0
    while i < len(format_str):
        matched_token = False
        for token in SORTED_DATE_TOKENS:
            if format_str.startswith(token, i):
                regex_str_parts.append(DATE_COMPONENT_REGEX_MAP[token])
                i += len(token)
                matched_token = True
                break
        if not matched_token:
            # Character is not a known token, treat as literal
            char = format_str[i]
            regex_str_parts.append(re.escape(char))
            i += 1
    final_regex_str = "".join(regex_str_parts)
    # We want to find this pattern anywhere in the filename stem
    # Add word boundaries or common delimiters if needed, or make it more flexible
    # For now, let's assume the pattern describes a significant, contiguous part of the name
    try:
        return re.compile(final_regex_str, re.IGNORECASE)
    except re.error as e:
        print(f"Warning: Could not compile regex for format '{format_str}': {e}")
        return None

def load_date_patterns():
    """Loads date format patterns from the JSON file."""
    patterns = []
    loaded_path = None
    for file_path in DATE_FORMATS_FILE_PATHS:
        try:
            # Try to construct path relative to script if not absolute
            if not os.path.isabs(file_path):
                script_dir = os.path.dirname(os.path.abspath(__file__))
                abs_file_path = os.path.join(script_dir, file_path)
            else:
                abs_file_path = file_path

            if os.path.exists(abs_file_path):
                with open(abs_file_path, 'r', encoding='utf-8') as f:
                    format_entries = json.load(f)
                loaded_path = abs_file_path
                break # Found and loaded a file
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {abs_file_path}: {e}")
            return [] # Critical error, return empty
        except Exception as e:
            print(f"Error loading date formats from {abs_file_path}: {e}")
            return []

    if not loaded_path:
        print(f"Warning: Date formats JSON file not found at expected locations: {DATE_FORMATS_FILE_PATHS}")
        return []

    print(f"Loading date patterns from: {loaded_path}")
    for entry in format_entries:
        compiled_regex = compile_pattern_from_format_string(entry)
        if compiled_regex:
            patterns.append({
                "regex": compiled_regex,
                "original_format": entry.get("format_string", "N/A"),
                "type": entry.get("type", "N/A")
            })
    print(f"Loaded {len(patterns)} date patterns.")
    return patterns

def extract_datetime_from_filename(filename_stem, date_patterns):
    """
    Attempts to extract date and time components from a filename stem
    using the loaded date patterns.
    Returns a dictionary with 'year', 'month', 'day', 'hour', 'minute', 'second'
    or None if no pattern matches.
    """
    for pattern_info in date_patterns:
        match = pattern_info["regex"].search(filename_stem)
        if match:
            data = match.groupdict()
            
            # Normalize data
            year = data.get('year')
            if not year and data.get('shortyear'):
                # Convert YY to YYYY (e.g., 25 -> 2025, 98 -> 1998)
                # This simple heuristic might need adjustment for very old dates
                short_year_int = int(data['shortyear'])
                year = str(2000 + short_year_int if short_year_int < 70 else 1900 + short_year_int) # Common heuristic
            
            month = data.get('month')
            day = data.get('day')
            dayofyear = data.get('dayofyear')

            hour = data.get('hour')
            minute = data.get('minute', "00") # Default if not present
            second = data.get('second', "00") # Default if not present
            millisecond = data.get('millisecond') # Optional

            if data.get('hour12') and data.get('ampm'):
                hour12_int = int(data['hour12'])
                ampm = data['ampm'].lower()
                if ampm == 'pm' and hour12_int != 12:
                    hour = str(hour12_int + 12)
                elif ampm == 'am' and hour12_int == 12: # Midnight case
                    hour = "00"
                else:
                    hour = data['hour12'].zfill(2)
            
            if not hour: # If no hour info at all
                hour, minute, second = DEFAULT_TIME_IF_ONLY_DATE_FOUND.split(':')

            # Basic validation
            if year and month and day:
                try:
                    # Further validate by trying to create a datetime object
                    dt_val = datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
                    return {
                        'year': year.zfill(4), 'month': month.zfill(2), 'day': day.zfill(2),
                        'hour': hour.zfill(2), 'minute': minute.zfill(2), 'second': second.zfill(2),
                        'millisecond': millisecond, # Can be None
                        'zulu': data.get('zulu'), # Can be None
                        'offset_sign': data.get('offset_sign'), # Can be None
                        'offset_hh': data.get('offset_hh'), # Can be None
                        'offset_mm': data.get('offset_mm'), # Can be None
                        'matched_format': pattern_info["original_format"]
                    }
                except ValueError:
                    # print(f"Debug: Invalid date components for {filename_stem} with {pattern_info['original_format']}: Y={year} M={month} D={day}")
                    continue # Invalid date components, try next pattern
    return None

# --- ExifTool Runner (ENHANCED DIAGNOSTIC VERSION) ---
def run_exiftool_batch(files_to_update_with_commands):
    """
    Run exiftool commands on batches of files.
    files_to_update_with_commands is a list of tuples: (filepath, list_of_exiftool_args)
    This function tries to batch files that have the *exact same* set of commands.
    """
    if not files_to_update_with_commands:
        return 0
    if EXIFTOOL_EXECUTABLE is None:
        print("Critical Error: EXIFTOOL_EXECUTABLE path not set before running batch.")
        return 0 # Or raise an exception

    # Group files by their command list (as a tuple to be hashable)
    command_groups = {}
    for filepath, commands in files_to_update_with_commands:
        command_tuple = tuple(commands)
        if command_tuple not in command_groups:
            command_groups[command_tuple] = []
        command_groups[command_tuple].append(filepath)

    total_files_reported_updated_by_exiftool = 0
    processed_batch_count = 0
    exiftool_dir = os.path.dirname(EXIFTOOL_EXECUTABLE) # Get ExifTool's directory

    for commands_tuple, filepaths in command_groups.items():
        processed_batch_count += 1
        if not filepaths:
            continue
        
        temp_filename = None
        print(f"\n--- Processing Batch {processed_batch_count} ---")
        print(f"Commands: {commands_tuple}")
        print(f"Files in this batch ({len(filepaths)}): {filepaths[:3]}..." if len(filepaths) > 3 else filepaths)

        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                f.write('\n'.join(filepaths))
                temp_filename = f.name
            
            cmd = [EXIFTOOL_EXECUTABLE, '-S', '-@', temp_filename] + list(commands_tuple)
            
            print(f"Running ExifTool command: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False,
                encoding='utf-8',
                cwd=exiftool_dir # Set current working directory for ExifTool
            )
            
            print(f"  ExifTool Return Code: {process.returncode}")
            print(f"  ExifTool STDOUT:\n{process.stdout.strip()}")
            if process.stderr.strip():
                print(f"  ExifTool STDERR:\n{process.stderr.strip()}")

            if process.returncode == 0:
                updated_in_this_batch = 0
                stdout_lower = process.stdout.lower()
                # Updated regex to be more robust for "N type files updated" or "N files updated"
                match = re.search(r"(\d+)\s+(?:(?:image|video|media|file)(?:s)?(?:\s+file(?:s)?)?|files?)\s+updated", stdout_lower)

                if match:
                    updated_in_this_batch = int(match.group(1))
                    total_files_reported_updated_by_exiftool += updated_in_this_batch
                    print(f"  ExifTool reported {updated_in_this_batch} file(s) updated in this batch.")
                elif "0 image files updated" in stdout_lower or \
                     "0 files updated" in stdout_lower or \
                     "files unchanged" in stdout_lower or \
                     (not stdout_lower.strip() and len(filepaths) > 0): # Check for empty output if files were processed
                    print(f"  ExifTool reported 0 files updated or files unchanged in this batch (Return Code 0).")
                else:
                    # This case means return code was 0, but output didn't match known success patterns.
                    print(f"  ExifTool return code 0, but specific 'updated' count not clearly parsed from STDOUT. Assuming 0 for this batch. STDOUT: '{stdout_lower.strip()}'")
            else:
                # Check for specific Perl DLL error
                if "perl5" in process.stderr and ".dll" in process.stderr:
                     print(f"  Warning: ExifTool returned error code {process.returncode}. Potential Perl DLL issue: {process.stderr.strip().splitlines()[0]}")
                else:
                    print(f"  Warning: ExifTool returned error code {process.returncode} for this batch.")


        except Exception as e:
            print(f"  An unexpected error occurred during ExifTool batch processing: {e}")
        finally:
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except Exception as e_unlink:
                    print(f"  Warning: Could not delete temp file {temp_filename}: {e_unlink}")
        print("--- End Batch ---")
    
    return total_files_reported_updated_by_exiftool

# --- Main ---
def main():
    # find_and_set_exiftool_path() is called globally already
    if EXIFTOOL_EXECUTABLE:
        print(f"Using ExifTool at: {EXIFTOOL_EXECUTABLE}")
    else:
        # This case should be handled by exit() in find_and_set_exiftool_path()
        print("Critical: ExifTool path not set. Exiting.") 
        return

    date_patterns = load_date_patterns()
    if not date_patterns:
        print("No date patterns loaded. Cannot proceed with filename parsing.")

    src_dir = input("Enter source folder PATH: ").strip()
    if not os.path.isdir(src_dir):
        print(f"Error: Source folder not found at '{src_dir}'")
        return

    dst_dir = os.path.join(src_dir, "_output_metadata_edited")
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir, exist_ok=True)

    temp_dir = os.path.join(src_dir, "_temp_metadata_editor")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    
    files_to_process_info = []
    skipped_files_log = []
    
    print("\nSTEP 1: Analyzing files and copying to temporary directory...")
    for filename in os.listdir(src_dir):
        if not filename.lower().endswith(SUPPORTED_EXTENSIONS):
            continue
        src_path = os.path.join(src_dir, filename)
        if os.path.isdir(src_path):
            continue
        filename_stem = os.path.splitext(filename)[0]
        datetime_info = extract_datetime_from_filename(filename_stem, date_patterns)
        if datetime_info:
            temp_path = os.path.join(temp_dir, filename)
            try:
                shutil.copy2(src_path, temp_path)
                files_to_process_info.append({'temp_path': temp_path, 'original_filename': filename, 'datetime_info': datetime_info})
                print(f"Copied: {filename} (Matched: {datetime_info['matched_format']})")
            except Exception as e:
                print(f"Error copying {filename}: {e}")
                skipped_files_log.append((filename, f"Copy error: {e}"))
        else:
            skipped_files_log.append((filename, "No matching date pattern found in filename"))
    
    if not files_to_process_info:
        print("\nNo files found matching any date patterns or supported extensions.")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        return

    print(f"\nSTEP 2: Preparing ExifTool commands for {len(files_to_process_info)} files...")
    exiftool_operations = []
    for file_info in files_to_process_info:
        dt_info = file_info['datetime_info']
        date_value = f"{dt_info['year']}:{dt_info['month']}:{dt_info['day']} {dt_info['hour']}:{dt_info['minute']}:{dt_info['second']}"
        
        commands = [
            f"-DateTimeOriginal={date_value}",
            f"-CreateDate={date_value}",
            f"-ModifyDate={date_value}",
            "-overwrite_original"
        ]
        exiftool_operations.append((file_info['temp_path'], commands))

    print("\nSTEP 3: Updating metadata using ExifTool...")
    exiftool_updated_count = run_exiftool_batch(exiftool_operations) # Use the count from ExifTool
    
    print(f"\nSTEP 4: Moving processed files to destination...")
    moved_count = 0
    processed_original_filenames = [info['original_filename'] for info in files_to_process_info]

    for entry in os.listdir(temp_dir): 
        temp_file_path = os.path.join(temp_dir, entry)
        if os.path.isfile(temp_file_path) and entry in processed_original_filenames:
            original_file_info = next((info for info in files_to_process_info if info['original_filename'] == entry), None)
            if not original_file_info:
                print(f"Warning: Could not find original info for {entry} in temp dir. Skipping move.")
                skipped_files_log.append((entry, "Internal error: Missing info for temp file"))
                continue

            dt_info = original_file_info['datetime_info']
            base_new_name = f"{dt_info['year']}{dt_info['month']}{dt_info['day']}"
            _, ext = os.path.splitext(entry)
            
            new_name = f"{base_new_name}{ext}"
            dst_path = os.path.join(dst_dir, new_name)
            counter = 1
            while os.path.exists(dst_path):
                new_name = f"{base_new_name}_{counter}{ext}"
                dst_path = os.path.join(dst_dir, new_name)
                counter += 1
            try:
                shutil.move(temp_file_path, dst_path)
                # Only increment moved_count if the file was actually reported as updated by ExifTool
                # This logic might be complex if ExifTool updates some files in a batch but not others.
                # For now, we assume if it's in temp_dir and was processed, it's eligible for move.
                # The exiftool_updated_count is a more accurate reflection of metadata changes.
                moved_count +=1 
            except Exception as e:
                print(f"Error moving {entry} to {dst_path}: {e}")
                skipped_files_log.append((entry, f"Move error: {e}"))
        elif entry not in processed_original_filenames and os.path.isfile(temp_file_path):
             print(f"Warning: File {entry} found in temp_dir but was not in initial processing list. Skipping move.")
             skipped_files_log.append((entry, "Unexpected file in temp folder"))

    if moved_count > 0 : # Only print if some files were moved
        print(f"Moved {moved_count} files to {dst_dir}")


    print(f"\nSTEP 5: Cleaning up temporary directory: {temp_dir}")
    try:
        shutil.rmtree(temp_dir)
        print(f"Removed temporary directory: {temp_dir}")
    except OSError as e:
        print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
    
    print("\n--- Processing Summary ---")
    print(f"Files initially copied for processing: {len(files_to_process_info)}")
    print(f"Files reported as updated by ExifTool: {exiftool_updated_count}") # Use the count from ExifTool
    print(f"Files successfully moved to output: {moved_count}")
    if skipped_files_log:
        print(f"Files skipped or with errors during processing: {len(skipped_files_log)}")
        for filename, reason in skipped_files_log:
            print(f"  - {filename}: {reason}")
            
if __name__ == "__main__":
    main()
