
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
    r = int(255 * r)
    g = int(255 * g)
    b = int(255 * b)
    return r, g, b

'''
import math, time
from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms

np = NeoPixel(Pin(4, Pin.OUT), 1)

while True:
    for hue in range(360):
        hsv = (hue * 2*math.pi/360, 1, 1)
        rgb = hsv_to_rgb(hsv)
        print(hsv, ' ' , rgb)
        np[0] = rgb
        np.write()
        sleep_ms(70)
'''

# Bibliotheken laden
'''
from machine import Pin
from neopixel import NeoPixel
from utime import sleep_ms

# GPIO-Pin für WS2812
pin_np = 4

# Anzahl der LEDs
leds = 8

# Helligkeit: 0 bis 255
brightness = 0

# Geschwindigkeit (Millisekunden)
speed = 50

# Initialisierung WS2812/NeoPixel
np = NeoPixel(Pin(pin_np, Pin.OUT), leds)

# Wiederholung (Endlos-Schleife)
while True:
    for i in range (leds):
        # Nächste LED einschalten
        np[i] = (brightness, brightness, brightness) # brightness, brightness)
        np.write()
        sleep_ms(speed)
        # LED zurücksetzen
        #np[i] = (0, 0, 0)
        #np.write()
        #sleep_ms(speed)
'''

'''
import rp2
import network
import ubinascii
import machine
import urequests as requests
import time
import socket
from utime import sleep

led = machine.Pin('LED', machine.Pin.OUT)
while True:
    led.value(1)
    sleep(0.5)
    led.value(0)
    sleep(0.5)
'''

'''
ringer_in = machine.Pin(3, machine.Pin.IN, machine.Pin.PULL_UP)
led = machine.Pin('LED', machine.Pin.OUT)
    
while (True):
    print(ringer_in.value())
    led.value(ringer_in.value())
    

# Bibliotheken laden
#from machine import ADC
from utime import sleep

# Initialisierung des ADC0
ldr = machine.ADC(0)

# Wiederholung
while True:
    # ADC als Dezimalzahl lesen
    read = ldr.read_u16()
    # Ausgabe in der Kommandozeile/Shell
    print("ADC: ", read)
    # Warten
    sleep(0.2)
'''

import rp2
import network
import ubinascii
import machine
import urequests as requests
import time
import socket
from utime import sleep
from neopixel import NeoPixel

print("Doorsign firmware 0.0")
print("Starting up")

rgbledcount = 8

onboard_led = machine.Pin('LED', machine.Pin.OUT)

def onboard_led_set(aState): 
    global onboard_led_state
    onboard_led_state = aState
    onboard_led.value(onboard_led_state)

def onboard_led_toggle():
    onboard_led_set(1 if (onboard_led_state==0) else 0)

onboard_led_state = None;
onboard_led_set(1);

np = NeoPixel(machine.Pin(4, machine.Pin.OUT), rgbledcount)

