'''
This animation blends each pixels between different randomly selected colors
'''

enabled = True
blend_ms = 3000

import time
import math
import random
import doorsign
import logger
import animation

lastframe_ms = None
startpixels = None
endpixels = None

blendstart_ms = None

def update(frame_ms, first_frame = False):
    global lastframe_ms
    global startpixels
    global endpixels
    global blendstart_ms
    
    if first_frame or (lastframe_ms == None):        
        # First frame.
        startpixels = [doorsign.randomColor() for _ in doorsign.pixelCount]
        endpixels =   [doorsign.randomColor() for _ in doorsign.pixelCount]

        blendstart_ms = frame_ms
        
        pixels = startpixels
    else:
        # Consecutive frame.
        diff = time.ticks_diff(frame_ms, blendstart_ms)
        
        blend = diff/blend_ms
        
        if (blend >= 1.0):
            # Blend finished. Return end pixels and start new blend.
            pixels = endpixels
            startpixels = endpixels
            endpixels =   [doorsign.randomColor() for _ in doorsign.pixelCount]

            blendstart_ms = frame_ms
        else:
            # Return current blend.
            pixels = doorsign.blendPixels(startpixels, endpixels, blend)
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == '__main__':
    
    animation.sample(update)
   