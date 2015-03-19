#! /usr/bin/env python

import argparse, sys

# Define parameters for cv2.VideoCapture.get()
height_param = 4
width_param = 3
fps_param = 5
current_frame_param = 1

def time_frame_to_ffmpeg(time,framerate):
    return '{0:02d}:{1:02d}:{2:02d}.{3:03d}'.format(time[0]/3600,(time[0]%3600)/60,time[0]%60,int(time[1]*1000/framerate))


def difference_to_ffmpeg(t1,t2,framerate):
    elapsed_seconds = t2[0]-t1[0]
    elapsed_frames = t2[1]-t1[1]
    
    if elapsed_frames < 0:
        elapsed_seconds -= 1
        elapsed_frames += framerate
    return time_frame_to_ffmpeg([elapsed_seconds,elapsed_frames],framerate)

# Take an input video and apply the transformation
# For each pass, read 1/num_passes columns from the input frames and write the same number of output frames
# start_time and stop_time take lists of form [seconds,frames] to calculate times
# If is_encoding is true, encoding will begin a new block at the start frame. Otherwise, it will assume that the frame is in the middle of a block.
# start_time and stop_time are lists [seconds,frames_within_second]
# Note that this value only matters for partial extraction
def transform_video(infile,outfile,num_passes=4,is_encoding=True,start_time=[],stop_time=[],encode_audio=True,verbose=False):
    
    import numpy as np
    from cv2 import VideoCapture, VideoWriter
    from cv2.cv import CV_FOURCC
    
    # Prevent nastiness...
    if num_passes < 1:
        num_passes = 1
        
    # Init video capture
    input_reader = VideoCapture()
    if input_reader.open(infile) == -1:
        return

    frame_height = int(input_reader.get(height_param))
    frame_width = int(input_reader.get(width_param))
    fps = float(input_reader.get(fps_param))
        
    # If too many passes specified, limit to number of columns
    if num_passes > frame_width:
        num_passes = frame_width #SLOW

    inext = infile.split('.')[-1]
    outext = outfile.split('.')[-1]

    # Prepare codec writer (AVI is best cross-platform)
    if outext == 'avi':
        fourcc = CV_FOURCC(*'XVID')  
    elif outext == 'm4v':
        fourcc = CV_FOURCC(*'MP4V')
    #elif outext == 'mp4':
    #    fourcc = cv2.cv.CV_FOURCC(*'FMP4')
    else:
        print 'Error: Output extension not supported'
        return
        
    tmpfile = 'obfuscate_tmp.{0}'.format(outext)
    output_writer = VideoWriter(tmpfile if encode_audio else outfile,fourcc,fps,(frame_width,frame_height))

    if (start_time != [] and start_time[1] > fps) or (stop_time != [] and stop_time[1] > fps):
        print 'Error: Cannot specify frame count greater than FPS'
        return

    start_frame = int(start_time[0] * fps) + start_time[1] if start_time != [] else 0
    stop_frame = int(stop_time[0] * fps) + 1 + stop_time[1] if stop_time != [] else -1 # to include the stop frame
    
    if verbose:
        print 'Start frame: {0}'.format(start_frame)
        if stop_frame > 0:
            print 'Stop frame: {0}'.format(stop_frame)
    
    if stop_frame > 0 and stop_frame <= start_frame:
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
    
    if verbose:
        print 'Converting...'

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
    
    if encode_audio:
        if verbose:
            print 'Copying audio...'
        
        import subprocess, os
        if 'win32' in sys.platform:
            ffmpeg_bin = 'ffmpeg.exe'
        else:
            ffmpeg_bin = 'ffmpeg'
            
        audio_command = [ffmpeg_bin]
        if start_time != []:
            audio_command += ['-ss',time_frame_to_ffmpeg(start_time,fps)]
        if stop_time != []:    
            duration = difference_to_ffmpeg(start_time,stop_time,fps)
            audio_command += ['-t', duration]
        
        audio_command += ['-i',infile,'-i', tmpfile, '-map', '1:v', '-map', '0:a']
        
        if inext == outext:
            audio_command += ['-c:a','copy']
        elif outext == 'avi':
            audio_command += ['-c:a','mp3', '-b:a', '192k']
        else:
            
            # Check what AAC codecs are installed
            found_fdk = False
            found_faac = False
            
            p = subprocess.Popen([ffmpeg_bin,'-codecs'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            codecs,_ = p.communicate()
            
            for line in codecs:
                data = line.split()
                if len(data) < 3:
                    continue
                else:
                    if 'libfdk_aac' in data[1]:
                        found_fdk = True
                        break
                    elif 'libfaac' in data[1]:
                        found_faac = True
                        # Keep looking for libfdk
            
            if found_fdk:
                # FDK AAC, best
                audio_command += ['-c:a','libfdk_aac', '-b:a', '192k',]
            elif found_faac:
                # FAAC, better
                audio_command += ['-c:a','libfaac', '-b:a', '192k',]
            else:
                # Experimental AAC, OK
                audio_command += ['-c:a','aac', '-b:a', '192k', '-strict', '-2']
        
        if not verbose:
            audio_command += ['-loglevel', 'error']
        
        audio_command += ['-c:v', 'copy', '-write_xing', '0', '-y', outfile]
                            
        subprocess.call(audio_command)
        os.remove(tmpfile)

def valid_vidfile(string):
    valid_extensions = ['.mp4','.m4v','.avi']
    if string[-4:] not in valid_extensions or len(string) < 5:
        raise argparse.ArgumentTypeError('{0} is not a valid extension'.format(string[-4:]))
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
    outfile_help = 'Output file name - must be .avi or .m4v (only .avi on some systems)'
    passes_help = 'Number of passes to make over input data. More means less memory but slower'
    start_help = 'Timecode to start encoding at (default 0). Form HH:MM:SS:FF (FF is frame within second)'
    stop_help = 'Timecode to stop at (default end of video). Form HH:MM:SS:FF (FF is frame within second)'
    decode_help = 'Set this flag if you are de-obfuscating a video with custom start/stop. Otherwise frames will be mis-aligned'
    noaudio_help = 'Set this flag to disable audio copying'
    verbose_help = 'Set this flag to enable verbose output'
    
    parser.add_argument('infile',action='store', type=valid_vidfile, help=infile_help)
    parser.add_argument('outfile',action='store', type=valid_vidfile, help=outfile_help)
    parser.add_argument('--passes', '-p', action='store', type=int, default=4, help=passes_help)
    parser.add_argument('--start', '-s', action='store', type=valid_timecode, default=[], help=start_help)
    parser.add_argument('--end', '-e', action='store', type=valid_timecode, default=[],help=stop_help)
    parser.add_argument('--decode' ,'-d',action='store_false',dest='encode',help=decode_help) # Actually stores whether we are encoding or decoding
    parser.add_argument('--noaudio',action='store_false',dest='audio',help=noaudio_help)
    parser.add_argument('--verbose','-v',action='store_true',help=verbose_help)
    args = parser.parse_args()
    
    transform_video(args.infile,args.outfile,args.passes,args.encode,args.start,args.end,args.audio,args.verbose)