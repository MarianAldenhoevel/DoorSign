'''
Encapsulates the machines watchdog timer.

We are running two threads and want watchdog-feeds from both. So we need one extra
level of indirection.

The hardware WDT is not enabled by default for debugging. But if our code detects
it *should* have fired we will log a message.

Configure the interval this software implementation uses. Set this solidly between the
expected heartbeat frequency, maximum of both tasks, and the interval of the hardware WDT
timer (see enable_wdt(), there are hardware limits) to avoid spurious activations.
'''

watchdog_interval_ms = 5000 
 
import machine
import _thread
import time
import logger
import lock

wdt = None
wdt_simulated_reset_occured = False
wdt_lock = lock.RecursiveLock()
        
thread_feed_ms = {}
    
def enable():
    global wdt
    
    logger.write('Enabling hardware watchdog timer')
    wdt = machine.WDT(0, 8000)
    
'''
Process a feed from one thread.
'''
def feed():
    global wdt
    global wdt_simulated_reset_occured

    wdt_lock.acquire()
    try:
        # Record ticks for the calling thread.
        thread_feed_ms[logger.get_thread_id()] = time.ticks_ms()
        
        # Now check the heartbeats of all threads and only feed
        # the watchdog if they are all fresh enough.
        for tf in thread_feed_ms.items():            
            age = time.ticks_diff(time.ticks_ms(), tf[1])
            # logger.write(str(tf) + ', ' + str(age) + ', ' + str(age>watchdog_interval_ms))
            if age > watchdog_interval_ms:
                # This one is too old. Report simulated timeout.
                if not wdt_simulated_reset_occured:
                    logger.write('Watchdog timeout on [' + tf[0] + ']')
                    wdt_simulated_reset_occured = True
                
                # Return, so don't feed the hardware WDT.
                return
            
        # If hardware WDT is enabled then feed it.
        if wdt:
            wdt.feed()
    
    finally:
        wdt_lock.release()
                           
if __name__ == '__main__':

    logger.write('__main__: No code')
