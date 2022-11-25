import time
import doorsign
import logger

def sample(updateFunc):
    start_ms = time.ticks_ms()
    
    while True:
        frame_ms = time.ticks_ms()
        pixels = updateFunc(frame_ms)        
        # print(str(frame_ms) + ' ' + doorsign.formatPixels(pixels))
        doorsign.setPixels(pixels)
        
        now_ms = time.ticks_ms()
        used_ms = time.ticks_diff(now_ms, frame_ms)
        remaining_ms = doorsign.frame_intervall_ms - used_ms
   
        time.sleep_ms(remaining_ms)
   
if __name__ == "__main__":
    logger.write("__main__: No code")
    