'''
A simplistic logging framework to replace print()-calls.

It associated thread-IDs with readable names and synchronizes print()s
'''
 
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
        loger_lock.release()

'''
Synchronized print() decorated with the thread name/ID
'''
def write(msg):
    logger_lock.acquire()
    try:
        # If the thread has registered a nice name use that.
        if _thread.get_ident() in thread_names:
            id = thread_names[_thread.get_ident()]
        else:
            id = str(_thread.get_ident())

        print('[' + id + '] ' + msg)
    finally:
        logger_lock.release()
        
if __name__ == '__main__':
    logger.write('__main__: No code')
