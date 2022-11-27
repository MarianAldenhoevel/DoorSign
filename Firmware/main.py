'''
Main code for the Doorsign project.

The top-level architecture uses two threads hopefully run on the two cores of the Raspberry Pi Pico.

core0, this main thread, is used to execute the network code.
core1, started from here, runs the pixel animation.

The code in this module does some simple initialization and then starts both threads.
'''

import os
import rp2
import time
import _thread
import core0
import core1
import logger
import doorsign
import watchdog

def Main():
    # Here we go!
    logger.write('Doorsign firmware 0.0')
    logger.write('<marian.aldenhoevel@marian-aldenhoevel.de>')
    logger.write('https://github.com/MarianAldenhoevel/DoorSign')
    
    # Turn on the onboard-LED to indicate we are on. The LED is later
    # controlled by the network thread.
    machine.Pin('LED', machine.Pin.OUT).on()

    # Turn off all neopixels in case the are left on from an old run.
    doorsign.off()

    logger.write('os.uname() = ' + str(os.uname()))

    # Report on what we think caused us to lose consciousness last.
    mrc = machine.reset_cause()
    if mrc == machine.PWRON_RESET:
        mrc = 'PWRON_RESET'
    #elif mrc == machine.HARD_RESET:
    #    mrc = 'HARD_RESET'
    elif mrc == machine.WDT_RESET:
        mrc = 'WDT_RESET'
    elif mrc == machine.DEEPSLEEP_RESET:
        mrc = 'DEEPSLEEP_RESET'
    elif mrc == machine.SOFT_RESET:
        mrc = 'SOFT_RESET'
    else:
        mrc = str(mrc)
    logger.write('Last reset cause was ' + mrc)

    # Wait a while to allow for a CTRL-C in case the code is broken
    # and cannot be stopped later.
    logger.write('Standing by for KeyboardInterrupt')
    for _ in range(40):
        time.sleep(0.1)

    logger.write('Starting up')

    # Give each task a chance to set up in a single threaded environment.
    core0.setup()
    core1.setup()

    # Enable hardware watchdog timer.
    #watchdog.enable()

    # Start both threads.
    _thread.start_new_thread(core1.task, ()) # NO braces after core1.task, we are passing the function...
    core0.task()

    # We really don't expect to get here.
    logger.write('Exited')

    # Need to keep the animation task alive even if the network task ends.  
    while True:
        time.sleep(0.1)

if __name__ == '__main__':
    Main()