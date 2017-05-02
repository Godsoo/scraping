#!/home/innodev/pythoncrawlers/bin/python

'''
torinstances.py

This script initializes, stopped and restarted instances of Tor / Polipo.

You need to put the config files into ./tor and ./polipo directories
with the following names format:

./tor/torrc_<instance_name>
./polipo/config_<instance_name>

Then you need to add the instance name at the TOR_INSTANCES tuple declared in
the current file.

'''

import time
import os
from subprocess import call

from mako.template import Template

HERE = os.path.abspath(os.path.dirname(__file__))
TOR_DATA = os.path.join(HERE, 'tor')
POLIPO_DATA = os.path.join(HERE, 'polipo')


TOR_INSTANCES = (
    'tor1',
    'tor2',
    'tor3',
    'tor4',
    'tor5',
    'tor6',
    'tor7',
    'tor8',
    'tor9',
    'tor10',
    'tor11',
    'tor12',
    'tor13',
    'tor14',
    'tor15',
    'tor16',
    'tor17',
    'tor18',
    'tor19',
    'tor20',
    'monkeyoffice',
    'musicroom',
    'camskill',
    'msg_amazon2',
    'main',
)


def check_pid(pid):
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
    except OSError:
        return False
    else:
        return True


def get_pid(filename):
    if os.path.exists(filename):
        with open(filename) as f:
            pid = f.read()
            if pid and pid.strip().isdigit():
                return pid.strip()
    return None


def get_pids(instance):
    ''' Return tuple (<tor_pid>, <polipo_pid>) '''
    tor_file = os.path.join(TOR_DATA, '%s.pid' % instance)
    polipo_file = os.path.join(POLIPO_DATA, '%s.pid' % instance)
    return (get_pid(tor_file), get_pid(polipo_file))


def config_exist(instance):
    ''' Return True if both config files exist '''
    tor_file = os.path.join(TOR_DATA, 'torrc_%s' % instance)
    polipo_file = os.path.join(POLIPO_DATA, 'config_%s' % instance)
    if os.path.exists(tor_file) and os.path.exists(polipo_file):
        return True
    return False


def start_tor(instance):
    tor_file = os.path.join(TOR_DATA, 'torrc_%s' % instance)
    call(['tor', '-f', tor_file])


def start_polipo(instance):
    polipo_file = os.path.join(POLIPO_DATA, 'config_%s' % instance)
    call(['polipo', '-c', polipo_file])


def stop_tor(instance, pid):
    tor_file = os.path.join(TOR_DATA, '%s.pid' % instance)
    os.kill(int(pid), 9)
    os.unlink(tor_file)


def stop_polipo(instance, pid):
    polipo_file = os.path.join(POLIPO_DATA, '%s.pid' % instance)
    os.kill(int(pid), 9)
    os.unlink(polipo_file)

def restart_all():
    for instance in TOR_INSTANCES:
        print 'Restarting instance %s ...' % instance
        tor_pid, polipo_pid = get_pids(instance)
        print 'Stopping instance %s ...' % instance
        if check_pid(tor_pid):
            stop_tor(instance, tor_pid)
        if check_pid(polipo_pid):
            stop_polipo(instance, polipo_pid)
        time.sleep(1)
        print 'Starting instance %s ...' % instance
        start_tor(instance)
        start_polipo(instance)

def create_instance():
    instance_name = raw_input('New instance name: ')
    socks_port = raw_input('Socks port: ')
    control_port = raw_input('Control port: ')
    http_port = raw_input('HTTP port: ')

    torrc_tplt = open('torrc.mak').read()
    polipo_tplt = open('polipo_config.mak').read()

    new_torrc = Template(torrc_tplt).render(
        name=instance_name,
        socks_port=socks_port,
        control_port=control_port,
    )
    new_polipo_config = Template(polipo_tplt).render(
        name=instance_name,
        http_port=http_port,
        socks_port=socks_port,
    )

    with open(os.path.join(TOR_DATA, 'torrc_%s' % instance_name), 'w') as f:
        f.write(new_torrc)
    with open(os.path.join(POLIPO_DATA, 'config_%s' % instance_name), 'w') as f:
        f.write(new_polipo_config)



if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        action = sys.argv[1]
        instance = None
        if len(sys.argv) > 2:
            instance = sys.argv[2]
        if instance and not config_exist(instance):
            print 'Missing config file/files for instance %s' % instance
            sys.exit(1)
        if action == 'start':
            if instance:
                print 'Starting instance %s ...' % instance
                tor_pid, polipo_pid = get_pids(instance)
                if not check_pid(tor_pid):
                    start_tor(instance)
                else:
                    print 'Tor instance is already running with pid: %s' % tor_pid
                if not check_pid(polipo_pid):
                    start_polipo(instance)
                else:
                    print 'Polipo is already running with pid: %s' % polipo_pid
            else:
                print 'Starting all ...'
                for instance in TOR_INSTANCES:
                    print 'Starting instance %s ...' % instance
                    tor_pid, polipo_pid = get_pids(instance)
                    if not check_pid(tor_pid):
                        start_tor(instance)
                    else:
                        print 'Tor instance is already running with pid: %s' % tor_pid
                    if not check_pid(polipo_pid):
                        start_polipo(instance)
                    else:
                        print 'Polipo is already running with pid: %s' % polipo_pid
        elif action == 'stop':
            if instance:
                print 'Stopping instance %s ...' % instance
                tor_pid, polipo_pid = get_pids(instance)
                if check_pid(tor_pid):
                    stop_tor(instance, tor_pid)
                else:
                    print 'Tor instance is not running'
                if check_pid(polipo_pid):
                    stop_polipo(instance, polipo_pid)
                else:
                    print 'Polipo is not running'
            else:
                print 'Stopping all ...'
                for instance in TOR_INSTANCES:
                    print 'Stopping instance %s ...' % instance
                    tor_pid, polipo_pid = get_pids(instance)
                    if check_pid(tor_pid):
                        stop_tor(instance, tor_pid)
                    if check_pid(polipo_pid):
                        stop_polipo(instance, polipo_pid)
        elif action == 'restart':
            if instance:
                print 'Restarting instance %s ...' % instance
                tor_pid, polipo_pid = get_pids(instance)
                print 'Stopping instance %s ...' % instance
                if check_pid(tor_pid):
                    stop_tor(instance, tor_pid)
                if check_pid(polipo_pid):
                    stop_polipo(instance, polipo_pid)
                time.sleep(1)
                print 'Starting instance %s ...' % instance
                start_tor(instance)
                start_polipo(instance)
            else:
                print 'Restarting all ...'
                restart_all()
        elif action == 'new':
            create_instance()
        else:
            print 'Sorry, I can\'t recognize the action "%s"' % action
        print 'Done.'
    else:
        print 'Nothing to do'
