import uos          # type: ignore
import request      # type: ignore
import ujson        # type: ignore
import modem        # type: ignore
import utime        # type: ignore

from usr.settings           import Settings                         # type: ignore
from usr.modules.logging    import getLogger                        # type: ignore
from usr.settings_server    import ThingsBoardConfig                # type: ignore

log = getLogger(__name__)

class Prefix:
    def __init__(self):
        self.product_code   = "BBA"
        self.hardware_ver   = "2"
        self.region_code    = "00"

        self.prefix = self.product_code + self.hardware_ver + self.region_code

class Provision(Prefix):
    def __init__(self, provision_config, username=None):
        super().__init__()

        self.__settings              = Settings()
        self.__provision_config      = provision_config
        self.__cfg_username          = username

        self.__device_id             = None

        self.__device_name           = self.__provision_config['deviceName']
        self.__credentialsType       = self.__provision_config['credentialsType']
        self.__provisionDeviceKey    = self.__provision_config['provisionDeviceKey']
        self.__provisionDeviceSecret = self.__provision_config['provisionDeviceSecret']

        if self.__cfg_username is not None:
            self.__device_token = self.__cfg_username
        else:
            self.__device_token = self.__provision_config['token']

    def __save_provision_config(self, key, value):
        usr_cfg = self.__settings.read("user")
        data = usr_cfg["provision"]
        data[key] = value
        ret = self.__settings.save(data)
        if ret == False:
            log.error("Failed to save provision config {{\"{}\" : {}}}.".format(key, value))
        return ret
    
    def __save_server_config(self, key, value):
        data = self.__settings.read("server")
        # log.debug("Server config before: {}".format(data))
        data[key] = value
        ret = self.__settings.save(data)
        # if ret == True:
        #     log.debug("Provision config {{\"{}\" : {}}} saved successfully.".format(key, value))
        # else:
        #     log.error("Failed to save server config {{\"{}\" : {}}}.".format(key, value))
        data = self.__settings.read("server")
        # log.debug("Server config after: {}".format(data))
        return ret

    def __get_device_id(self):
        _device_id = modem.getDevImei()
        _last_5_digits = _device_id[-5:]
        return _last_5_digits
    
    def __generate_device_name(self):
        _device_name = None
        self.__device_id = self.__get_device_id()
        _device_name = self.prefix + self.__device_id
        return _device_name if _device_name else None
    
    def __generate_device_token(self):
        _device_token = None
        try:
            url = "https://thingsboard.bonboncar.vn/api/v1/provision"
            headers = {"Content-Type" : "application/json"}
            data = {
                "deviceName"            : self.__device_name,
                "provisionDeviceKey"    : self.__provisionDeviceKey,
                "provisionDeviceSecret" : self.__provisionDeviceSecret,
                "credentialsType"       : self.__credentialsType,
                # "token"                 : self.__device_token
            }
            response = request.post(url=url, data=ujson.dumps(data), headers=headers, timeout=10)
            if response.status_code == 200:
                _response_data_dict = response.json()
                _response_status = _response_data_dict.get('status')
                if _response_status == 'SUCCESS':
                    _response_credentialsValue = _response_data_dict.get('credentialsValue')
                    if _response_credentialsValue:
                        _device_token = _response_credentialsValue
                else:
                    _errorMsg = _response_data_dict.get('errorMsg')
                    log.error("Failed to generate device token, error msg: {}".format(_errorMsg))
                    log.info("Maybe device already created on server, check and try again")
            else:
                log.error("Failed to generate device token, response status code: {}".format(response.status_code))
        except Exception as e:
            log.error("Exception occurred while generating device token: {}".format(e))

        return _device_token

    def process_provisioning(self):
        ret = True
        if self.__device_token is None:
            #* First check if device name is exists
            if self.__device_name is None:
                log.info("Device name is None, generating new device name.")
                try:
                    self.__device_name = self.__generate_device_name()
                except Exception as e:
                    log.error("Exception occurred while generating device name: {}".format(e))
                    self.__device_name = None

                # Make sure that device name is generated
                if self.__device_name is not None:
                    log.info("Device name generated successfully: {{{}}}".format(self.__device_name))              
                    ret = self.__save_provision_config("deviceName", self.__device_name)
                else:
                    log.error("Failed to generate device name, using default device name.")
                    self.__device_name = "BBA-ERROR"
            else:
                log.info("Found Device Name: {{{}}}".format(self.__device_name))

            #* Proceed to generate device token
            log.info("Device token is None, generating new device token.")

            try:
                self.__device_token = self.__generate_device_token()
            except Exception as e:
                log.error("Exception occurred while generating device token: {}".format(e))
                self.__device_token = None

            # Make sure that device token is generated
            if self.__device_token is not None:
                log.info("Device token generated successfully: {{{}}}".format(str(self.__device_token)))     
                ret1 = self.__save_provision_config("token", self.__device_token)
                ret2 = self.__save_server_config("username", self.__device_token)
                if ret1 == False or ret2 == False:
                    log.error("Failed to save device token or username, token: {} - username: {}".format(self.__device_token, self.__device_token))
                    ret = False
        else:
            log.info("Found Device Token: {{{}}}".format(str(self.__device_token)))
            return ret
        return ret
    
class InitProvision:
    def __init__(self):
        self._settings = Settings()
        self._provision_config = self._settings.read("user")
        self.__username = self.get_usrername_from_config()

    def get_usrername_from_config(self):
        _settings = Settings()
        _server_cfg = _settings.read("server")
        _username = _server_cfg.get("username")
        return _username
    
    def start_provisioning(self):
        Provision(self._provision_config["provision"], self.__username).process_provisioning()
