'''
This implements the network task.

Sets up WiFi as STA (Client) or AP (Access point) as _configured in _config.json

If set up as AP also runs a DNS server to implement a captive portal. The implementation
of that is right here and trivial.

Then it starts a primitive web server also implemented here. The web server supports
delivery of static resources and API endpoints all hardcoded.

The network task controls the _onboard LED. When setting up the LED is on, when setup
is completed sucessfully it turns off. If an error is encountered connecting in STA mode
a code is blinked. 

In operation the onboard LED turns on while network requests are being serviced.
'''

import rp2
import os
import machine
import network
import ubinascii
import time
import socket
import select
import ujson
import watchdog
import struct
import core1
import logger
import doorsign

_onboard = machine.Pin('LED', machine.Pin.OUT)
_myip = None
_config = None
_nextNTPSync = None
_boot_ms = time.ticks_ms()

def setup():
    global _config
    
    # Load _configuration
    logger.write('Reading config.json')
    with open('config.json') as fp:
        _config = ujson.load(fp)
    
'''
When the task fails to make a connection it blinks an error code on the
onboard LED
'''
def fatalConnectionError(code, message):
    _onboard.off()
    logger.write('FATAL: ' + str(code) + ' - ' + message)
    
    time.sleep(1)
    for _ in range(code):
        _onboard.on()
        time.sleep(0.5)
        _onboard.off()
        time.sleep(0.5)
        
    raise RuntimeError(message)    

'''
Single function to handle a DNS request.

Packet decoding adapted from #https://stackoverflow.com/questions/65060776/reading-dns-packet-in-python

We decode the request just for giggles. We don't even use it and always respond the same.
'''

OpCodeStrs = [
        'QUERY', 
        'IQUERY', 
        'STATUS', 
        '(reserved)', 
        'NOTIFY', 
        'UPDATE'
]

RCodeStrs = [
    'No Error', 
    'Format Error', 
    'Server Failure', 
    'Name Error', 
    'Not Implemented', 
    'Refused', 
    'XY Domain', 
    'XY RR Set', 
    'NX RR Set', 
    'Not Auth', 
    'Not Zone'
]
    
def handleDNS(socket):
    try:
        _onboard.on()

        request, client = socket.recvfrom(1024) # Big enough for anyone?

        # Decode DNS header.
        l = len(request)
        dnsDict = dict(
            ID      = request[0]*256+request[1],
            QR      = bool(request[2] & int('10000000', 2)),
            Opcode  =     (request[2] & int('01111000', 2))>>3,            
            AA      = bool(request[2] & int('00000100', 2)),
            TC      = bool(request[2] & int('00000010', 2)),
            RD      = bool(request[2] & int('00000001', 2)),
            RA      = bool(request[3] & int('10000000', 2)),
            Z       =     (request[3] & int('01110000', 2)),
            RCode   =     (request[3] & int('00001111', 2)),
            QDCOUNT = request[4]*256+request[5],
            ANCOUNT = request[6]*256+request[7],
            NSCOUNT = request[8]*256+request[9],
            ARCOUNT = request[10]*256 + request[11],
            # --
            QTYPE   = request[l-4]*256+request[l-3],
            QCLASS  = request[l-2]*256+request[l-2]
        )

        # Decode some values to strings.
        OpCode = dnsDict['Opcode']
        if (OpCode >= 0) and (OpCode < len(OpCodeStrs)):
            dnsDict['OpcodeStr'] = OpCodeStrs[OpCode]
        else:
            dnsDict['OpcodeStr'] = str(OpCode) + '?'
            
        RCode = dnsDict['RCode']
        if (RCode >= 0) and (RCode < len(RCodeStrs)):
            dnsDict['RCodeStr'] = RCodeStrs[RCode]
        else:
            dnsDict['RCodeStr'] = str(RCode) + '?'

        # Parse QNAME starting at byte #12.        
        n = 12
        qname = ''
        
        # Get field size.
        argSize = int(request[n])
        n += 1
        
        # Are there more fields?
        while (argSize != 0) and (n < len(request)):
            # Yes. Extract the substring and apped a period.
            qname += request[n:n+argSize].decode() + '.'
            n += argSize
                
            # Get next field size.
            argSize = int(request[n])
            n += 1
            
        dnsDict['QNAME'] = qname[:-1] # Chop off extra period we have added.

        logger.write('DNS query for \"' + dnsDict['QNAME'] + '\" from ' + client[0])

        # Build the response.
        response = bytearray()
        response = request[:2] 							# Request ID
        response += b'\x81\x80' 						# Response flags
        response += request[4:6] + request[4:6] 		# QD/AN count
        response += b'\x00\x00\x00\x00' 				# NS/AR count
        response += request[12:] 						# Original request body
        response += b'\xC0\x0C' 						# Pointer to domain name at byte 12
        response += b'\x00\x01\x00\x01' 				# Type and class (A record / IN class)
        response += b'\x00\x00\x00\x3C' 				# Time to live 60 seconds
        response += b'\x00\x04' 						# Response length (4 bytes = 1 ipv4 address)
        response += bytes(map(int, _myip.split('.'))) 	# IP address parts
        
        # And deliver it.
        socket.sendto(response, client)

    except Exception as e:
        logger.write('Error handling DNS request ' + str(e))

    finally:
        _onboard.off()

