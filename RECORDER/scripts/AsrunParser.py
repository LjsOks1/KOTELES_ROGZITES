import json
from datetime import datetime,timedelta
import sys
import codecs
import string

def process_harris_asrun(asrun_filename,json_filename):
    timeline_json={"timeline": {"headline":asrun_filename,
                             "type":"default",
                             "text":"" } }
    eventList=[]
    with codecs.open(asrun_filename,encoding='iso-8859-2') as input_file:
        for i,line in enumerate(input_file):
            event={}
            try:
                date_str=line[9:17]+'-'+line[39:47]
                date_=datetime.strptime(date_str,"%Y%m%d-%H:%M:%S")
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
                    eventList.append(event)
            except:
                print sys.exc_info()[0], "in line :" , line
        timeline_json['timeline']['date']=eventList
    input_file.close()
    json_file=codecs.open(json_filename,"w",encoding="utf-8")   
    json.dump(timeline_json,json_file)
    json_file.close()
    



def process_colossus_asrun(asrun_filename,json_filename):
    timeline_json={"timeline": {"headline":asrun_filename,
                             "type":"default",
                             "text":"" } }
    eventList=[]
    with codecs.open(asrun_filename,encoding='iso-8859-2') as input_file:
        for i,line in enumerate(input_file):
            tags=line.encode('UTF-8').split("|")
            event={}
            date_=datetime.strptime(tags[0].rsplit(":",1)[0],"%d/%m/%y - %H:%M:%S")
            dur_=timedelta(0,int(tags[5].split(":")[2]),0,0,int(tags[5].split(":")[1]),int(tags[5].split(":")[0]))
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
    json_file=codecs.open(json_filename,"w",encoding="utf-8")   
    json.dump(timeline_json,json_file)
    json_file.close()
    


def main():
    if len(sys.argv) < 3:
        exit("""
Usage: {0} <asrun filename> <json filename>
 Where:
  asrun filename: Filename og the asrun log file.
  json filename : Where to save the json timelinejs config file.
""".format(sys.argv[0]))

    # Collect arguments
    asrun_filename = sys.argv[1]
    json_filename = sys.argv[2]
    if string.find(asrun_filename,"Colossus")>-1 :
        process_colossus_asrun(asrun_filename,json_filename)
    else: 
        process_harris_asrun(asrun_filename,json_filename)

if __name__ == "__main__":
    main()
