# Contains all functions related to organizing song files

import os
from pathlib import Path
import shutil


def migrate(origin: str, dest: str):
    ''' Moves songs from one directory to another'''
    # Expands the paths, if needed
    origin = os.path.expanduser(origin)
    dest = os.path.expanduser(dest)
    print(origin)
    print(dest)
    # Move every song file to the destination directory
    for path, subdirs, files in os.walk(origin):
        print(subdirs)
        for name in files:
            if name.endswith('.mp3'):
                # Find current file name
                curr_file_name = os.path.join(path, name)
                print(f'curr_file_name is {curr_file_name}. path is {path}')
                final_file_name = ''
                # If file is not in any subdirectories
                if path == origin:
                    final_file_name = os.path.join(dest, name)
                # Find directory names for the album and artist
                else:
                    dirs = os.path.split(path)
                    album_dir = dirs[-1]
                    dirs = os.path.split(dirs[-2])
                    artist_dir = dirs[-1]
                    # Create the album and artist directories in the dest
                    dest_dir = os.path.join(dest, artist_dir, album_dir)
                    os.makedirs(dest_dir, exist_ok=True)
                    final_file_name = os.path.join(dest_dir, name)
                # Move the file
                print(f'Moving {name} to {final_file_name}')
                os.rename(curr_file_name, final_file_name)
    # Now delete the empty directories
    for path, subdirs, files in os.walk(origin):
        for name in subdirs:
            dir_path = os.path.join(path, name)
            shutil.rmtree(dir_path)

if __name__ == '__main__':
    migrate('~/Music/TestLibrary', '~/Music/Music/Media.localized')