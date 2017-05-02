# -*- coding: utf-8 -*-
__author__ = 'juraseg'
import urlparse

from torctl import TorCtl

def _tor_new_id(host, port):
    conn = TorCtl.connect(controlAddr=host, controlPort=port)
    if conn:
        TorCtl.Connection.send_signal(conn, "NEWNYM")

spider_system_ip = '148.251.79.44'

instances = [
    'tormain',
    'monkeyoffice',
    'musicroom',
    'camskill',
    'msg_amazon2'
]

proxy_ports = {
    'tormain': [8123, 8122, 8124, 8126, 8128],  # 8123 is port of load-balancing proxy
    'monkeyoffice': [8125],
    'musicroom': [8127],
    'camskill': [8129],
    'msg_amazon2': [8130]
}

control_ports = {
    'tormain': [9051, 9053, 9057, 9063],
    'monkeyoffice': [9055],
    'musicroom': [9059],
    'camskill': [9071],
    'msg_amazon2': [9065]
}

def get_tor_instance(proxy_str):
    url_parsed = urlparse.urlparse(proxy_str)
    # only locally running tor instances
    if url_parsed.hostname != 'localhost' \
            and url_parsed.hostname != '127.0.0.1' \
            and url_parsed.hostname != spider_system_ip:
        return None

    for tor_instance, tor_ports in proxy_ports.items():
        if url_parsed.port in tor_ports:
            return tor_instance
    return None

def _renew_ip_tor(tor_instance_name):
    if tor_instance_name not in control_ports:
        return
    for port in control_ports[tor_instance_name]:
        _tor_new_id('localhost', port)

def renew_ip_tor(proxy_str):
    tor_instance_name = get_tor_instance(proxy_str)
    if tor_instance_name:
        _renew_ip_tor(tor_instance_name)
        return True
    else:
        return False
