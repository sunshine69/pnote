#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, socket, threading, random
import time
from utils import *

def randomMAC():
        """ borrow from somewhere """
        mac = [ 0x00, 0x16, 0x3e,
                random.randint(0x00, 0x7f),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff) ]
        return ':'.join(map(lambda x: "%02x" % x, mac))

def m_server(dbcon):
    """ Multicast sever """
    ANY = "0.0.0.0"
    SENDERPORT=15000
    MCAST_ADDR = "239.192.168.1"
    MCAST_PORT = 16000
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.bind((ANY,SENDERPORT))
    #Tell the kernel that we want to multicast and that the data is sent to everyone (255 is the level of multicasting)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 255)
    station_id = get_dbconfig(dbcon, 'station_id')
    if not station_id:
        station_id = randomMAC()
        set_dbconfig(dbcon, 'station_id', station_id)
    user_name =  get_config_key('global','user_name','')
    if user_name == '':
        user_name = get_text_from_user(title='Enter user_name for this config', msg = 'Enter your user_name:', default_txt = os.getlogin(), size = -1, show_char = True, completion = True, search_dlg = None)
        save_config_key('global', 'user_name', user_name)
    port =  user_name =  get_config_key('global','tcp_port','16000')# use same as mcast port for now
    MSG = "%s:%s:%s" % (user_name, station_id, port)
    while 1:
            time.sleep(int(get_config_key('global','mcast_interval','30')) )
            sock.sendto(MSG,(MCAST_ADDR,MCAST_PORT) )

