# sync-philips-as111
Sync Linux desktop time with Philips A111/12 docking station

The Philips AS111/12 is a bluetooth speaker with clock and micro-usb port. In addition to the bluetooth audio device you are able to sync the current time by using a bluetooth serial connection. 

This is a little python script that is used in order to set the current time of the docking station called 'Philips AS111/12'.

Usage:
```
USAGE: sync-philips_as111 <mac>
```

Example:
```
$ ./sync-philips_as111 00:1D:DF:51:53:2B
Connect to 00:1D:DF:51:53:2B
Set current time 2018-08-13 20:07:57
Sync finished
```

## Pre-condition
Before you can use this script you must pair the device.


**Note*
On Ubuntu this script runs as expected after paring. But on Raspbian it was a hard to make it work since I've always got the error 'connection refused'.
I think that the following command make it work
```
sudo hciconfig hci0 sspmode 0
```

For PIN use 0000.


## API
In order to sync the time you need an RFCOMM connection. Port is 1. 

The byte sequence that must be send looks as follows:
```
Example is for 2018-08-13 20:30:24

\x99\x0B\x87\x11\x08\x14\x12\x08\x0D\x14\x1E\x18\x11
|                    |   |   |   |   |   |   |   + static postamble
|                    |   |   |   |   |   |   + Seconds in hex
|                    |   |   |   |   |   + minutes in hex
|                    |   |   |   |   + hour in hex
|                    |   |   |   + day in hex
|                    |   |   + ordinal of month, e.g. "08" for August
|                    |   + last two digits of year in hex, here "12" for 2018
|                    + first two digits of year in hex, here "14" for 2018
+ static preamble        
```
