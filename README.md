# metadata_updater

A Python script to repair missing or incorrect photo and video metadata (EXIF dates) by extracting date and time information from filenames. Especially useful for files from sources that strip original metadata (e.g., WhatsApp, messaging apps, cloud services, etc.).

## Features
- Automatically updates EXIF metadata (DateTimeOriginal, CreateDate, ModifyDate) based on date/time found in filenames.
- Supports a wide range of image and video formats (JPG, PNG, HEIC, MP4, etc.).
- Flexible date pattern recognition (not limited to any single format).
- Separates files into two output folders:
  - `_output_metadata_edited`: Files successfully updated with new metadata.
  - `_output_outliers`: Files that could not be updated (either no date found in filename or ExifTool update failed).
- Detailed logging and error reporting in CLI.

## Requirements
- Python 3.11+ 
    - consider using [Anaconda](https://anaconda.org/) to easily manage and switch between Python versions
- ExifTool 13.30+
    - [ExiTool] (https://exiftool.org/) not included in this repository; must be downloaded separately

  - **To install ExifTool on Windows:**
    1. Go to [https://exiftool.org/](https://exiftool.org/) and download the Windows executable zip archive.
    2. Unzip the archive inside the folder you cloned this repository into.
    3. Rename the file `exiftool(-k).exe` to `exiftool.exe` for command-line use.
    4. Make sure the `exiftool_files` folder (from the zip) is in the same directory as `exiftool.exe`.

  - **macOS:**
    1. The recommended method is using [Homebrew](https://brew.sh/): `brew install exiftool`.
    2. Alternatively, download the "macOS Package" from [ExifTool's website](https://exiftool.org/).
    3. Mount the .dmg file and run the installer.

  - **Linux:**
    1. Most distributions offer ExifTool via their package manager (e.g., `sudo apt install libimage-exiftool-perl` for Debian/Ubuntu).
    2. Alternatively, download the "Perl Archive" from [ExifTool's website](https://exiftool.org/).
    3. Unpack the archive and follow the installation instructions in the `README` file (typically involves `perl Makefile.PL`, `make`, `make test`, `sudo make install`).

  For comprehensive installation details, refer to the official [ExifTool installation instructions](https://exiftool.org/#install).

## Usage
1. **Clone or download this repository** to a folder of your choice.
2. **Ensure ExifTool is present**: The script will look for `exiftool.exe` in the project or system PATH.
3. **Open a terminal** and navigate (`cd`) to the project folder.
4. **Run the script:**
   ```sh
   python metadata_editor.py
   ```
5. **Follow the prompts:**
   - Enter the path to the folder containing your photos/videos when asked.
   - The script will process all supported files in that folder.
6. **Check the results:**
   - `_output_metadata_edited/` will contain files with updated metadata and renamed by date.
   - `_output_outliers/` will contain files that could not be updated (either no date in filename or update failed).

## Notes
- The script supports many common filename date formats. You can expand or edit the date patterns in `Insights/date_formats_source.json`.
- Files are first copied to a temporary folder for safe processing. Originals are never modified.
- If a file already exists in the output folder, a numeric suffix will be added to avoid overwriting.
- All processing steps and any errors are logged to the console for review.

## Supported Filename Patterns
- Many other date/time patterns (see `Insights/date_formats_source.json` for details)

## License
See [LICENSE](LICENSE).