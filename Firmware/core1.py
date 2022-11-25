import machine
import time
import logger
import doorsign
import random
import os

program_blend_ms = 5000
program_switch_interval_ms = 30000

def task():
    logger.write('NeoPixel task starting')
    
    #while True:
    #    logger.write('X')
    #    time.sleep(2)

    # Import all modules named "program_*"
    files = os.listdir()
    programfiles = filter(lambda file: file.startswith('program_') and file.endswith('.py'), files)
    modulenames = list(map(lambda file: file.split('.')[0], programfiles))
    programs = list(map(__import__, modulenames))        
    programs = list(filter(lambda program: program.enabled, programs))
    
    programcount = len(programs)
    if programcount == 0:
        logger.write('No programs available')
        return
    elif programcount > 1:
        logger.write("Available programs: " + ', '.join(program.__name__ for program in programs))
    
    new_programs = programs[:]
    old_programs = []
    
    active_program = None
    
    # Pick the first program to execute. We are guaranteed to have one because we returned if we didn't.
    active_program = random.choice(new_programs)
    new_programs.remove(active_program)
    old_programs.append(active_program)
    if len(new_programs) == 0:
        new_programs = old_programs
        old_programs = []
    active_program_start_ms = time.ticks_ms()
    
    if programcount > 1:
        logger.write('First program: ' + active_program.__name__)
    
    next_program = None

    while True:
        frame_ms = time.ticks_ms()
        
        if (active_program):
            active_pixels = active_program.update(frame_ms)
            
            if (next_program):
                next_pixels = next_program.update(frame_ms)
            
                # Blend between the two programs in interval milliseconds
                diff = time.ticks_diff(frame_ms, next_program_start_ms)
                blend = diff/program_blend_ms
                        
                if (blend >= 1.0):
                    # Finished blend. Swap programs.
                    active_program = next_program
                    active_program_start_ms = frame_ms
                    next_program = None
                    pixels = next_pixels
                else:
                    # Blend between the two programs.
                    pixels = doorsign.blendPixels(active_pixels, next_pixels, blend)
            else:
                # No next program scheduled at the moment
                pixels = active_pixels
                
                # Do we have a next program and want it now?
                if (programcount >= 2) and (time.ticks_diff(frame_ms, active_program_start_ms) >= program_switch_interval_ms):
                    # Pick a next program to execute.            
                    while True:
                        next_program = random.choice(new_programs)                        
                        new_programs.remove(next_program)
                        old_programs.append(next_program)    
                        if len(new_programs) == 0:
                            new_programs = old_programs
                            old_programs = []
                            
                        if next_program is not active_program:
                            break
                        
                    next_program_start_ms = frame_ms
                                        
                    logger.write('Next program: ' + next_program.__name__)
            
        else:
            # No program at all. All off.
            pixels = [[0, 0, 0]] * doorsign.neoPixelCount
            
        # Output the pixels if not under manual control
        if not doorsign.manual_control:
            doorsign.setNeoPixels(pixels)
        
        # Sleep for the remainder of the frame if any.
        now_ms = time.ticks_ms()
        used_ms = time.ticks_diff(now_ms, frame_ms)
        remaining_ms = doorsign.frameintervall_ms - used_ms
   
        if remaining_ms > 0:
            time.sleep_ms(remaining_ms)
   
if __name__ == "__main__":
    logger.write("Running stand-alone task()")
    task()
    logger.write("task() exited")