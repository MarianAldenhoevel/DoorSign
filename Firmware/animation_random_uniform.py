'''
This animation blends each pixels between one uniform randomly selected colors
'''

enabled = True
blend_ms = 2 * 60 * 1000
preferred_duration_ms = 60 * 60 * 1000

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
        pixel = doorsign.randomColor()
        startpixels = [(0, 0, 0)] * doorsign.pixel_count
        startpixels[1] = pixel
        startpixels[3] = pixel
        startpixels[5] = pixel
        startpixels[7] = pixel

        pixel = doorsign.randomColor()
        endpixels = [(0, 0, 0)] * doorsign.pixel_count
        endpixels[1] = pixel
        endpixels[3] = pixel
        endpixels[5] = pixel
        endpixels[7] = pixel

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
            
            pixel = doorsign.randomColor()
            endpixels = [(0, 0, 0)] * doorsign.pixel_count
            endpixels[1] = pixel
            endpixels[3] = pixel
            endpixels[5] = pixel
            endpixels[7] = pixel

            blendstart_ms = frame_ms
        else:
            # Return current blend.
            pixels = doorsign.blendPixels(startpixels, endpixels, blend)
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == '__main__':
    
    animation.sample(update)
   