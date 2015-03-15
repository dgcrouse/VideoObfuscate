#Video Obfuscation by Temporal Rotation

There are many reasons one might want to prevent a video from being scraped/analyzed by machines, most notably privacy (I will not comment on others due to their dubious legality). 
In this day and age, advertisers, market researchers, and others are all looking at what we share online. This project aims to obfuscate video in such a way that its content is unrecognizable to machine analysis,
but which allows humans to get the gist of what is happening in the video. This is to ensure that someone does not download an obfuscated file that contains material that they do not want, or which is unsavory.

As an added bonus, the transform is fast (runs in ~4x realtime, at least from SSD), low-memory (used less than 400mb to convert a 1024x436 video), and relatively CPU-light (used 160% of a core on my quad-i7 2.5 ghz mobile)

#Usage

`python transform.py (input file name) (output file name.avi) (optional number of passes)`

This transforms the input file into the output file in a given number of passes. Passes reduce memory usage but increase computation time. 4 works well for 720p, more are required for higher resolution. Input file can be mp4 or avi, output must be avi (for cross-platform compatability)

#How It Works

Video can be viewed as an image in 3 dimensions, the third being traditionally assigned to time. This method "chops" the data up into chunks along the time axis, with a time length the same as the width of the image.
These chunks are then rotated about the x-axis so that the former y-axis is the new time axis. This results in a video in which each frame is a single scanline across a certain number of frames. Put another way, the old column
coordinates are now frame coordinates and vice versa. If the time is not evenly divided into chunks, remaining columns are filled with black.

Since this would use a LOT of RAM on high-resolution videos, I implement a "pass" system. Each input frame is read n times, and only a chunk of (width/n) columns will be rotated to get the same number of frames. Each time
through still reads (frame width) frames, though, to get the full movie width.

As a proof of concept, I transformed Sintel, the Open Movie, (© copyright Blender Foundation | www.sintel.org) using my method. You can find the result here: https://www.youtube.com/watch?v=qO6ymAyPGcg. Download it in 720p (It MUST be this resolution or it won't work), then pass it back through the transformation to restore the video.

Edit: YouTube changed the resolution, which made it impossible to de-obfuscate. Uploading fixed version soon

Audio support is coming soon.
