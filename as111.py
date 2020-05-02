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

from bluetooth import *
import datetime
import json
import sys
from time import sleep




debug = 0
socket = None
sequence = 0
device = {
    "mac" : "",
    "name" : "",
    "version" : "",
    "datetime" : "",
    "volume" : 0,
    "capabilities" : []
}

capabilities = ["0-VOLUME", "1-DSC", "2-DBB", "3-TREBLE", "4-BASS",
                "5-FULL", "6-CHARGING", "7-BATTERY", "8-DATETIME",
                "9-EQ1", "10-EQ2", "11-EQ3", "12-EQ4", "13-EQ5",
                "14-ALARM_VOLUME", "15-AC_DC_POWER_MODE",
                "16-REMOTE_CONTROL", "17-FM_STATION_SEARCH",
                "18-FM_FREQUENCY_TUNING", "19-FM_AUTO_PROGRAM",
                "20-FM_MANUAL_PROGRAM", "21-FM_PRESET_STATION",
                "22-DOCK_ALARM_1", "23-DOCK_ALARM_2",
                "24-DOCK_ALARM_LED", "25-AUDIO_SOURCE", "26-APPALM",
                "27-RCAPPSC" ]




def _log(s):
    if debug == 1:
        print(s)



def print_help():

    print("""
 USAGE:   as111.py <mac> [command1] [params] [command2] ...
 EXAMPLE: Set volume to 12
          $ ./as111.py vol 12

          Hacks and command queueing
          as111.py 00:1D:DF:52:F1:91 display 5 8765 countup 0:10 countdown 0:10 mins-n-secs 5

 sync                    Synchronizes time between PC and dock
 vol [+-]<0-32>          Sets volume to value which is between 0 and 32
 mute                    Sets volume to 0
 alarm-led <off|on>      Activates / deactivates alarm LED

 Hacks:
 mins-n-secs <secs>      Displays minutes and seconds instead of hour and minutes for <secs> seconds
 countdown <mm:ss>       Starts countdown
 countup <mm:ss>         Starts counting up
 display <secs> <number> Displays any 4-digit <number> for <secs> seconds
 sleep <n>               Hold processing for n seconds

 Other:
 info                    Prints device info
 json                    Prints device info in JSON format
 debug                   Activates debug mode
 help                    Information about usage, commands and parameters
    """)




def print_info():

    print("""
MAC:     %s
Name:    %s
Version: %s
Time:    %s
Volume:  %i
    """ % (device["mac"], device["name"], device["version"], device["datetime"], device["volume"]) )




def print_json():
    print(json.dumps(device, indent=2))




def connect():

    global socket

    _log("DEBUG: Connnect to %s" % device["mac"])

    try:
        client_socket = BluetoothSocket( RFCOMM )
        client_socket.connect((device["mac"], 1))
        client_socket.settimeout(2)

    except btcommon.BluetoothError as error:
        print("ERROR: %s" % error)
        print("ERROR: Connection failed! Check mac address and device.\n")
        exit(1)

    socket = client_socket

    _log("DEBUG: Connnected to %s" % device["mac"])




def disconnect():

    _log("DEBUG: disconnect")

    try:
        socket.close()

    except:
        pass

    _log("DEBUG: disconnected")




def send(data):

    raw = []

    _log("DEBUG: >>> %s" % (" ".join(str(i) for i in data)))

    try:
        socket.send(bytes(data))
        raw = list(socket.recv(255))

        _log("DEBUG: <<< %s" % (" ".join(str(i) for i in raw)))

    except btcommon.BluetoothError as error:
        print("ERROR: request failed, %s" % error)

    return raw




def _get_request(command, payload = []):

    global sequence

    length = 3 + len(payload)
    sequence += 1
    request = [ 153, length, sequence, command ]

    checksum = command
    for p in payload:
        request += [ p ]
        checksum += p

    request += [ ( -1 * checksum ) & 255 ]

    return request




def get_timestamp_as_array():

    dt_now = datetime.datetime.now()

    cc  = dt_now.year // 100
    yy  = dt_now.year % 100
    mm  = dt_now.month - 1
    dd  = dt_now.day
    h24 = dt_now.hour
    m   = dt_now.minute
    s   = dt_now.second

    return [cc, yy, mm, dd, h24, m, s]




def _list_to_string(l):

    s = ""
    for c in l:
        s += chr(c) if c != 0 else ""

    return s




def request_device_info():

    # request device name
    _log("DEBUG: request device name")

    request = _get_request(8)
    raw = send(request)
    device["name"] = _list_to_string(raw)[4:-1]

    _log("DEBUG: device name is \"%s\"" % device["name"])

    # request device version
    _log("DEBUG: request device version")

    request = _get_request(19)
    raw = send(request)
    device["version"] = _list_to_string(raw)[4:-1]

    _log("DEBUG: device version is \"%s\"" % device["version"])

    # request device volume
    _log("DEBUG: request current volume")

    request = _get_request(15, [ 0 ])
    raw = send(request)
    device["volume"] = raw[-2]

    _log("DEBUG: current volume is %i" % device["volume"])

    # request device capabilities
    _log("DEBUG: request device capabilities")

    raw = send(_get_request(6))
    parse_capabilities(raw[8:-1])
    _log("DEBUG: device capabilities requested: %s" % ", ".join(device["capabilities"]))




