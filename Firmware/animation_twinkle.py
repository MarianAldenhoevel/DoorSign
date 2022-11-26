'''
This animation turns on a single white LED for a short interval for a twinkling effect
'''

enabled = True

import time
import math
import random
import doorsign
import logger
import animation

lastframe_ms = None
pixels = None

blendstart_ms = None
blend_ms = 1000

def update(frame_ms, first_frame = False):
    global lastframe_ms
    global pixels
    
    if first_frame or (lastframe_ms == None):        
        # First frame. Initialize to all black
        pixels = [[0,0,0]] * doorsign.pixelCount
        offtimes_ms = [0] * doorsign.pixelCount
    
        # Turn on a random pixel.
        pixelindex = random.randrange(doorsign.pixelCount)
        pixels[pixelindex] = [255, 255, 255]

        result = pixels
    else:
        # Consecutive frame
        
        # Turn off all pixels
        pixels = [[0, 0, 0]] * doorsign.pixelCount
                
        # Maybe turn on a random pixel
        if random.random() > 0.6:
            pixelindex = random.randrange(doorsign.pixelCount)
            pixels[pixelindex] = [255, 255, 255]
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == '__main__':
   
   animation.sample(update)
   