from os import listdir
from os.path import isfile, join
import sys,os,re,datetime

class Playlist():
    def __init__(self):
        self.fd=None
   
    def createPlaylist(self,playlist_filename,seq_num,starttime):
        self.fd=open(playlist_filename,'w')
        self.fd.write("#EXTM3U\n")
        self.fd.write("#EXT-X-VERSION:3\n")
        self.fd.write("#EXT-X-TARGETDURATION:15\n")
        self.fd.write("#EXT-X-MEDIA-SEQUENCE:"+str(seq_num)+"\n")
        #FIXME: We should have a better method to find out the exact time of the startime.
        self.fd.write("#EXT-X-PROGRAM-DATE-TIME:"+starttime.strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")


    def append_segment(self,segment_name):
        if self.fd:
            self.fd.write("#EXTINF:15.0,\n")
            self.fd.write(segment_name+'\n')
    def end_segments(self):
        if self.fd:
            self.fd.write("#EXT-X-ENDLIST\n")
    def closePlaylist(self):
        if self.fd:
	    self.fd.close()
            self.fd=None


def sorted_ls(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime
    return list(sorted(os.listdir(path), key=mtime))

def ScanToPlaylist(directory, playlist_filename,urlroot):
#    onlyfiles = [ f for f in listdir(directory) if isfile(join(directory,f)) ]
    onlyfiles = sorted_ls(directory)    
    if len(onlyfiles):
#FIXME: Doesn't work with general filenames! 
#Works with channel_segment%d.ts Other format needs testing
#Fails if the first filename is not a ts file. 
        s=re.split(r'[._]+|segment',onlyfiles[0])
        t=os.path.getmtime(os.path.join(directory,onlyfiles[0]))
        playlist=Playlist()
        playlist.createPlaylist(playlist_filename,int(s[len(s)-2]),datetime.datetime.fromtimestamp(t))       
        for f in onlyfiles:
            if f.endswith(".ts"):    
                playlist.append_segment(urlroot+f)
#       playlist.end_segments()
        playlist.closePlaylist()


def main():
    if len(sys.argv) < 4:
        exit("""
Usage: {0} <directory> <playlist filename> <url_root> 

ScanToPlaylist scans every *.ts file in the specified directory and compile the m3u8 
playlist with the given filename. url_root is used as the prefix of the media files
in the media playlist. If there is an existing playlist file, it is truncated. 
Playlist file

""".format(sys.argv[0]))

    # Collect arguments
    directory = sys.argv[1]
    playlist_filename = sys.argv[2]
    urlroot = sys.argv[3]
  
    ScanToPlaylist(directory,playlist_filename,urlroot)


if __name__ == "__main__":
    main()
