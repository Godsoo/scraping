import os
from fabric.api import run, cd
from fabric.state import env
from fabric.contrib.files import exists
import compileall

log_str = "[%s] %s: %s"

here = os.path.dirname(os.path.abspath(__file__))


def has_syntax_errors():
    d = os.path.join(here, 'product_spiders/spiders')
    if not compileall.compile_dir(d, quiet=1):
        return True

    return False


def run_bg(cmd, sockname='dtach', **kwargs):
    """
    Run task in background using dtach command
    :param cmd: command to run in background on target host
    :param sockname: socket name - useful when you want to
    :param kwargs:
    :return: result of running fabric.api.run command
    """
    if not exists("/usr/bin/dtach"):
        raise Exception("dtach is not installed on target host!")
    kwargs['pty'] = False
    return run('dtach -n `mktemp -u /tmp/{}.XXXX` {}'.format(sockname, cmd), **kwargs)


existing_dirs = ['spiders', 'fuzzywuzzy', 'performance_monitoring', 'tests', 'contrib', 'scripts',
                 'productsupdater', 'base_spiders', 'tasks', 'custom_crawl_methods',
                 'downloadermiddleware', 'emailnotifier', 'fixers', 'spidermanager']


def deploy(username=None, password=None, restart=0):
    if has_syntax_errors():
        print 'Some of the spiders contain syntax errors. Aborting deployment'
        return

    restart = int(restart)

    if restart:
        with cd('~/product-spiders/productspidersweb'):
            run('./stop.sh')

    with cd('~/product-spiders'):
        if username is not None and password is not None:
            print(log_str % (env.host_string, 'run', 'hg pull -uv'))
            res = run('hg pull -uv --config "auth.assembla.prefix=hg.assembla.com" --config "auth.assembla.username=%(username)s" --config "auth.assembla.password=%(password)s"' % {'username': username, 'password': password}, quiet=True)
            for res_str in res.split("\n"):
                print(log_str % (env.host_string, 'out', res_str))
        else:
            run('hg pull -uv')
        # update active changeset saved in file
        # this is needed because "hg summary" is too slow to be used by app, it needs cache
        run('/home/innodev/pythoncrawlers/bin/python ~/product-spiders/product_spiders/scripts/save_current_changeset_to_file.py')

    if restart:
        with cd('~/product-spiders/productspidersweb'):
            run('./start.sh')


def deploy_celery():
    with cd("~"):
        run_bg('supervisorctl -c .supervisor/supervisord.conf restart celery:*')


def deploy_webapp():
    with cd("~"):
        run('supervisorctl -c .supervisor/supervisord.conf restart spiders-web')


def deploy_slave():
    if has_syntax_errors():
        print 'Some of the spiders contain syntax errors. Aborting deployment'
        return
    with cd('~/product-spiders-repo'):
        run('hg pull -uv')
#        run('hg update')
        # run('cp  ~/product-spiders-repo/product_spiders/*.txt ~/product-spiders-multi/product_spiders/')
        run('cp ~/product-spiders-repo/product_spiders/productsupdater/*.py ~/product-spiders/product_spiders/productsupdater/')
        run('cp ~/product-spiders-repo/spider_stats/*.py ~/product-spiders/spider_stats')
        run('cp  ~/product-spiders-repo/product_spiders/productsupdater/metadataupdater/*.py ~/product-spiders/product_spiders/productsupdater/metadataupdater')
        run('cp -r ~/product-spiders-repo/product_spiders/base_spiders ~/product-spiders/product_spiders/')
        run('cp -r ~/product-spiders-repo/product_spiders/downloadermiddleware ~/product-spiders/product_spiders/')
        run('cp -r ~/product-spiders-repo/product_spiders/spidermanager ~/product-spiders/product_spiders/')
        run('cp -r ~/product-spiders-repo/product_spiders/emailnotifier ~/product-spiders/product_spiders/')
        run('cp -r ~/product-spiders-repo/product_spiders/custom_crawl_methods ~/product-spiders/product_spiders/')
        run('cp -r ~/product-spiders-repo/product_spiders/performance_monitoring ~/product-spiders/product_spiders/performance_monitoring')
        run('cp ~/product-spiders-repo/product_spiders/*.py ~/product-spiders/product_spiders/')

        run('cp ~/product-spiders/product_spiders/db_new.py ~/product-spiders/product_spiders/db.py')
        run('cp -r ~/product-spiders-repo/productspidersweb/* ~/product-spiders/productspidersweb/')
        run('cp -r ~/product-spiders-repo/product_spiders/tasks/* ~/product-spiders/product_spiders/tasks/')
        run('cp -r ~/product-spiders-repo/product_spiders/contrib/* ~/product-spiders/product_spiders/contrib/')
        run('cp -r ~/product-spiders-repo/product_spiders/fixers/* ~/product-spiders/product_spiders/fixers/')
        run('cp -r ~/product-spiders-repo/product_spiders/error_detection/* ~/product-spiders/product_spiders/error_detection/')
        run('cp -r ~/product-spiders-repo/product_spiders/scripts/* ~/product-spiders/product_spiders/scripts/')
        run('cp -r ~/product-spiders-repo/changes_updater/* ~/product-spiders/changes_updater/')
        run('cp ~/product-spiders-repo/zabbix/all_servers/check_bad_run.py ~/product-spiders/zabbix/all_servers/')

        d = os.path.join(here, 'product_spiders')
        dirs = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
        for d_ in dirs:
            # skipping folders starting with dot .
            if d_.startswith('.'):
                print 'skip dir', d_
                continue
            if d_ not in existing_dirs:
                print 'new dir', d_
                run('cp -r ~/product-spiders-repo/product_spiders/%s ~/product-spiders/product_spiders/' % d_)


