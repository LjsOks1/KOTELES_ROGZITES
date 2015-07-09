#include <gst/gst.h>
#include <gst/video/video.h>
#include <glib.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int load_config_file(char* filename,
                     char** config_string,
                     int max_size)
{
  FILE *ifp;
  char line[255];
  int i;
  ifp = fopen(filename, "r");
  *config_string=malloc(max_size);
  **config_string='\0';
  if (ifp == NULL) {
    fprintf(stderr, "Can't open the config file. (%s)\n",filename);
    exit(1);
  }
  while( fgets(line,255,ifp)!=NULL) {
    for(i=0;i<strlen(line);i++) 
        if(line[i] =='\\' || line[i]=='\n')
           line[i]=' ';
    line[i]='\0';
    strcat(*config_string,line);
  }
  
  return 0;
}

static gboolean
bus_call (GstBus     *bus,
          GstMessage *msg,
          gpointer    data)
{
  GMainLoop *loop = (GMainLoop *) data;

  switch (GST_MESSAGE_TYPE (msg)) {

    case GST_MESSAGE_EOS:
      g_print ("End of stream\n");
      g_main_loop_quit (loop);
      break;

    case GST_MESSAGE_ERROR: {
      gchar  *debug;
      GError *error;

      gst_message_parse_error (msg, &error, &debug);
      g_free (debug);

      g_printerr ("Error: %s\n", error->message);
      g_error_free (error);

      g_main_loop_quit (loop);
      break;
    }
    default:
      break;
  }

  return TRUE;
}


static GstClockTime
get_local_system_time()
{
  GstClock *system_clock;
  GstClockTime epoch_time,local_time;
  time_t tspec,tspec_local;
  struct tm *tms;
  int epoch_hour;
  char *tz;
  system_clock=gst_system_clock_obtain();
  g_object_set(G_OBJECT(system_clock),"clock-type",GST_CLOCK_TYPE_REALTIME,NULL);  
  epoch_time=gst_clock_get_time(system_clock);
  tspec=(time_t)GST_TIME_AS_SECONDS(epoch_time);
  tms=localtime(&tspec);
  tz=getenv("TZ");
  setenv("TZ","",1);
  tzset();
  tspec_local=mktime(tms);
  if (tz)
     setenv("TZ",tz,1);
  else
     unsetenv("TZ");
  tzset();
//  epoch_hour=(epoch_time%(24*60*60*GST_SECOND))/(60*60*GST_SECOND);
//  local_time=epoch_time+((tms->tm_hour-epoch_hour)*60*60*GST_SECOND);
  local_time=epoch_time+((tspec_local-tspec)*GST_SECOND);
  g_print("Epoch time:%"GST_TIME_FORMAT" Local time:%"GST_TIME_FORMAT"\n",
           GST_TIME_ARGS(epoch_time),GST_TIME_ARGS(local_time));
  return local_time;
}

static gboolean
update_location(struct tm *tms, GstElement *hlsSink)
{
  gchar *location;
  char *left_pos,*right_pos;
  char new_location[255],new_date[255];
  memset(new_location,'\0',sizeof(new_location));
  g_object_get(G_OBJECT(hlsSink),"location",&location,NULL);
  g_print("Current location:%s\n",location);
  sprintf(new_date,"%04i%02i%02i",
        tms->tm_year+1900,tms->tm_mon+1,tms->tm_mday);
  left_pos=strchr(location,'_');
  right_pos=strrchr(location,'_');
  strncpy(new_location,location,(left_pos-location+1));
  strcat(new_location,new_date);
  strcat(new_location,right_pos);
  g_object_set(G_OBJECT(hlsSink),"location",new_location,NULL);
  g_free(location);
  g_print("New location:%s\n",new_location);
  return TRUE;
}

static gboolean
switch_day(struct tm *tms,GstElement *hlsSink) 
{
  g_print("Switching date...\n");
  update_location(tms,hlsSink);
  g_object_set(G_OBJECT(hlsSink),"index",10000,NULL);
  return TRUE;
}


