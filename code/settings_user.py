class UserConfig:
    class _server:
        none = 0x0
        AliIot = 0x1
        ThingsBoard = 0x2

    class _loc_method:
        none = 0x0
        gps = 0x1
        cell = 0x2
        wifi = 0x4
        all = 0x7

    debug = 1

    log_level = "DEBUG"

    server = _server.ThingsBoard

    loc_method = _loc_method.gps

    ota_status = {
        "sys_current_version": "",
        "sys_target_version": "--",
        "app_current_version": "",
        "app_target_version": "--",
        "upgrade_module": "--",
        "upgrade_status": "--",
    }

    apn = {
        "apn": "iot.1nce.net",
        "username": "",
        "password": "",
    }

    provision = {
        "deviceName" : None,
        "provisionDeviceKey": "twmnvuzdlamjjuedqxn1",
        "provisionDeviceSecret": "owmqcfwqg2uycwzty7ij",
        "credentialsType": "ACCESS_TOKEN",
        "token": None,
    }
