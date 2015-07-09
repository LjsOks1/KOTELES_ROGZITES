#!/usr/bin/env python 
from __future__ import print_function

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst

import datetime


GObject.threads_init()
Gst.init(None)
import sys,os
import logging,logging.handlers

logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)
handler = logging.handlers.RotatingFileHandler("/var/log/HLSRecorder_"+sys.argv[2]+".log", maxBytes=(1048576*5), backupCount=7)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

def exit(msg):
#    print(msg, file=sys.stderr)
    logger.debug(msg)
    sys.exit()
                

class Playlist():
    def __init__(self):
        self.fd=None
   
    def createPlaylist(self,playlist_filename,seq_num):
        self.fd=open(playlist_filename,'w',1)
        self.fd.write("#EXTM3U\n")
        self.fd.write("#EXT-X-VERSION:3\n")
        self.fd.write("#EXT-X-TARGETDURATION:15\n")
        self.fd.write("#EXT-X-MEDIA-SEQUENCE:"+str(seq_num)+"\n")
        #FIXME: We should have a better method to find out the exact time of the startime.
        self.fd.write("#EXT-X-PROGRAM-DATE-TIME:"+datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")

   
    def openPlaylist(self,playlist_filename):
        self.fd=open(playlist_filename,'a',1)

    def append_segment(self,segment_name):
        if self.fd:
            self.fd.write("#EXTINF:15.0,\n")
            self.fd.write(segment_name+'\n')

    def segment_discontinuity(self):
        if self.fd:
	    self.fd.write("#EXT-X-DISCONTINUITY\n")
         #FIXME: We should have a better method to find out the exact time of the startime.
            self.fd.write("#EXT-X-PROGRAM-DATE-TIME:"+datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')+"+01:00\n")

    def end_segments(self):
        if self.fd:
            self.fd.write("#EXT-X-ENDLIST\n")
    def closePlaylist(self):
        if self.fd:
	    self.fd.close()
            self.fd=None

class HLSRecorder(object):
    
    def __init__(self):
        self.fd = None
        self.mainloop = GObject.MainLoop()
        result=True

#   Setup recording pipeline. 
#   As simple as: souphttpsrc location=uri ! hlsdemux ! multifilesink
        self.pipeline=Gst.Pipeline.new("recorder")
        self.souphttpsrc=Gst.ElementFactory.make("souphttpsrc","souphttpsrc")
        self.hlsdemux=Gst.ElementFactory.make("hlsdemux","hlsdemux")
        self.multifilesink=Gst.ElementFactory.make("multifilesink","multifilesink")
        result=self.pipeline.add(self.souphttpsrc)
        result=self.pipeline.add(self.hlsdemux)
        result=self.pipeline.add(self.multifilesink)        
        result=self.souphttpsrc.link(self.hlsdemux)
        self.multifilesink.set_property("post-messages",True)

#   hlsdemux doesn't have static source pad. Need to use event handler
#   to connect multifilesink
        result=self.hlsdemux.connect("pad-added",self.on_pad_added)        

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        result=self.bus.connect("message::eos", self.on_eos)
        result=self.bus.connect("message::error", self.on_error)
        result=self.bus.connect("message::tags",self.on_info)
        result=self.bus.connect("message::state-changed",self.on_state_changed)
        result=self.bus.connect("message::element",self.on_file_change)
        result=self.bus.connect("sync-message::stream-status",self.on_stream_status)

#   Construct Playlist
        self.playlist=Playlist()
#Add probe to log fragment downloads...
        hls_pad=self.multifilesink.get_static_pad("sink")
        hls_pad.add_probe(Gst.PadProbeType.ALL_BOTH,self.cb_hlsdemux_sink_probe,0)

    def on_info(self,error,debug):
        print(error)
    def on_stream_status():
        logger.debug("Stream-status called!")

    def cb_hlsdemux_sink_probe(self,pad,info,user_data):
        logger.debug("Probe on multifilesink received buffer.")
        #if info.type and Gst.PadProbeType.BUFFER:
        #    buff=info.get_buffer()
            #print(buff)
            #print(self.souphttpsrc.get_property("location"))
        return Gst.PadProbeReturn.PASS

    def on_file_change(self,bus,msg):
        structure=msg.get_structure()
        if structure.get_name()=="GstMultiFileSink":         
            filename=os.path.basename(structure.get_string("filename"))   
            (result,timestamp)=structure.get_clock_time("timestamp")
            (result,stream_time)=structure.get_clock_time("stream-time")
            (result,running_time)=structure.get_clock_time("running-time")
            (result,duration)=structure.get_clock_time("duration")
            logger.debug(filename+" received. Timestamp:"+str(timestamp)+" Stream-time:"+
                      str(stream_time)+" Running-time:"+str(running_time)+" Duration:"+str(duration))
            self.playlist.append_segment(self.uriroot+'/'+self.channel+'/'+self.date+'/'+filename)
            current_date=datetime.datetime.today().strftime("%Y%m%d") 
            if not current_date==self.date:
                self.date=current_date
                self.multifilesink.set_property("location",
                    os.path.join(self.docroot,self.channel,self.date,str(os.getpid())+"_%06d.ts"))
                if not os.path.exists(os.path.join(self.docroot,self.channel,self.date)):
                    os.makedirs(os.path.join(self.docroot,self.channel,self.date))
                self.playlist.end_segments()
                self.playlist.closePlaylist()
                (result,index) = structure.get_int("index")
                self.playlist.createPlaylist(os.path.join(self.docroot,self.channel,self.date,"playlist.m3u8"),index+1)
#        else:
            #print("Message from element: "+structure.get_name())
    def on_pad_added(self,element,pad):
        mfs_sinkpad=self.multifilesink.get_static_pad("sink")
        result=pad.link(mfs_sinkpad)
        logger.debug("HLSDemux src pad added.")
   
    def exit(self, msg):
        self.stop()
        exit(msg)

    def stop(self):
#   Stop recording and exit mainloop
        self.pipeline.set_state(Gst.State.NULL)
        result=self.pipeline.get_state(Gst.CLOCK_TIME_NONE)
        logger.debug("State changed to NULL with result:"+str(result))
        self.mainloop.quit()

    def record(self, stream,channel,docroot,uriroot):
#   Set location and start the pipeline 
       self.uri=stream
       self.channel=channel  
       self.docroot=docroot
       self.uriroot=uriroot
       self.date=datetime.datetime.today().strftime("%Y%m%d")
       self.souphttpsrc.set_property("location", stream)
       self.multifilesink.set_property("location",
              os.path.join(self.docroot,self.channel,self.date,str(os.getpid())+"_%06d.ts"))
       if not os.path.exists(os.path.join(self.docroot,self.channel,self.date)):
           os.makedirs(os.path.join(self.docroot,self.channel,self.date))
#   Playlist file handling
       if os.path.isfile(os.path.join(self.docroot,self.channel,self.date,"playlist.m3u8")):
           self.playlist.openPlaylist(os.path.join(self.docroot,self.channel,self.date,"playlist.m3u8"))
           self.playlist.segment_discontinuity()
       else:
           self.playlist.createPlaylist(os.path.join(self.docroot,self.channel,self.date,"playlist.m3u8"),0)
         
       result=self.pipeline.set_state(Gst.State.PLAYING)
       logger.debug("Pipeline started with result: "+str(result))
       self.mainloop.run()
      
    def on_eos(self, bus, msg):
        # Stop playback on end of stream
        self.stop()
        logger.debug("Pipeline stopped after eos message!")

    def on_error(self, bus, msg):
        # Print error message and exit on error
        error = msg.parse_error()[1]
        logger.debug(str(error))
        self.exit(error)
    
    def on_state_changed(self,bus,msg):
        states=msg.parse_state_changed()
        if msg.src.get_name() == "recorder" and states[1]==4 and os.getenv("GST_DEBUG_DUMP_DOT_DIR"): #To state is PLAYING
            Gst.debug_bin_to_dot_file (msg.src, Gst.DebugGraphDetails.ALL, "recorder-ts")
            logger.debug("pipeline dot file created in "+os.getenv("GST_DEBUG_DUMP_DOT_DIR"))

def main():
    if len(sys.argv) < 5:
        exit("""
Usage: {0} <srcurl> <channel> <docroot> <urlroot>
 Where:
   srcurl: The http address where HLS stream should be captured from.
   channel: The name of the channel. TS segments will be saved to the docroot/channel/date directory.
   docroot: The document root on the local filesystem.
   urlroot: Url root in the media playlist file. Segments will be served from the urlroot/channel/date/filename address.
""".format(sys.argv[0]))

    # Collect arguments
    url = sys.argv[1]
    channel = sys.argv[2]
    docroot = sys.argv[3]
    urlroot = sys.argv[4]
 
    # Create the recorder and  start recording
    recorder = HLSRecorder()
    # Blocks until record is done 
    recorder.record(url,channel,docroot,urlroot)

if __name__ == "__main__":
    main()
