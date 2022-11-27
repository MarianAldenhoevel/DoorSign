'''
This animation blends each pixels between different randomly selected colors
'''

enabled = False
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

p1 = (0, 0, 255)
p2 = (255, 0, 0)

def update(frame_ms, first_frame = False):
    global lastframe_ms
    global startpixels
    global endpixels
    global blendstart_ms
    
    if first_frame or (lastframe_ms == None):        
        # First frame.
        startpixels = [(0, 0, 0)] * doorsign.pixel_count
        endpixels =   [(0, 0, 0)] * doorsign.pixel_count
        
        startpixels[0] = p1
        endpixels[0] = p2
        
        blendstart_ms = frame_ms
        
        pixels = startpixels[:]
    else:
        # Consecutive frame.
        diff = time.ticks_diff(frame_ms, blendstart_ms)
        
        blend = diff/blend_ms
        
        if (blend >= 1.0):
            # Blend finished. Return end pixels and start new blend.
            pixels = endpixels[:]
            startpixels = endpixels[:]
            
            if startpixels[0] == p1:
                endpixels[0] = p2
            else:
                endpixels[0] = p1
            
            blendstart_ms = frame_ms
        else:
            # Return current blend.
            pixels = doorsign.blendPixels(startpixels, endpixels, blend)
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == '__main__':
    
    animation.sample(update)
   