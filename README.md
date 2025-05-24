# metadata_updater
 a script that will update all your pics' metadata according to the file name, to "repair" missing metadata as a result of using tools such as whatsapp that delete the original metadata

## Requirements
- Python 3.11+ (consider using anaconda https://anaconda.org/ as you'll be able to swap between python versions easily)
- ExifTool (https://exiftool.org/) (included in the folder when pulled/cloned)

## Usage
- clone or pull this into a folder of your choice, the sub-folder called "metadata-updater" will be created, containing the .py script to run
- CD into the PATH of the folder, then start the script by running "python photo_renamer.py"
- follow the prompt instructions (provide the correct folder PATH, otherwise the script will create new folders inside this folder itself -METADA_UPDATER-)
- inside the folder of your choice, when the script completed its tasks, you will find a new folder called "_output" with the files, with the updated metadata

## Notice
- currently supporting inputs of images coming from whatsapp. will be able to take "IMG-YYYYMMDD-WA####.jpg" formatted files (the standard whatsapp naming) and use these information to update the metadata. 
- currently working to expand the script capabilities to "inteligently" take the file name formatting and extract the date + time, regardless of the fixed structure or not