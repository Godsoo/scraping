import os
import sys
import re
from datetime import datetime
from collections import defaultdict
import traceback

from importutils import import_metadata_changes

here = os.path.abspath(os.path.dirname(__file__))
pid_file = os.path.join(here, 'import_metadata.pid')

def check_pid(pid):        
    """ Check For the existence of a unix pid. """
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    else:
        return True

if __name__ == '__main__':
    if os.path.exists(pid_file):
        pid = int(open(pid_file).read())
        if check_pid(pid):
            print 'The importer is already running with pid=%s' % pid
            sys.exit()
        else:
            os.unlink(pid_file)
            
    
    open(pid_file, 'w').write(str(os.getpid()))
    
    
    files = os.listdir(here)
    website_files = defaultdict(list)
    for f in files:
        m = re.search('(\d+)-(\d+)-\d+-\d+-\d+\.json$', f)
        if m:
            member_id, website_id = m.groups(0)
            website_files[int(website_id)].append(f)
            
    for website_id in website_files:
        files = website_files[website_id]
        files.sort()
        for f in files:
            print 'Importing ' + f
            try:
                import_metadata_changes(f)
                os.rename(os.path.join(here, f), os.path.join(here, 'backup/' + f))
            except Exception:
                print "Errors found %s" % os.path.join(here, 'errors/' + f.replace('json', 'log'))
                os.rename(os.path.join(here, f), os.path.join(here, 'errors/' + f))
                with open(os.path.join(here, 'errors/' + f.replace('json', 'log')), 'w') as error_f:
                    error_f.write(traceback.format_exc())
            
    os.unlink(pid_file)
