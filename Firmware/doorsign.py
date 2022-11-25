import machine
import math
import time
import random
from machine import Pin
from neopixel import NeoPixel
import _thread
import logger

pixelCount = 8

np = NeoPixel(machine.Pin(4, machine.Pin.OUT), pixelCount)

pixel_lock = _thread.allocate_lock()
updating = 0

framerate = 25 # Frames/s
frame_intervall_ms = 1000//framerate # How many ms per frame?

manual_control = False

def setManualControl(manual):
    global manual_control
    
    pixel_lock.acquire()
    try:
        manual_control = manual
    finally:
        pixel_lock.release()

def rgb_to_hsv(rgb_color):
    """Converts colors from the RGB color space to the HSV color space.
    Parameters
    ----------
    rgb_color : tuple (r, g, b)
        Color in the RGB color space
    Returns
    -------
    tuple (h, s, v)
        Color in the HSV color space
    """
    (r, g, b) = rgb_color
    r = r/255.0
    g = g/255.0
    b = b/255.0
    high = max(r, g, b)
    low = min(r, g, b)
    h, s, v = high, high, high

    d = high - low
    s = 0 if high == 0 else d/high

    if high == low:
        h = 0.0
    else:
        h = {
            r: (g - b) / d + (6 if g < b else 0),
            g: (b - r) / d + 2,
            b: (r - g) / d + 4,
        }[high]
        h /= 6

    h = math.trunc(360 * h)
    s = math.trunc(100 * s)
    v = math.trunc(100 * v)

    return h, s, v

def hsv_to_rgb(hsv_color):
    """Converts colors from the HSV color space to the RGB color space.
    Parameters
    ----------
    hsv_color : tuple (h, s, v)
        Color in the HSV color space
    Returns
    -------
    tuple (r, g, b)
        Color in the RGB color space
    """
    (h, s, v) = hsv_color
    h = h/360.0
    s = s/100.0
    v = v/100.0
    
    i = math.floor(h*6)
    f = h*6 - i
    p = v * (1-s)
    q = v * (1-f*s)
    t = v * (1-(1-f)*s)

    r, g, b = [
        (v, t, p),
        (q, v, p),
        (p, v, t),
        (p, q, v),
        (t, p, v),
        (v, p, q),
    ][int(i%6)]
    
    r = math.trunc(255 * r)
    g = math.trunc(255 * g)
    b = math.trunc(255 * b)
    
    return r, g, b

def randomColor():
    return hsv_to_rgb((random.randint(0,360), 255, random.randint(5,255)))

def blendPixel(pixel1, pixel2, blend):
    return (
        math.trunc(pixel1[0] * (1.0-blend) + pixel2[0] * blend),
        math.trunc(pixel1[1] * (1.0-blend) + pixel2[1] * blend),
        math.trunc(pixel1[2] * (1.0-blend) + pixel2[2] * blend),
    )
        
def blendPixels(pixels1, pixels2, blend):
    result = [(0, 0, 0)] * pixelCount
    for pixelIndex in range(pixelCount):
        result[pixelIndex] = blendPixel(pixels1[pixelIndex], pixels2[pixelIndex], blend)
        
    return result
def beginUpdate():
    global updating

    if updating == 0:
        pixel_lock.acquire()
        updating += 1
    
def endUpdate():
    global updating
    
    if updating > 0:
        updating -= 1
        if updating == 0:
            np.write()
            pixel_lock.release()
            
def setPixel(pixelIndex, pixel):
    beginUpdate()
    try:
        np[pixelIndex] = pixel
    finally:
        endUpdate()
    
def setPixels(pixels):
    beginUpdate()
    try:
        for pixelIndex in range(pixelCount):
            setPixel(pixelIndex, pixels[pixelIndex])            
    finally:
        endUpdate()        
            
def off():
    pixels = [(0, 0, 0)] * pixelCount
    setPixels(pixels)

def formatPixel(pixel):
    return pixel[0].to_bytes(1, 'big').hex() + pixel[1].to_bytes(1, 'big').hex() +pixel[2].to_bytes(1, 'big').hex()

def formatPixels(pixels):
    return '<' + ','.join([formatPixel(pixel) for pixel in pixels]) + '>'

if __name__ == "__main__":

    logger.write("__main__: All pixels off")
    off()