def deploy_slave_repo(repo, directory):
    if has_syntax_errors():
        print 'Some of the spiders contain syntax errors. Aborting deployment'
        return
    with cd('~/{}'.format(repo)):
        run('hg pull -uv')
        run('cp ~/{}/product_spiders/productsupdater/*.py ~/{}/product_spiders/productsupdater/'.format(repo, directory))
        run('cp ~/{}/spider_stats/*.py ~/{}/spider_stats'.format(repo, directory))
        run('cp  ~/{}/product_spiders/productsupdater/metadataupdater/*.py ~/{}/product_spiders/productsupdater/metadataupdater'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/base_spiders ~/{}/product_spiders/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/downloadermiddleware ~/{}/product_spiders/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/spidermanager ~/{}/product_spiders/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/emailnotifier ~/{}/product_spiders/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/custom_crawl_methods ~/{}/product_spiders/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/performance_monitoring ~/{}/product_spiders/performance_monitoring'.format(repo, directory))
        run('cp ~/{}/product_spiders/*.py ~/{}/product_spiders/'.format(repo, directory))

        run('cp ~/{}/product_spiders/db_new.py ~/{}/product_spiders/db.py'.format(directory, directory))
        run('cp -r ~/{}/productspidersweb/* ~/{}/productspidersweb/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/tasks/* ~/{}/product_spiders/tasks/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/contrib/* ~/{}/product_spiders/contrib/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/fixers/* ~/{}/product_spiders/fixers/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/error_detection/* ~/{}/product_spiders/error_detection/'.format(repo, directory))
        run('cp -r ~/{}/product_spiders/scripts/* ~/{}/product_spiders/scripts/'.format(repo, directory))
        run('cp ~/{}/zabbix/all_servers/check_bad_run.py ~/{}/zabbix/all_servers/'.format(repo, directory))
        run('cp -r ~/{}/changes_updater/* ~/{}/changes_updater/'.format(repo, directory))

        d = os.path.join(here, 'product_spiders')
        dirs = [x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x))]
        for d_ in dirs:
            # skipping folders starting with dot .
            if d_.startswith('.'):
                print 'skip dir', d_
                continue
            if d_ not in existing_dirs:
                print 'new dir', d_
                run('cp -r ~/{}/product_spiders/{} ~/{}/product_spiders/'.format(repo, d_, directory))


def deploy_restart():
    if has_syntax_errors():
        print 'Some of the spiders contain syntax errors. Aborting deployment'
        return
    with cd('~/product-spiders/productspidersweb'):
        run('./stop.sh')
        run('./start.sh')


def deploy_zabbix():
    """
    needs root access
    """
    with cd('/home/innodev/product-spiders/zabbix/agents'):
        run('cp -v *.py /home/zabbix')
        run('chown zabbix:zabbix /home/zabbix/*.py')
        run('chmod +x /home/zabbix/*.py')
