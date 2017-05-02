import sys
import os.path

HERE = os.path.dirname(os.path.abspath(__file__))
product_spiders_root = os.path.dirname(HERE)
project_root = os.path.dirname(product_spiders_root)

sys.path.append(project_root)

from product_spiders.db import Session
from product_spiders.scheduler import schedule_crawls_on_workers

here = os.path.abspath(os.path.dirname(__file__))


def check_pid(pid):
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

if __name__ == '__main__':
    pid_file_name = 'crawl.pid'
    pid_file = os.path.join(here, pid_file_name)
    if os.path.exists(pid_file):
        try:
            pid = int(open(pid_file).read())
        except ValueError:
            os.unlink(pid_file)
        else:
            if check_pid(pid):
                print 'The script is running with pid=%s' % pid
                sys.exit(1)
            else:
                os.unlink(pid_file)

    open(pid_file, 'w').write(str(os.getpid()))

    db_session = Session()
    spider_names = None
    if len(sys.argv) > 1:
        spider_names = sys.argv[1:]

    schedule_crawls_on_workers(db_session)

    os.unlink(pid_file)