def parse_capabilities(caps):

    caps.reverse()
    supported = []
    i = 0

    for c in caps:
        for bit in range(0, 8):
            r = c >> (i % 8)
            if r & 1 == 1:
                supported += [ capabilities[i] ]
            i += 1

    device["capabilities"] = supported




def sync_time():

    ts = get_timestamp_as_array()
    ts_string = "%02d%02d-%02d-%02d %02d:%02d:%02d" % (ts[0], ts[1],
                                ts[2] + 1, ts[3], ts[4], ts[5], ts[6])

    _log("DEBUG: sync time to %s" % ts_string)

    send(_get_request(17, [ 8 ] + ts))

    device["datetime"] = ts_string

    _log("DEBUG: time synced")



def display_mins_n_secs(secs):

    while (secs >=0):
        ts = get_timestamp_as_array()
        ts_string = "%02d%02d-%02d-%02d %02d:%02d:%02d" % (ts[0], ts[1],
                                    ts[2] + 1, ts[3], ts[5], ts[6], ts[6])

        ts[4] = ts[5]
        ts[5] = ts[6]
        ts[6] = 0

        _log("DEBUG: display minutes and seconds %s" % ts_string)

        send(_get_request(17, [ 8 ] + ts))

        device["datetime"] = ts_string

        _log("DEBUG: displayed minutes and seconds")

        try:
            sleep(1)
            secs -= 1
        except:
            return




def display_number(number):

    ts = get_timestamp_as_array()

    ts[4] = number // 100 % 100
    ts[5] = number % 100
    ts[6] = 0

    ts_string = "%02d:%02d" % (ts[4], ts[5])

    _log("DEBUG: set display to %s" % ts_string)

    send(_get_request(17, [ 8 ] + ts))

    device["datetime"] = ts_string

    _log("DEBUG: display set")




def countdown(minutes, seconds, step = -1):

    step = 1 if step > 0 else -1

    ts = get_timestamp_as_array()

    total = minutes * 60 + seconds
    remain = total

    while (remain >= 0):

        if step == -1:
            display = remain
        else:
            display = total - remain

        ts[4] = display // 60
        ts[5] = display % 60
        ts[6] = 0

        ts_string = "%02d:%02d" % (ts[4], ts[5])

        _log("DEBUG: set countdown to %s" % ts_string)

        send(_get_request(17, [ 8 ] + ts))

        device["datetime"] = ts_string

        _log("DEBUG: countdown set")
        try:
            sleep(1)
            remain -= 1
        except:
            print("INFO: countdown interrupted")
            return




def set_volume(vol):

    vol = vol if vol <= 32 else 32
    vol = vol if vol >= 0 else 0

    _log("DEBUG: Set volume to %i" % vol)

    raw = send(_get_request(17, [ 0, vol ]))

    _log("DEBUG: volume set to %i" % vol)




def set_alarm_led(status):

    status = status if status == 1 else 0

    _log("DEBUG: Set volume to %i" % vol)

    raw = send(_get_request(17, [ 24, status ]))

    _log("DEBUG: volume set to %i" % vol)



if __name__ == "__main__":

    if len(sys.argv) < 2:
        print_help()
        exit(1)

    if len(sys.argv) > 2 and sys.argv[2] == "debug":
        debug = 1

    device["mac"] = sys.argv[1]
    connect()

    request_device_info()

    # process commands
    args = sys.argv[1:]
    while(len(args) > 0):
        command = args[0]
        args = args[1:]

        if command == "vol":

            try:
                if args[0][0] in "-+":
                    vol = device["volume"] + int(args[0])
                else:
                    vol = int(args[0])

                set_volume(vol)

            except:
                print("ERROR: Volume must be between 0 and 32")
                exit(1)

            args = args[1:]

        elif command == "mute":

            set_volume(0)

        elif command == "alarm-led":

            status = 1 if args[0] == "on" else 0
            set_alarm_led(status)
            args = args[1:]

        elif command == "sleep":

            try:
                secs = int(args[0])
            except:
                print("ERROR: seconds must be numeric")
                exit(1)

            try:
                sleep(secs)
            except:
                pass

            args = args[1:]

        elif command == "sync":

            sync_time()

        elif command == "countdown" or command == "countup":

            try:
                param = args[0].split(":")
                minutes = int(param[0])
                secs = int(param[1])
            except:
                print("ERROR: time must be given in numeric format mm:ss")
                exit(1)

            countdown(minutes, secs, -1 if command == "countdown" else 1)
            args = args[1:]

        elif command == "mins-n-secs":

            try:
                secs = int(args[0])
            except:
                print("ERROR: seconds must be numeric")
                exit(1)
            display_mins_n_secs(secs)
            args = args[1:]

        elif command == "display":

            try:
                secs = int(args[0]) % 60
                number = int(args[1])
            except:
                print("ERROR: seconds must be numeric")
                exit(1)

            display_number(number)

            try:
                sleep(secs)
            except:
                pass
            args = args[2:]

        elif command == "info":

            print_info()

        elif command == "json":

            print_json()

        elif command == "help":

            print_help()

    sync_time()
    disconnect()
    exit(0)