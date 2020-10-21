# Checks all songs in a directory tree for missing metadata.
# Outputs result to .json

import os
from pathlib import Path
import mutagen
import json


def checkMetaFile(file: str):
    ''' Returns included and missing metadata of a song file '''
    data = mutagen.File(file)
    if data is None:
        data = dict()

    looking_for = {'TPE1', 'TPE2', 'TIT2', 'USLT:desc:eng',
                   'TALB', 'APIC:Cover'}
    included_items = dict()
    for x in looking_for:
        if x in data:
            included_items[x] = data[x]
    missing_items = [x for x in looking_for if x not in data]
    return (included_items, missing_items)


def checkMetaDir(input_directory: Path, output_file: str):
    perfect_files = []
    imperfect_files = []
    for path, subdirs, files in os.walk(input_directory):
        for name in files:
            if name.endswith('.mp3'):
                fileName = os.path.join(path, name)
                (_, missing) = checkMetaFile(fileName)
                if len(missing) > 0:
                    imperfect_files.append({"file": fileName,
                                           "missing": missing})
                else:
                    perfect_files.append({"file": fileName})
    json_data = json.dumps({"goodFiles": imperfect_files,
                            "badFiles": imperfect_files})
    f = open(output_file, 'w')
    f.write(json_data)
    f.close()



if __name__ == "__main__":
    input_directory = ''
    while input_directory == '':
        try:
            expanded_path = os.path.expanduser(input('enter input directory: '))
            input_directory = Path(expanded_path)
        except Exception:
            print('Directory not found. If you would like to quit, enter ^c')

    output_file = ''
    while output_file == '':
        try:
            output_temp = os.path.expanduser(input('enter output file: '))
            f = open(output_temp, 'a')
            f.close()
            output_file = output_temp
        except Exception:
            print('Could not create output file. If you would like to quit, enter ^c')

    checkMetaDir(input_directory, output_file)
