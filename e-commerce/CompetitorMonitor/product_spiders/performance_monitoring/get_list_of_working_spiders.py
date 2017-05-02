# -*- coding: utf-8 -*-
__author__ = 'juraseg'

import sys
import os.path

here = os.path.abspath(os.path.dirname(__file__))
product_spiders_folder = os.path.dirname(here)
root_folder = os.path.dirname(product_spiders_folder)
productspidersweb_folder = os.path.join(root_folder, 'productspidersweb')

sys.path.append(product_spiders_folder)
sys.path.append(root_folder)
sys.path.append(productspidersweb_folder)

from product_spiders.db import Session
from productspidersweb.models import Crawl, Spider

import re

def get_list_of_processes_with_usage():
    import subprocess

    try:
        cmd_output = subprocess.check_output(['ps -e -o "%cpu,%mem,command"'], shell=True)
    except subprocess.CalledProcessError as e:
        if e.returncode == 1:
            return []
        else:
            raise Exception("Error '%s' while executing command `%s`" % (str(e), 'ps -ef -o "%%cpu,%%mem,cmd"'))
    else:
        return cmd_output.split("\n")


def extract_data(line):
    parts = line.split()
    if not parts:
        return None
    cpu, mem, cmd = parts[0], parts[1], ' '.join(parts[2:])
    return {
        'cpu': float(cpu),
        'mem': float(mem),
        'cmd': cmd
    }

def check_is_spiders_process(cmd):
    if 'scrapyd.runner' in cmd and '_job=' in cmd:
        return True
    return False

jobid_regex = re.compile("_job=([a-zA-Z0-9]*)")
def extract_job_id(cmd):
    res = jobid_regex.findall(cmd)
    if not res:
        return None
    return res[0]

def get_spider_by_cmd(cmd):
    db_session = Session()

    jobid = extract_job_id(cmd)
    if not jobid:
        print "Couldn't extract jobid from: '%s'" % cmd
        return None

    jobid = unicode(jobid)
    spider = db_session.query(Spider)\
        .join(Crawl, Crawl.spider_id == Spider.id)\
        .filter(Crawl.jobid == jobid)\
        .filter(Crawl.status == 'running')\
        .first()

    if not spider:
        print "Couldn't find spider running with jobid: '%s'" % jobid

    db_session.close()

    return spider

def get_spiders_usage():
    processes = get_list_of_processes_with_usage()

    spiders = []

    for line in processes[1:]:
        data = extract_data(line)
        if not data:
            continue
        if not check_is_spiders_process(data['cmd']):
            continue

        spider = get_spider_by_cmd(data['cmd'])
        if not spider:
            print "Couldn't find spider for cmd: '%s'" % data['cmd']
            continue

        spiders.append({'spider': spider, 'cpu_usage': data['cpu'], 'mem_usage': data['mem']})

    return spiders

if __name__ == '__main__':
    spiders = get_spiders_usage()

    overall_cpu = sum([x['cpu_usage'] for x in spiders])
    overall_mem = sum([x['mem_usage'] for x in spiders])

    print ""
    print "Overall CPU usage: %0.3f" % overall_cpu
    print "Overall memory usage: %0.3f" % overall_mem

    spiders = sorted(spiders, key=lambda x: (x['cpu_usage'], x['mem_usage']), reverse=True)

    print ""
    print "Most offensive spiders:"
    for s in spiders[:3]:
        print "CPU: %0.3f, memory: %0.3f, name: %s" % (s['cpu_usage'], s['mem_usage'], s['spider'].name)