import os
import sys
import inspect
from urlparse import urlparse
import json
from datetime import date, datetime, time
from sqlalchemy.ext.declarative import DeclarativeMeta
import string
from functools import wraps
import time as tm

from scrapy.spider import BaseSpider
import logging


CRAWL_STATUSES = ('scheduled', 'scheduled_on_worker', 'schedule_errors',
                  'running', 'crawl_finished', 'errors_found', 'processing_finished',
                  'upload_finished', 'upload_errors',
                  'retry')

UI_CRAWL_STATUSES = list(CRAWL_STATUSES[:])
UI_CRAWL_STATUSES.remove('crawl_finished')
UI_CRAWL_STATUSES.remove('scheduled')
UI_CRAWL_STATUSES.remove('scheduled_on_worker')

SPIDER_ERROR_STATUSES = ('possible', 'real', 'fixed')

HERE = os.path.dirname(__file__)
SPIDERS_PATH = os.path.abspath(os.path.join(HERE, '../../product_spiders/spiders'))
TEMP_ACCOUNT_PATH = os.path.join(SPIDERS_PATH, 'temp')
TEMP_SPIDER_PATH = os.path.join(TEMP_ACCOUNT_PATH, 'temp.py')
TEMP_SPIDER_COMPILED_PATH = os.path.join(TEMP_ACCOUNT_PATH, 'temp.pyc')

def get_account_spider_classes(dir_name):
    spider_files = []

    root, dirs, files = os.walk(os.path.join(SPIDERS_PATH, dir_name)).next()

    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            spider_files.append(f)

    spiders = []
    old_path = sys.path[:]
    sys.path.append(SPIDERS_PATH)
    for spider_file in spider_files:
        spider_module = __import__(dir_name + '.' + spider_file[:-3], fromlist=['*'])

        spider_classes = [cls for name, cls in inspect.getmembers(spider_module, inspect.isclass)
                          if issubclass(cls, BaseSpider) and cls.__module__ == spider_module.__name__ and getattr(cls, 'name')]

        spider_class = spider_classes[-1] if spider_classes else None
        if spider_class:
            spiders.append(spider_class)

    sys.path = old_path[:]

    return spiders

def get_account_spiders(dir_name):
    return [x.name for x in get_account_spider_classes(dir_name)]

def get_account_name(dir_name):
    old_path = sys.path[:]
    sys.path.append(SPIDERS_PATH)
    account_module = __import__(dir_name)
    sys.path = old_path[:]

    return account_module.ACCOUNT_NAME

def get_account_dir_name(account_name):
    root, dirs, files = os.walk(SPIDERS_PATH).next()

    for d in dirs:
        name = get_account_name(d)
        if name == account_name:
            return d
    return None

def get_account(account_name):
    dir_name = get_account_dir_name(account_name)
    if not dir_name:
        return None
    return [account_name, get_account_spiders(dir_name)]

def get_accounts():
    accounts = []
    root, dirs, files = os.walk(SPIDERS_PATH).next()

    for d in dirs:
        account_name = get_account_name(d)
        accounts.append([account_name, get_account_spiders(d)])

    return accounts

def get_spider_source_file(account_name, spider_name):
    account_dir = get_account_dir_name(account_name)

    root, dirs, files = os.walk(os.path.join(SPIDERS_PATH, account_dir)).next()

    spider_file = None  # default value to return if no file is found

    old_path = sys.path[:]
    sys.path.append(SPIDERS_PATH)
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            spider_module = __import__(account_dir + '.' + f[:-3], fromlist=['*'])

            spider_classes = [cls for name, cls in inspect.getmembers(spider_module)
                              if isinstance(cls, type)
                              and issubclass(cls, BaseSpider) and getattr(cls, 'name')]

            spider_class = spider_classes[-1] if spider_classes else None
            if spider_class and spider_class.name == spider_name:
                spider_file = os.path.join(SPIDERS_PATH, account_dir, f)
                break

    sys.path = old_path[:]

    return spider_file

def get_spider_module(account_name, spider_name):
    account_dir = get_account_dir_name(account_name)

    root, dirs, files = os.walk(os.path.join(SPIDERS_PATH, account_dir)).next()

    res_spider_module = None  # default value to return if no file is found

    old_path = sys.path[:]
    sys.path.append(SPIDERS_PATH)
    for f in files:
        if f.endswith('.py') and f != '__init__.py':
            spider_module = __import__(account_dir + '.' + f[:-3], fromlist=['*'])

            spider_classes = [cls for name, cls in inspect.getmembers(spider_module)
                              if isinstance(cls, type)
                              and issubclass(cls, BaseSpider) and getattr(cls, 'name')]

            spider_class = spider_classes[-1] if spider_classes else None
            if spider_class and spider_class.name == spider_name:
                res_spider_module = spider_module
                break

    sys.path = old_path[:]

    return res_spider_module

