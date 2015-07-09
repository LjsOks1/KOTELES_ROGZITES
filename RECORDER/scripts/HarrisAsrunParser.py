import json
from datetime import datetime,timedelta
import sys
import codecs
import string
import os

def process_harris_event(line):
    event={}
    after_midnight=False
    try:
        if int(line[39:41])>23:
            after_midnight=True
            date_str=line[9:17]+'-'+str(int(line[39:41])-24).zfill(2)+line[41:47]
        else:
            date_str=line[9:17]+'-'+line[39:47]    
        date_=datetime.strptime(date_str,"%Y%m%d-%H:%M:%S")
        if after_midnight:
            date_=date_+timedelta(1)
        str_dur=line[90:98]
        dur_=timedelta(0,int(str_dur.split(":")[2]),0,0,int(str_dur.split(":")[1]),int(str_dur.split(":")[0]))
        if dur_>timedelta(0,0,0,0,5,0):
            event={ "startDate": datetime.strftime(date_,"%Y,%m,%d,%H,%M,%S"),
                "endDate": datetime.strftime(date_+dur_,"%Y,%m,%d,%H,%M,%S"),
                "headline":line[131:167].strip(),
                "text":line[57:89].strip(),
                "asset":
                    {
                        "media": "",
                        "credit":"",
                        "caption":""
                    }
            }
        return event,after_midnight
    except:
        return event,after_midnight 

def process_harris_date(channel,txdate):
    filename2=datetime.strftime(txdate,"%Y%m%d")+"_"+channel+".LOG"
    filename1=datetime.strftime(txdate-timedelta(1),"%Y%m%d")+"_"+channel+".LOG"
    timeline_json={"timeline": {"headline":filename2,
                             "type":"default",
                             "text":"" } }
    timeline_json2={"timeline": {"headline":filename2,
                             "type":"default",
                             "text":"" } }
    eventList=[]  # This is for the events for the previous day we run the script
    eventList2=[] # This is for the events after midnight, the day when we run the script
#Start with events after midnight of the previous txday asrun log...
    with codecs.open(os.path.join("/mnt/dais/logexp",filename1),encoding='iso-8859-2') as input_file:
        for i,line in enumerate(input_file):
            event,after_midnight=process_harris_event(line)
            if after_midnight & len(event)>0:
                eventList.append(event)
    input_file.close()
#Now process events before midnight of the current txday asrun...
    with codecs.open(os.path.join("/mnt/dais/logexp",filename2),encoding='iso-8859-2') as input_file:
        for i,line in enumerate(input_file):
            event,after_midnight=process_harris_event(line)
            if (not after_midnight) & len(event)>0:
                eventList.append(event)
            elif after_midnight & len(event)>0:
                eventList2.append(event)
    input_file.close()
#Lets write out the collected events as a JSON for yesterday
    timeline_json['timeline']['date']=eventList
    json_file=codecs.open("/var/www/html/"+channel+"/"+datetime.strftime(txdate,"%Y%m%d")+"/asrun.json","w","utf-8")
    json.dump(timeline_json,json_file)
    json_file.close()
#Lets write out the collected events as a JSON for today (events before 6am) 
    timeline_json2['timeline']['date']=eventList2
    json_file=codecs.open("/var/www/html/"+channel+"/"+datetime.strftime(txdate+timedelta(1),"%Y%m%d")+"/asrun.json","w","utf-8")
    json.dump(timeline_json2,json_file)
    json_file.close()

    
def main():
    channels=["m1","m2","m3"]
    tx_date=datetime.today()-timedelta(1)
    for channel in channels:
        process_harris_date(channel,tx_date)

if __name__ == "__main__":
    main()