'''
Build a representation of the sensors and led settings
'''

def pluralize(n, unit):
    if n == 0:
        return ''
    elif n == 1:
        return '1 ' + unit + ' '
    else:
        return str(n) + ' ' + unit + 's '

def apiData():
    result = {}
    
    doorsign.beginUpdate()
    try:
        # Get filesystem information.
        v = os.statvfs('/')
        size_bytes = v[1]*v[2]
        free_bytes = v[0]*v[3]
        
        # Get uptime. May wrap around and give values that are too short.
        ticks = time.ticks_diff(time.ticks_ms(), _boot_ms)
        s, ms = divmod(ticks, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        
        result['uptime'] = (pluralize(d, 'day') + pluralize(h, 'hour') + pluralize(m, 'minute') + pluralize(s, 'second')).strip()
        result['firmware_version'] = doorsign.firmware_version
        result['manual_control'] = doorsign.manual_control
        result['pixels'] = [{'R': p[0], 'G': p[1], 'B': p[2]} for p in doorsign.getPixels()]            
        result['adc'] = doorsign.readADC()
        result['animations'] = [a.__name__ for a in core1.animations]
        result['active_animation'] = (core1.active_animation.__name__ if core1.active_animation else None);
        result['size_bytes'] = size_bytes
        result['free_bytes'] = free_bytes
    finally:
        doorsign.endUpdate()
    
    return result

def extractHeader(data, header):
    search = b'\r\n' + header + b': '
    headerpos = data.find(search)

    if headerpos == -1:
        return None
    else:
        data = data[headerpos + len(search):]
        
        endpos = data.find(b'\r\n')
        if endpos == -1:
            value = data.decode()
        else:    
            value = data[:endpos].decode()
   
        return value    

'''
This function implements the complete handling of a http request.
''' 
def handleHttp(socket):
    _onboard.on()
    try:
        cl, addr = socket.accept()    
        logger.write('Client connected from '+ str(addr))
        
        cl.settimeout(10)
        request_data = cl.recv(1024) # Only read this much data. We don't care if they send any more.
        
        # Minimal sanity-check.
        if len(request_data) > 6:
            statuscode = 0
            statustext = None
            method = None
            resource = None
            response = None
            responsefilesize = None 

            try:
                # Split the request into headers and body.
                separator = b'\r\n\r\n'
                separator_pos = request_data.find(separator)
                request_header = request_data[:separator_pos]
                request_body = request_data[separator_pos + len(separator):]
                                
                # Extract method and the resource requested from the request. 
                method = request_header[:request_header.find(b' ')].decode()
                request_header = request_header[len(method) + 1:]

                resource = request_header[:request_header.find(b' ')].decode()
                request_header = request_header[len(resource) + 1:]
                
                # Separate query parameters.
                i = resource.find('?')                
                if i != -1:
                    paramstr = resource[i+1:]
                    resource = resource[0:i]
                else:
                    paramstr = ''
                            
                # Parse query parameters into a dictionary by name and value.
                params = {}
                for p in paramstr.split('&'):
                    i = p.find('=')
                    if i == -1:
                        name = p
                        value = ''
                    else:
                        name = p[0:i]
                        value = p[i+1:]
            
                    params[name] = value
        
                # Default to index page.
                if (resource == '') or (resource == '/'):
                    resource = 'index.html'

                # Determine content-type by file extension.
                ext = resource[resource.rfind('.'):]
                if ext == '.html':
                    contenttype = 'text/html'
                elif ext == '.ico':
                    contenttype = 'image/x-icon'
                elif ext == '.png':
                    contenttype = 'image/png'                
                elif ext == '.jpg':
                    contenttype = 'image/jpeg'
                elif ext == '.svg':
                    contenttype = 'image/svg+xml'
                elif ext == '.xml':
                    contenttype = 'application/xml'
                elif ext == '.js':
                    contenttype = 'text/javascript'
                else:
                    contenttype = 'application/octet-stream'
        
                if (method == 'GET') or (method == 'HEAD'):        
                    # GET or HEAD: First test for the special endpoints that implement the
                    # API. If no match assume it is for static content.  

                    if resource == '/api':
                        # Return sensor data and LED status.
                        response = ujson.dumps(apiData())
                        contenttype = 'application/json'            
                        
                    elif resource.endswith('/'):
                        # List directory.
                        response = ujson.dumps(os.listdir('/www/' + resource))
                        contenttype = 'application/json'
                        
                    else:   
                        # Static resource. Just read the size here. We will open and send the file
                        # later in chunks to support large content. If the file does not exist
                        # this will also raise the exception we want to catch to produce a 404.
                        responsefilesize = os.stat('/www/' + resource)[6]
                            
                    statuscode = 200
                    statustext = 'OK'
            
                elif method == 'DELETE':
                    # DELETE: Just attempt it and face the consequences.
                    os.remove('/www/' + resource)
                    
                    statuscode = 200
                    statustext = 'OK'
            
                elif method == 'POST':
                    # POST: Test for special api endpoints. If no match treat as file upload
                    # for a poor man's OTA update.
                    
                    if resource == '/reset':
                        # Well. This will not even produce a http result, just hit itself 
                        # over the head with a hammer right now.
                        machine.reset()

                    elif resource == '/animation':
                        # Request core0 to switch to a new animation. Pass in the name of the
                        # next animation module or leave empty for a random next animation.
                        core1.request_animation = params.get('name', '')
                        
                        # Build response                                 
                        response = ujson.dumps([a.__name__ for a in core1.animations])
                        
                        contenttype = 'application/json'            
                        statuscode = 200
                        statustext = 'OK'
                        
                    elif resource == '/api':
                        # Read each pixel and update if there is data for that channel.
                        hasChannelData = False
                        doorsign.beginUpdate()
                        try:
                            for pixelIndex in range(doorsign.pixel_count):                                                            
                                r, g, b = doorsign.getPixel(pixelIndex)
                                
                                p = 'r' + str(pixelIndex) 
                                if p in params:
                                    r = int(params[p])
                                    hasChannelData = True
                                    
                                p = 'g' + str(pixelIndex) 
                                if p in params:
                                    g = int(params[p])
                                    hasChannelData = True
                                
                                p = 'b' + str(pixelIndex) 
                                if p in params:
                                    b = int(params[p])
                                    hasChannelData = True
                                
                                doorsign.setPixel(pixelIndex, (r, g, b))
                        finally:
                            # Enable/Disable animation if explicitly asked for in the request parameters.
                            doorsign.setManualControl(params.get('manual', doorsign.manual_control) in [True, 'true', 'True', 'TRUE', 1, '1'])
                            
                            # Then conditionally disable animation on the pixels if any data has been set remotely.                    
                            if hasChannelData:
                                doorsign.setManualControl(True)
                        
                        # Build response                                 
                        response = ujson.dumps(apiData())
                        
                        # End pixel update phase. This will send the data out to the LEDs.
                        doorsign.endUpdate()                    

                        contenttype = 'application/json'            
                        statuscode = 200
                        statustext = 'OK'            
                    else:
                        # Not a special endpoint. Treat as file upload. We use raw data upload so
                        # the filename is simply the resource POSTed to and the data is the whole
                        # body of the request.
                        
                        contentlength = int(extractHeader(request_header, b'Content-Length'))
                        
                        written = 0
                        with open('/www/' + resource, "wb") as dest:                            
                            # We have only received the start of the data when we looked at the
                            # request. Save and read and save and read the rest...
                            while True:
                                dest.write(request_body)

                                written += len(request_body)
                                if written >= contentlength:
                                    break
                            
                                request_body = cl.recv(2048)
                                if not request_body:
                                    time.sleep(0.1)
                            
                        statuscode = 200
                        statustext = 'OK (' + str(written) + ' bytes written to \"' + resource + '\")' 
                else:
                    raise RuntimeError('Unsupported http-method: \"' + method + '\"')
                                                    
            except OSError as e:
                    
                if e.errno == errno.ENOENT:
                    response = ''
                    statuscode = 404
                    statustext = 'Not Found'
                else:
                    if e.errno == 28:
                        # Not in error codes?
                        e = 'No space left on device'
                        
                    response = ''        
                    statuscode = 500
                    statustext = 'Internal Server Error (' + str(e) + ')'
                            
            except Exception as e:
                response = ''
                statuscode = 500
                statustext = 'Internal Server Error (' + str(e) + ')'
                
            finally:
                # At this point we have collected everything we need to produce the response to the client.

                # Determine content length. Either we have a string in response or we know we are about
                # to send a static file.
                if responsefilesize:
                    contentlength = str(responsefilesize)
                elif response:
                    contentlength = len(response)
                else:
                    contentlength = None

                # Print something resembling common log format.
                logger.write(addr[0] + ' ' + method + ' \"' + resource + (('?' + paramstr) if paramstr else '') + '\" ' + str(statuscode) + ' ' + statustext + ((' (' + str(contentlength) + ' bytes of ' + contenttype + ')') if contentlength else '')) 
                
                # Send http header with status.
                cl.sendall('HTTP/1.0 ' + str(statuscode) + ' ' + statustext)
                
                if contentlength:
                    cl.sendall('\r\nContent-Length: ' + str(contentlength) + '\r\nContent-Type: ' + contenttype)
                
                cl.sendall('\r\n\r\n')
                    
                # Send body.
                if method != 'HEAD': # HEAD: The server MUST NOT return a content-body
                    if responsefilesize:
                        # Open file and send it in chunks.
                        with open('/www/' + resource, 'rb') as f:
                            while True:
                                buf = f.read(2048)
                                if not buf:
                                    # No more bytes read. We are done.
                                    break
                                cl.sendall(buf)
                                
                    elif response:
                        # Just answer with the prepared content.
                        cl.sendall(response)
                
                cl.close()
                logger.write('Connection closed')
        else:
            cl.close()
            logger.write('Mutilated request')

    finally:
        _onboard.off()

    # End of handleHttp()

def syncNTP():
    global _nextNTPSync
    
    # We can only query the NTP server if we are a WIFI client (STA)
    # and a ntp host is _configured. Otherwise this is a NOP.
    if not (('STA' in _config) and ('ntpserver' in _config['STA'])):
        return

    logger.write('Syncing RTC with network time')
        
    '''
    At its most basic, the NTP protocol is a clock request transaction, where a client requests the current time from a server,
    passing its own time with the request. The server adds its time to the data packet and passes the packet back to the client.
    When the client receives the packet, the client can derive two essential pieces of information: the reference time at the
    server and the elapsed time, as measured by the local clock, for a signal to pass from the client to the server and back again.
    Repeated iterations of this procedure allow the local client to remove the effects of network jitter and thereby gain a
    stable value for the delay between the local clock and the reference clock standard at the server. This value can then be
    used to adjust the local clock so that it is synchronized with the server. Further iterations of this protocol exchange
    can allow the local client to continuously correct the local clock to address local clock skew.
    
    ...
    
    Nah, we'll just send an emtpy request and pick the time out of the respone. Fair?
    '''
    
    ntpserver = _config['STA']['ntpserver']
    
    NTP_DELTA = 2208988800
    
    request = bytearray(48)
    request[0] = 0x1B
    
    _onboard.on()
            
    addr = socket.getaddrinfo(ntpserver, 123)[0][-1]
    ntp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Send request and read response.
        ntp.sendto(request, addr)
        response = ntp.recv(48)
        
        # Decode response from packet and decompose into a time tuple.
        ntp_time = struct.unpack("!I", response[40:44])[0]        
        tm = time.gmtime(ntp_time - NTP_DELTA)
        
        # Update RTC
        rtc = machine.RTC()
        rtc.datetime((tm[0], tm[1], tm[2], tm[6] + 1, tm[3], tm[4], tm[5], 0))

        # Schedule the next sync in 24 hours.
        _nextNTPSync = time.ticks_add(time.ticks_ms(), 1000 * 60 * 60 * 24)
        
        logger.write('RTC synced with network time')
    
    except Exception as e:
        logger.write('Error requesting network time from ' + ntpserver + ' (' + str(e) + ')')
        
        # Schedule the next sync using the RTC alarm.
        _nextNTPSync = time.ticks_add(time.ticks_ms(), 1000 * 60)
        
    finally:
        _onboard.off()
        ntp.close()
    
def task():

    global _myip
    global _nextNTPSync
    
    logger.register_thread_name('NET ')
    watchdog.feed() # First feed to make us known to the WDT
    logger.write('Network task starting')
    _onboard.on()

    rp2.country('DE')
    
    if ('STA' in _config) and ('AP' in _config):
        fatalConnectionError(2, '_configuration error: Both STA and AP defined in _config')
    elif 'STA' in _config:
        logger.write('Setting up as STA (client)')
        wlan = network.WLAN(network.STA_IF)
    elif 'AP' in _config:
        logger.write('Setting up as AP (Access Point)')
        wlan = network.WLAN(network.AP_IF)
        #wlan._config(security = 3)
        #wlan._config(authmode = 3)
        wlan._config(essid = _config['AP']['essid'])
        if _config['AP']['pw']:
            wlan._config(password = _config['AP']['pw'])
    else:
        _onboard.off()
        logger.write('Neither STA nor AP defined in _config. Network is done.')
        return
        
    # wlan._config(hostname = 'doorsign')
    wlan.active(True)

    # logger.write(str(wlan.scan()))
        
    # Disable power-saving because this is a server
    wlan.config(pm = 0xa11140)

    logger.write('MAC = ' + ubinascii.hexlify(network.WLAN().config('mac'),':').decode())

    # Other things to query
    # logger.write(wlan.config('channel'))
    # logger.write(wlan.config('essid'))
    # logger.write(wlan.config('txpower'))

    if wlan.isconnected():
        logger.write('Disconnecting from stale connection')
        wlan.disconnect()
        timeout = 5
        while (timeout > 0) and (wlan.isconnected()):
            watchdog.feed()
            timeout -= 1
            time.sleep(1)
        
    if 'STA' in _config:
        logger.write('Connecting to: ' + _config['STA']['ssid'] + (' /w password' if _config['STA']['pw'] else ''))

        wlan.connect(_config['STA']['ssid'], _config['STA']['pw'])

        # Wait for connection with 10 second timeout
        timeout = 100
        while timeout > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            timeout -= 1
            logger.write('Waiting for connection...')
            time.sleep(1)
            watchdog.feed()
            
        _onboard.off()
            
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
            fatalConnectionError(4, 'Wi-Fi connection failed status = ' + str(wlan.status()))
        else:
            _onboard.off()
            logger.write('Connected')
            
            syncNTP()
            
    else:
        # Immediately ready as AP. Indicate by turning off _onboard-LED.
        _onboard.off()

    try:
        # Where am I?
        _myip = wlan.ifconfig()[0]
        logger.write('IP = ' + _myip)
        
        inputsockets = []
        
        http = None
        dns = None
        
        if 'AP' in _config:
            # Set up DNS server socket for captive portal.
            addr = socket.getaddrinfo('0.0.0.0', 53, 0, socket.SOCK_DGRAM)[0][-1]

            dns = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            dns.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            dns.setblocking(False)
        
            dns.bind(addr)
            
            inputsockets.append(dns)

            logger.write('DNS server listening on ' + str(addr))
            
        # Set up HTTP server socket.
        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]

        http = socket.socket()
        http.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        http.bind(addr)
        http.listen(1)

        inputsockets.append(http)

        logger.write('Http server listening on ' + str(addr))
        
        # Main loop: Wait for connections and service them.
        while True:
            watchdog.feed()

            if _nextNTPSync and (time.ticks_diff(_nextNTPSync, time.ticks_ms())) <= 0:
                syncNTP()
            
            readable, writeable, errored = select.select(inputsockets, [], [], 1)
            
            for s in readable:
                if (s is http):
                    handleHttp(s)
                elif (s is dns):
                    handleDNS(s)
                else:
                    raise RuntimeError('select() returned unknown readable socket')    
    finally:
        if wlan.isconnected():
            logger.write('Disconnecting')
            wlan.disconnect()
            timeout = 5
            while (timeout > 0) and (wlan.isconnected()):
                watchdog.feed()
                timeout -= 1
                time.sleep(1)
            
if __name__ == '__main__':

    logger.write('Running stand-alone task()')
    setup()
    task()
    logger.write('task() exited')