def get_logs_url(request, spider, db_session):
    from productspidersweb.models import WorkerServer
    worker_server = None
    if spider.worker_server_id:
        worker_server = db_session.query(WorkerServer).get(spider.worker_server_id)

    if not worker_server or worker_server.name == 'Default':
        url_data = urlparse(request.url)
        if not spider.enable_multicrawling:
            return '%s://%s:6800/logs/default/%s' % (url_data.scheme, url_data.netloc.split(':')[0], spider.name)
        else:
            return '%s://%s:6801/logs/default/%s' % (url_data.scheme, url_data.netloc.split(':')[0], spider.name)
    elif worker_server.name == 'Slave 2 (Scrapy 0.24)':
        return 'http://%s:6801/logs/default/%s/' % (worker_server.host, spider.name)
    elif worker_server.name == 'Slave 2 (Scrapy 1)':
        return 'http://%s:6805/logs/default/%s/' % (worker_server.host, spider.name)
    else:
        return '%slogs/default/%s' % (worker_server.scrapy_url, spider.name)


def get_log_crawl(c, spider, crawl):
    server = None
    if crawl.worker_server_id:
        q = c.execute("select * from worker_server where id = %s" % int(crawl.worker_server_id))
        server = q.fetchone()

    if not server:
        if spider.enable_multicrawling:
            scrapy_url = 'http://localhost:6801/'
        else:
            scrapy_url = 'http://localhost:6800/'
    else:
        scrapy_url = server['scrapy_url']

    log_url = scrapy_url + 'logs/default/%s/%s.log' % (spider.name, crawl.jobid)

    return log_url


class DatetimeJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return super(DatetimeJSONEncoder, self).default(obj)

def get_sqlalchemy_json_encoder(revisit_self=False, fields_to_expand=None, fields_to_ignore=None):
    if fields_to_expand is None:
        fields_to_expand = []
    if fields_to_ignore is None:
        fields_to_ignore = []
    _visited_objs = []

    class AlchemyEncoder(DatetimeJSONEncoder):
        def default(self, obj):
            if isinstance(obj.__class__, DeclarativeMeta):
                # don't re-visit self
                if revisit_self:
                    if obj in _visited_objs:
                        return None
                    _visited_objs.append(obj)

                # go through each field in this SQLalchemy class
                fields = {}
                for field in [x for x in dir(obj) if not x.startswith('_') and x != 'metadata' and x not in fields_to_ignore]:
                    val = obj.__getattribute__(field)

                    # is this field another SQLalchemy object, or a list of SQLalchemy objects?
                    if isinstance(val.__class__, DeclarativeMeta) or (
                    isinstance(val, list) and len(val) > 0 and isinstance(val[0].__class__, DeclarativeMeta)):
                        # unless we're expanding this field, stop here
                        if field not in fields_to_expand:
                            # not expanding this field: set it to None and continue
                            fields[field] = None
                            continue

                    fields[field] = val
                    # a json-encodable dict
                return fields

            return super(AlchemyEncoder, self).default(obj)

    return AlchemyEncoder

def save_uploaded_file(file_field, file_path):
    input_file = file_field.file

    output_file = open(file_path, 'wb+')

    # Finally write the data to the output file
    input_file.seek(0)
    while 1:
        data = input_file.read(2 << 16)
        if not data:
            break
        output_file.write(data)
    output_file.close()

def validate_spider(spider_path):
    dir_name, spider_file = os.path.split(spider_path)

    old_path = sys.path[:]
    sys.path.append(dir_name)

    try:
        spider_module = __import__(spider_file[:-3], fromlist=['*'])
    except ImportError:
        print "ImportError"
        return False
    except SyntaxError:
        print "SyntaxError"
        return False
    except StandardError:
        print "Other error"
        return False

    sys.path = old_path[:]

    return True

def get_spider_class(account_name, spider_name):
    spcls = None
    try:
        classes = get_account_spider_classes(get_account_dir_name(account_name))
        for cls in classes:
            if cls.name == spider_name:
                spcls = cls
    except StandardError as e:
        print e
        return None

    return spcls

def clear_temp_spider():
    if os.path.isfile(TEMP_SPIDER_PATH):
        os.remove(TEMP_SPIDER_PATH)
    if os.path.isfile(TEMP_SPIDER_COMPILED_PATH):
        os.remove(TEMP_SPIDER_COMPILED_PATH)

def account_exists(path):
    return os.path.exists(os.path.join(SPIDERS_PATH, path))

def create_spider_file(path, name, spider_id):
    spider_text = '''import os
from product_spiders.base_spiders.localspider import LocalSpider

HERE = os.path.dirname(os.path.abspath(__file__))

class LegoSpider(LocalSpider):
    name = '%s'
    path = os.path.join(HERE, '%s.csv')''' % (name, spider_id)

    with open(os.path.join(SPIDERS_PATH, path + '/' + name + '.py'), 'w') as f:
        f.write(spider_text)

def valid_spider_name(name):
    valid_chars = "-_() %s%s" % (string.ascii_letters, string.digits)
    for c in name:
        if c not in valid_chars:
            return False

    return True

def delete_spider(path, name):
    if os.path.exists(os.path.join(SPIDERS_PATH, path + '/' + name + '.py')):
        os.unlink(os.path.join(SPIDERS_PATH, path + '/' + name + '.py'))


def timeit_pyramid_view(view_fn):
    @wraps(view_fn)
    def fn(*args, **kwargs):
        start = tm.time()
        res = view_fn(*args, **kwargs)
        logging.info("View '%s' loaded for %0.3fs" % (view_fn.__name__, tm.time() - start))
        return res
    return fn