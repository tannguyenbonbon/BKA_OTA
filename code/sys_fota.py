import fota
import utime
import log
import ql_fs
import request

URL1 = "https://raw.githubusercontent.com/tannguyenbonbon/OTA/main/dfota_1.bin"
URL2 = "https://raw.githubusercontent.com/tannguyenbonbon/OTA/main/dfota_2.bin"

log.basicConfig(level=log.INFO)
fota_log = log.getLogger("Fota")

class SysFOTA:
    def __init__(self):
        self.__fota = fota()    # Creates a FOTA object

    def result(self, args):
        print('download status:',args[0],'download process:',args[1])

    def run(self):
        fota_log.info("Start downloading file....")
        # Methods of mini FOTA
        res = self.__fota.httpDownload(url1=URL1,url2=URL2)
        if res != 0:
            fota_log.error("httpDownload error")
            return
        fota_log.info("wait httpDownload update...")
        utime.sleep(2)