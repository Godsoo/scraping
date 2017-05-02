# -*- coding: utf-8 -*-
"""
The script walks through "spiders" folder searching for files which use "144.76.118.46".
Then id add an import from config module and patches paramiko transport creation with constants from config
"""
import os

def file_has(filepath):
    with open(filepath) as f:
        if "host = '144.76.118.46'" in f.read():
            return True
    return False


def fix_file(filepath):
    print "Fixing file: {}".format(filepath)
    with open(filepath) as f:
        lines = list(f)
    latest_spiders_import = 0
    for i, line in enumerate(lines):
        if 'import' in line:
            if 'product_spiders' in line:
                latest_spiders_import = i
        if 'from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT' in line:
            latest_spiders_import = None
            break
    if latest_spiders_import is not None:
        lines.insert(latest_spiders_import, 'from product_spiders.config import CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT\n')
    new_lines = []
    for line in lines:
        if line.strip() == "host = '144.76.118.46'" or line.strip() == "#host = '144.76.118.46'":
            continue
        if line.strip() == 'port = 22' or line.strip() == "#port = 22":
            continue
        if line.strip() == 'transport = paramiko.Transport((host, port))' or line.strip() == "#transport = paramiko.Transport((host, port))":
            line = line.replace('transport = paramiko.Transport((host, port))', 'transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))')
        new_lines.append(line)
    with open(filepath, 'w') as f:
        f.writelines(new_lines)


def main():
    for dirpath, dirnames, filenames in os.walk('../spiders'):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                if file_has(filepath):
                    fix_file(filepath)


# auxiliary methods to get list of affected spiders
def file_has2(filepath):
    with open(filepath) as f:
        if "transport = paramiko.Transport((CLIENTS_SFTP_HOST, CLIENTS_SFTP_PORT))" in f.read():
            return True
    return False


def get_spider_name(filepath):
    with open(filepath) as f:
        for line in f:
            if line.startswith('    name =') or line.startswith('    name='):
                name = line.replace('    name =', '').replace('    name=', '').strip().strip('"').strip("'")
                return name


def main2():
    for dirpath, dirnames, filenames in os.walk('../spiders'):
        for filename in filenames:
            if filename.endswith('.py'):
                filepath = os.path.join(dirpath, filename)
                if file_has2(filepath):
                    name = get_spider_name(filepath)
                    # if name is not None:
                    #     print name
                    if name is None:
                        print "Couldn't get spider name from: %s" % filepath


if __name__ == '__main__':
    main2()