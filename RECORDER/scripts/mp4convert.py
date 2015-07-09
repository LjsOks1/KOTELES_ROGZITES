#!/usr/bin/env python

## @package mp4convert
# WSGI application to export mp4 segments from HLS transport stream.
#
# This code is used as a WSGI Apache extension. Add the following lines to the main
# Apache config file (/etc/apache2/apache2.conf):
#
#     WSGIScriptAlias /mp4export /usr/local/src/RECORDER/scripts/mp4convert.py
#     <Directory /usr/local/src/RECORDER/scripts>
#         Order allow,deny
#         Allow from all
#     </Directory>
#     
# If restart fails due to missing mod_wsgi, install it with
#      apt-get install libapache2-mod-wsgi
#
 
#Python imports
import sys
import signal
 
from wsgiref.simple_server import make_server
from cgi import parse_qs,escape
 
#GStreamer imports
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst

#GObject.threads_init()
Gst.init(None)
 
 
#MP4 pipeline has placeholders for filename and indexes! 
MP4_PIPELINE = "multifilesrc location=%s start-index=%d stop-index=%d ! "\
                 "tsdemux name=demux  "\
                 "demux. ! h264parse ! queue ! mp4mux faststart=true name=mux  "\
                 "demux. ! aacparse ! queue ! mux. "\
                 "mux. ! appsink sync=false name=endpoint max-buffers=3"
 
class MP4Convert(object):

    def __init__(self,location,start,stop,environ):
#        self.mainloop=GObject.MainLoop()
        print >> environ['wsgi.errors'], "Converter class initializng...."
        pipe=MP4_PIPELINE % (location,start,stop)
        self.pipeline = Gst.parse_launch(pipe)
        self.endpoint = self.pipeline.get_by_name('endpoint')
        self.pipeline.set_state(Gst.State.PLAYING)
        
#        self.mainloop.run()
        
    def next(self):
        sample= self.endpoint.emit("pull-sample")
        if sample is None:
#            if self.endpoint.is_eos():
            self.stop()
            raise StopIteration
        else:
            buf =  sample.get_buffer()
            data=buf.extract_dup(0,buf.get_size())
            return data
 
    def stop(self):
        self.pipeline.set_state(Gst.State.NULL)
#        self.mainloop.quit()
 
    def __iter__(self):
        return self
 

def application(environ, start_response):
    print >> environ['wsgi.errors'] , "mp4convert started."
    print >> environ['wsgi.errors'] , environ['PATH_INFO']
    if environ['PATH_INFO'] == '/mp4export':
        d=parse_qs(environ['QUERY_STRING'])
        channel=d.get('channel',[''])[0]
        segment_start=d.get('from',[''])[0]
        segment_end=d.get('to',[''])[0]
        
        location="/var/www/html/"+channel+"/"+segment_start[0:8]+"/"+channel+"_"+ \
                    segment_start[0:8]+"_segment%05d.ts"
        start_index=int(segment_start[8:10])*240+int(segment_start[10:12])*4+10001
        stop_index=int(segment_end[8:10])*240+int(segment_end[10:12])*4+10001
        filename=channel+"_"+segment_start+"_"+segment_end+".mp4"
        start_response("200 OK", [
            ("Content-Disposition",'attachment; filename='+filename),
        ])
#        print >> environ['wsgi.errors'] ,location,start_index,stop_index        
        return iter(MP4Convert(location,start_index,stop_index,environ))
    else:
        start_response("404 Not Found", [
            ("Content-Type", "text/html"),
            ("Content-Length", str(len(ERROR_404)))
        ])
        return iter([ERROR_404])
 
 
if __name__ == '__main__':
    #This looks for the port number as a comandline argument
    args = sys.argv[1:]
    if not args :
        sys.exit('Usage: %s port_number' % __file__)
    port = int(args[0])
 
    #Launch an instance of wsgi server
    #print 'Launching mp4 server on port ', port
    httpd = make_server('', port, application)
 
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.kill()
        #print "Shutdown mp4 server ..."

