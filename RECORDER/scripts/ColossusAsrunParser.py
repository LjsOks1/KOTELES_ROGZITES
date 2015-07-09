import json
from datetime import datetime,timedelta
import sys
import codecs
import string
import os

def process_colossus_asrun(channel,tx_date):
    timeline_json={"timeline": {"headline":channel[0]+" "+datetime.strftime(tx_date,"%Y-%m-%d"),
                             "type":"default",
                             "text":"" } }
    eventList=[]
    asrun_filename=os.path.join("/mnt/cls/ftproot/asrunlog/log",channel[0],
           "AsRunLog.Colossus"+channel[1][0]+"."+datetime.strftime(tx_date,"%Y.%m.%d")+".txt")
    with codecs.open(asrun_filename,encoding='iso-8859-2') as input_file:
        for i,line in enumerate(input_file):
            tags=line.encode('UTF-8').split("|")
            event={}
            date_=datetime.strptime(tags[0].rsplit(":",1)[0],"%d/%m/%y - %H:%M:%S")
            dur_=timedelta(0,int(tags[5].split(":")[2]),0,0,int(tags[5].split(":")[1]),
                         int(tags[5].split(":")[0]))
            if dur_>timedelta(0,0,0,0,9,0) and not tags[1]=="Logo":
                event={ "startDate": datetime.strftime(date_,"%Y,%m,%d,%H,%M,%S"),
                    "endDate": datetime.strftime(date_+dur_,"%Y,%m,%d,%H,%M,%S"),
                    "headline":tags[2],
                    "text":tags[1],
                    "asset":
                         {
                             "media": "",
                             "credit":"",
                             "caption":""
                         }
                }
                eventList.append(event)
        timeline_json['timeline']['date']=eventList
    input_file.close()
    json_filename=os.path.join("/var/www/html",channel[1][1],
            datetime.strftime(tx_date,"%Y%m%d"),"asrun.json")
    json_file=codecs.open(json_filename,"w",encoding="utf-8")   
    json.dump(timeline_json,json_file)
    json_file.close()
    


def main():
    channels={"Duna1":["101","duna"],
              "Duna2":["102","dunaworld"]
             }
    tx_date=datetime.today()
    for channel in channels.items():
        process_colossus_asrun(channel,tx_date)

if __name__ == "__main__":
    main()
