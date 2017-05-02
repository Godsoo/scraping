import os
import ConfigParser

SMTP_USER = 'SMTP_Injection'
SMTP_FROM = 'reporting@competitormonitor.com'
SMTP_PASS = '3eef967340aa0546a6eb2f722bea5d922ad63d6e'
SMTP_HOST = 'smtp.sparkpostmail.com'
SMTP_PORT = 587

EMAIL_MESSAGES = {
    'running': {
        'subject': '[CM - %(spider)s] Crawl started',
        'body': 'Crawl started for spider %(spider)s'
    },
    'processing_finished': {
        'subject': '[CM - %(spider)s] Crawl finished',
        'body': 'The crawl was finished for %(spider)s'
    },
    'errors_found': {
        'subject': '[CM - %(spider)s] Errors found',
        'body': 'Errors found for the last crawl of %(spider)s'
    },
    'upload_finished': {
        'subject': '[CM - %(spider)s] Upload finished',
        'body': 'Upload finished for %(spider)s'
    },
    'upload_errors': {
        'subject': '[CM - %(spider)s] Upload finished',
        'body': 'Errors found for the upload of changes for %(spider)s'
    }
}

server_host = '176.9.139.235'
server_user = 'compmon'
server_pass = '24orWWoS'

SERVERS = {'s1': {'host': '176.9.139.235', 'user': 'compmon', 'password': '24orWWoS', 'port': 2777},
           's2': {'host': '78.46.103.233', 'user': 'compmon', 'password': 'Za3f44y', 'port': 22},
           's3': {'host': '78.46.90.119', 'user': 'compmon', 'password': '24orWWoS', 'port': 22}}

new_system_api_roots = {
    'new_system': 'http://5.9.94.52:6543',
    'lego_system': 'http://5.9.94.52:6542',
}

api_key = '3Df7mNg'

upload_destinations = {
    'old_system': {
        'folder': '/home/compmon/data/',
        'folder_meta': '/home/compmon/data/meta',
        'type': 'old',
        'server': 's1'
    },
    'keter_system': {
        'folder': '/home/compmon/compmon2/data_importers/keter/changes/',
        'folder_meta': '/home/compmon/compmon2/data_importers/keter/metadata_changes',
        'folder_additional': '/home/compmon/compmon2/data_importers/keter/additional_changes',
        'type': 'new',
        'server': 's2'
    },
    'new_system': {
        'folder': '/home/compmon/compmon2/data_importers/changes/',
        'folder_meta': '/home/compmon/compmon2/data_importers/metadata_changes',
        'folder_additional': '/home/compmon/compmon2/data_importers/additional_changes',
        'folder_full_listing': '/home/compmon/compmon2/data_importers/full_exports',
        'folder_full_listing_meta': '/home/compmon/compmon2/data_importers/full_exports_metadata',
        'type': 'new',
        'server': 's2'
    },
    'orange_system': {
        'folder': '/home/compmon/orange_compmon/data_importers/changes/',
        'folder_meta': '/home/compmon/orange_compmon/data_importers/metadata_changes',
        'folder_additional': '/home/compmon/orange_compmon/data_importers/additional_changes',
        'folder_full_listing': '/home/compmon/orange_compmon/data_importers/full_exports',
        'folder_full_listing_meta': '/home/compmon/orange_compmon/data_importers/full_exports_metadata',
        'type': 'new',
        'server': 's2'
    },
    'telecoms_system': {
        'folder': '/home/compmon/telecoms_compmon/data_importers/changes/',
        'folder_meta': '/home/compmon/telecoms_compmon/data_importers/metadata_changes',
        'folder_additional': '/home/compmon/telecoms_compmon/data_importers/additional_changes',
        'type': 'new',
        'server': 's2'
    },
    'lego_system': {
        'folder': '/home/compmon/compmon2/data_importers/lego/changes/',
        'folder_meta': '/home/compmon/compmon2/data_importers/lego/metadata_changes',
        'type': 'new',
        'folder_additional': '/home/compmon/compmon2/data_importers/lego/additional_changes',
        'server': 's2'
    }
}

# deletions review settings start
check_deletions_members_ids = [2411, 31, 32, 33]
check_deletions_spiders = ['legousa-walmart.com',
                           'legousa-target.com',
                           'legousa-toywiz.com',
                           'lego_usa_etoys_com',
                           'legousa-etoys.com',
                           'lego-usa-amazon.com-direct',
                           'lego-usa-amazon.com',
                           'legousa-ebay.com',
                           'legousa-toysrus.com',
                           'legousa-barnesandnoble.com',
                           'lego_usa_boscovs_com',
                           'legousa-boscovs.com',
                           'legousa-newegg.com',
                           'legousa-rakuten.com',
                           'legousa-sears.com',
                           'legousa-kmart.com',
                           'arco-new-amazon.co.uk',
                           'arco-b-new-amazon.co.uk',
                           'arco-c-amazon.co.uk']
check_deletions_matched_max = 5
check_deletions_unmatched_max = 2
deletions_review_purge_days = 2
# deletions review settings end

SFTP_USER = 'compmon'
SFTP_HOST = '176.9.139.235'
SFTP_PASSWD = '24orWWoS'
SFTP_PORT = 2777

SFTP_DST = '/home/compmon/data/'
SFTP_DST_KETER = '/home/compmon/compmon/data_importers/changes'
SFTP_DST_NEW = '/home/compmon/compmon2/data_importers/changes'
SFTP_DST_META = '/home/compmon/data/meta'
SFTP_DST_META_KETER = '/home/compmon/compmon/data_importers/metadata_changes'
SFTP_DST_META_NEW = '/home/compmon/compmon2/data_importers/metadata_changes'
SFTP_DST_ADDITIONAL_NEW = '/home/compmon/compmon2/data_importers/additional_changes'

SFT_DST_MAP_IMAGES = '/home/compmon/map_images'
SFT_DST_HOME_IMAGES = '/home/compmon/home_images'

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))

MAX_SPIDER_IDLE = 20 * 60

TESTING_ACCOUNT = 1912

# Proxy Service

PROXY_SERVICE_HOST = 'http://88.198.32.57:8080/proxy_service/api/v1.0/'
PROXY_SERVICE_USER = 'griffin'
PROXY_SERVICE_PSWD = 'wells1897'

PROXY_SERVICE_ALGORITHM_CHOICES = (
    (1, 'round'),
    (2, 'random'),
)

# Celery

BROKER_URL = 'amqp://innodev:innodev@localhost:5672/spiders'

TOR_PROXY = 'http://127.0.0.1:8123'


CLIENTS_SFTP_HOST = 'sftp.competitormonitor.com'
CLIENTS_SFTP_PORT = 2222

here = os.path.dirname(os.path.abspath(__file__))
fname = os.path.join(here, 'config.ini')
if os.path.exists(fname):
    config = ConfigParser.RawConfigParser()
    config.read(fname)
    sections = [x for x in config.sections() if x.startswith('server_')]

    SERVERS = {}
    for s in sections:
        name = s.split('_')[1]
        host = config.get(s, 'host')
        user = config.get(s, 'user')
        password = config.get(s, 'password')
        port = int(config.get(s, 'port'))
        SERVERS[name] = {'host': host, 'user': user, 'password': password, 'port': port}

    tor_section = filter(lambda x: x == 'tor_main', config.sections())
    if tor_section:
        TOR_PROXY = config.get(tor_section[0], 'url')
    celery_section = filter(lambda x: x == 'celery', config.sections())
    if celery_section:
        BROKER_URL = config.get(celery_section[0], 'broker_url')

HG_EXEC = '/usr/bin/hg'
