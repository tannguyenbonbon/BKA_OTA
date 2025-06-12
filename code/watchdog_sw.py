import _thread
import usys as sys
import utime as time
from machine import Pin
from misc import Power
from usr.modules.logging import getLogger

log = getLogger(__name__)

class WatchDog:
    def __init__(self, max_count):
        self.__max_count = max_count
        self.__count = self.__max_count
        self.__tid = None

    def bark(self):
        log.debug("SW Watchdog timer was triggered !")
        Power.powerRestart()

    def feed(self):
        self.__count = self.__max_count

    def __check(self):
        while True:
            if self.__count == 0:
                self.bark()
            else:
                self.__count = (self.__count - 1)
            time.sleep(10)

    def start(self):
        log.debug("start")
        if not self.__tid or (self.__tid and not _thread.threadIsRunning(self.__tid)):
            try:
                _thread.stack_size(0x1000)
                self.__tid = _thread.start_new_thread(self.__check, ())

            except Exception as e:
                sys.print_exception(e)
                log.error(str(e))

    def stop(self):
        if self.__tid:
            try:
                _thread.stop_thread(self.__tid)
                log.debug("stop")
            except:
                pass
        self.__tid = None