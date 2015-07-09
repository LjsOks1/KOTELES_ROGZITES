/*
 * GStreamer
 * Copyright (C) 2005 Thomas Vander Stichele <thomas@apestaart.org>
 * Copyright (C) 2005 Ronald S. Bultje <rbultje@ronald.bitfreak.net>
 * Copyright (C) 2014 Lajos Okos <<lajos.okos@gmail.com>>
 * 
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 *
 * Alternatively, the contents of this file may be used under the
 * GNU Lesser General Public License Version 2.1 (the "LGPL"), in
 * which case the following provisions apply instead of the ones
 * mentioned above:
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Library General Public
 * License as published by the Free Software Foundation; either
 * version 2 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Library General Public License for more details.
 *
 * You should have received a copy of the GNU Library General Public
 * License along with this library; if not, write to the
 * Free Software Foundation, Inc., 59 Temple Place - Suite 330,
 * Boston, MA 02111-1307, USA.
 */

/**
 * SECTION:element-vbisrc
 *
 * FIXME:Describe vbisrc here.
 *
 * <refsect2>
 * <title>Example launch line</title>
 * |[
 * gst-launch -v -m vbisrc ! private/teletext ! teletextdec ! text/plain ! fakesink
 * ]|
 * </refsect2>
 */

#ifdef HAVE_CONFIG_H
#  include <config.h>
#endif

#include <string.h>
#include <gst/gst.h>
#include "gstvbisrc.h"

GST_DEBUG_CATEGORY_STATIC (gst_vbisrc_debug);

#define GST_CAT_DEFAULT gst_vbisrc_debug
#define BUFFER_COUNT 5
#define ALL_SERVICES_625 ( VBI_SLICED_TELETEXT_B | \
                           VBI_SLICED_VPS | \
                           VBI_SLICED_CAPTION_625 | \
                           VBI_SLICED_WSS_625 | \
                           VBI_SLICED_VBI_625 )

/* Filter signals and args */
enum
{
  /* FILL ME */
  LAST_SIGNAL
};

enum
{
  PROP_0,
  PROP_SILENT,
  PROP_DEV
};

/* the capabilities of the output.
 *
 * describe the real formats here.
 */
static GstStaticPadTemplate src_factory = GST_STATIC_PAD_TEMPLATE ("src",
    GST_PAD_SRC,
    GST_PAD_ALWAYS,
    GST_STATIC_CAPS ("ANY")
    );

#define gst_vbisrc_parent_class parent_class
G_DEFINE_TYPE (Gstvbisrc, gst_vbisrc, GST_TYPE_PUSH_SRC);

static GstFlowReturn gst_vbisrc_create(GstPushSrc *psrc, GstBuffer **buf);
static gboolean gst_vbisrc_start(GstBaseSrc *bsrc);
static gboolean gst_vbisrc_stop(GstBaseSrc *bsrc);

static void gst_vbisrc_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec);
static void gst_vbisrc_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec);

/* GObject vmethod implementations */

/* initialize the vbisrc's class */
static void
gst_vbisrc_class_init (GstvbisrcClass * klass)
{
  GObjectClass *gobject_class;
  GstElementClass *gstelement_class;
  GstBaseSrcClass *gstbasesrc_class;
  GstPushSrcClass *gstpushsrc_class;

  gobject_class = (GObjectClass *) klass;
  gstelement_class = (GstElementClass *) klass;
  gstbasesrc_class = (GstBaseSrcClass *) klass;
  gstpushsrc_class = (GstPushSrcClass *) klass;

  gobject_class->set_property = gst_vbisrc_set_property;
  gobject_class->get_property = gst_vbisrc_get_property;

  g_object_class_install_property (gobject_class, PROP_SILENT,
      g_param_spec_boolean ("silent", "Silent", "Produce verbose output ?",
          FALSE, G_PARAM_READWRITE));
  g_object_class_install_property (gobject_class, PROP_DEV,
      g_param_spec_string ("device", "Device", "Device to use. Default: /dev/vbi0",
          "/dev/vbi0", G_PARAM_READWRITE));


  gst_element_class_set_details_simple(gstelement_class,
    "VBI source element using zvbi library",
    "VBI sliced data source",
    "Using zvbid proxy daemon. Make shure it is running!",
    "lajos.okos@gmail.com");

  gst_element_class_add_pad_template (gstelement_class,
      gst_static_pad_template_get (&src_factory));

  gstbasesrc_class->start = gst_vbisrc_start;
  gstbasesrc_class->stop = gst_vbisrc_stop;
  gstpushsrc_class->create = gst_vbisrc_create;

  GST_DEBUG_CATEGORY_INIT (gst_vbisrc_debug, "vbisrc",
      0, "vbisrci log messages");
}

/* initialize the new element
 * instantiate pads and add them to element
 * set pad calback functions
 * initialize instance structure
 */
