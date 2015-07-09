import requests
import urllib
from bs4 import BeautifulSoup
import datetime
import sys
import time
import os

def get_all_files(url):
    soup = BeautifulSoup(requests.get(url).text)

    for tr in soup.find('div', {'class': 'list'}).find_all('tr'):
        file={}
        try:
            if tr.find('td',{'class':'t'}).string=="application/octet-stream":
                file['href']=tr.find('a')['href']
                file['modtime']=datetime.datetime.strptime(tr.find('td',{'class':'m'}).string,"%Y-%b-%d %H:%M:%S")  
                yield file
        except (AttributeError,TypeError):
            print("Error in line: "+tr.prettify())
            pass

def download_file(url,local_filename,modtime):
    print("Downloading file: "+url+" to local file: "+local_filename)
    urllib.urlretrieve(url,local_filename)
    os.utime(local_filename,(time.mktime(modtime.timetuple()),time.mktime(modtime.timetuple())))

def RecoverFromEncoder(url,local_path, startime,endtime):
   index=0
   for file in get_all_files(url):
        if file['modtime']>starttime and file['modtime']<endtime:
            index+=1
            download_file(url+"/"+file['href'],local_path+"/"+file['href'],file['modtime'])

if __name__ == "__main__":
    if len(sys.argv)<3:
       exit("""
This application downloads ts segments from the encoder.
Usage: {0} url, local_path, starttime endtime

   url : The url address of the ts segments
   local_path: local directory to store ts segments.
   startime: Copy files with modification date>starttime.
             Format: YYYY-MM-DDTHH:MI:SS
   endtime : (Optional) If set, copy file that modification time<endtime.
             If missing, endtime=now()""".format(sys.argv[0]))

    url=sys.argv[1]
    local_path=sys.argv[2]
    starttime=datetime.datetime.strptime(sys.argv[3],"%Y-%m-%dT%H:%M:%S")
    if sys.argv[3]:
        endtime=datetime.datetime.strptime(sys.argv[4],"%Y-%m-%dT%H:%M:%S")
    else:
        endtime=datetime.datetime.now()

    RecoverFromEncoder(url, local_path, starttime,endtime)

