'''
A simplistic logging framework to replace print()-calls.

It associated thread-IDs with readable names and synchronizes print()s
'''

import time
import _thread

logger_lock = _thread.allocate_lock()

thread_names = {}

'''
Associates a name with the current thread ID
'''
def register_thread_name(name):
    logger_lock.acquire()
    try:
        if name:
            thread_names[_thread.get_ident()] = name
        else:
            del thread_names[_thread.get_ident()]
    finally:
        logger_lock.release()

'''
If the thread has registered a nice ID use that
'''
def get_thread_id():
    if _thread.get_ident() in thread_names:
        id = thread_names[_thread.get_ident()]
    else:
        id = str(_thread.get_ident())
        
    return id

'''
Synchronized print() decorated with the timestamp and thread name/ID
'''
def write(msg):
    logger_lock.acquire()
    try:
        y, mo, d, h, mi, s, _, _ = time.gmtime()
        print('{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d} [{:s}] {:s}'.format(
              y, mo, d, h, mi, s,
              get_thread_id(),
              msg
        ))
    finally:
        logger_lock.release()
        
if __name__ == '__main__':
    
    write('__main__: No code')

