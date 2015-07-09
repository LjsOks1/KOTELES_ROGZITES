# name of your binary
bin_PROGRAMS = mtva-encoder

# list of source files
# the prefix is the name of the binary
mtva_encoder_SOURCES = main.c

# list of headers we're not going to install
noinst_HEADERS = 

# our CFLAGS and LDFLAGS used for compiling and linking
# make sure you prefix these with the name of your binary
mtva_encoder_CFLAGS = $(GST_CFLAGS)
mtva_encoder_LDFLAGS = $(GST_LIBS) 
mtva_encoder_LDADD = -lgstvideo-1.0
