import numpy as np
import cv2


# Take an input video and apply the transformation
# For each pass, read 1/num_passes columns from the input frames and write the same number of output frames
def transform_video(infile,outfile,num_passes=1):
    
    # Prevent nastiness...
    if num_passes < 1:
        num_passes = 1
        
    # Init video capture
    vcap = cv2.VideoCapture()
    if vcap.open(infile) == -1:
        return

    frame_height = int(vcap.get(4))
    frame_width = int(vcap.get(3))
        
    # If too many passes specified, limit to number of columns
    if num_passes > frame_width:
        num_passes = frame_width #SLOW

    # Prepare codec writer (AVI is best cross-platform)
    fourcc = cv2.cv.CV_FOURCC(*'XVID')
    vwrite = cv2.VideoWriter(outfile,fourcc,vcap.get(5),(frame_width,frame_height))

    # Calculate number of columns to read per pass
    stripe_width = frame_width/num_passes
    if frame_width % num_passes != 0:
        stripe_width += 1


    # Create frame buffer. Last dimension is color. No alpha support yet...
    # Here, we read the first frame to get the dtype for the matrix
    frames = np.empty([frame_height,stripe_width,frame_width,3],vcap.read()[1].dtype)


    vcap.set(1,0) # Reset to beginning of video
    
    # This is true as long as we have frames to read
    frames_to_read = True

    block_count = 0 # Counts the number of frame blocks we read (used to set frame position)
    while frames_to_read:
        
        # Loop through n passes
        for pass in xrange(num_passes):
            vcap.set(1,block_count * frame_width) # Rewind to beginning of pass. If first pass, does nothing
            
            true_width = min(stripe_width*(pass+1),frame_width) - stripe_width * pass # Since we overestimate the pass width
            
            # Read the frames
            for cnt in xrange(frame_width):
                
                #If we have frames remaining, read them (or at least try)
                if frames_to_read:
                    frames_to_read,frame = vcap.read()
                      
                # Otherwise, just zero it. We don't break out because there are more spots to fill
                if not frames_to_read: # check again because may be set in last if
                    frame = np.zeros([frame_height,frame_width,3],frames.dtype)
  
                # Read slice of frame into output buffer.
                frames[:,:true_width,cnt,:] = frame[:,stripe_width*pass:stripe_width*pass+true_width]

            # Write next frames to output
            for i in xrange(true_width):
                vwrite.write(frames[:,i,:,:])
                
        block_count += 1    # Processed another block of input frames
        
    # Clean up
    vcap.release()
    vwrite.release()  
    

if __name__ == "__main__":
    transform_video('sintel.mp4','sintel_obfuscated.avi',4)