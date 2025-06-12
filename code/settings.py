import uos
import ql_fs
import modem
import _thread
import usys as sys

try:
    from usr.dev_settings_server import AliIotConfig, ThingsBoardConfig
except ImportError:
    from usr.settings_server import AliIotConfig, ThingsBoardConfig
try:
    from usr.dev_settings_loc import LocConfig
except ImportError:
    from usr.settings_loc import LocConfig
from usr.settings_user import UserConfig

PROJECT_NAME = "QuecPython-Tracker"

PROJECT_VERSION = "1.3.3"

FIRMWARE_NAME = uos.uname()[0].split("=")[1]

FIRMWARE_VERSION = modem.getDevFwVersion()

class Settings:

    def __init__(self, config_file="/usr/tracker_config.json"):
        self.__file = config_file
        self.__lock = _thread.allocate_lock()
        self.__data = {}
        self.__init_config()

    def __init_config(self):
        try:
            if not ql_fs.path_exists(self.__file):
                # UserConfig init
                self.__data["user"] = {k: v for k, v in UserConfig.__dict__.items() if not k.startswith("_")}
                self.__data["user"]["ota_status"]["sys_current_version"] = FIRMWARE_VERSION
                self.__data["user"]["ota_status"]["app_current_version"] = PROJECT_VERSION

                # CloudConfig init
                self.__data["server"] = {}
                if self.__data["user"]["server"] == UserConfig._server.AliIot:
                    self.__data["server"] = {k: v for k, v in AliIotConfig.__dict__.items() if not k.startswith("_")}
                elif self.__data["user"]["server"] == UserConfig._server.ThingsBoard:
                    self.__data["server"] = {k: v for k, v in ThingsBoardConfig.__dict__.items() if not k.startswith("_")}

                # LocConfig init
                self.__data["loc"] = {k: v for k, v in LocConfig.__dict__.items() if not k.startswith("_")}
                
                # Save config
                ql_fs.touch(self.__file, self.__data)
            else:
                self.__data = ql_fs.read_json(self.__file)
        except Exception as e:
            sys.print_exception(e)

    def reload(self):
        with self.__lock:
            try:
                self.__data = ql_fs.read_json(self.__file)
                return True
            except Exception as e:
                sys.print_exception(e)
                return False

    def read(self, key=None):
        with self.__lock:
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