static GstPadProbeReturn
cb_hlssink_event_upstream(GstPad *pad,
                 GstPadProbeInfo *info,
                 gpointer user_data)
{
   GstEvent *event=gst_pad_probe_info_get_event(info);
   GstElement *hlsSink=gst_pad_get_parent_element(pad);
   switch (GST_EVENT_TYPE(event)) {
      case GST_EVENT_CUSTOM_UPSTREAM: { 
         GstClockTime running_time,local_time;
         gboolean all_headers;
         guint count,duration;
         time_t tspec;
         struct tm *tms;

         if(gst_video_event_is_force_key_unit(event)) {
            gst_video_event_parse_upstream_force_key_unit(event,&running_time,&all_headers,&count);
            local_time=get_local_system_time();
            g_object_get(G_OBJECT(hlsSink),"target-duration",&duration,NULL);            
            g_print("Key unit requested at %"GST_TIME_FORMAT" for %"GST_TIME_FORMAT" with duration: %isec.\n",
                  GST_TIME_ARGS(local_time),GST_TIME_ARGS(running_time),duration);
            if (running_time>duration*GST_SECOND) {
                if (local_time/(60*60*24*GST_SECOND) != 
                             ((local_time-(duration*GST_SECOND))/(60*60*24*GST_SECOND))) {
                   tspec=GST_TIME_AS_SECONDS(local_time+(duration*GST_SECOND));
                   tms=gmtime(&tspec);
                   switch_day(tms,hlsSink);
                }            
            }
         }
         break;
      }
      default:
         break;
   } 
   return GST_PAD_PROBE_OK;
}

static GstPadProbeReturn
cb_hlssink_event_downstream(GstPad *pad,
                 GstPadProbeInfo *info,
                 gpointer user_data)
{
   GstEvent *event=gst_pad_probe_info_get_event(info);
   GstElement *hlsSink=gst_pad_get_parent_element(pad);
   switch (GST_EVENT_TYPE(event)) {
      case GST_EVENT_CUSTOM_DOWNSTREAM: { 
         GstClockTime running_time,local_time,timestamp,stream_time;
         gboolean all_headers;
         guint count,duration;
         time_t tspec;
         struct tm *tms;

         if(gst_video_event_is_force_key_unit(event)) {
            gst_video_event_parse_downstream_force_key_unit(event,
                    &timestamp,&stream_time,&running_time,&all_headers,&count);
            g_object_get(G_OBJECT(hlsSink),"target-duration",&duration,NULL);            
            local_time=get_local_system_time(); 
            g_print("Key unit returned at %"GST_TIME_FORMAT
                              " timestamp:%"GST_TIME_FORMAT
                              " running time:%"GST_TIME_FORMAT"\n",
                GST_TIME_ARGS(local_time),GST_TIME_ARGS(timestamp),GST_TIME_ARGS(running_time));
/*            if(running_time>duration*GST_SECOND) {
                if (local_time/(60*GST_SECOND) != 
                             ((local_time-(duration*GST_SECOND))/(60*GST_SECOND))) {
                   tspec=GST_TIME_AS_SECONDS(local_time+(duration*GST_SECOND));
                   tms=gmtime(&tspec);
                   switch_day(tms,hlsSink);
                }            
            }
*/        }
         break;
      }
      default:
         break;
   } 
   return GST_PAD_PROBE_OK;
}


