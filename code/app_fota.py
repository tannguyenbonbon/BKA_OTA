import app_fota
import utime
import sys
import ql_fs

from misc                    import Power
from usr.settings            import Settings
from usr.modules.logging     import getLogger

from usr.modules.thingsboard import THINGSBOARD_SERVER as server

log = getLogger(__name__)

class OTAState:
    OTA_IDLE        = 0
    OTA_START       = 1
    OTA_DOWNLOADING = 2
    OTA_UPDATING    = 3
    OTA_FAILED      = 4
    OTA_DONE        = 5

class AppFOTA(OTAState):
    def __init__(self):
        self.__updater_path = "/usr/.updater"
        self.__fota         = app_fota.new()
        self.__settings     = Settings()

    def save_new_version(self, targetFWVer):
        usr_cfg = self.__settings.read("user")
        data = usr_cfg["ota_status"]
        data["app_current_version"] = targetFWVer
        
        ret = self.__settings.save(data)
        if ret != True:
            log.error("Failed to save new version to config file")
        return ret
    
    def cleanup_updater(self):
        if ql_fs.path_exists(self.__updater_path):
            log.info("Found .updater folder left over, cleaning up folder")
            try:
                ql_fs.rmdirs(self.__updater_path)
            except Exception as e:
                log.error(e)
        else:
            log.info("No need to cleanup .updater")
        
    def push_ota_status(self, ota_status):
        ota_st = {"ota_status": ota_status}
        res = server.send_telemetry(ota_st)
        if res != True:
            log.error("Failed to send OTA status to Thingsboard. Error code:", res)

    def push_failed_reason(self, failure_code, failure_detail, url=None):
        if not url:
            fail_reason = {
                "ota_failure_code": failure_code,
                "ota_failure_detail": failure_detail
            }
        else:
            result = ', '.join([item['file_name'] for item in url])
            fail_reason = {
                "ota_failure_code": failure_code,
                "ota_failure_detail": failure_detail,
                "file_failed": result
            }
        res = server.send_telemetry(fail_reason)
        if res != True:
            log.error("Failed to send OTA failed reason")

    def is_valid_url(self, url):
        log.info("Validating URL: {}".format(url))
        if url.startswith("http://") or url.startswith("https://"):
            return True
        else:
            log.error("Invalid URL format")
            return False

    def get_filename(self, url):
        filename = url.split("/")[-1]
        return filename
        
    def get_path_from_url(self, url):
        path = ""
        if url:
            filename = self.get_filename(url)
            if "modules" in url:
                path = "/usr/modules/{}".format(filename)
            else:
                path = "/usr/{}".format(filename)
        return path
    
    def process_mul_files_fota(self, targetFWUrl, targetFWVer):
        log.info("Multiple files FOTA")
        urls = targetFWUrl.split(",")
        urls = [url.strip() for url in urls]
        url_count = len(urls)
        log.info("Number of files detected: {}".format(url_count))

        download_list = []
        filename = local_path = ""
        err = res = None

        for url in urls:
            if self.is_valid_url(url):
                local_path = self.get_path_from_url(url)
                download_list.append({'url':url ,'file_name':local_path})

        if len(download_list) > 0:
            self.push_ota_status(OTAState.OTA_DOWNLOADING)
            utime.sleep(1)
            try:
                res = self.__fota.bulk_download(download_list)
            except Exception as e:
                err = e
                log.error(str(err))
            if not res and not err:
                log.info("Files downloaded successfully. Starting update...")
                try:
                    self.__fota.set_update_flag()
                except Exception as e:
                    err = e
                    log.error(str(e))
                
                self.push_ota_status(OTAState.OTA_UPDATING)
                utime.sleep(1)
                if not err:
                    self.push_ota_status(OTAState.OTA_DONE)
                    utime.sleep(1)
                    self.save_new_version(targetFWVer)
                else:
                    self.push_ota_status(OTAState.OTA_FAILED)
                    utime.sleep(1)
                    self.push_failed_reason(str(err), "set_update_flag() failed!")
                    log.error("Set update flag failed!")
                log.info("Restarting system...")
                Power.powerRestart()
            else:
                log.error("Failed to download files. Error files: {}".format(res))
                self.push_ota_status(OTAState.OTA_FAILED)
                utime.sleep(1)
                self.push_failed_reason(str(err), "File download failed", res)
                utime.sleep(1)
                self.cleanup_updater()
                return
        else:
            log.error("No valid URLs found in the list.")
            self.push_ota_status(OTAState.OTA_FAILED)
            utime.sleep(1)
            self.push_failed_reason(str(err), "No valid URLs")
            return

    def process_single_file_fota(self, targetFWUrl, targetFWVer):
        log.info("Single file FOTA")
        url = targetFWUrl.strip()
        err = res = 0

        if self.is_valid_url(url):               
            self.push_ota_status(OTAState.OTA_DOWNLOADING)
            log.info("URL is valid, starting download...")
            local_path = self.get_path_from_url(url)
            try:
                res = self.__fota.download(url=url, file_name=local_path)
            except Exception as e:
                log.error(str(e))

            if not res and not err:
                log.info("File downloaded successfully. Starting update")
                try:
                    self.__fota.set_update_flag()
                except Exception as e:
                    err = e
                    log.error(str(e))
                self.push_ota_status(OTAState.OTA_UPDATING)
                utime.sleep(1)
                if not err:
                    self.push_ota_status(OTAState.OTA_DONE)
                    utime.sleep(1)
                    self.save_new_version(targetFWVer)
                else:
                    self.push_ota_status(OTAState.OTA_FAILED)
                    utime.sleep(1)
                    self.push_failed_reason(str(err), "set_update_flag() failed!")
                    log.error("Set update flag failed!")
                log.info("Restarting system...")
                Power.powerRestart()
            else:
                log.error("Failed to download file. Error code:", res)
                self.push_ota_status(OTAState.OTA_FAILED)
                utime.sleep(1)
                self.push_failed_reason(str(err), "File download failed")
                utime.sleep(1)
                self.cleanup_updater()
                return
        else:
            log.error("Invalid URLs")
            self.push_ota_status(OTAState.OTA_FAILED)
            utime.sleep(1)
            self.push_failed_reason(str(err), "Invalid URLs")
            return

    def process_target_url(self, targetFWUrl, targetFWVer):
        number_of_file = targetFWUrl.count(",")

        if number_of_file > 0:
            self.process_mul_files_fota(targetFWUrl, targetFWVer)
        else:
            self.process_single_file_fota(targetFWUrl, targetFWVer)
            

    def start_app_fota(self, targetFWVer, targetFWUrl):
        usr_cfg = self.__settings.read("user")["ota_status"]
        app_current_version = usr_cfg["app_current_version"]
        log.info("Current app version: {} - Target app version: {}".format(app_current_version, targetFWVer))

        if app_current_version != targetFWVer:
            log.info("OTA START")
            self.push_ota_status(OTAState.OTA_START)
            utime.sleep(1)
            self.process_target_url(targetFWUrl, targetFWVer)
        else:
            log.warning("App version is the same. No need to update.")
            return
