'''
This animation turns on a single white LED for a short interval for a twinkling effect
'''

enabled = True
preferred_duration_ms = 6 * 1000

import time
import math
import random
import doorsign
import logger
import animation

lastframe_ms = None
pixels = None

def update(frame_ms, first_frame = False):
    global lastframe_ms
    global pixels
    
    if first_frame or (lastframe_ms == None):        
        # First frame. Initialize to all black
        pixels = [[0,0,0]] * doorsign.pixel_count
        offtimes_ms = [0] * doorsign.pixel_count
    
        # Turn on a random pixel.
        pixelindex = random.randrange(doorsign.pixel_count)
        pixels[pixelindex] = [255, 255, 255]

        result = pixels
    else:
        # Consecutive frame
        
        # Turn off all pixels
        pixels = [[0, 0, 0]] * doorsign.pixel_count
                
        # Maybe turn on a random pixel
        if random.random() > 0.6:
            pixelindex = random.randrange(doorsign.pixel_count)
            pixels[pixelindex] = [255, 255, 255]
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == '__main__':
   
   animation.sample(update)
   