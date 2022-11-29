'''
This module implements access to the pixels on the board. It also defines
some support functions for color-management, blending et al.

The general API is to wrap update in beginUpdate() and endUpdate() calls
which may be nested. The first call to beginUpdate() aqcuires a lock. The 
last call to endUpdate() sends the data to the LEDs and then releases the
lock.

So make sure you try..finally every one of them!
'''

firmware_version = '0.3'
pixel_count = 8 # Hardware-Config: Number of pixels on the board.
framerate = 25 # Frames/s for animations.

gamma = 2.8

import machine
import math
import time
import random
from machine import Pin
from neopixel import NeoPixel
import _thread
import lock
import logger

# Set up gamma correction lookup table.
_gamma_table = []

for input in range(256):
    output = math.trunc((((input / 255) ** gamma) * 255) + 0.5)
    _gamma_table.append(output)

_pixel_lock = lock.RecursiveLock()

_rawpixels = [(0, 0, 0)] * pixel_count
_np = NeoPixel(machine.Pin(4, machine.Pin.OUT), pixel_count)

_adc_pins = [
    machine.ADC(26), # ADC0
    machine.ADC(28), # ADC1
    machine.ADC(28)  # ADC2
]

frame_intervall_ms = 1000//framerate # How many ms per frame?

manual_control = False

def beginUpdate():
    _pixel_lock.acquire()
    
def endUpdate():
    assert _pixel_lock.mine() # If not someone has not wrapped their begin-/endUpdate-calls correctly. 
    
    # Safe to query the lock. It is ours. If we are about to actually unlock send the final
    # pixel data out.
    if _pixel_lock.count() == 1:
        _np.write()
        
    _pixel_lock.release()

def setManualControl(manual):
    global manual_control
    
    _pixel_lock.acquire()
    try:
        manual_control = manual
    finally:
        _pixel_lock.release()

def readADC():
    result = []
    for pin in _adc_pins:
        result.append(pin.read_u16())

    return result

'''
Convert from RGB color space to HSV. 
RGB is a tuple of three integers in the range 0..255. 
HSV is returned as a tuple of integers (0..360, 0..100, 0..100)
'''
def RGBToHSV(rgb_color):

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

'''
Convert from HSV color space to RGB. 
HSV is a tuple of integers (0..360, 0..100, 0..100)
RGB is returned as a tuple of three integers in the range 0..255. 
'''
def HSVToRGB(hsv_color):
    
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
    return HSVToRGB((random.randint(0,360), 255, random.randint(5,255)))

def clamp(channel, min=0, max=255):
    if channel < min:
        channel = min
    elif channel > max:
        channel = max
        
    return channel

'''
Scale the channels of pixel by a floating point scalefactor. The factor is arbitrary,
the results are truncated and clamped.
'''
def scalePixel(pixel, scalefactor):
    return (
        clamp(math.trunc(pixel[0] * float(scalefactor))),
        clamp(math.trunc(pixel[1] * float(scalefactor))),
        clamp(math.trunc(pixel[2] * float(scalefactor)))
    )

'''
Scale all pixels by a floating point scalefactor. The factor is arbitrary,
the results are truncated and clamped.
'''
def scalePixels(pixels , scalefactor):
    result = [(0, 0, 0)] * pixel_count
    for pixelIndex in range(pixel_count):
        result[pixelIndex] = scalePixel(pixels[pixelIndex], scalefactor)
        
    return result

''' 
Linear blend between two single pixels, blend is a float between 0 and 1.
'''
def blendPixelLinear(pixel1, pixel2, blend):
    
    # Clamp blend value
    if blend < 0.0:
        blend = 0.0
    elif blend > 1.0:
        blend = 1.0

    return (
        math.trunc(pixel1[0] * (1.0-blend) + pixel2[0] * blend),
        math.trunc(pixel1[1] * (1.0-blend) + pixel2[1] * blend),
        math.trunc(pixel1[2] * (1.0-blend) + pixel2[2] * blend)
    )
        
