'''
This module implements a recursive lock that can be reacquired by the owning
thread any number of times but will lock out other threads.

See __main__ for usage.
'''

import _thread
import time
import random

class RecursiveLock:
    
    # Constructor
    def __init__(self):
        self._synclock1 = _thread.allocate_lock()
        self._synclock2 = _thread.allocate_lock()
        
        self._lock = _thread.allocate_lock()
        
        # Keep track of the thread that currently holds the lock, if any.
        # If unlocked this is set to None.
        self._lockingthread = None
        
        self._lockcount = 0
        
    # Acquire lock. This will block only if another thread is holding the
    # lock. The same thread may aqcuire the lock any number of times.
    def acquire(self):
        self._synclock1.acquire()
        # I think we're alone now...
        # It is safe to read and write the internal state.
        
        # Attention. Synclock1 is not simply released at the end, but in
        # a ratchet-fashion with synclock2.        
        if self._lockingthread == _thread.get_ident():
            # The actual lock is ours anyway. Just increment the 
            # lock count.
            self._lockcount += 1
            self._synclock1.release()
        else:
            # Some other thread MAY be holding the actual lock. Tricky.
            #
            # We need to release the _synclock before we (potentially)
            # start waiting for the actual lock otherwise the other thread can
            # never relase that actual lock.
            #
            # But we need to also make sure that we are not switched out while
            # we do so. For thos we use synclock2 to protect this section
            # exclusively.
            self._synclock2.acquire()
            try:
                # Release synclock1. This allows the owning thread
                # to eventually release the actual lock...
                self._synclock1.release()
                
                # ..so we can aqcuire it here. This will block if another thread
                # is holding the lock. But because we have released synclock1 if
                # they want to release the actual lock they can and we can go on
                # here.
                self._lock.acquire()
                
                # ..we still have synclock2. So we still are alone here and and can
                # update internal state to note it is ours.
                self._lockingthread = _thread.get_ident()
                self._lockcount = 1
            finally:
                self._synclock2.release()

    # Release the lock. This will only release the underlying lock object when the
    # number of calls to require matches the calls to acquire.
    def release(self):
        self._synclock1.acquire()
        try:
            # I think we're alone now...
            
            assert self._lockingthread == _thread.get_ident()
            assert self._lockcount > 0
            
            self._lockcount -= 1
            
            # If we are down to zero remove us from the internal state and then
            # release the actual lock.
            if self._lockcount == 0:
                self._lockingthread = None
                self._lock.release()
        finally:
            self._synclock1.release()

    # Synonym for acquire()
    def lock(self):
        acquire(self)

    # Synonym for release()
    def unlock(self):
        release(self)

    # Returns True if the lock is held by anyone, False if not. 
    def locked(self):
        self._synclock1.acquire()
        try:
            return bool(self._lockingthread)
        finally:
            self._synclock1.release()

    # Returns True if the lock is held by the calling thread, False if not.
    def mine(self):
        self._synclock1.acquire()
        try:
            return self._lockingthread == _thread.get_ident()
        finally:
            self._synclock1.release()

    # Returns the current level/count of locks. Only safe if called by the
    # locking thread.
    def count(self):
        assert self.mine()
        return self._lockcount

    # Creates a human-readable string representation of the current state of the Lock object.
    def __str__(self):
        self._synclock1.acquire()
        try:
            # I think we're alone now...
            
            if not self._lockingthread:
                return 'unlocked'
            else:
                return 'locked by [' + str(self._lockingthread) + '] ' + ('(myself) ' if self._lockingthread == _thread.get_ident() else '') + 'count=' + str(self._lockcount)
            
        finally:
            self._synclock1.release()

    # For usage as context manager.
    def __enter__(self):
        self.acquire()
        return self
    
    # For usage as context manager.
    def __exit__(self, type, value, traceback):
        self.release()
    
    
def unit_tests():
    print('Trivial test:')
    
    def show(lo):
        print(lo)
        print('locked=', lo.locked())
        print('mine=  ', lo.mine())
        
    
    l = RecursiveLock()
    show(l)
    
    l.acquire()
    show(l)
    
    l.acquire()
    show(l)
    
    l.release()
    show(l)
    
    l.release()
    show(l)
    
    print()
    print('Use as context manager')
    with RecursiveLock() as ll:
        show(ll)
    
    print()
    print('More interesting tests:')
    
    s = _thread.allocate_lock()
    def syncprint(msg):
        s.acquire()
        try:
            print(msg)
        finally:
            s.release()
    
    def task0():
        for i in range(10):
            syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))                
            with l:
                with l:
                    syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))
                    with l:
                        syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))
                
    def task1():
        for i in range(10):
            syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))
            with l:
                syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))
                with l:
                    syncprint('[' + str(_thread.get_ident()) + '] - ' + str(i) + ' - ' + str(l))
                           
    _thread.start_new_thread(task1, ()) # NO braces after core1.task, we are passing the function...
    task0()
    
    # Wait for task1 to end before actually returning.
    for _ in range(5):
        time.sleep(1)
    
if __name__ == '__main__':
    
    unit_tests()
    print('Exited')