static void
gst_vbisrc_init (Gstvbisrc * vbisrc)
{
  vbisrc->srcpad = gst_pad_new_from_static_template (&src_factory, "src");
  GST_PAD_SET_PROXY_CAPS (vbisrc->srcpad);
  gst_element_add_pad (GST_ELEMENT (vbisrc), vbisrc->srcpad);

  vbisrc->silent = FALSE;
  vbisrc->services = VBI_SLICED_TELETEXT_B;
  vbisrc->device = g_strdup("/dev/vbi0");
  /* configure to be a live source */
  gst_base_src_set_live(GST_BASE_SRC (vbisrc),TRUE);
  /* output a segment in time */
  gst_base_src_set_format(GST_BASE_SRC(vbisrc), GST_FORMAT_TIME);
  /* set timestamps on outgoing buffers based on the running_time 
     when they were captured. */
  gst_base_src_set_do_timestamp(GST_BASE_SRC(vbisrc),TRUE);
}

static void
gst_vbisrc_set_property (GObject * object, guint prop_id,
    const GValue * value, GParamSpec * pspec)
{
  Gstvbisrc *filter = GST_VBISRC (object);

  switch (prop_id) {
    case PROP_SILENT:
      filter->silent = g_value_get_boolean (value);
      break;
    case PROP_DEV:
      g_free(filter->device);
      filter->device=g_value_dup_string(value);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static void
gst_vbisrc_get_property (GObject * object, guint prop_id,
    GValue * value, GParamSpec * pspec)
{
  Gstvbisrc *filter = GST_VBISRC (object);

  switch (prop_id) {
    case PROP_SILENT:
      g_value_set_boolean (value, filter->silent);
      break;
    case PROP_DEV:
      g_value_set_string(value,filter->device);
      break;
    default:
      G_OBJECT_WARN_INVALID_PROPERTY_ID (object, prop_id, pspec);
      break;
  }
}

static GstFlowReturn 
gst_vbisrc_create(GstPushSrc *psrc, GstBuffer **buf)
{
  Gstvbisrc *vbisrc = GST_VBISRC_CAST(psrc);
  GstFlowReturn ret;
  GstMapInfo info;
  fd_set rd;
  int res;
  struct timeval timeout;
  int vbi_fd=vbi_capture_fd(vbisrc->pVbiCapt);
  vbi_capture_buffer *pVbiBuf;
  vbi_sliced *pVbiData;
  GstBuffer *outbuf;
  uint lineCount;
  uint line;
  
  FD_ZERO(&rd);
  FD_SET(vbi_fd,&rd);
  select(vbi_fd +1 ,&rd , NULL, NULL, NULL);
  if (FD_ISSET(vbi_fd,&rd))
  {
    timeout.tv_sec = 0;
    timeout.tv_usec = 1000;
    res = vbi_capture_pull_sliced(vbisrc->pVbiCapt,&pVbiBuf,&timeout);
    if (res>0 && pVbiBuf !=NULL)
    {
      lineCount = ((unsigned int)pVbiBuf->size)/sizeof(vbi_sliced);
      pVbiData = pVbiBuf->data;
      GST_LOG_OBJECT(vbisrc,"Having %d lines in buffer",lineCount);
      for (line=0; line<lineCount; line++ ) {
        if((pVbiData[line].id & (VBI_SLICED_TELETEXT_B))!=0) {
           GST_LOG_OBJECT(vbisrc,"SLICED_TELETEXT found in line %d",pVbiData[line].line);
        }
      }
      ret=GST_BASE_SRC_CLASS(parent_class) -> alloc (GST_BASE_SRC_CAST(vbisrc),
               -1,pVbiBuf->size,&outbuf);
      gst_buffer_map(outbuf,&info,GST_MAP_WRITE);
      memcpy(info.data,(guint8*)pVbiBuf->data,pVbiBuf->size);
      gst_buffer_unmap(outbuf,&info);
      *buf=GST_BUFFER_CAST(outbuf);
      GST_LOG_OBJECT (vbisrc,"Buffer pushed with size: %d", pVbiBuf->size);

     return ret;     
    }
  }
  return GST_FLOW_ERROR;
}

static gboolean gst_vbisrc_start (GstBaseSrc *bsrc)
{
  Gstvbisrc *src;
  src=GST_VBISRC(bsrc);
  char *pErr;
  
  if(src->pProxyClient == NULL)
  //Need to open the device
  {
    src->pProxyClient=vbi_proxy_client_create(src->device,"zvbi-proxy",0,&pErr,0);
    if (src->pProxyClient!=NULL)
    {
      src->pVbiCapt=vbi_capture_proxy_new(src->pProxyClient,
                                  BUFFER_COUNT,0,&src->services,0,&pErr);
    }
  }
  return TRUE;
}

static gboolean gst_vbisrc_stop(GstBaseSrc *bsrc)
{
  Gstvbisrc *src;
  src=GST_VBISRC(bsrc);

  vbi_capture_delete(src->pVbiCapt);
  src->pVbiCapt=NULL;
  
  vbi_proxy_client_destroy(src->pProxyClient);
  src->pProxyClient=NULL;

  return TRUE;
}

