import os
import sys
import errno
import paramiko
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.append('..')
sys.path.append(os.path.abspath(os.path.join(HERE, '../../productspidersweb')))

import config
from db import Session
from productspidersweb.models import Spider, Crawl


def rexists(sftp, path):
    try:
        sftp.stat(path)
    except IOError, e:
        if e.errno == errno.ENOENT:
            return False
        raise
    else:
        return True


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

def read_pid(pid_file_path):
    with open(pid_file_path) as pid_f:
        return int(pid_f.read())

def write_pid(pid_file_path, pid):
    with open(pid_file_path, 'w') as pid_f:
        pid_f.write(str(pid))

def upload_recent_map_screenshots(db_session):
    '''
    Will upload to the remote server the latest screenshots if the changes
    already have been uploaded.
    If the crawl does not exists then it (the screenshot) will be removed from the file system.
    '''

    imagespath = os.path.join(config.DATA_DIR, 'map_images')
    scrpath = config.SFT_DST_MAP_IMAGES
    scrpath_tmp = os.path.join(config.SFT_DST_MAP_IMAGES, 'tmp')

    if os.path.exists(imagespath):
        all_images = filter(lambda f: f.endswith('.jpg'), os.listdir(imagespath))
        srv_details = config.SERVERS['s2']
        rsa_key = paramiko.RSAKey.from_private_key_file('/home/innodev/.ssh/id_rsa')
        transport = paramiko.Transport((srv_details['host'], srv_details['port']))
        transport.connect(username=srv_details['user'], pkey=rsa_key)
        sftp = paramiko.SFTPClient.from_transport(transport)
        if not rexists(sftp, scrpath):
            sftp.mkdir(scrpath)
        if not rexists(sftp, scrpath_tmp):
            sftp.mkdir(scrpath_tmp)
        for image_ in all_images:
            image_info = image_.split('__')[0]
            try:
                prefix, website_id, crawl_id, tstamp = image_info.split('_')
            except:
                prefix, website_id, crawl_id, tstamp, price = image_info.split('_')
            spider = db_session.query(Spider).filter(Spider.website_id == int(website_id)).first()
            if spider:
                crawl = db_session.query(Crawl)\
                    .filter(Crawl.id == int(crawl_id),
                            Crawl.spider_id == spider.id)\
                    .first()
            else:
                crawl = None
            if not crawl:
                os.unlink(os.path.join(imagespath, image_))
            elif crawl.status == 'upload_finished':
                try:
                    localpath = os.path.join(imagespath, image_)
                    remotepath = os.path.join(scrpath, image_)
                    remotepath_tmp = os.path.join(scrpath_tmp, image_)
                    sftp.put(localpath, remotepath_tmp)
                    sftp.rename(remotepath_tmp, remotepath)
                except Exception, e:
                    with open(os.path.join(imagespath, 'errors.log'), 'a') as f_err:
                        f_err.write('%s - %s\n' % (datetime.now(), e.message))
                else:
                    os.unlink(os.path.join(localpath))
        transport.close()

if __name__ == '__main__':
    pid_file_name = 'map_images_uploader.pid'
    pid_file_path = os.path.join(HERE, pid_file_name)
    if os.path.exists(pid_file_path):
        pid = read_pid(pid_file_path)
        if check_pid(pid):
            sys.exit()
        else:
            os.unlink(pid_file_path)

    write_pid(pid_file_path, os.getpid())

    db_session = Session()
    upload_recent_map_screenshots(db_session)
    db_session.close()
