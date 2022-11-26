'''
This module implements the animation task.

It loads all modules named animation_*.py found in the current folder and checks their enabled-value. If
enabled the animation is added to a pool of available animations.

If there aren't any enabled animations the task ends. Otherwise one is selected at random as the active
animation.

If there are two or more animations enabled the task will after a while select a next animation from
the pool and blend between the two.

Care is taken that all enabled animations are used and never back-to-back.
'''

animation_switch_interval_ms = 30000 # Time in ms before animations are switched-
animation_blend_ms = 5000 # Blend time between animations.

import machine
import time
import logger
import doorsign
import random
import os

def task():

    register_thread_name('ANIM')
    logger.write('Animation task starting')
    
    # Import all modules named animation_*.py:
    # List files, filter by name, strip off the .py extension, load as module and finally filter by their enabled variable.
    animationfiles = filter(lambda file: file.startswith('animation_') and file.endswith('.py'), os.listdir())
    modulenames = list(map(lambda file: file.split('.')[0], animationfiles))
    animations = list(map(__import__, modulenames))        
    animations = list(filter(lambda animation: animation.enabled, animations))
    
    animationcount = len(animations)
    if animationcount == 0:
        logger.write('No animations available')
        return
    elif animationcount > 1:
        logger.write('Available animations: ' + ', '.join(animation.__name__ for animation in animations))
    
    # Initialize two arrays. new_animations holds the animation modules that can be picked, the other
    # holds the ones that have already been run to implement draw without put back.
    new_animations = animations[:]
    old_animations = []
    
    # Randomly pick the first animation to execute. We are guaranteed to have one 
    # because we returned if we didn't.
    active_animation = random.choice(new_animations)
    new_animations.remove(active_animation)
    old_animations.append(active_animation)
    if len(new_animations) == 0:
        new_animations = old_animations
        old_animations = []
    active_animation_start_ms = time.ticks_ms()
    
    if animationcount > 1:
        logger.write('First animation: ' + active_animation.__name__)
    
    next_animation = None

    '''
    Main loop
    '''
    while True:
        frame_ms = time.ticks_ms()
        
        if (active_animation):
            # Get the pixels for the active animation.
            active_pixels = active_animation.update(frame_ms)
            
            # Are we running a next animation?
            if (next_animation):
                # Yes. Get their pixels.
                next_pixels = next_animation.update(frame_ms)
            
                # Blend between the two animations in interval milliseconds
                diff = time.ticks_diff(frame_ms, next_animation_start_ms)
                blend = diff/animation_blend_ms
                        
                if (blend >= 1.0):
                    # Finished blend. Swap animations, we will only be running the next
                    # animation as active now.
                    active_animation = next_animation
                    active_animation_start_ms = frame_ms
                    next_animation = None

                    # Use the pixels of the next animation directly.
                    pixels = next_pixels
                else:
                    # Blend between the two animations' pixel arrays.
                    pixels = doorsign.blendPixels(active_pixels, next_pixels, blend)
            else:
                # No next animation scheduled at the moment. The pixels for the active animation
                # get used directly.
                pixels = active_pixels
                
                # Do we have a next animation in our portfolio and do we want it now?
                if (animationcount >= 2) and (time.ticks_diff(frame_ms, active_animation_start_ms) >= animation_switch_interval_ms):
                    # Pick a next animation to execute. Brutally sample until we do not 
                    # get the same as the active one.           
                    while True:
                        next_animation = random.choice(new_animations)                                                
                        if next_animation is not active_animation:
                            break

                    new_animations.remove(next_animation)
                    old_animations.append(next_animation)    
                    if len(new_animations) == 0:
                        new_animations = old_animations
                        old_animations = []
                    next_animation_start_ms = frame_ms
                                                                
                    logger.write('Next animation: ' + next_animation.__name__)
            
        else:
            # No animation at all. All off.
            pixels = [[0, 0, 0]] * doorsign.pixelCount
            
        # Output the pixels only if currently not under manual control. Animation
        # keeps running.
        if not doorsign.manual_control:
            doorsign.setPixels(pixels)
        
        # Sleep for the remainder of the frame if any.
        now_ms = time.ticks_ms()
        used_ms = time.ticks_diff(now_ms, frame_ms)
        remaining_ms = doorsign.frame_intervall_ms - used_ms
   
        if remaining_ms > 0:
            time.sleep_ms(remaining_ms)
   
if __name__ == '__main__':
    
    logger.write('Running stand-alone task()')
    task()
    logger.write('task() exited')