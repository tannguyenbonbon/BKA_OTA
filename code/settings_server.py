class AliIotConfig:

    product_key = ""
    product_secret = ""
    device_name = ""
    device_secret = ""
    server = "iot-as-mqtt.cn-shanghai.aliyuncs.com"
    qos = 1

class ThingsBoardConfig:
    host = "mq.bonboncar.vn"
    port = 1883
    qos = 1
    client_id = "123"
    username = None
    
    #!Custom username
    # username = "backup_tracker_test2"
    username = "tan_test_backup"
    # username = "tan_backup_tracker"
    # username = "huy_backup_tracker"
    # username = "luc_backup_tracker"
    # username = "thuan_backup_tracker"
    # username = "liem_backup_tracker"