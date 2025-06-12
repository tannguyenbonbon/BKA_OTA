import utime as time
from misc import Power
from machine import Timer
from usr.modules.logging import getLogger

log = getLogger(__name__)

class WatchDogTimer:
    def __init__(self):
        self.timer1 = Timer(Timer.Timer1)

    def __bark(self, args):
        log.debug("HW Watchdog timer was triggered !")
        Power.powerRestart()

    def start(self, expired_time):
        self.__Expiration = expired_time
        ret = -1
        ret = self.timer1.start(period=self.__Expiration * 1000, mode=self.timer1.ONE_SHOT, callback=self.__bark)
        return ret
    
    def stop(self):
        ret = -1
        ret = self.timer1.stop()
        return ret
    
    def reset(self, expired_time):
        ret = -1
        ret = self.stop()
        ret = self.start(expired_time)
        return ret



