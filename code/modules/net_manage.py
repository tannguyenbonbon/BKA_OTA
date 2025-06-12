import sys
import net
import sim
import ntptime
import osTimer
import _thread
import dataCall
import checkNet
import utime as time
import modem

from misc                       import Power
from usr.modules.logging        import getLogger
from usr.settings               import Settings
from usr.provision              import InitProvision

log = getLogger(__name__)

class ApnConfig:
    def __init__(self):
        self.__settings = Settings()

    def __read_apn_config(self, ret_dict):
        self.__settings.reload()
        self.usr_cfg = self.__settings.read("user")
        self.usr_apn_cfg = self.usr_cfg.get("apn")
        if ret_dict:
            return self.usr_apn_cfg
        return self.usr_apn_cfg["apn"]

    def apn(self, ret_dict=False):
        return self.__read_apn_config(ret_dict)
    
    def __save_apn_config(self, key, value):
        usr_config = self.__settings.read("user")

        if "apn" not in usr_config or not isinstance(usr_config["apn"], dict):
            usr_config["apn"] = {}
        usr_config["apn"][key] = value

        ret = self.__settings.save({"user": usr_config})
        if ret == False:
            log.error("Fail to save {{}}:{{}} to file".format(key, value))
        return ret
    
    def update_new_apn(self, apn):
        log.debug("Updating APN configuration: %s" % apn)
        _old_apn = self.apn(ret_dict=True)
        _new_apn = apn

        ret1 = ret2 = ret3 = True
        
        print("Current APN: %s, New APN: %s" % (_old_apn, _new_apn))
        if type(_new_apn) is not dict:
            log.error("Invalid APN format. Expected a Dict, got %s." % type(_new_apn))
            return False
        
        #* Process APN data
        _old_apn_apn = _old_apn.get("apn", None)
        _new_apn_apn = _new_apn.get("apn", None)
        if (_old_apn_apn == _new_apn_apn) or (not _old_apn_apn or not _new_apn_apn):
            log.error("APN Invalid!")
            return False
        
        ret1 = self.__save_apn_config(key='apn', value=_new_apn_apn)
        if ret1 == True:
            log.info("New APN-APN save successfully")

        #* Process username and password
        _old_apn_usrname = _old_apn.get("username", None)
        _new_apn_usrname = _new_apn.get("username", None)

        if (_old_apn_usrname == _new_apn_usrname):
            log.warning("APN-Username is the same, no need to change")
        else:
            ret2 = self.__save_apn_config(key='username', value=_new_apn_usrname)
            if ret2 == True:
                log.info("New APN-Username save successfully")

        _old_apn_pw = _old_apn.get("password", None)
        _new_apn_pw = _new_apn.get("password", None)

        if (_old_apn_pw == _new_apn_pw):
            log.warning("APN-Password is the same, no need to change")
        else:
            ret3 = self.__save_apn_config(key='password', value=_new_apn_pw)
            if ret3 == True:
                log.info("New APN-Password save successfully")

        ret = ret1 and ret2 and ret3

        if ret == True:
            print("apn: {}\nusername: {}\npassword:{}\n".format(_new_apn_apn, _new_apn_usrname, _new_apn_pw))
            ret = dataCall.setPDPContext(profileID=1, ipType=0, apn=_new_apn_apn, username=_new_apn_usrname, password=_new_apn_pw, authType=0)
            if ret == 0:
                log.info("setPDPContext successfully!")

        return ret