np[0] = (255//10, 255//10, 0) # Yellow
np.write()

secrets = {
    'ssid': 'Heinrichsweg 9',
    'pw': 'ZZkY23grMGpNLfP2'
}

# Set country to avoid possible errors
rp2.country('DE')

wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# print(wlan.scan())

# Disable power-saving if used as server
wlan.config(pm = 0xa11140)

# See the MAC address in the wireless chip OTP
mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
print('MAC = ' + mac)

# Other things to query
# print(wlan.config('channel'))
# print(wlan.config('essid'))
# print(wlan.config('txpower'))

np[0] = (255//10, 100//10, 0) # Orange
np.write()

print('Connecting to: ' + secrets['ssid'])

wlan.connect(secrets['ssid'], secrets['pw'])

# Wait for connection with 10 second timeout
timeout = 200
while timeout > 0:
    if wlan.status() < 0 or wlan.status() >= 3:
        break
    timeout -= 1
    print('Waiting for connection...')
    onboard_led_toggle()
    time.sleep(0.5)

onboard_led_set(0)
    
# Handle connection error
# Error meanings
# 0  Link Down
# 1  Link Join
# 2  Link NoIp
# 3  Link Up
# -1 Link Fail
# -2 Link NoNet
# -3 Link BadAuth

if wlan.status() != 3:
    np[0] = (255//10, 0, 0) # Red
    np.write()
    raise RuntimeError('Wi-Fi connection failed status = ' + str(wlan_status()))
else:
    np[0] = (0, 255//10, 0) # Green
    np.write()
    print('Connected')
    status = wlan.ifconfig()
    print('IP = ' + status[0])
    sleep(3) # so we can see the green LED
    np[0] = (0, 0, 0) # Off for normal operations.
    np.write()
    
# Function to load in static file    
def get_file(filename):
    with open(filename, 'r') as file:
        data = file.read()
        
    return data

# HTTP server with socket
addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

s = socket.socket()
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(addr)
s.listen(1)

print('Listening on', addr)
            
def responseError(statuscode, statustext):
    cl.sendall("HTTP/1.0 200 OK \r\nContent-Length: " + str(len(response)) + "\r\nContent-Type: " + ct + "\r\n\r\n")
        
            
# Listen for connections
while True:
    try:
        cl, addr = s.accept()
        onboard_led_set(1)
        
        print('Client connected from', addr)
        
        request = str(cl.recv(1024))

        if len(request) > 6:
            method = request[2:request.find(" ")]
            request = request[len(method) + 3:]
            
            resource = request[1:request.find(" ")]
            request = request[len(resource) + 3:]
            
            i = resource.find("?")
            if i != -1:
                paramstr = resource[i+1:]
                resource = resource[0:i]                
            else:
                paramstr = ""
               
            params = {}
            for p in paramstr.split("&"):
                i = p.find("=")
                if i == -1:
                    name = p
                    value = ""
                else:
                    name = p[0:i]
                    value = p[i+1:]
           
                params[name] = value
            
            #for key in params:
            #    print(key + "->" + params[key])
            
            if (resource == ""):
                resource = "index.html"

            print(method + " " + resource + (("?" + paramstr) if paramstr != "" else ""))

            '''
            r = str(r)
            led_on = r.find('GET /?led=on')
            led_off = r.find('GET /?led=off')
            #print('led_on = ', led_on)
            #print('led_off = ', led_off)
            if led_on > -1:
                print('LED ON')
                led.value(1)
                
            if led_off > -1:
                print('LED OFF')
                led.value(0)
            '''
            
            #response = 'Hello World'
            
            if (method=="GET") or (method=="HEAD"):
                response = get_file(resource)
                ext = resource[resource.find("."):]
                if ext==".html":
                    ct = "text/html"
                else:
                    ct = "application/octet-stream"
            elif method=="POST":
                
                if resource == "set":
                    for i in range(rgbledcount):
                        rgb = (
                            int(params.get("r" + str(i), 0)),
                            int(params.get("g" + str(i), 0)),
                            int(params.get("b" + str(i), 0)),
                        )
                        #print(rgb)
                        np[i] = rgb
                    np.write()
                        
                response = "{}"
                ct = "application/json"
            else:
                raise RuntimeError("Unsupported http-method: \"" + method + "\"")
                                    
            print(addr[0] + " " + method + " \"" + resource + (("?" + paramstr) if paramstr != "" else "") + "\" 200 OK (" + str(len(response)) + " bytes of " + ct + ")")                             
            cl.sendall("HTTP/1.0 200 OK \r\nContent-Length: " + str(len(response)) + "\r\nContent-Type: " + ct + "\r\n\r\n")
            
            if method!="HEAD": # The server MUST NOT return a content-body
                cl.sendall(response)
                
        cl.close()
        print('Connection closed')
            
    except OSError as e:
            
        if e.errno == errno.ENOENT:
            statuscode = 404
            statustext = "Not found"
        else:
            print(e)
            raise
        
        print(addr[0] + " " + method + " \"" + resource + (("?" + paramstr) if paramstr != "" else "") + "\" " + str(statuscode) + " " + statustext)                             
        cl.sendall("HTTP/1.0 " + str(statuscode) + " " + statustext)
        cl.close()
        print('Connection closed')
        
    finally:
        onboard_led_set(0)
        
# Make GET request
#request = requests.get('http://www.google.com')
#print(request.content)
#request.close()
