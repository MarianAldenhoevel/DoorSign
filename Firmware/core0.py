'''
This implements the network task.

Sets up WiFi as STA (Client) or AP (Access point) as configured in config.json

If set up as AP also runs a DNS server to implement a captive portal. The implementation
of that is right here and trivial.

Then it starts a primitive web server also implemented here. The web server supports
delivery of static resources and API endpoints all hardcoded.

The network task controls the onboard LED. When setting up the LED is on, when setup
is completed sucessfully it turns off. If an error is encountered connecting in STA mode
a code is blinked. 

In operation the LED turns on while network requests are being serviced.
'''

import rp2
import machine
import network
import ubinascii
import time
import socket
import select
import ujson
import logger
import doorsign
import watchdog

onboard = machine.Pin('LED', machine.Pin.OUT)
myip = None
config = None

def setup():
    global config
    
    # Load configuration
    logger.write('Reading config.json')
    with open('config.json') as fp:
        config = ujson.load(fp)
    
'''
When the task fails to make a connection it blinks an error code on the
onboard LED
'''
def fatalConnectionError(code, message):
    onboard.off()
    logger.write('FATAL: ' + str(code) + ' - ' + message)
    
    time.sleep(1)
    for _ in range(code):
        onboard.on()
        time.sleep(0.5)
        onboard.off()
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
        onboard.on()

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
        response += bytes(map(int, myIP.split('.'))) 	# IP address parts
        
        # And deliver it.
        socket.sendto(response, client)

    except Exception as e:
        logger.write('Error handling DNS request ' + str(e))

    finally:
        onboard.off()

'''
This function implements the complete handling of a http request.
''' 
def handleHttp(socket):
    onboard.on()
    try:
        cl, addr = socket.accept()    
        logger.write('Client connected from '+ str(addr))
        
        request = str(cl.recv(1024)) # Only read this much data. We don't care if they send any more.
        # print(request)
    
        # Minimal sanity-check.
        if len(request) > 6:
            statuscode = 0
            statustext = ''
            method = ''
            resource = ''
            response = ''
            
            try:        
                # Extract method and the resource requested from the request. 
                method = request[2:request.find(' ')]
                request = request[len(method) + 3:]
                
                resource = request[1:request.find(' ')]
                request = request[len(resource) + 3:]
                
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
                if (resource == ''):
                    resource = 'index.html'
            
                # Determine content-type by file extension.
                ext = resource[resource.find('.'):]
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
        
                # This server either serves static resource on GET requests OR
                # answers with (minimal) dynamic content to POST requests.

                if (method == 'GET') or (method == 'HEAD'):        
                    # Load the resource.
                    logger.fs_lock.acquire()
                    try:
                        with open('/www/' + resource, 'rb') as file:
                            response = file.read()
                    finally:
                        logger.fs_lock.release()
                    
                    statuscode = 200
                    statustext = 'OK'
            
                elif method == 'POST':
                    
                    if resource == 'set':
                        # Disable animation on the pixels. And indicate beginning of an update.
                        doorsign.setManualControl(True)
                        doorsign.beginUpdate()
                        try:                    
                            for pixelIndex in range(doorsign.pixelCount):                                
                                pixel = (
                                    int(params.get('r' + str(pixelIndex), 0)),
                                    int(params.get('g' + str(pixelIndex), 0)),
                                    int(params.get('b' + str(pixelIndex), 0)),
                                )
                                print(pixel)
                                doorsign.setPixel(pixelIndex, pixel)
                        finally:
                            # End pixel update phase. This will send the data out to the LEDs.
                            doorsign.endUpdate()                    

                        # No interesting response. Just keep AJAXers happy.    
                        response = '{}'
                        contenttype = 'application/json'
            
                        statuscode = 200
                        statustext = 'OK'            
                    else:
                        # Unsupported endpoint
                        statuscode = 404
                        statustext = 'Not Found (Endpoint \"' + resource + '\")' 
                else:
                    raise RuntimeError('Unsupported http-method: \"' + method + '\"')
                                                    
            except OSError as e:
                    
                if e.errno == errno.ENOENT:
                    response = ''
                    statuscode = 404
                    statustext = 'Not Found'
                else:
                    response = ''        
                    statuscode = 500
                    statustext = 'Internal Server Error (' + str(e) + ')'
                            
            except BaseException as e:
                response = ''
                statuscode = 500
                statustext = 'Internal Server Error (' + str(e) + ')'
                    
            finally:
                logger.write(addr[0] + ' ' + method + ' \"' + resource + (('?' + paramstr) if paramstr else '') + '\" ' + str(statuscode) + ' ' + statustext + ((' (' + str(len(response)) + ' bytes of ' + contenttype + ')') if response else '')) 
                cl.sendall('HTTP/1.0 ' + str(statuscode) + ' ' + statustext)
                
                if response:
                    cl.sendall('\r\nContent-Length: ' + str(len(response)) + '\r\nContent-Type: ' + contenttype + '\r\n')
                
                cl.sendall('\r\n')
                    
                if response and (method != 'HEAD'): # HEAD: The server MUST NOT return a content-body
                    cl.sendall(response)
                
                cl.close()
                logger.write('Connection closed')
        else:
            cl.close()
            logger.write('Mutilated request')

    finally:
        onboard.off()

    # End of handleHttp()

def task():

    global myIP
    
    logger.register_thread_name('NET')
    watchdog.feed() # First feed to make us known to the WDT
    logger.write('Network task starting')
    onboard.on()

    rp2.country('DE')

    if ('STA' in config) and ('AP' in config):
        fatalConnectionError(2, 'Configuration error: Both STA and AP defined in config')
    elif 'STA' in config:
        logger.write('Setting up as STA (client)')
        wlan = network.WLAN(network.STA_IF)
    elif 'AP' in config:
        logger.write('Setting up as AP (Access Point)')
        wlan = network.WLAN(network.AP_IF)
        wlan.config(
                essid = config['AP']['essid'],
                password = config['AP']['pw']
        )
    else:
        onboard.off()
        logger.write('Neither STA nor AP defined in config. Network is done.')
        return
        
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
        time.sleep(2)
        watchdog.feed()
    
    if 'STA' in config:
        logger.write('Connecting to: ' + config['STA']['ssid'] + (' /w password' if config['STA']['pw'] else ''))

        wlan.connect(config['STA']['ssid'], config['STA']['pw'])

        # Wait for connection with 10 second timeout
        timeout = 100
        while timeout > 0:
            if wlan.status() < 0 or wlan.status() >= 3:
                break
            timeout -= 1
            logger.write('Waiting for connection...')
            time.sleep(1)
            watchdog.feed()
            
        onboard.off()
            
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
            onboard.off()
            logger.write('Connected')
            
    else:
        # Immediately ready as AP. Indicate by turning off onboard-LED.
        onboard.off()

    try:
        # Where am I?
        myIP = wlan.ifconfig()[0]
        logger.write('IP = ' + myIP)
        
        inputsockets = []
        
        http = None
        dns = None
        
        if 'AP' in config:
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
            
            # "http://worldtimeapi.org/api/timezone/Etc/UTC"
            
            watchdog.feed()
            
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
            time.sleep(2)

if __name__ == '__main__':

    logger.write('Running stand-alone task()')
    setup()
    task()
    logger.write('task() exited')