int
main (int   argc,
      char *argv[])
{
  GMainLoop *loop;

  GstElement *pipeline;
  GstBus *bus;
  guint bus_watch_id;
  char *pipeline_config;
  GError *error = NULL;
  GstClock *system_clock;
  GstClockTime current_time,scheduled_start;
  GstClockID t_clock_id;
  int start_index;
  time_t tspec;
  struct tm *tms;
  /* Initialisation */
  gst_init (&argc, &argv);

  loop = g_main_loop_new (NULL, FALSE);


  /* Check input arguments */
  if (argc != 2) {
    g_printerr ("Usage: %s <pipeline_config_filename>\n", argv[0]);
    return -1;
  }


  /* Create gstreamer pipeline */
  load_config_file(argv[1],&pipeline_config,1024);
  pipeline = gst_parse_launch(pipeline_config,&error);
  if (!pipeline) {
         g_print ("Parse error: %s\n", error->message);
         exit (1);
  }
  free(pipeline_config);
  
/* we add a message handler */
  bus = gst_pipeline_get_bus (GST_PIPELINE (pipeline));
  bus_watch_id = gst_bus_add_watch (bus, bus_call, loop);
  gst_object_unref (bus);


  /* Set the pipeline to "paused" state*/
  g_print ("Pausing pipeline...: %s\n", argv[1]);
  gst_element_set_state (pipeline, GST_STATE_PAUSED);

  /* Find the hlssink element in the pipeline */
  GValue pValue;
  GstElement *phlsSink=NULL;
  char* pElementName;
  GstPad *pad;
  GstIterator* pItrElements = gst_bin_iterate_elements((GstBin*)pipeline);
  while(GST_ITERATOR_OK==gst_iterator_next(pItrElements,&pValue)) {
     pElementName=gst_element_get_name(g_value_get_object(&pValue));
//     g_print("Element %s found.\n ",pElementName);
     if (strcmp(pElementName,"hlssink0")==0) {
         phlsSink=g_value_dup_object(&pValue);

         break;
     }
     g_value_reset(&pValue);
  }
  g_value_unset(&pValue);
  gst_iterator_free(pItrElements);

  /* Calculate when to start the pipeline */
  system_clock=gst_system_clock_obtain();
  //gst_pipeline_use_clock(pipeline,system_clock);
  g_object_set(G_OBJECT(system_clock),"clock-type",GST_CLOCK_TYPE_REALTIME,NULL);  
  current_time=gst_clock_get_time(system_clock);
  scheduled_start=((current_time/(15*GST_SECOND))+1)*15*GST_SECOND; //Should be rounded to the next15 sec
  tspec=(time_t)GST_TIME_AS_SECONDS(scheduled_start); 
  tms=localtime(&tspec);
  start_index=(tms->tm_hour*60*4+tms->tm_min*4+tms->tm_sec/15)+10001; // Restart every day
//  start_index=(tms->tm_min*4+tms->tm_sec/15)+10001;  // Restart every hour
//  start_index= tms->tm_sec/15 + 10001; // Restart every minute

  /* Set up hlssink and start recording */ 
  if (phlsSink!=NULL) {
     update_location(tms,phlsSink);
     pad=gst_element_get_static_pad(phlsSink,"sink");
     /* Install probe to catch events from hlssink */
     gst_pad_add_probe(pad,GST_PAD_PROBE_TYPE_EVENT_UPSTREAM,
       (GstPadProbeCallback)cb_hlssink_event_upstream,NULL,NULL);
     gst_pad_add_probe(pad,GST_PAD_PROBE_TYPE_EVENT_DOWNSTREAM,
       (GstPadProbeCallback)cb_hlssink_event_downstream,NULL,NULL);
     g_object_set(G_OBJECT(phlsSink),"index",start_index,NULL);
     t_clock_id=gst_clock_new_single_shot_id(system_clock,scheduled_start);
     g_print(" Start of record  scheduled for: %s  Index value:%i \n", asctime(tms),start_index);
     if(GST_CLOCK_OK == gst_clock_id_wait(t_clock_id,NULL)) {
        gst_clock_id_unref(t_clock_id);
        gst_element_set_state(pipeline,GST_STATE_PLAYING);
        /* Iterate */
        g_print ("Running...\n");
        g_main_loop_run (loop);
     }
  }

  /* Out of the main loop, clean up nicely */
  g_print ("Returned, stopping pipeline\n");
  gst_element_set_state (pipeline, GST_STATE_NULL);

  g_print ("Deleting pipeline\n");
  gst_object_unref (GST_OBJECT (pipeline));
  g_source_remove (bus_watch_id);
  g_main_loop_unref (loop);

  return 0;
}
