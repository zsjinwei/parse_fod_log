#!/usr/bin/env python
# -*- coding: utf-8 -*-
# author: huangjinwei@meizu.com
# create time: 2018-08-06 11:00

import os, sys, re
import time
import datetime
from dateutil import parser

log_path = ''

time_pattern = r"([0-9]{2}?-[0-9]{2}? [0-9]{2}?:[0-9]{2}?:[0-9]{2}?\.[0-9]{3}?).*?"

tp_downup_state = 'idle'      # Touch screen down or up
fs_downup_state = 'idle'      # FingerprintService down or up
screen_onoff_state = 'idle'   # Screen on or off(AOD)
powkey_downup_state = 'idle'  # Power Key down or up
process_state = 'idle'

result_map = {
    'lastFdTime' : '',
    'lastFuTime' : '',
    'down2up_time': 0,
    'capture_start' : 0,
    'auth_time' : '',
    'fu2auth_time' : 0,
    'auth_result' : "success",
    'auth_fid' : '0',
    'auth_fail_reason': [],
}

# for color log
def red_log(Str):
    print("\033[31m"+str(Str)+"\033[0m")
    pass

def green_log(Str):
    print("\033[32m"+str(Str)+"\033[0m")
    pass

def yellow_log(Str):
    print("\033[33m"+str(Str)+"\033[0m")
    pass

def blue_log(Str):
    print("\033[34m"+str(Str)+"\033[0m")
    pass

def cyan_log(Str):
    print("\033[36m"+str(Str)+"\033[0m")
    pass

