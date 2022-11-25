import sys
import time
import doorsign
import logger
import program
import math
import random

enabled = True

lastframe_ms = None
pixels = None

blendstart_ms = None
blend_ms = 1000

def update(frame_ms):
    global lastframe_ms
    global pixels
    
    if (lastframe_ms == None):        
        # First frame. Initialize to all black
        pixels = [[0,0,0]] * doorsign.neoPixelCount
        offtimes_ms = [0] * doorsign.neoPixelCount
    
        # Turn on a random pixel.
        pixelindex = random.randrange(doorsign.neoPixelCount)
        pixels[pixelindex] = [255, 255, 255]

        result = pixels
    else:
        # Consecutive frame
        
        # Turn off all pixels
        pixels = [[0, 0, 0]] * doorsign.neoPixelCount
                
        # Maybe turn on a random pixel
        if random.random() > 0.6:
            pixelindex = random.randrange(doorsign.neoPixelCount)
            pixels[pixelindex] = [255, 255, 255]
            
    lastframe_ms = frame_ms
    
    return pixels

if __name__ == "__main__":
   
   program.sample(update)
   