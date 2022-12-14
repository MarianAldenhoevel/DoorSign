'''
A simplistic logging framework to replace print()-calls.

It associated thread-IDs with readable names and synchronizes print()s
'''

logfile_size = 10*1024 # Rotate after this many bytes.
logfile_count = 0 # Keep this many log files around. 0 to disable log to file.
logfolder = './log'

import os
import time
import _thread
import lock

_logger_lock = lock.RecursiveLock()
_thread_names = {}

_current_index = None
_current_filename = None

if logfile_count:
    # Creat the folder if it doesn't exist.
    try:
        os.mkdir(logfolder)
    except:
        pass

    # Find the first free logfile index 
    files = os.listdir()
    files = list(filter(lambda file: file.startswith('log.') and file.endswith('.txt'), os.listdir(logfolder)))
    if files:
        files.sort()
        _current_index = int(files[-1].split('.')[1])
    else:
        _current_index = 1
    _current_filename = logfolder+ '/log.' + str(_current_index) + '.txt'

'''
Associates a name with the current thread ID
'''
def register_thread_name(name):
    _logger_lock.acquire()
    try:
        if name:
            _thread_names[_thread.get_ident()] = name
        else:
            del _thread_names[_thread.get_ident()]
    finally:
        _logger_lock.release()

'''
If the thread has registered a nice ID use that
'''
def get_thread_id():
    if _thread.get_ident() in _thread_names:
        id = _thread_names[_thread.get_ident()]
    else:
        id = str(_thread.get_ident())
        
    return id

'''
Synchronized print() decorated with the timestamp and thread name/ID
'''
def write(msg):
    global _current_filename
    global _current_index

    _logger_lock.acquire()
    try:
        y, mo, d, h, mi, s, _, _ = time.gmtime()
        msg = '{:04d}.{:02d}.{:02d} {:02d}:{:02d}:{:02d} [{:s}] {:s}'.format(
            y, mo, d, h, mi, s,
            get_thread_id(),
            msg
        )
        
        print(msg)

        if logfile_count:
            try:
                # Append to current log file. 
                with open(_current_filename, 'a+') as f:
                    f.write(msg + '\n')
            
                size = os.stat(_current_filename)[6]
                if size >= logfile_size:
                    # Start next log file when we log again.
                    _current_index += 1
                    _current_filename = logfolder + '/log.' + str(_current_index) + '.txt'
            
                    # Cleanup old logs.
                    files = os.listdir()
                    files = list(filter(lambda file: file.startswith('log.') and file.endswith('.txt'), os.listdir(logfolder)))
                    files.sort()
                    while len(files) > logfile_count:
                        os.remove(logfolder + '/' + files.pop(0))
                    
            except Exception as e:
                # print(e) # Don't use the logger itself it doesn't feel too well.
                pass

    finally:
        _logger_lock.release()
        
if __name__ == '__main__':
    
    write('__main__: No code')