def print_result():
    if process_state == "idle" and fs_downup_state == 'fs_finger_up' and tp_downup_state == 'tp_finger_up':
        print(">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
        print("FD TIME: " + result_map['lastFdTime'])
        print("FU TIME: " + result_map['lastFuTime'])
        print("FD to FU TIME: " + str(result_map['down2up_time']) + "ms")
        if result_map['capture_start'] == 1:
            print("Auth result: " + result_map['auth_result'])
            print("Auth FID: " + result_map['auth_fid'])
            if result_map['auth_result'] == "fail":
                red_log("AUTH FAIL REASON: ")
                for res in result_map['auth_fail_reason']:
                    red_log("  " + str(res))
        else:
            red_log("AUTH FAIL REASON: ")
            red_log("  fastTouch and capture not started")
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        print("\n")

if len(sys.argv) > 1:
    log_path = sys.argv[1]
else:
    print("Usage: " + sys.argv[0] + " path/to/LogFile")
    quit()

with open(log_path) as reader:
    lastFdTime = datetime.datetime.now()
    lastFuTime = datetime.datetime.now()

    lastPowFdTime = datetime.datetime.now()
    lastPowFuTime = datetime.datetime.now()

    for index, line in enumerate(reader):
        #blue_log('current state: ' + tp_downup_state)

        # find TouchScreen FINGER DOWN or UP
        res = re.findall(time_pattern+r"MzPhoneWindowManager.*?keycode=413 (down|up)", line)
        if len(res) > 0:
            #blue_log(res)
            if (tp_downup_state == 'idle' or tp_downup_state == 'tp_finger_up') and len(res[0]) > 1 and res[0][1] == 'down':
                blue_log(res[0][0] + " TP FINGER DOWN.")
                tp_downup_state = 'tp_finger_down'
                lastFdTime = parser.parse(res[0][0])
                result_map['lastFdTime'] = res[0][0]
                result_map['auth_fail_reason'] = []
                result_map['capture_start'] = 0
            elif tp_downup_state == 'tp_finger_down' and len(res[0]) > 1 and res[0][1] == 'up':
                blue_log(res[0][0] + " TP FINGER UP.")
                tp_downup_state = 'tp_finger_up'
                lastFuTime = parser.parse(res[0][0])
                result_map['lastFuTime'] = res[0][0]
                delta_time = lastFuTime - lastFdTime
                result_map['down2up_time'] = delta_time.days * 24 * 60 * 60 * 1000 + delta_time.seconds * 1000 + delta_time.microseconds / 1000
                #result_map['down2up_time'] = (lastFuTime - lastFdTime).microseconds/1000
                yellow_log("FD to FU time: " + str(result_map['down2up_time']) + "ms")
                print_result()
            else:
                red_log(str(res) + " is unexpected in tp_downup_state")

        # find FingerprintService notify HAL FINGER DOWN or UP
        res = re.findall(time_pattern+r"FingerprintService: notifyHal status: ([0-9])", line)
        if len(res) > 0:
            #blue_log(res)
            if len(res[0]) > 1 and res[0][1] != '':
                if (fs_downup_state=='idle' or fs_downup_state == 'fs_finger_up') and res[0][1] == '1':
                    blue_log(res[0][0] + " FS FINGER DOWN.")
                    fs_downup_state = 'fs_finger_down'
                    process_state = 'processing'
                    result_map['capture_start'] = 1
                elif fs_downup_state == 'fs_finger_down' and res[0][1] == '2':
                    blue_log(res[0][0] + " FS FINGER UP.")
                    fs_downup_state = 'fs_finger_up'
                    print_result()
                elif res[0][1] == '7':
                    pass
                else:
                    red_log(str(res) + " is unexpected in fs_downup_state")

        # find onAuthenticate
        res = re.findall(time_pattern+r"FingerprintService: onAuthenticated, fingerId = (-?[0-9]+)", line)
        if len(res) > 0:
            #blue_log(res)
            if len(res[0]) > 1 and res[0][1] != '':
                green_log(res[0][0] + " Authenticated result: " + str(res[0][1]))
                result_map['auth_time'] = res[0][0]
                if res[0][1] == '0':
                    result_map['auth_result'] = "fail"
                else:
                    result_map['auth_result'] = "success"
                result_map['auth_fid'] = res[0][1]
                process_state = 'idle'
                if fs_downup_state == 'fs_finger_up':
                    fu2auth_time = parser.parse(res[0][0]) - lastFuTime
                    result_map['fu2auth_time'] = fu2auth_time.days * 24 * 60 * 60 * 1000 + fu2auth_time.seconds * 1000 + fu2auth_time.microseconds / 1000
                    yellow_log("FINGER UP happened before Authenticate returned, diff=" + str(result_map['fu2auth_time']) + "ms")
                print_result()

        # find Enrollment
        res = re.findall(time_pattern+r"(onEnrollResult\(fid=[0-9]+, gid=0, rem=[0-9]+\)|onEnrollmentHelp--> helpMsgId:[0-9]+)", line)
        if len(res) > 0:
            blue_log(res)
            if len(res[0]) > 1 and res[0][1] != '':
                pass

        # find fail reason
        res = re.findall(time_pattern+r"(PROFILING.*?|acquiredInfo = [0-9]+, vendorCode = [0-9]+|SynaFP.*?Latent Image.*?|SynaFP.*?finger lifted.*?|FINGERPRINT_ACQUIRED_.*?)\n", line)
        if len(res) > 0:
            #blue_log(res)
            if process_state == "processing":
                result_map['auth_fail_reason'].append(res)
            else:
                red_log(str(res) + " is unexpected")

        # find screen on or screen off state
        #res = re.findall(time_pattern+r"FingerprintService: state ([0-9]+)", line)
        res = re.findall(time_pattern+r"DisplayUtils: onEvent = (.*?)[,\n]", line)
        if len(res) > 0:
            #blue_log(str(res))
            if len(res[0]) > 1 and res[0][1] != '':
                if (screen_onoff_state == 'idle' or screen_onoff_state == 'screen_on') and res[0][1] == 'aod_in':
                    yellow_log("\n<<================================<<")
                    yellow_log(res[0][0] + " SCREEN OFF")
                    yellow_log(">>================================>>\n")
                    screen_onoff_state == 'screen_off'
                elif (screen_onoff_state == 'idle' or screen_onoff_state == 'screen_off') and res[0][1] == 'screen_on':
                    yellow_log("\n<<================================<<")
                    yellow_log(res[0][0] + " SCREEN ON")
                    yellow_log(">>================================>>\n")
                    screen_onoff_state == 'screen_on'
                else:
                    red_log(str(res) + " is unexpected in screen_onoff_state")

        # find power key event
        res = re.findall(time_pattern+r"MzPhoneWindowManager.*?keycode=26 (down|up)", line)
        if len(res) > 0:
            #blue_log(str(res))
            if len(res[0]) > 1 and res[0][1] != '':
                if (powkey_downup_state == 'idle' or powkey_downup_state == 'powkey_up') and res[0][1] == 'down':
                    blue_log(res[0][0] + " POWER KEY DOWN")
                    lastPowFdTime = parser.parse(res[0][0])
                    if powkey_downup_state == 'powkey_up':
                        fd2fu_time = parser.parse(res[0][0]) - lastPowFuTime
                        fd2fu_time_ms = fd2fu_time.days * 24 * 60 * 60 * 1000 + fd2fu_time.seconds * 1000 + fd2fu_time.microseconds / 1000
                        cyan_log("Last power key up to current power key down time: " + str(fd2fu_time_ms) + "ms")
                    powkey_downup_state = 'powkey_down'
                elif (powkey_downup_state == 'powkey_down') and res[0][1] == 'up':
                    blue_log(res[0][0] + " POWER KEY UP")
                    lastPowFuTime = parser.parse(res[0][0])
                    powkey_downup_state = 'powkey_up'
                else:
                    red_log(str(res) + " is unexpected in powkey_downup_state")


