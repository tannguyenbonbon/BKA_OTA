import uos
import ql_fs
import modem
import _thread
import usys as sys
from misc import Power
from usr.modules.logging import getLogger

log = getLogger(__name__)

class WorkingModeConfig:

    # loc_gps_read_timeout, work_cycle_watchdog, work_cycle_period, work_mode_timeline(=work_cycle_period + work_cycle_watchdog)
    WORKING_MODE_PARAMS = [
        #MODE 1 - 1 Data Point Every 5 mins  (2 mins timeout if GPS not fixed)
        #GPS Timeout: 2 mins | Watchdog: 3 mins | Cycle: 5 mins | Timeline: 8 mins
        [120, 180, 300, 480],
        #MODE 2 - 1 Data Point Every 15 mins (3 mins timeout if GPS not fixed)
        # GPS Timeout: 3 mins | Watchdog: 4 mins | Cycle: 15 mins | Timeline: 24 mins         
        [180, 240, 900, 1140],
        #MODE 3 - 1 Data Point Every 30 mins (5 mins timeout if GPS not fixed)
        # GPS Timeout: 5 mins | Watchdog: 6 mins | Cycle: 30 mins | Timeline: 50 mins
        [300, 360, 1800, 2160],
        #MODE 4 - 1 DATA POINT EVERY 1 HOUR  (10 mins timeout if GPS not fixed)
        # GPS Timeout: 10 mins | Watchdog: 15 mins | Cycle: 1 hour | Timeline: 1 hour 50 mins
        [600, 660, 3600, 4260],
        #MODE 5 - 1 DATA POINT EVERY 6 HOURS (30 mins timeout if GPS not fixed)
        # GPS Timeout: 30 mins | Watchdog: 60 mins | Cycle: 6 hours | Timeline: 7 hours 30 mins    
        [1800, 1860, 21600, 23460],
        #MODE 6 - 1 DATA POINT EVERY 24 HOURS (30 mins timeout if GPS not fixed)
        # GPS Timeout: 30 mins | Watchdog: 60 mins | Cycle: 24 hours | Timeline: 25 hours
        [1800, 1860, 86400, 88260],
        #MODE 7 - Real-Time 
        [300, 1800, 300, 21540],
    ]

    def __init__(self):
        self.loc_gps_read_timeout   = 0
        self.work_cycle_watchdog    = 0
        self.work_cycle_period      = 0
        self.work_mode_timeline     = 0

    def set_config(self, mode):
        cfg = self.WORKING_MODE_PARAMS[mode - 1]
        self.loc_gps_read_timeout, self.work_cycle_watchdog, self.work_cycle_period, self.work_mode_timeline = cfg
    
    def get_config(self):
        return {
            "loc_gps_read_timeout"  : self.loc_gps_read_timeout,
            "work_cycle_watchdog"   : self.work_cycle_watchdog,
            "work_cycle_period"     : self.work_cycle_period,
            "work_mode_timeline"    : self.work_mode_timeline,
        }
class SettingWorkingMode(WorkingModeConfig):

    WORKING_MODE_KEY = "Working_Mode"

    def __init__(self, config_file="/usr/working_mode_config.json"):
        super().__init__()

        self.__file = config_file
        self.__lock = _thread.allocate_lock()
        self.__data = {}

        self.default_mode = 1

        self.__init_config()

        current_mode = self.get_current_mode
        log.debug("Current Working Mode: {}\n".format(current_mode))

        #Check Mode is valid
        if type(current_mode) is not (int):
            log.error("Current Working Mode is not an integer ! Using default: Mode {}".format(self.default_mode))
            current_mode = self.default_mode

        if not (1 <= current_mode <= len(self.WORKING_MODE_PARAMS)):
            log.debug("WARNING: Mode {} Invalid ! Using default: Mode {}".format(current_mode, self.default_mode))
            current_mode = self.default_mode

            #Save default mode
            res = self.save({self.WORKING_MODE_KEY : current_mode})
            if res == False:
                log.debug("Write default mode failed !\n")\

        #Set Config
        self.set_config(current_mode)

    def __init_config(self):
        try:
            if not ql_fs.path_exists(self.__file):
                self.__data[self.WORKING_MODE_KEY] = self.default_mode
                ql_fs.touch(self.__file, self.__data)
            else:
                self.__data = ql_fs.read_json(self.__file)
        except Exception as e:
            sys.print_exception(e)

    def read(self, key=None):
        with self.__lock:
            res = -1
            try:
                return self.__data if key is None else self.__data.get(key)
            except Exception as e:
                sys.print_exception(e)

    def save(self, data):
        with self.__lock:
            res = -1
            if isinstance(data, dict):
                self.__data.update(data)
                res = ql_fs.touch(self.__file, self.__data)
            return True if res == 0 else False
        
    def update_new_working_mode(self, value):
        device_mode = self.get_current_mode
        attrb_mode = value

        if type(attrb_mode) is not (int):
            log.error("Shared Attribute Working Mode is not an integer")
            return
        
        if not (1 <= attrb_mode <= len(self.WORKING_MODE_PARAMS)):
            log.error("Shared Attribute Working Mode {} Invalid !".format(attrb_mode))
            return

        log.debug("Current Mode: {} | Shared Attribute Mode: {}".format(device_mode, attrb_mode))

        if device_mode == attrb_mode:
            log.debug("No need to change working mode")
        else:
            log.debug("New working mode found, process to update new working mode")
            res = self.save({self.WORKING_MODE_KEY : attrb_mode})
            if res == True:
                log.debug("New working mode (Mode {}) save success. Device will be reset to apply config".format(attrb_mode))
                Power.powerRestart()

    @property
    def get_current_mode(self):
        return self.read(self.WORKING_MODE_KEY)
