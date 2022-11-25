import sys
import time
import doorsign
import logger
import program

enabled = True

lastframe_ms = None
startpixels = None
endpixels = None

blendstart_ms = None
blend_ms = 3000

def update(frame_ms):
    global lastframe_ms
    global startpixels
    global endpixels
    global blendstart_ms
    
    if (lastframe_ms == None):        
        # First frame. Initialize to random colors and set up the colors to fade to.
        startpixels = [doorsign.randomColor() for _ in range(doorsign.pixelCount)]
        endpixels =   [doorsign.randomColor() for _ in range(doorsign.pixelCount)]

        blendstart_ms = frame_ms
        
        # logger.write("Initial blend start at " + str(blendstart_ms) + " " + doorsign.formatPixels(startpixels) + " -> " + doorsign.formatPixels(endpixels))
        
        result = startpixels
    else:
        # Consecutive frame
        diff = time.ticks_diff(frame_ms, blendstart_ms)
        
        # Blend between the startpixels and endpixels in interval milliseconds
        blend = diff/blend_ms
        
        if (blend >= 1.0):
            # Finished one blend. Update to final colors for this frame and set up
            # next blend.
            result = endpixels
            startpixels = endpixels
            endpixels =   [doorsign.randomColor() for _ in range(doorsign.pixelCount)]

            blendstart_ms = frame_ms

            # logger.write("New blend start at " + str(blendstart_ms) + " " + doorsign.formatPixels(startpixels) + " -> " + doorsign.formatPixels(endpixels))
        else:
            # Calculate blend
            result = doorsign.blendPixels(startpixels, endpixels, blend)
            
    lastframe_ms = frame_ms
    
    return result

if __name__ == "__main__":
    
    program.sample(update)
   