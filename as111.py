#!/usr/bin/python

import sys
import datetime
from bluetooth import *

device = {
    "mac" : "",
    "name" : "<unknown>",
    "version" : "<unknown>"
}




def check_args(argv):

    if len(sys.argv) != 2:
        print("\nSync desktop time with Philips A111/12 docking station")
        print("\nUSAGE: sync-philips_as111 <mac>\n")
        return None

    return sys.argv[1]




def connect(device):

    try:
        client_socket = BluetoothSocket( RFCOMM )
        client_socket.connect((device["mac"], 1))
        client_socket.settimeout(2)

    except:
        return None

    return client_socket




def disconnect(client_socket):

    client_socket.close()




def send(client_socket, bytes):

    client_socket.send("".join(map(chr, bytes)))

    raw = ""
    try:
	    while True:
		    r = client_socket.recv(255)
		    if not r:
			    break
		    raw = raw + r
		    # we have reach end of message
		    if r.find(";") != -1:
			    break
    except:
	    pass

    return raw




def get_timestamp_as_array():

    dt_now = datetime.datetime.now()

    cc  = dt_now.year / 100
    yy  = dt_now.year % 100
    mm  = dt_now.month - 1
    dd  = dt_now.day
    h24 = dt_now.hour
    m   = dt_now.minute
    s   = dt_now.second

    return [cc, yy, mm, dd, h24, m, s]




def retrieve_device_info(client_socket):

    try:
        # retrieve model name
        bytes = [153, 3, 156, 8, 92]
        s = send(client_socket, bytes)
        device["name"] = s[4:-1]

        # retrieve model version
        bytes = [153, 3, 133, 19, 104]
        s = send(client_socket, bytes)
        device["version"] = s[5:-3]
        return True

    except:
        return False




def set_time(client_socket, ts):

    # \x99 \x0B \x87(seq.) \x11 \x08 \xYY \xYY \xMM \xDD \xhh \xmm \xss \x11(checksum)
    try:
        bytes = [153, 11,  135, 17,  8] + ts + [17]
        send(client_socket, bytes)
    except:
        return False

    return True




if __name__ == "__main__":

    device["mac"] = check_args(sys.argv)

    if ( device["mac"] == None):
        exit(1)

    print("Connect to %s" % device["mac"])
    socket = connect(device)
    if (socket == None):
        print("\nConnection failed! Check mac address and device.\n")
        exit(1)

    if (not retrieve_device_info(socket)):
        print("Error while retrieving device info!")
        exit(1)

    print("\nConnected device is:")
    print("name:    Philips %s" % device["name"])
    print("version: %s" % device["version"])

    ts = get_timestamp_as_array()
    print("\nSet current time %02d%02d-%02d-%02d %02d:%02d:%02d" % tuple(ts))
    if (not set_time(socket, ts)):
        print("Failed to set time.")
        disconnect(socket)
        exit(1)

    print("Time set successfully!\n")

    disconnect(socket)
    exit(0)
