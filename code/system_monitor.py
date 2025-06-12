import gc
import utime
import _thread
import uos

class SystemMonitor:

    def __init__(self):
        pass
        # info = uos.uname()
        # info_dict = {}
        # for item in info:
        #     if "=" in item:
        #         key, value = item.split("=", 1)
        #         info_dict[key] = value

        # print("Model:", info_dict.get("sysname"))
        # print("Release:", info_dict.get("release"))
        # print("Version:", info_dict.get("version"))
        # print("QPY Version:", info_dict.get("qpyver"))

    def __monitoring(self, RAM, ROM):
        while True:
            #*==================== STORAGE INFORMATION ====================
            if ROM == True:
                usr = uos.statvfs("/usr")
                usr_free_bytes = usr[0] * usr[3]

                bak = uos.statvfs("/bak")
                bak_free_bytes = bak[0] * bak[3]

                print("==================== STORAGE INFORMATION ====================")
                print('Get status information of the /usr directory:', usr)
                print("File system block size in bytes  (f_bsize): {}".format(usr[0]))
                print('Number of available blocks       (f_bfree): {}'.format(usr[3]))
                print('Total usr remaining: {} bytes ({:.2f} KB - {:.4f} MB) in /usr\n'.format(usr_free_bytes, usr_free_bytes / 1024, (usr_free_bytes / 1024) / 1024))

                print('Get status information of the /bak directory:', bak)
                print("File system block size in bytes  (f_bsize): {}".format(bak[0]))
                print('Number of available blocks       (f_bfree): {}'.format(bak[3]))
                print('Total bak remaining: {} bytes ({:.2f} KB - {:.4f} MB) in /bak\n'.format(bak_free_bytes, bak_free_bytes / 1024, (bak_free_bytes / 1024) / 1024))

            #*==================== MEMORY INFORMATION ====================
            if RAM == True:
                gc.collect()

                free_bytes  = gc.mem_free()
                used_bytes  = gc.mem_alloc()
                total_bytes = free_bytes + used_bytes

                free_kb  = free_bytes  / 1024
                used_kb  = used_bytes  / 1024
                total_kb = total_bytes / 1024

                print("==================== MEMORY INFORMATION ====================")
                print("RAM Available    : {:.2f} KB ({} bytes)".format(free_kb, free_bytes))
                print("RAM Used         : {:.2f} KB ({} bytes)".format(used_kb, used_bytes))
                print("Total RAM        : {:.2f} KB ({} bytes)\n".format(total_kb, total_bytes))
            
            utime.sleep(1)

    def start_monitor(self, RAM=True, ROM=True):
        _thread.stack_size(0x4000)
        _thread.start_new_thread(self.__monitoring, (RAM, ROM))

    
    @property
    def get_storage_info(self):
        usr = uos.statvfs("/usr")
        usr_total_size_kb = (usr[0] * usr[2]) / 1024
        usr_free_size_kb = (usr[0] * usr[3]) / 1024
        usr_size = {
            "usr_total": int(usr_total_size_kb),
            "usr_free": int(usr_free_size_kb)
        }

        bak = uos.statvfs("/bak")
        bak_total_size_kb = (bak[0] * bak[2]) / 1024
        bak_free_size_kb = (bak[0] * bak[3]) / 1024
        bak_size = {
            "bak_total": int(bak_total_size_kb),
            "bak_free": int(bak_free_size_kb)
        }

        return (usr_size, bak_size)
