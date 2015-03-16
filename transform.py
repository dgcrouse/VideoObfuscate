#! /usr/bin/env python

import argparse

# Define parameters for cv2.VideoCapture.get()
height_param = 4
width_param = 3
fps_param = 5
current_frame_param = 1

# Take an input video and apply the transformation
# For each pass, read 1/num_passes columns from the input frames and write the same number of output frames
# start_time and stop_time take lists of form [seconds,frames] to calculate times
# If is_encoding is true, encoding will begin a new block at the start frame. Otherwise, it will assume that the frame is in the middle of a block.
# Note that this value only matters for partial extraction
def transform_video(infile,outfile,num_passes=4,is_encoding=True,start_time=[],stop_time=[]):
    
    # Prevent nastiness...
    if num_passes < 1:
        num_passes = 1
        
    # Init video capture
    input_reader = cv2.VideoCapture()
    if input_reader.open(infile) == -1:
        return

    frame_height = int(input_reader.get(height_param))
    frame_width = int(input_reader.get(width_param))
    fps = float(input_reader.get(fps_param))
        
    # If too many passes specified, limit to number of columns
    if num_passes > frame_width:
        num_passes = frame_width #SLOW

    # Prepare codec writer (AVI is best cross-platform)
    fourcc = cv2.cv.CV_FOURCC(*'XVID')
    output_writer = cv2.VideoWriter(outfile,fourcc,fps,(frame_width,frame_height))

    start_frame = int(start_time[0] * fps) + start_time[1] if start_time != [] else 0
    stop_frame = int(stop_time[0] * fps) + 1 + stop_time[1] if stop_time != [] else -1 # to include the stop frame
    
    if (stop_frame > 0 and stop_frame <= start_frame):
        return

    # Calculate number of columns to read per pass
    pass_width = frame_width/num_passes
    if frame_width % num_passes != 0:
        pass_width += 1

    first_block = True
    if is_encoding:
        block_count = 0 # Set initial block number to 0
        global_offset = start_frame # but access all frames with this offset
        pass_offset = 0
        line_offset = 0
    else:
        block_count = start_frame/frame_width               # Acknowledge what block we should be in
        global_offset = 0                                   # And access frames with no offset
        pass_offset = (start_frame%frame_width)/pass_width  # Start on this pass #
        line_offset = (start_frame%frame_width)%pass_width # And this frame within the pass.

    # Create frame buffer. Last dimension is color. No alpha support yet...
    # Here, we read the first frame to get the dtype for the matrix
    frames = np.zeros([frame_height,pass_width,frame_width,3],input_reader.read()[1].dtype)
    frames_to_read = True

    while frames_to_read and (stop_frame < 0 or block_count * frame_width + global_offset < stop_frame):
        
        # Loop through n passes
        for read_pass in range(pass_offset if first_block else 0,num_passes):
            block_start_frame = block_count * frame_width + global_offset
            input_reader.set(current_frame_param,block_start_frame) # Rewind to beginning of pass.
            
            true_width = min(pass_width*(read_pass+1),frame_width) - pass_width * read_pass # Since we overestimate the pass width
            frames_to_read = True # So we don't cut off part of the last block
            # Read the frames
            for cnt in xrange(frame_width):
                frames_to_read = frames_to_read and (not is_encoding or stop_frame < 0 or block_start_frame+cnt < stop_frame)
                #If we have frames remaining, read them (or at least try)
                if frames_to_read:
                    frames_to_read,frame = input_reader.read()
                      
                # Otherwise, just zero it. We don't break out because there are more spots to fill
                if not frames_to_read: # check again because may be set in last if
                    frame = np.zeros([frame_height,frame_width,3],frames.dtype)
  
                # Read slice of frame into output buffer.
                frames[:,line_offset:true_width,cnt,:] = frame[:,pass_width*read_pass+line_offset:pass_width*read_pass+true_width]
            
            # Write next frames to output
            for i in range(line_offset,min(stop_frame-block_start_frame,true_width) if stop_frame > 0 and not is_encoding else true_width):
                output_writer.write(frames[:,i,:,:])
                
            line_offset = 0 # Only valid for first pass
                
        block_count += 1    # Processed another block of input frames
        first_block = False
        
    # Clean up
    input_reader.release()
    output_writer.release()  
    
    
def valid_infile(string):
    valid_extensions = ['.mp4','.m4v','.avi']
    if string[-4:] not in valid_extensions or len(string) < 5:
        raise argparse.ArgumentTypeError('{0} is not a valid extension'.format(string[-4:]))
    else:
        return string

def avifile(string):
    if string[-4:] != '.avi' or len(string) < 5:
        raise argparse.ArgumentTypeError('Extension of output file must be .avi')
    else:
        return string
        
def valid_timecode(string):
    segments = string.split(':')
    if len(segments) > 4:
        raise argparse.ArgumentTypeError('Invalid Timecode')
    
    outcode = [0,0]
    
    for cnt,seg in enumerate(segments):
        if len(seg) != 2 or not seg.isdigit():
            raise argparse.ArgumentTypeError('Invalid Timecode')
        if cnt == len(segments)-1:
            outcode[1] = int(seg)
        else:
            outcode[0] += pow(60,len(segments)-2-cnt) * int(seg)
    return outcode
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Obfuscate or De-Obfuscate a video.\n Obfuscates by default.')
    infile_help = 'File to process - must be .avi,.mp4, or .m4v (only .avi on some systems)'
    outfile_help = 'Output file name - must be .avi'
    passes_help = 'Number of passes to make over input data. More means less memory but slower'
    start_help = 'Timecode to start encoding at (default 0). Form HH:MM:SS:FF (FF is frame within second)'
    stop_help = 'Timecode to stop at (default end of video). Form HH:MM:SS:FF (FF is frame within second)'
    decode_help = 'Set this flag if you are de-obfuscating a video with custom start/stop. Otherwise frames will be mis-aligned'
    
    parser.add_argument('infile',action='store', type=valid_infile, help=infile_help)
    parser.add_argument('outfile',action='store', type=avifile, help=outfile_help)
    parser.add_argument('--passes', '-p', action='store', type=int, default=4, help=passes_help)
    parser.add_argument('--start', '-s', action='store', type=valid_timecode, default=[], help=start_help)
    parser.add_argument('--end', '-e', action='store', type=valid_timecode, default=[],help=stop_help)
    parser.add_argument('--decode' ,'-d',action='store_false',dest='encode',help=decode_help) # Actually stores whether we are encoding or decoding
    args = parser.parse_args()
    
    import numpy as np
    import cv2
    transform_video(args.infile,args.outfile,args.passes,args.encode,args.start,args.end)