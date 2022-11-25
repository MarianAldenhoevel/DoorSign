import rp2
import _thread
import core0
import core1
import logger
import time
import doorsign

# Here we go!
logger.write("Doorsign firmware 0.0")
logger.write("2022 marian.aldenhoevel@marian-aldenhoevel.de")
logger.write("https://github.com/MarianAldenhoevel/DoorSign")

doorsign.off()

logger.write('Standing by for KeyboardInterrupt')
for _ in range(40):
    time.sleep(0.1)

logger.write("Starting up")

# Global setup.
rp2.country('DE')

# Start both threads.
_thread.start_new_thread(core1.task, ())
core0.task()

# We really don't want to get here.
logger.write("Exited")