class NetManager(ApnConfig):
    def __init__(self):
        super().__init__()
        self.__conn_flag = 0
        self.__disconn_flag = 0
        self.__disconn_flag_by_user = 0
        self.__reconn_flag = 0
        self.__callback = None
        self.__net_check_timer = osTimer()
        self.__net_check_cycle = 2 * 60 * 1000
        self.__reconn_tid = None
        self.__apn = self.apn(ret_dict=True)
        dataCall.setCallback(self.__net_callback)
        self.check_apn()

    '''
        dataCall.setCallback(fun)
        Parameter：

        fun - The name of the callback function. The format and parameters of the callback function is described as follows:
        Registers a callback function. When the network status changes, such as when the network is disconnected or the reconnection is successful, this callback function will be triggered to inform the user of the network status.
        args[0]	Integer	PDP context ID, indicating which PDP network state has changed
        args[1]	Integer	Network status. 0 means the network is disconnected and 1 means the network is connected
    '''
    def __net_callback(self, args):
        log.debug("profile id[%s], net state[%s], last args[%s]" % args)
        try:
            if args[1] == 0: # Network disconnected
                if self.__disconn_flag_by_user == 0:
                    log.debug("Unexpected network disconnect.. Attempting reconnection...")
                    self.__net_check_timer.stop()

                    self.net_check(None)
                    self.__net_check_timer.start(self.__net_check_cycle, 1, self.net_check)
                else:
                    log.debug("Network explicitly disconnected by user.")
                    self.__net_check_timer.delete_timer()
            elif args[1] == 1:  # Network connected
                log.debug("Network connected.")
        except Exception as e:
            sys.print_exception(e)
            log.error(str(e))

        # Call the user-defined callback if it's set
        if callable(self.__callback):
            self.__callback(args)

    def set_callback(self, callback):
        if callable(callback):
            self.__callback = callback
            return True
        return False

    def net_connect(self):
        res = -1
        if self.__conn_flag != 0:
            # Connection is already in progress or established
            return -2

        self.__conn_flag = 1

        try:
            # Reconnect net.
            if net.getModemFun() != 1:
                _res = self.net_disconnect()
                log.debug("net.getModemFun() != 1 net_connect net_disconnect %s" % _res)
                time.sleep(5)
                # Retry setting the modem function to '1'
                retries = 0
                max_retries = 3
                while retries < max_retries:
                    _res = net.setModemFun(1)
                    log.debug("Attempt %d: net.setModemFun(1) returned %d" % ((retries + 1), _res))
                    if _res == 0:
                        break
                    retries += 1
                    time.sleep(3)
                if _res != 0:
                    log.error("Failed to enable modem function after retries.")
                    return -3

            # Check sim status
            # _res = self.sim_status()
            # if _res != 1:
            #     log.error("SIM card is not ready. %d" % _res)
            #     return -4

            # Wait net connect.
            '''
                This method checks the SIM card status, module network registration status, and PDP context activation status in order.
                If PDP context activation is detected successfully within the specified timeout period, it will return a result immediately.
                Otherwise, it will continue waiting until the timeout is reached.
            '''
            stage, state = checkNet.waitNetworkReady(300)
            # log.debug("checkNet.waitNetworkReady %s" % str(_res))
            if stage == 3 and state == 1:
                log.info('Network connection successful')
                InitProvision().start_provisioning()  # Start provisioning after successful connection
                res = 0  # Success
            else:
                log.error("Network did not become ready. Status: %d" %(_res))
                res = -5
        except Exception as e:
            sys.print_exception(e)
            log.error(str(e))
            res = -6  # Indicating an unexpected exception
        finally:
            # Reset connection flag regardless of success or failure
            self.__conn_flag = 0

            # Restart the periodic network check timer
            self.__net_check_timer.stop()
            self.__net_check_timer.start(self.__net_check_cycle, 1, self.net_check)
        return res

    def net_disconnect(self, by_user=False):
        if self.__disconn_flag != 0:
            return False

        self.__disconn_flag = 1
        self.__disconn_flag_by_user = by_user
        self.__net_check_timer.stop()

        max_retries = 5  # Maximum number of retries
        retry_count = 0  # Retry counter
        success = False  # Flag to track success

        # Loop to attempt disconnecting up to max_retries times
        while retry_count < max_retries:
            # Try disabling modem (setModemFun(0))
            log.debug("Attempting to disable modem (setModemFun(0)) - attempt %d" % (retry_count + 1))
            res = net.setModemFun(0)

            if res != 0:  # If the first attempt fails, reset modem function (setModemFun(4))
                log.debug("setModemFun(0) failed with result %d, attempting to reset modem (setModemFun(4))" % (res))
                res = net.setModemFun(4)

            # Log the final result of the attempt
            if res == 0:
                success = True
                log.debug("Successfully disconnected on attempt %d." % (retry_count + 1))
                break  # Exit loop if successful
            else:
                retry_count += 1
                log.debug("Attempt %d failed. Retrying..." % (retry_count))

        # After loop, check if it was successful
        if not success:
            log.error("Failed to disconnect after %d attempts." % (max_retries))

        # Reset the disconnection flag
        self.__disconn_flag = 0

        # Optionally restart the network check timer on failure
        # if not success:
        #     log.debug("Restarting network check timer after failure.")
        #     self.__net_check_timer.start(self.__net_check_cycle, 1, self.net_check)

        return success

    def net_reconnect(self):
        log.debug("net_reconnect")
        if self.__reconn_flag != 0:
            return False
        self.__reconn_flag = 1
        res = self.net_connect() if self.net_disconnect() else False
        self.__reconn_flag = 0
        self.__reconn_tid = None
        return res

    def net_status(self):
        return True if self.sim_status() == 1 and self.net_state() and self.call_state() else False

    def net_state(self):
        try:
            _net_state_ = net.getState()
            # log.debug("net.getState() %s" % str(_net_state_))
            return True if isinstance(_net_state_, tuple) and len(_net_state_) >= 2 and _net_state_[1][0] in (1, 5) else False
        except Exception as e:
            sys.print_exception(e)
            log.error(str(e))
        return False

    def net_config(self, state=None):
        if state is None:
            return net.getConfig()
        elif state in (0, 5, 6):
            return (net.setConfig(state) == 0)
        return False

    def net_mode(self):
        _net_mode_ = net.getNetMode()
        if _net_mode_ == -1 or not isinstance(_net_mode_, tuple) or len(_net_mode_) < 4:
            return -1
        if _net_mode_[3] in (0, 1, 3):
            return 2
        elif _net_mode_[3] in (2, 4, 5, 6, 8):
            return 3
        elif _net_mode_[3] in (7, 9):
            return 4
        return -1

    def net_check(self, args):
        if not self.net_status():
            try:
                if not self.__reconn_tid or (self.__reconn_tid and not _thread.threadIsRunning(self.__reconn_tid)):
                    _thread.stack_size(0x2000)
                    self.__reconn_tid = _thread.start_new_thread(self.net_reconnect, ())
            except Exception as e:
                sys.print_exception(e)
                log.error(str(e))

    def call_state(self):
        try:
            call_info = self.call_info()
            # log.debug("dataCall.getInfo %s" % str(call_info))
            return True if isinstance(call_info, tuple) and len(call_info) >= 3 and call_info[2][0] == 1 else False
        except Exception as e:
            sys.print_exception(e)
            log.error(str(e))
        return False

    def call_info(self):
        return dataCall.getInfo(1, 0)

    def sim_status(self):
        # # Check net modem.
        # if net.getModemFun() == 0:
        #     net.setModemFun(1)
        
        # Check sim status.
        '''
            Return Value
            Integer type. SIM card status codes, as described in details below.
            -1	API execution exception.
            0	The SIM card does not exist/has been removed.
            1	The SIM card is ready.
            2	The SIM card has been blocked and waiting for CHV1 password.
            3	The SIM card has been blocked and needs to be unblocked with CHV1 password.
            4	The SIM card has been blocked due to failed SIM/USIM personalized check.
            5	The SIM card is blocked due to an incorrect PCK. An MEP unblocking password is required.
            6	Expecting key for hidden phone book entries
            7	Expecting code to unblock the hidden key
            8	The SIM card has been blocked and waiting for CHV2 password.
            9	The SIM card has been blocked and needs to be unblocked with CHV2 password.
            10	The SIM card has been blocked due to failed network personalization check.
            11	The SIM card is blocked due to an incorrect NCK. An MEP unblocking password is required.
            12	The SIM card has been blocked due to failed personalization check of network lock.
            13	The SIM card is blocked due to an incorrect NSCK. An MEP unblocking password is required.
            14	The SIM card has been blocked due to failed personalization check of the service provider.
            15	The SIM card is blocked due to an incorrect SPCK. An MEP unblocking password is required.
            16	The SIM card has been blocked due to failed enterprise personalization check.
            17	The SIM card is blocked due to an incorrect CCK. An MEP unblocking password is required.
            18	The SIM card is being initialized and waiting for completion.
            19	The SIM card is blocked for the following six reasons.
            1) Use of CHV1 is blocked.
            2) Use of CHV2 is blocked.
            3) Use of the universal PIN is blocked.
            4) Use of code to unblock the CHV1 is blocked.
            5) Use of code to unblock the CHV2 is blocked.
            6) Use of code to unblock the universal PIN is blocked.
            20	The SIM card is invalid.
            21	Unknown status.
        '''
        count = 0
        while sim.getStatus() == -1 and count < 3:
            time.sleep_ms(100)
            count += 1
        return sim.getStatus()
    
    @property
    def modem_imei(self):
        return modem.getDevImei()

    @property
    def sim_imsi(self):
        return sim.getImsi()

    @property
    def sim_iccid(self):
        return sim.getIccid()
    
    @property
    def sim_phoneNumber(self):
        return sim.getPhoneNumber()

    @property
    def sim_signal_csq(self):
        return net.csqQueryPoll()
    
    @property
    def sim_operator(self):
        return net.operatorName()
    
    @property
    def current_apn(self):
        return self.__apn

    def sync_time(self, timezone=7):
        """Sync device time from server.

        Args:
            timezone (int): timezone. range: [-12, 12] (default: `7`)

        Returns:
            bool: True - success, False - failed.
        """
        return (self.net_status() and timezone in range(-12, 13) and ntptime.settime(timezone) == 0)

    def check_apn(self):
        _res = self.sim_status()
        if _res != 1:
            log.error("SIM card is not ready. %d" % _res)
            return False

        # Configure the APN information according to your actual needs
        # Get the APN information of the first cellular NIC and check if the current one is the one you specified
        pdpCtx = dataCall.getPDPContext(1)
        if pdpCtx != -1:
            if (pdpCtx[1] != self.__apn['apn']) and (pdpCtx[1] != 'v-internet'):
                # If it is not the APN you need, configure it as follows
                ret = dataCall.setPDPContext(profileID=1, ipType=0, apn=self.__apn['apn'], username=self.__apn['username'], password=self.__apn['password'], authType=0)
                if ret == 0:
                    log.debug('APN configuration successful. Ready to restart to make APN take effect.')
                    log.debug('Please re-execute this program after restarting. curr: %s | new: %s' % (pdpCtx[1] ,self.__apn['apn']))
                    ret = self.__save_apn_config(key='apn', value=self.__apn['apn'])
                    Power.powerRestart()
                else:
                    log.debug('APN configuration failed.')
                    return False
            else:
                log.debug('The APN %s is correct and no configuration is required' % pdpCtx[1])
                return True
        else:
            log.debug('Failed to get PDP Context.')
            return False