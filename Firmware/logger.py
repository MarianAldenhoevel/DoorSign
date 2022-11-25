import _thread

logger_lock = _thread.allocate_lock()

def write(msg):
    logger_lock.acquire()
    try:
        print('[' + str(_thread.get_ident()) + '] ' + msg)
    finally:
        logger_lock.release()
        
if __name__ == "__main__":
    logger.write("__main__: No code")
