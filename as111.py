#!/usr/bin/python3
#
# MIT License
#
# Copyright (c) 2020 heckie75
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

import datetime
import json
import os
import re
import socket
import subprocess
import sys
import time

DEBUG = 3
INFO = 2
WARN = 1
ERROR = 0

loglevel = 0


def log(msg, level=INFO):

    _LEVELS = ["ERROR", "WARN", "INFO", "DEBUG"]
    if loglevel >= level:
        print("%s:\t%s" % (_LEVELS[level], msg))


class AS111():

    _MAC_PATTERN = "00:1D:DF:[0-9A-F]{2}:[0-9A-F]{2}:[0-9A-F]{2}"

    _KNOWNDOCKS_FILE = ".known_as111"
    _STOP_SIGNAL_FILE = ".as111_stop"

    _PORT_BLUETOOTH = "Bluetooth"
    _PORT_SERIAL = "Serial"

    _verbose = 0
    _client_socket = None
    _serial = None
    _sequence = 0
    _devices = list()
    _aliases = dict()

    _capabilities = ["0-VOLUME", "1-DSC", "2-DBB", "3-TREBLE", "4-BASS",
                     "5-FULL", "6-CHARGING", "7-BATTERY", "8-DATETIME",
                     "9-EQ1", "10-EQ2", "11-EQ3", "12-EQ4", "13-EQ5",
                     "14-ALARM_VOLUME", "15-AC_DC_POWER_MODE",
                     "16-REMOTE_CONTROL", "17-FM_STATION_SEARCH",
                     "18-FM_FREQUENCY_TUNING", "19-FM_AUTO_PROGRAM",
                     "20-FM_MANUAL_PROGRAM", "21-FM_PRESET_STATION",
                     "22-DOCK_ALARM_1", "23-DOCK_ALARM_2",
                     "24-DOCK_ALARM_LED", "25-AUDIO_SOURCE", "26-APPALM",
                     "27-RCAPPSC"]

    def __init__(self):

        if self._is_windows():
            self._devices, self._device = self._get_devices_for_windows()

        else:
            self._devices, self._device = self._get_devices_for_linux()

        self._aliases = self._read_aliases()
        for _d in self._devices:
            if _d["address"] in self._aliases:
                _d["alias"] = self._aliases[_d["address"]]

    def _get_devices_for_linux(self):

        def _exec_bluetoothctl(commands=[]):

            command_str = "\n".join(commands)

            p1 = subprocess.Popen(["echo", "-e", "%s\nquit\n\n" % command_str],
                                  stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["bluetoothctl"],
                                  stdin=p1.stdout,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
            p1.stdout.close()
            out, err = p2.communicate()
            return out.decode("utf8")

        output = _exec_bluetoothctl()

        controllers = list()
        for match in re.finditer("Controller ([0-9A-F:]+) (.+)", output):
            controllers.append(match.group(1))

        _devices = list()
        for controller in controllers:
            time.sleep(.25)
            output = _exec_bluetoothctl(["select %s" % controller, "devices"])
            for match in re.finditer("Device (%s) (.+)" % self._MAC_PATTERN, output):
                _devices.append({
                    "port": self._PORT_BLUETOOTH,
                    "address": match.group(1),
                    "mac": match.group(1),
                    "controller": controller,
                    "name": match.group(2),
                    "connected": False,
                    "alias": "",
                    "version": "",
                    "capabilities": [],
                    "datetime": "",
                    "volume": 0
                })

        _connected_device = None
        for _device in _devices:
            output = _exec_bluetoothctl(
                ["select %s" % _device["controller"], "info %s" % _device["mac"]])
            for match in re.finditer("Connected: (yes|no)", output):
                if match.group(1) == "yes":
                    _device["connected"] = True
                    _connected_device = _device

        return _devices, _connected_device

    def _get_devices_for_windows(self):

        global devices

        import serial.tools.list_ports
        _devices = list()
        for p in list(serial.tools.list_ports.comports()):
            if p.hwid.startswith("BTHENUM"):
                _mac = "".join(["%s%s" % (s, ":" if i % 2 else "") for i, s in enumerate(
                    p.hwid.split("\\")[-1].split("&")[-1][:12])])[:-1]
                if re.match(self._MAC_PATTERN, _mac):
                    _devices.append(
                        {
                            "port": self._PORT_SERIAL,
                            "address" : _mac if "BTPROTO_RFCOMM" in dir(socket) else p.device,
                            "mac": _mac,
                            "controller": "",
                            "name": p.description,
                            "connected": True,  # actually it maybe it's not connected
                            "alias": "",
                            "version": "",
                            "capabilities": [],
                            "datetime": "",
                            "volume": 0
                        }
                    )

        return _devices, _devices[0] if len(_devices) else None

    def _is_windows(self):

        return os.name == "nt"

    def _read_aliases(self):

        try:
            filename = os.path.join(os.environ['USERPROFILE'] if self._is_windows(
            ) else os.environ['HOME'] if "HOME" in os.environ else "~", self._KNOWNDOCKS_FILE)

            aliases = dict()

            if os.path.isfile(filename):
                with open(filename, "r") as ins:
                    for line in ins:
                        _s = line.split(" ")
                        aliases[_s[0]] = " ".join(_s[1:]).strip()

        except:
            pass

        return aliases

    def get_aliases(self):

        return self._aliases

    def get_address_n_alias(self, s):

        aliases = self.get_aliases()
        for _m in aliases:
            if s == _m or s in aliases[_m]:
                return _m, aliases[_m]

        if re.match(self._MAC_PATTERN, s) or s.startswith("COM"):
            return s, None
        else:
            return None, None

    def get_devices(self):

        return self._devices

    def get_connected_device(self):

        return self._device

    def connect(self, address):

        try:
            if re.match(self._MAC_PATTERN, address):
                log("Connnect via Bluetooth to %s" % address, DEBUG)
                self._client_socket = socket.socket(
                    socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
                self._client_socket.connect((address, 1))
                self._client_socket.settimeout(2)
                self._device = list(
                    filter(lambda _d: _d["address"] == address, self._devices))[0]

            elif address.startswith("COM"):
                import serial
                log("Connnect via serial port to %s" % address, DEBUG)
                self._serial = serial.Serial(address, timeout=.1)

        except:
            log(
                "Connection failed! Check mac address and device.\n", ERROR)

            return False

        log("Connnected to %s" % self._device["address"], DEBUG)
        self.sync_time()
        self.request_device_info()

        return True

    def disconnect(self):

        log("disconnect", DEBUG)
        try:
            if self._client_socket:
                self._client_socket.close()

            if self._serial:
                self._serial.close()

        except:
            pass

        log("disconnected", DEBUG)

    def _get_request(self, command, payload=[]):

        length = 3 + len(payload)
        self._sequence += 1
        self._sequence &= 255
        request = [153, length, self._sequence, command]

        checksum = command
        for p in payload:
            request += [p]
            checksum += p

        request += [(-1 * checksum) & 255]

        return request

    def _send(self, data, lresponse=32):

        try:
            log(">>> %s" % (" ".join(str(i) for i in data)), DEBUG)

            raw = []
            if self._serial:
                self._serial.write(data)
                self._serial.flush()
                raw = list(self._serial.read(lresponse))

                if lresponse != len(raw):
                    log("Length of response is %i but expected %i" % (len(raw), lresponse), WARN)

            elif self._client_socket:
                self._client_socket.send(bytes(data))
                raw = list(self._client_socket.recv(255))

        except:
            log("request failed", ERROR)

        log("<<< %s (%i bytes)" % (" ".join(str(i) for i in raw), len(raw)), DEBUG)
        return raw

    def _get_timestamp_as_array(self):

        dt_now = datetime.datetime.now()

        cc = dt_now.year // 100
        yy = dt_now.year % 100
        mm = dt_now.month - 1
        dd = dt_now.day
        h24 = dt_now.hour
        m = dt_now.minute
        s = dt_now.second

        return [cc, yy, mm, dd, h24, m, s]

    def _list_to_string(self, l):

        s = ""
        for c in l:
            s += chr(c) if c != 0 else ""

        return s

    def _stop_file_path(self):

        return os.path.join(os.environ["TEMP"] if self._is_windows() else "/tmp", self._STOP_SIGNAL_FILE)

    def set_stop_signal(self):

        open(self._stop_file_path(), "w").close()

    def clean_stop_signal(self):

        if self.is_stop_signal():
            os.remove(self._stop_file_path())

    def is_stop_signal(self):

        return os.path.isfile(self._stop_file_path())

    def request_device_info(self):

        def parse_capabilities(caps):

            caps.reverse()
            supported = list()
            i = 0

            for c in caps:
                for bit in range(0, 8):
                    r = c >> (i % 8)
                    if r & 1 == 1:
                        supported.append(self._capabilities[i])
                    i += 1

            self._device["capabilities"] = supported

        # request device name
        log("request device name", DEBUG)

        request = self._get_request(8)
        raw = self._send(request, lresponse=10)
        self._device["name"] = self._list_to_string(raw)[4:-1]

        log("device name is \"%s\"" % self._device["name"], INFO)

        # request device version
        log("request device version", DEBUG)

        request = self._get_request(19)
        raw = self._send(request, lresponse=17)
        self._device["version"] = self._list_to_string(raw)[4:-1]

        log("device version is \"%s\"" %
            self._device["version"], INFO)

        # request device volume
        log("request current volume", DEBUG)

        request = self._get_request(15, [0])
        raw = self._send(request, lresponse=7)
        self._device["volume"] = raw[-2]

        log("current volume is %i" % self._device["volume"], INFO)

        # request device capabilities
        log("request device capabilities", DEBUG)

        raw = self._send(self._get_request(6), lresponse=13)
        parse_capabilities(raw[8:-1])
        log("device capabilities requested: %s" %
            ", ".join(self._device["capabilities"]), DEBUG)

    def sync_time(self):

        ts = self._get_timestamp_as_array()
        ts_string = "%02d%02d-%02d-%02d %02d:%02d:%02d" % (ts[0], ts[1],
                                                           ts[2] + 1, ts[3], ts[4], ts[5], ts[6])

        log("sync time to %s" % ts_string, INFO)

        self._send(self._get_request(17, [8] + ts), lresponse=6)

        self._device["datetime"] = ts_string

        log("time synced", DEBUG)

    def display_mins_n_secs(self, secs):

        while (secs >= 0 and not self.is_stop_signal()):

            before = time.time()

            ts = self._get_timestamp_as_array()
            ts_string = "%02d%02d-%02d-%02d %02d:%02d:%02d" % (ts[0], ts[1],
                                                               ts[2] + 1, ts[3], ts[5], ts[6], ts[6])

            ts[4] = ts[5]
            ts[5] = ts[6]
            ts[6] = 0

            log("display minutes and seconds %s" % ts_string, INFO)

            self._send(self._get_request(17, [8] + ts), lresponse=6)

            self._device["datetime"] = ts_string

            log("displayed minutes and seconds", DEBUG)

            try:
                secs -= 1
                time.sleep(max(0, 1 - (time.time() - before)))
            except:
                log(
                    "displaying minutes and seconds interrupted", WARN)
                return

    def display_date(self):

        ts = self._get_timestamp_as_array()
        ts_string = "%02d%02d-%02d-%02d %02d:%02d:%02d" % (ts[0], ts[1],
                                                           ts[2] + 1, ts[3], ts[5], ts[6], ts[6])

        ts[4] = ts[3]
        ts[5] = ts[2] + 1
        ts[6] = 0

        log("display date %s" % ts_string, INFO)

        self._send(self._get_request(17, [8] + ts), lresponse=6)

        self._device["datetime"] = ts_string

        log("displayed date", DEBUG)

        try:
            time.sleep(1)
        except:
            log("displaying minutes and seconds interrupted", WARN)
            return

    def display_number(self, secs, number):

        ts = self._get_timestamp_as_array()

        ts[4] = number // 100 % 100
        ts[5] = number % 100
        ts[6] = 0

        ts_string = "%02d:%02d" % (ts[4], ts[5])

        log("set display to %s" % ts_string, INFO)

        self._send(self._get_request(17, [8] + ts), lresponse=6)

        self._device["datetime"] = ts_string

        log("display set", DEBUG)

        try:
            time.sleep(secs)
        except:
            log("displaying number interrupted", WARN)

    def countdown(self, minutes, seconds, step=-1):

        step = 1 if step > 0 else -1

        ts = self._get_timestamp_as_array()

        total = minutes * 60 + seconds
        remain = total

        while (remain >= 0 and not self.is_stop_signal()):

            before = time.time()

            if step == -1:
                display = remain
            else:
                display = total - remain

            ts[4] = display // 60
            ts[5] = display % 60
            ts[6] = 0

            ts_string = "%02d:%02d" % (ts[4], ts[5])

            log("set countdown to %s" % ts_string, INFO)

            self._send(self._get_request(17, [8] + ts), lresponse=6)

            self._device["datetime"] = ts_string

            log("countdown set", DEBUG)
            try:
                remain -= 1
                time.sleep(max(0, 1 - (time.time() - before)))
            except:
                log("counting interrupted", WARN)
                return

    def set_volume(self, vol):

        vol = vol if vol <= 32 else 32
        vol = vol if vol >= 0 else 0

        log("Set volume to %i" % vol, INFO)

        self._send(self._get_request(17, [0, vol]), lresponse=6)
        self._device["volume"] = vol

        log("volume set to %i" % vol, DEBUG)

    def set_alarm_led(self, status):

        status = status if status == 1 else 0

        log("Set alarm led to %i" % status, INFO)

        self._send(self._get_request(17, [24, status]), lresponse=6)

        log("alarm led set to %i" % status, DEBUG)

    def blink_alarm_led(self, secs):

        log("Blink alarm led for %i seconds" % secs, INFO)

        secs *= 2

        while (secs >= 0 and not self.is_stop_signal()):

            self._send(self._get_request(17, [24, secs % 2]), lresponse=6)

            try:

                time.sleep(.5)
                secs -= 1

            except:

                log(
                    "displaying minutes and seconds interrupted", WARN)
                return

        log("blinked led set for %i seconds" % secs, DEBUG)


def print_docks(as111):

    for _device in as111.get_devices():

        print("""\
Port:       %s
Adress:     %s
MAC:        %s
Controller: %s
Name:       %s
Alias:      %s
Connected:  %s
""" % (_device["port"], _device["address"], _device["mac"], _device["controller"], _device["name"], _device["alias"], "yes" if _device["connected"] == True else "no"))


def print_info(device):

    print("""
MAC:       %s
Alias:     %s
Name:      %s
Version:   %s
Time:      %s
Volume:    %i
    """ % (device["mac"], device["alias"], device["name"], device["version"], device["datetime"], device["volume"]))


def print_json(device):
    print(json.dumps(device, indent=2))


def print_help():

    print("""
 USAGE:   as111.py <mac|alias|-|docks|stop> [command1] [params] [command2] ...
 EXAMPLE: Set volume to 12
          $ ./as111.py vol 12

          Hacks and command queueing
          as111.py 00:1D:DF:52:F1:91 display 5 8765 countup 0:10 countdown 0:10 mins-n-secs 5

 <mac|alias|-|docks>     Use specific mac, alias or "-" for current connected dock
                         "docks" lists all paired docking stations
                         "stop" sends a signal in order to terminate a running as111 process
 sync                    Synchronizes time between PC and dock
 vol [+-]<0-32>          Sets volume to value which is between 0 and 32
 mute                    Sets volume to 0
 alarm-led <off|on>      Activates / deactivates alarm LED

 Hacks:
 date                    Displays date
 mins-n-secs <secs>      Displays minutes and seconds instead of hour and minutes for <secs> seconds
 alarm-led blink <n>     let alarm LED blink n times
 countdown <mm:ss>       Starts countdown
 countup <mm:ss>         Starts counting up
 display <secs> <number> Displays any 4-digit <number> for <secs> seconds
 sleep <n>               Hold processing for n seconds

 Other:
 stop                    use in order to stop long running thread, e.g. as111.py stop
 info                    Prints device info
 json                    Prints device info in JSON format
 verbose                 Verbose mode
 debug                   Debug mode
 help                    Information about usage, commands and parameters
    """)


if __name__ == "__main__":

    if len(sys.argv) < 2:
        print_help()
        exit(1)

    if len(sys.argv) > 2 and sys.argv[2] in ["debug", "verbose"]:

        loglevel = DEBUG if sys.argv[2] == "debug" else INFO

    as111 = AS111()
    if sys.argv[1] == "stop":
        log("Set stop signal", INFO)
        as111.set_stop_signal()
        exit(0)

    elif sys.argv[1] == "docks":
        print_docks(as111)
        exit(0)

    elif sys.argv[1] == "help":

        print_help()
        exit(0)

    elif sys.argv[1] == "-":
        _device = as111.get_connected_device()
        if _device == None:
            log("No device connected.", ERROR)
            exit(1)

        address, alias = as111.get_address_n_alias(_device["address"])
        log("use %s, %s" % (address, alias or "(w/o alias)"), INFO)

    else:
        address, alias = as111.get_address_n_alias(sys.argv[1])

        if address == None:
            log("Unable to resolve address for alias. Check .known_as111 file.", ERROR)
            exit(1)

        elif alias:
            log("Found alias \"%s\"" % alias, INFO)

    as111.clean_stop_signal()
    connected = as111.connect(address)
    if not connected:
        log("Unable to connect to %s" % address)
        exit(1)

    # process commands
    args = sys.argv[1:]
    while(len(args) > 0):
        command = args[0]
        args = args[1:]

        if command == "vol":

            try:
                if args[0][0] in "-+":
                    device = as111.get_connected_device()
                    vol = device["volume"] + int(args[0])
                else:
                    vol = int(args[0])

                as111.set_volume(vol)

            except:
                log("Volume must be between 0 and 32", ERROR)
                exit(1)

            args = args[1:]

        elif command == "mute":

            as111.set_volume(0)

        elif command == "alarm-led":

            if args[0] == "blink":
                try:
                    as111.blink_alarm_led(int(args[1]))
                    args = args[1:]
                except:
                    log("seconds must be given and numeric", ERROR)
            else:
                status = 1 if args[0] == "on" else 0
                as111.set_alarm_led(status)

            args = args[1:]

        elif command == "sleep":

            try:
                secs = int(args[0])
            except:
                log("seconds must be numeric", ERROR)
                exit(1)

            try:
                time.sleep(secs)
            except:
                log("sleeping interrupted", WARN)

            args = args[1:]

        elif command == "sync":

            as111.sync_time()

        elif command == "countdown" or command == "countup":

            try:
                param = args[0].split(":")
                minutes = int(param[0])
                secs = 0 if len(param) != 2 else int(param[1])
            except:
                log("time must be given in numeric format mm:ss", ERROR)
                exit(1)

            as111.countdown(minutes, secs, -1 if command == "countdown" else 1)
            args = args[1:]

        elif command == "mins-n-secs":

            try:
                secs = int(args[0])
            except:
                log("seconds must be numeric", ERROR)
                exit(1)
            as111.display_mins_n_secs(secs)
            args = args[1:]

        elif command == "date":

            as111.display_date()

        elif command == "display":

            try:
                secs = int(args[0]) % 60
                number = int(args[1])
            except:
                log("seconds must be numeric", ERROR)
                exit(1)

            as111.display_number(secs, number)
            args = args[2:]

        elif command == "info":

            print_info(as111.get_connected_device())

        elif command == "json":

            print_json(as111.get_connected_device())

        elif command == "debug":

            loglevel = DEBUG

        elif command == "verbose":

            loglevel = INFO

    as111.sync_time()
    as111.disconnect()
    as111.clean_stop_signal()
    exit(0)
