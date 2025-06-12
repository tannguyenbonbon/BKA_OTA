import usys
import utime
import ujson
import _thread

from usr.lib.umqtt              import MQTTClient
from usr.modules.logging        import getLogger
from usr.working_mode           import SettingWorkingMode
from usr.settings               import Settings

log = getLogger(__name__)

class MqttTopic:
    TELEMETRY          = 'v1/devices/me/telemetry'
    ATTRIBUTE          = 'v1/devices/me/attributes'
    ATTRIBUTE_RESPONSE = 'v1/devices/me/attributes/response/'
    ATTRIBUTE_REQUEST  = 'v1/devices/me/attributes/request/'
    RPC_RESPONSE       = 'v1/devices/me/rpc/response/'
    RPC_REQUEST        = 'v1/devices/me/rpc/request/'

class TBDeviceMQTTClient:
    def __init__(self):
        self.__settings     = Settings()
        self.__server_cfg   = self.__settings.read("server")

        self.__host         = self.__server_cfg.get("host")
        self.__port         = self.__server_cfg.get("port")
        self.__username     = self.__server_cfg.get("username")
        self.__password     = self.__server_cfg.get("password")
        self.__qos          = self.__server_cfg.get("qos")
        self.__client_id    = self.__server_cfg.get("client_id")

        self.__mqtt         = None
        self.__thread_id    = None
        self.__status       = False

        self.__callback       = print
        self.__error_callback = print
        
        self.__attrb_request_id = 0

        self.__working_mode = SettingWorkingMode()

    
    def __get_username(self):
        self.__server_cfg = self.__settings.read("server")
        _username = self.__server_cfg.get('username', None)
        _retry = 0
        while _username is None and _retry < 10:
            log.debug("Username not found in server config, retrying:{}/{}".format(_retry + 1, 10))
            self.__settings.reload()
            self.__server_cfg = self.__settings.read("server")
            _username = self.__server_cfg.get('username', None)
            _retry += 1 
            utime.sleep(1)
        if _username is None:
            _username = "default_backup_tracker"
        return _username

    def __wait_msg(self):
        """This function is in a thread to wait server downlink message."""
        while True:
            try:
                if self.__mqtt:
                    self.__mqtt.wait_msg()
            except Exception as e:
                usys.print_exception(e)
                log.error(e)
            finally:
                utime.sleep_ms(100)

    def __start_wait_msg(self):
        """Start a thread to wait server message and save this thread id."""
        # If this method is called in a thread, it is necessary to ensure that the thread stack created is >= 16K. For details, please refer to the mqtt reconnection sample code.
        _thread.stack_size(0x4000) # 16K Stack Size
        self.__thread_id = _thread.start_new_thread(self.__wait_msg, ())

    def __stop_wait_msg(self):
        """Stop the thread for waiting server message."""
        if self.__thread_id is not None:
            _thread.stop_thread(self.__thread_id)
            self.__thread_id = None

    @property
    def status(self):
        # return self.__status
        state = self.__mqtt.get_mqttsta() if self.__mqtt else -1
        # log.debug("mqtt state: %s" % state)
        return True if state == 0 else False

    def set_callback(self, callback):
        if callable(callback):
            self.__callback = callback
            return True
        return False

    def set_error_callback(self, callback):
        if callable(callback):
            self.__error_callback = callback
            return True
        return False

    def connect(self, clean_session=False):
        try:
            self.__username = self.__get_username()
            log.info("Connecting to Thingsboard with token: %s" % self.__username)
            self.__mqtt = MQTTClient(self.__client_id, self.__host, self.__port, self.__username, self.__password, keepalive=120, reconn=True)
            self.__mqtt.set_callback(self.__callback)
            self.__mqtt.error_register_cb(self.__error_callback)

            if self.__mqtt.connect(clean_session=clean_session) == 0:
                self.__status = True
                self.__mqtt.subscribe(MqttTopic.RPC_REQUEST + "+", self.__qos)
                self.__mqtt.subscribe(MqttTopic.ATTRIBUTE_RESPONSE + "+", self.__qos)
                self.__mqtt.subscribe(topic=MqttTopic.ATTRIBUTE, qos=self.__qos)
                self.__start_wait_msg()
                log.debug("Connected to {}".format(self.__host))
                return True
        except Exception as e:
            usys.print_exception(e)
            log.error(str(e))
        return False

    def disconnect(self):
        try:
            if self.__mqtt:
                self.__mqtt.disconnect()
                # self.__mqtt = None
                self.__stop_wait_msg()
                log.debug("MQTT Disconnect")
            return True
        except Exception as e:
            usys.print_exception(e)
            log.error(str(e))
        finally:
            self.__status = False
        return False
    
    def reconnect(self):
        try:
            if self.__mqtt:
                self.__mqtt.disconnect()
                self.__mqtt.connect()
            return True
        except Exception as e:
            usys.print_exception(e)
            log.error(str(e))
        finally:
            self.__status = False
        return False

    def close(self):
        try:
            if self.__mqtt:
                self.__mqtt.close()
                # log.debug("close")
            return True
        except Exception as e:
            usys.print_exception(e)
            log.error(str(e))
        finally:
            self.__mqtt = None
        return False

    def send_telemetry(self, data):
        try:
            self.__mqtt.publish(MqttTopic.TELEMETRY, ujson.dumps(data), qos=self.__qos)
            return True
        except Exception as e:
            usys.print_exception(e)
            log.error(str(e))
        return False

    def send_rpc_reply(self, data, request_id):
        try:
            self.__mqtt.publish(MqttTopic.RPC_RESPONSE + request_id, ujson.dumps(data), qos=self.__qos)
            return True
        except Exception as e:
            usys.print_exception(e)
        return False
    
    def send_shared_attributes_request(self, *keys):
        topic = MqttTopic.ATTRIBUTE_REQUEST + str(self.__attrb_request_id)
        joined_keys = ",".join(keys)
        payload = ujson.dumps({"sharedKeys": joined_keys})

        try:
            self.__mqtt.publish(topic, payload, qos=1)
            self.__attrb_request_id += 1
            return True
        except Exception as e:
            usys.print_exception(e)
            return False
        
    def process_shared_attributes_rsp(self, data):
        _data = ujson.loads(data)

        if isinstance(_data, dict):
            shared_attribute = _data.get("shared", None)
        else:
            shared_attribute = None
            log.debug("Not a shared attributes")
            return None
        
        log.debug("Got Shared Attribute: {}".format(shared_attribute))

        if isinstance(shared_attribute, dict):
            _working_mode_value = shared_attribute.get("working_mode_attrb", None)

            _targetFWVer = shared_attribute.get("targetFwVer", None)
            _targetFWUrl = shared_attribute.get("targetFwUrl", None)

        if _working_mode_value:
            self.__working_mode.update_new_working_mode(_working_mode_value)
        elif _targetFWVer and _targetFWUrl:
            from usr.app_fota import AppFOTA # type: ignore
            self.__app_fota = AppFOTA()
            self.__app_fota.start_app_fota(_targetFWVer, _targetFWUrl)


THINGSBOARD_SERVER = TBDeviceMQTTClient()