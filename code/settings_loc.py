from machine import UART
class LocConfig:
    class _gps_mode:
        internal = 0x1
        external_uart = 0x2
        external_i2c = 0x3

    class _map_coordinate_system:
        WGS84 = "WGS84"
        GCJ02 = "GCJ02"

    class _gps_sleep_mode:
        none = 0x0
        pull_off = 0x1
        backup = 0x2
        standby = 0x3

    profile_idx = 1
    map_coordinate_system = _map_coordinate_system.WGS84
    gps_sleep_mode = _gps_sleep_mode.none

    gps_cfg = {
        "UARTn": UART.UART1,
        "buadrate": 115200,
        "databits": 8,
        "parity": 0,
        "stopbits": 1,
        "flowctl": 0,
        "gps_mode": _gps_mode.internal,
        "PowerPin": None,
        "StandbyPin": None,
        "BackupPin": None,
    }

    # cell_cfg = {
    #     "serverAddr": "bbcar.thingstream.io",
    #     "port": 80,
    #     "token": "HmmdrJaTQWSj8VJTKYRX2w",
    #     "timeout": 3,
    #     "profileIdx": profile_idx,
    # }

    # wifi_cfg = {
    #     "token": "HmmdrJaTQWSj8VJTKYRX2w"
    # }
