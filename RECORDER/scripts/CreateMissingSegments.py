import glob
import sys
import os
import re
import datetime
import shutil
import m3u8
from m3u8.model import Segment

def sorted_ls(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(glob.glob(os.path.join(path,"*.ts")), key=mtime))

def ScanDirectory(directory):
    files=[]
    base_filename=None
    onlyfiles = sorted_ls(directory)    
    if len(onlyfiles):
        base_filename=os.path.basename(onlyfiles[0]).split('.')[0][:-5]
        for f in onlyfiles:
            files.append(int(os.path.basename(f).split('.')[0][-5:]))
    else:
        print("No *ts files in directory, or directory doesn't exists.\n")
    return base_filename,files


def main():
    if len(sys.argv) < 3:
        exit("""
Usage: {0} <directory> <blank media filename>  

CreateMissingSegments scans every *.ts file in the specified directory and recover the
missing ones with copying the blank media file with the correct filename. Playlist file 
also corrected. After the application scans a directory it should contain a proper 24
hour long continuos hls stream.

Assumptions:
  - First segment starts at 00:00:00 with index 10001
  - Last segment starts at 23:59:45 with index 15760
  - Every segment is 15 sec long
""".format(sys.argv[0]))

    # Collect arguments
    directory = sys.argv[1]
    blank_filename = sys.argv[2]

#FIXME The current day should be processed more carefully!!!!
#      Not supported in the initia release.
    today=datetime.datetime.now().strftime("%Y%m%d")
    if today!=os.path.split(directory)[1]:
        base_filename,files=ScanDirectory(directory)
        if len(files)>500: #We need at least 500 valid media files to fill up the gaps.
#            playlist=m3u8.load(os.path.join(directory,"playlist.m3u8"))
            playlist=m3u8.M3U8()
            playlist.is_endlist=True
            playlist.target_duration=15
            playlist.version="3"
            playlist.media_sequence="10001"
            for i in range(10001, 15761):
                if i not in files:
                    print(base_filename+"% must be created",i)
                    shutil.copyfile(blank_filename,os.path.join(directory,
                             base_filename+str(i).zfill(5)+".ts"))
                new_segment=Segment(base_filename+str(i).zfill(5)+".ts",'',duration=15)
                playlist.segments.append(new_segment)
            playlist.dump(os.path.join(directory,"playlist.m3u8"))
    else:
        print("Current day is not supported in this version.\n")
 



if __name__ == "__main__":
    main()