'''
Linear blend between two complete pixel arrays, blend is a float between 0 and 1.
'''
def blendPixelsLinear(pixels1, pixels2, blend):
    result = [(0, 0, 0)] * pixel_count
    for pixelIndex in range(pixel_count):
        result[pixelIndex] = blendPixelLinear(pixels1[pixelIndex], pixels2[pixelIndex], blend)
        
    return result

''' 
More clever blend between two single pixels, blend is a float between 0 and 1.

The blend happens in HSV space with H going the "short way".
'''
def blendPixel(pixel1, pixel2, blend):
    
    # Clamp blend value
    if blend < 0.0:
        blend = 0.0
    elif blend > 1.0:
        blend = 1.0

    # Convert pixels to HSV space.
    hsv1 = RGBToHSV(pixel1)
    hsv2 = RGBToHSV(pixel2)
    
    # print('hsv1 ' + str(hsv1))
    # print('hsv2 ' + str(hsv2))
    
    # Swap so that Pixel2 has the larger H value.
    if hsv1[0] > hsv2[0]:
        hsv1, hsv2 = hsv2, hsv1 # Very pythonic swap.
        blend = 1.0 - blend;
  
    # The hue value wraps around at 360. We want it to blend along the
    # shortest arc. If the direct difference is greater than 180 go
    # the other way.
    if hsv2[0] - hsv1[0] > 180:
        h = (hsv1[0] + 360) * (1.0 - blend) + hsv2[0] * blend
        if h > 360:
            h -= 360
    else:
        h = hsv1[0] * (1.0 - blend) + hsv2[0] * blend
    
    # Blend S and V linearly.
    hsv = (
        math.trunc(h),
        math.trunc(hsv1[1] * (1.0-blend) + hsv2[1] * blend),
        math.trunc(hsv1[2] * (1.0-blend) + hsv2[2] * blend)
    )
    
    # print('hsv  ' + str(hsv))
    
    # Return as RBG value
    return HSVToRGB(hsv)

'''
More clever blend between two single pixels, blend is a float between 0 and 1.

The blend happens in HSV space with H going the "short way".
'''
def blendPixels(pixels1, pixels2, blend):
    result = [(0, 0, 0)] * pixel_count
    for pixelIndex in range(pixel_count):
        result[pixelIndex] = blendPixel(pixels1[pixelIndex], pixels2[pixelIndex], blend)
        
    return result

''' 
Set a single pixel.
'''            
def setPixel(pixelIndex, pixel):
    beginUpdate()
    try:
        # Store the raw rgb value for reading back.
        _rawpixels[pixelIndex] = pixel

        # Gamma-correct the RGB values.
        gammapixel = (_gamma_table[pixel[0]], _gamma_table[pixel[1]], _gamma_table[pixel[2]])

        # Send the corrected values to the hardware.
        _np[pixelIndex] = gammapixel
    finally:
        endUpdate()

'''
Update all pixels from an array.
'''    
def setPixels(pixels):
    beginUpdate()
    try:
        for pixelIndex in range(pixel_count):
            setPixel(pixelIndex, pixels[pixelIndex])            
    finally:
        endUpdate()        

''' 
Read a single pixel.
'''            
def getPixel(pixelIndex):
    return _rawpixels[pixelIndex]
        
'''
Read all pixels.
'''    
def getPixels():
    beginUpdate()
    try:
        pixels = [(0,0,0)] * pixel_count
        for pixelIndex in range(pixel_count):
            pixels[pixelIndex] = getPixel(pixelIndex)            
    finally:
        endUpdate()
        
    return pixels

'''
Turn all pixels off
'''        
def off():
    pixels = [(0, 0, 0)] * pixel_count
    setPixels(pixels)

'''
Print a single pixel as a six-digit hex string.
'''
def formatPixel(pixel):
    return pixel[0].to_bytes(1, 'big').hex() + pixel[1].to_bytes(1, 'big').hex() +pixel[2].to_bytes(1, 'big').hex()

'''
Format a pixel array for string output.
'''
def formatPixels(pixels):
    return '<' + ','.join([formatPixel(pixel) for pixel in pixels]) + '>'

if __name__ == '__main__':

    logger.write('__main__: All pixels off')
    off()
    
    print(_gamma_table)