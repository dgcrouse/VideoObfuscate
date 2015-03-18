#Video Obfuscation by Temporal Rotation

There are many reasons one might want to prevent a video from being scraped/analyzed by machines, most notably privacy (I will not comment on others due to their dubious legality). 
In this day and age, advertisers, market researchers, and others are all looking at what we share online. This project aims to obfuscate video in such a way that its content is unrecognizable to machine analysis,
but which allows humans to get the gist of what is happening in the video. This is to ensure that someone does not download an obfuscated file that contains material that they do not want, or which is unsavory.

As an added bonus, the transform is fast (runs in ~4x realtime, at least from SSD), low-memory (used less than 400mb to convert a 1024x436 video), and relatively CPU-light (used 160% of a core on my quad-i7 2.5 ghz mobile)

# Dependencies

OpenCV: http://opencv.org/ - This will be going away if I can help it.

Numpy: http://www.numpy.org/

ffmpeg: http://www.ffmpeg.org/

#Usage

NOTE: Audio support is experimental and uses the ffmpeg binary. If output is .m4v, duration of the output video will be reported incorrectly. Also, if using .m4v output, will use best available audio codec between libfdk\_aac, libfaac, and experimental ffmpeg AAC.

You can call `python transform.py` or simply `transform.py`

`transform.py [-h] [--passes PASSES] [--start START] [--end END] [--decode] [--noaudio] [--verbose] infile outfile`

Obfuscate or De-Obfuscate a video. Obfuscates by default.

positional arguments:

infile                File to process - must be .avi,.mp4, or .m4v (only .avi on some systems)

outfile               Output file name - must be .avi or .m4v (for some reason .mp4 trips up OpenCV)

optional arguments:
  
-h, --help            show this help message and exit
  
--passes PASSES, -p PASSES  Number of passes to make over input data. More means less memory but slower
  
--start START, -s START Timecode to start encoding at (default 0). Form HH:MM:SS:FF (FF is frame within second)
  
--end END, -e END     Timecode to stop at (default end of video). Form HH:MM:SS:FF (FF is frame within second)
  
--decode, -d          Set this flag if you are de-obfuscating a video with custom start/stop. Otherwise frames will be mis-aligned

--noaudio             Set this flag to disable audio copying

--verbose             Set this flag to enable verbose output from ffmpeg

#How It Works

Video can be viewed as an image in 3 dimensions, the third being traditionally assigned to time. This method "chops" the data up into chunks along the time axis, with a time length the same as the width of the image.
These chunks are then rotated about the x-axis so that the former y-axis is the new time axis. This results in a video in which each frame is a single scanline across a certain number of frames. Put another way, the old column
coordinates are now frame coordinates and vice versa. If the time is not evenly divided into chunks, remaining columns are filled with black.

Since this would use a LOT of RAM on high-resolution videos, I implemented a "pass" system. Each input frame is read n times, and only a chunk of (width/n) columns will be rotated to get the same number of frames. Each time
through still reads (frame width) frames, though, to get the full movie width.

As a proof of concept, I transformed Sintel, the Open Movie, (© copyright Blender Foundation | www.sintel.org) using my method. You can find the result here: https://www.youtube.com/watch?v=qO6ymAyPGcg. Download it in 720p (It MUST be this resolution or it won't work), then pass it back through the transformation to restore the video.
