from machine import UART, Timer
from usr.modules.common import Condition
class TimerContext(object):
    """基于machine.Timer的定时器实现(ONE_SHOT模式)。支持上下文管理器协议。"""
    __timer = Timer(Timer.Timer1)

    def __init__(self, timeout, callback):
        self.timeout = timeout  # ms; >0 will start a one shot timer, <=0 do nothing.
        self.timer_cb = callback  # callback after timeout.

    def __enter__(self):
        if self.timeout > 0:
            self.__timer.start(period=self.timeout, mode=Timer.ONE_SHOT, callback=self.timer_cb)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.timeout > 0:
            self.__timer.stop()


class Serial(object):
    """串口通信"""

    def __init__(self, port=2, baudrate=115200, bytesize=8, parity=0, stopbits=1, flowctl=0):
        port = getattr(UART, 'UART{}'.format(port))
        self.__uart = UART(port, baudrate, bytesize, parity, stopbits, flowctl)
        self.__uart.set_callback(self.__uart_cb)
        self.__cond = Condition()

    def __uart_cb(self, args):
        self.__cond.notify(info=False)

    def __timer_cb(self, args):
        self.__cond.notify(info=True)

    def write(self, data):
        self.__uart.write(data)

    def read(self, size, timeout=0):
        """
        read from uart port with block or noblock mode.
        :param size: int, N bytes you want to read. if read enough bytes, return immediately.
        :param timeout: int(ms). =0 for no blocking, <0 for block forever, >0 for block until timeout.
        :return: bytes actually read.
        """
        if timeout == 0:
            return self.__uart.read(size)

        r_data = b''
        with TimerContext(timeout, self.__timer_cb):
            while len(r_data) < size:
                raw = self.__uart.read(1)
                if not raw:
                    if self.__cond.wait():
                        break
                else:
                    r_data += raw
        return r_data
