import sys
import os
import csv
from cgi import escape
import json
import urllib2
from decimal import Decimal
from datetime import datetime
from datetime import timedelta
import StringIO
import time
import tempfile
from changes_updater import ChangesUpdater

from twisted.internet import task
from scrapy.xlib.pydispatch import dispatcher
from scrapy import signals
from sqlalchemy import and_, desc

from productsupdater import ProductsUpdater
from productsupdater.metadataupdater import MetadataUpdater
from metadata_db import MetadataDB
from contrib.compmon2 import Compmon2API


from export import (export_metadata_changes,
                    export_metadata, export_changes_new, export_additional_changes,
                    export_errors, export_delisted_duplicate_errors_new)
import shutil

from spiderretrymanager import SpiderRetryManager

HERE = os.path.dirname(os.path.abspath(__file__))

sys.path.append(os.path.abspath(os.path.join(HERE, '../productspidersweb')))

from productspidersweb.models import (
    Account,
    Crawl,
    CrawlHistory,
    Spider,
    DeletionsReview,
    CrawlStats,
    SpiderException,
    AdditionalFieldsGroup
)

from db import Session
from utils import get_receivers, DatetimeJSONEncoder
from emailnotifier import EmailNotifier, EmailNotifierException
from updatevalidator import UpdateValidator
import config

from celery import Celery


SPIDERS_NEW_UPDATER = ['lego-usa-amazon.com', 'bensons_mattressman.co.uk', 'arco-b-rs-online.com',
                       'heimkaup-eymundsson.is', 'arco-c-rs-online.com', 'arco-a-rs-online.com',
                       'sonae-amazon.es-marketplace', 'competitivecyclist.com', 'lego-fr-amazon.com',
                       'eglobalcentral_be', 'eglobalcentral_com_es',
                       'eglobalcentral_fr', 'eglobalcentral_fr', 'eglobalcentral.co.uk',
                       'sonae-pixmania.pt', 'pixmania.fr', 'wiggle.co.uk', 'crc-fr-wiggle.com',
                       'bedstoreuk_spider', 'hamiltonbeach-walmart.com', 'wiggle.com-de', 'jerseyelectricity-johnlewis.com',
                       'biw-mex-feed', 'alltricks.com', 'husqvarna-germany-amazon', 'crc-bike-discount.de', 'sonae-fnac.pt',
                       'mattelmegabloks-walmart.com', 'biw-usa-feed', 'vseinstrumenti_ru', 'crc_sp-probikeshop.fr',
                       'legouk-amazon.co.uk', 'arco-a-workwearexpress.com', 'crc_uk-winstanleysbikes.co.uk', 'biw-bra-feed',
                       'specialitycommerceus-amazon-marketplace', 'jerseyelectricity-amazon-buybox', 'heimkaup',
                       'biw_uk_amazon_direct', 'tyreleader.co.uk', 'legofrance-cdiscount.com', 'evanscycles.com',
                       'performancebike.com', 'getinthemix-ebay-junodjandstudio', 'biw-aus-feed', 'wiggle.com-es',
                       'arco-b-seton.co.uk', 'seton.co.uk', 'sonae-fnac.pt-direct', 'sigmasport-tredz.co.uk',
                       'legosw-amazon.co.uk', 'sigmasport-wiggle.co.uk', 'crc_fr-probikeshop.fr',
                       'thebookpeople-longtail-thebookpeople.co.uk', 'halfords.com', 'zyro-bikeinn.com', 'sonae-worten.pt',
                       'legodk-amazon.co.uk', 'fragrancedirect-debenhams.com', 'feelunique', 'allianceonline-nisbets.co.uk',
                       'pricepoint.com', 'hamiltonbeach-amazon.com', 'fragrancedirect-boots.com',
                       'householdessentials-googleshopping']

def _get_crawl_log_file_path(spider_name, log_name):
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.dirname(here)
    # Scrapy 0.14
    src = os.path.join(root, '.scrapy/.scrapy/scrapyd/logs/default/%s/%s' % (spider_name, log_name))
    if os.path.exists(src) and os.path.isfile(src):
        return src
    # Scrapy 0.16
    src = os.path.join(root, '.scrapy/scrapyd/logs/default/%s/%s' % (spider_name, log_name))
    if os.path.exists(src) and os.path.isfile(src):
        return src
    # Scrapy 1.0
    src = os.path.join(root, 'logs/default/%s/%s' % (spider_name, log_name))
    if os.path.exists(src) and os.path.isfile(src):
        return src
    return None


class DeleteCheckerExtension(object):
    def __init__(self):
        dispatcher.connect(self.spider_closed,
                           signal='export_finished')

    def spider_closed(self, spider, spider_stats):
        db_session = Session()
        current_crawl = db_session.query(Crawl).get(spider.crawl_id)
        website_id = current_crawl.spider.website_id
        member_id = current_crawl.spider.account.member_id
        if (current_crawl.spider.check_deletions or
            (member_id in config.check_deletions_members_ids
             and spider.name in config.check_deletions_spiders)):
                spider.log('DeletedCheckerExtension: Checking deletions...')
                products_updater = ProductsUpdater(db_session)
                deletions = []
                changes_old_file = os.path.join(config.DATA_DIR, '%s_changes_old.csv' % current_crawl.id)
                if os.path.exists(changes_old_file):
                    with open(changes_old_file) as f:
                        changes = products_updater.get_changes(f)
                        deletions = filter(lambda x: x['change_type'] == 'deletion', changes)

                if deletions:
                    matches = []
                    for upload_dst in current_crawl.spider.account.upload_destinations:
                        system_found = False
                        type_ = None
                        if upload_dst.name in config.new_system_api_roots:
                            system_found = True
                            compmon_host = config.new_system_api_roots[upload_dst.name]

                            url = ('%(compmon_host)s/api/get_matched_products.json?'
                                   'website_id=%(website_id)s&api_key=3Df7mNg' % {'compmon_host': compmon_host,
                                                                                  'website_id': website_id})
                            type_ = 'json'
                        elif upload_dst.name == 'old_system':
                            system_found = True
                            url = ('http://www.competitormonitor.com/login.html?action=get_products_api&'
                                   'website_id=%(website_id)s&matched=1' % {'website_id': website_id})
                            type_ = 'csv'
                        if system_found:
                            spider.log('Get matches => %s' % url)
                            matches += self._get_matches(website_id, url, type_)
                    spider.log('%s matches found' % len(matches))
                    matched_added = unmatched_added = 0
                    account_name = current_crawl.spider.account.name
                    site = current_crawl.spider.name
                    spider_id = current_crawl.spider.id
                    matches_idx = []
                    for match in matches:
                        matches_idx.append(match['identifier'])
                    spider.log('DeletedCheckerExtension: %s deletions found' % len(deletions))
                    for product in deletions:
                        if product['identifier']:
                            if product['identifier'] in matches_idx:
                                if matched_added != config.check_deletions_matched_max:
                                    matched_added += 1
                                    matched = True
                                else:
                                    continue
                            else:
                                if unmatched_added != config.check_deletions_unmatched_max:
                                    unmatched_added += 1
                                    matched = False
                                else:
                                    continue
                            deletions_review = DeletionsReview(crawl_date=datetime.now(),
                                                               account_name=account_name,
                                                               site=site,
                                                               product_name=product['name'].decode('utf-8'),
                                                               matched=matched,
                                                               url=product['url'].decode('utf-8'),
                                                               dealer=product['dealer'].decode('utf-8'),
                                                               status='new',
                                                               spider_id=spider_id,
                                                               crawl_id=spider.crawl_id)
                            db_session.add(deletions_review)
                            db_session.commit()
        db_session.close()


    def _get_matches(self, website_id, url, type_='json'):
        import logging
        logging.debug('-> get_matches(%s)' % (website_id))
        try:
            response = urllib2.urlopen(url)
            data = response.read()
            f = StringIO.StringIO(data)
            if type_ == 'json':
                products = json.load(f)
                return products.get('matches', [])
            else:
                csv_dict = csv.DictReader(f)
                matches = []
                for line in csv_dict:
                    matches.append(line)
                return matches
        finally:
            logging.debug('<- get_matches(%s)' % (website_id))


class UpdateManagerExtension(object):
    def __init__(self, crawler):
        self.crawler = crawler
        self.notifier = EmailNotifier(config.SMTP_USER, config.SMTP_PASS,
                                      config.SMTP_FROM, config.SMTP_HOST,
                                      config.SMTP_PORT)

        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal='export_finished')
        dispatcher.connect(self.request_scheduled, signal=signals.request_scheduled)

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_opened(self, spider):
        spider._crawler = self.crawler
        db_session = Session()

        if hasattr(spider, 'main_website_id'):
            main_spider = db_session.query(Spider).filter(Spider.website_id == spider.main_website_id).first()
            if main_spider:
                main_spider_last_crawl = db_session.query(Crawl) \
                    .filter(Crawl.spider_id == main_spider.id) \
                    .filter(Crawl.status == 'upload_finished') \
                    .order_by(desc(Crawl.crawl_date), desc(Crawl.id)) \
                    .first()
                if main_spider_last_crawl:
                    spider.main_website_last_crawl_id = main_spider_last_crawl.id

        products_updater = ProductsUpdater(db_session)
        crawl = products_updater.start_crawl(spider.name)
        if not crawl:
            self.correct_crawl = False
            return
        else:
            self.correct_crawl = True
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).first()
        if db_spider and db_spider.price_conversion_rate is not None:
            spider.price_conversion_rate = Decimal(db_spider.price_conversion_rate)

        spider.enable_metadata = db_spider.enable_metadata

        # send notification
        self._send_notification(crawl, spider)

        spider.crawl_id = crawl.id
        spider.website_id = db_spider.website_id

        # get previous crawl
        prev_crawl = db_session.query(Crawl)\
            .filter(Crawl.spider_id == db_spider.id,
                    Crawl.id != crawl.id)\
            .order_by(desc(Crawl.crawl_date),
                      desc(Crawl.id))\
            .first()
        if prev_crawl:
            spider.prev_crawl_id = prev_crawl.id
            spider.prev_crawl_date = prev_crawl.crawl_date

        # upload destinations
        account = db_session.query(Account).get(db_spider.account_id)
        if account.upload_destinations:
            spider.upload_dst = account.upload_destinations[0].name
        else:
            spider.upload_dst = None

        # if db_spider.use_tor:
        #     spider.stat_proxy = TOR_PROXY
        #     pass
        # elif db_spider.use_proxies:
        #     if db_spider.proxy_list_id:
        #         proxy_list = db_session.query(ProxyList).filter(ProxyList.id == db_spider.proxy_list_id).first()
        #         if not proxy_list:
        #             spider.stat_proxy = ';'.join(PROXIES)
        #         else:
        #             spider.stat_proxy = ';'.join(proxy_list.proxies.split('\n'))
        #     else:
        #         spider.stat_proxy = ';'.join(PROXIES)

        db_session.close()

    def request_scheduled(self):
        """ Closing spider if it's invalid, only possible when the spider already started """
        if not self.correct_crawl:
            import logging
            logging.error("UpdateManagerExtension: invalid crawl (no record in db): stopping")
            self.crawler.stop()

    def spider_closed(self, spider, spider_stats):
        # WARNING!!!
        # Here we load account and spider objects from database and expunge them from session
        # so they want affect database anymore when their data is accessed.
        # The reason to this is that when you get an object from database
        # the session blocks its table from modification until session is commited.
        # It also locks every time you access any of this object's field until session is commited.
        # We want to avoid this to be able to make changes to database structure without shutting down
        # all spiders.
        # We also load last two crawls, but later before validator
        if not self.correct_crawl:
            return

        #Enable new updater for all spiders
        if True or spider.name in SPIDERS_NEW_UPDATER:
            return self.spider_closed_new(spider, spider_stats)

        postprocess_start = time.time()
        db_session = Session()
        db_spider_expunged = db_session.query(Spider).filter(Spider.name == spider.name).first()
        db_session.expunge(db_spider_expunged)
        db_session.commit()

        current_crawl = db_session.query(Crawl).get(spider.crawl_id)
        # write crawl stats
        if not current_crawl.stats:
            current_crawl.stats = CrawlStats()
        current_crawl.stats.request_count = spider_stats.get('downloader/request_count', 0)
        current_crawl.stats.request_bytes = spider_stats.get('downloader/request_bytes', 0)
        current_crawl.stats.response_count = spider_stats.get('downloader/response_count', 0)
        current_crawl.stats.response_bytes = spider_stats.get('downloader/response_bytes', 0)
        current_crawl.stats.item_scraped_count = spider_stats.get('item_scraped_count', 0)
        current_crawl.stats.item_dropped_count = spider_stats.get('item_dropped_count', 0)
        stats = spider_stats
        stats['antibot_blocked_count'] = spider.antibot_blocked_count if hasattr(spider, 'antibot_blocked_count') else 0
        if hasattr(spider, '_proxies_list'):
            stats['proxies'] = ';'.join(spider._proxies_list)
        if hasattr(spider, 'full_run'):
            stats['BSM'] = True
            if spider.full_run:
                stats['full_run'] = True
            else:
                stats['full_run'] = False

        current_crawl.stats.stats_json = json.dumps(stats, cls=DatetimeJSONEncoder)

        db_session.add(current_crawl.stats)
        db_session.commit()

        previous_crawl = db_session.query(Crawl)\
                                   .filter(and_(Crawl.spider_id == db_spider_expunged.id,
                                                Crawl.id < spider.crawl_id))\
                                   .order_by(desc(Crawl.crawl_date), desc(Crawl.id)).first()

        old_products = []
        if previous_crawl:
            old_products = self._get_products(os.path.join('data', '%s_products.csv' % previous_crawl.id))

        products = self._get_products(os.path.join('data', '%s_products.csv' % current_crawl.id))

        import logging
        logging.error("SPIDER CLOSED: No. of products: %d" % len(products))

        metadata_updater = MetadataUpdater(getattr(spider, 'metadata_rules') if hasattr(spider, 'metadata_rules') else {})
        products_updater = ProductsUpdater(db_session, metadata_updater)
        changes, additions, deletions, updates = products_updater.compute_changes(spider.crawl_id, old_products, products,
                                                                                  db_spider_expunged.silent_updates)
        additional_changes = products_updater.compute_additional_changes(spider.crawl_id, old_products, products)

        logging.error('Finished calculating changes')

        path_new = os.path.join('data', '%s_changes_new.csv' % current_crawl.id)
        path_additional = os.path.join('data/additional', '%s_changes.json-lines' % current_crawl.id)

        export_changes_new(path_new, changes, spider.website_id)
        logging.error('Finished exporting changes')

        export_additional_changes(path_additional, additional_changes)
        logging.error('Finished exporting additional changes')

        metadata_changes = []
        immutable_metadata = ''
        reviews_count = 0

        if spider.enable_metadata:
            meta_db = MetadataDB(db_session, current_crawl.id)

            if db_spider_expunged.immutable_metadata:
                immutable_metadata = db_spider_expunged.immutable_metadata

            # compute metadata changes
            old_meta = []
            if previous_crawl:
                old_meta = self._get_products_metadata(os.path.join('data/meta', '%s_meta.json' % previous_crawl.id),
                                                       "json", metadata_db=meta_db, crawl_id=previous_crawl.id)
                if not old_meta:
                    old_meta = self._get_products_metadata(os.path.join('data/meta', '%s_meta.json-lines' % previous_crawl.id),
                                                           "json-lines", metadata_db=meta_db,
                                                           crawl_id=previous_crawl.id)

            meta = self._get_products_metadata(os.path.join('data/meta', '%s_meta.json' % current_crawl.id), "json",
                                               metadata_db=meta_db, crawl_id=current_crawl.id)
            if not meta:
                meta = self._get_products_metadata(os.path.join('data/meta', '%s_meta.json-lines' % current_crawl.id),
                                                   "json-lines", metadata_db=meta_db, crawl_id=current_crawl.id)

            if previous_crawl:
                meta = products_updater.merge_products(old_meta, meta, meta_db, current_crawl.id, previous_crawl.id)

            export_metadata(os.path.join('data/meta', '%s_meta.json-lines' % current_crawl.id), meta, meta_db,
                            current_crawl.id)
            metadata_changes = products_updater.compute_metadata_changes(spider.crawl_id, old_meta, meta, meta_db,
                                                                         current_crawl.id,
                                                                         previous_crawl.id if previous_crawl else None)
            export_metadata_changes(os.path.join('data/meta', '%s_meta_changes.json-lines' % current_crawl.id),
                                    metadata_changes)

            # count reviews
            for p in meta:
                metadata = meta_db.get_metadata(p['identifier'], current_crawl.id)
                if metadata and 'reviews' in metadata:
                    reviews_count += len(metadata['reviews'])
            logging.error('Finished exporting metadata')
        logging.error('Finished exporting')

        path_errors = os.path.join('data', '%s_errors.csv' % current_crawl.id)

        errors = []

        # spider error alerts
        if hasattr(spider, 'errors'):
            spider_error_alerts = spider.errors
        else:
            spider_error_alerts = None

        # Connection errors
        if spider_stats:
            max_errors_perc = 10
            errors_code = [403, 408, 500, 502, 503, 504]
            total_response = spider_stats.get('downloader/response_count', 0)
            if not total_response:
                errors.append((20, 'The crawler has received no response from the server'))
            total_error_response = spider_stats.get('downloader/exception_type_count/twisted.internet.error.TimeoutError', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.defer.TimeoutError', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.error.ConnectionDone', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.error.ConnectionRefusedError', 0)
            for code in errors_code:
                total_error_response += spider_stats.get('downloader/response_status_count/%s' % code, 0)
            if total_response and (float(total_error_response) / float(total_response) * 100 > max_errors_perc) \
               and not db_spider_expunged.ignore_connection_errors:
                errors.append((19, 'Too many responses with error code'))

            exceptions = []
            exc_count = 0
            db_session.query(SpiderException).filter(SpiderException.spider_id == db_spider_expunged.id).delete()
            for stat in spider_stats:
                if 'spider_exceptions' in stat and "/" in stat:
                    exception = stat.split("/")[1]
                    exceptions.append(exception)
                    exc_count += spider_stats[stat]
                    # errors.append("Exception raised when crawling: %s" % exception)

            if exceptions:
                s = SpiderException()
                s.spider_id = db_spider_expunged.id
                s.date = datetime.today().date()
                s.exceptions = '\n'.join(exceptions)
                s.log_name = current_crawl.jobid + '.log'
                # s.total = spider_stats.get('downloader/exception_count', 0)
                s.total = exc_count
                db_session.add(s)
                here = os.path.abspath(os.path.dirname(__file__))
                root = os.path.dirname(here)
                dst = os.path.join(root, 'data/exceptions')
                src = _get_crawl_log_file_path(spider.name, s.log_name)
                if src is None:
                    logging.error("Can't find log file for spider %s crawl %s" % (spider.name, current_crawl.jobid))
                else:
                    try:
                        shutil.copy(src, dst)
                    except IOError, e:
                        logging.error("Error copying log file %s to %s: %s" % (src, dst, e.message))

                db_session.commit()
        logging.error('Finished adding spider stats')

        validator = UpdateValidator()
        if not validator.valid_crawl(current_crawl,
                                     changes,
                                     metadata_changes,
                                     additional_changes,
                                     products,
                                     spider_error_alerts,
                                     immutable_metadata,
                                     reviews_mandatory=db_spider_expunged.reviews_mandatory,
                                     reviews_count=reviews_count):
            errors.extend(validator.errors)

        if errors:
            products_updater.set_with_errors(spider.crawl_id, errors)
            export_errors(path_errors, errors)
        else:
            products_updater.set_finished(spider.crawl_id)

        logging.error('Finished validation')

        # Save crawl history
        crawl_history = CrawlHistory(current_crawl)
        db_session.add(crawl_history)
        db_session.commit()

        # Should retry crawl?
        if SpiderRetryManager.spider_should_retry_on_deletions(db_session, errors):
            SpiderRetryManager.retry_spider(db_session, spider.crawl_id, reason='Too many deletions')

        postprocess_end = time.time()
        stats['postprocess_time'] = str(postprocess_end - postprocess_start)
        current_crawl.stats.stats_json = json.dumps(stats, cls=DatetimeJSONEncoder)
        db_session.add(current_crawl.stats)
        db_session.commit()

        # send notification
        self._send_notification(current_crawl, spider, errors)

        db_session.close()

    def get_spider_settings(self, spider, db_session):
        check_category_changes_members = [69]
        settings = {'max_additions': spider.additions_percentage_error or '',
                    'max_deletions': spider.deletions_percentage_error or '',
                    'max_updates': spider.price_updates_percentage_error or '',
                    'ignore_identifier_changes': spider.ignore_identifier_changes or False,
                    'max_out_stock': spider.stock_percentage_error or '',
                    'max_price_percentage_change': spider.max_price_change_percentage or '',
                    'immutable_metadata': spider.immutable_metadata or '',
                    'collect_reviews': spider.reviews_mandatory or False,
                    'ignore_additional_changes': spider.ignore_additional_changes.split('|')
                                                 if spider.ignore_additional_changes else '',
                    'silent_updates': spider.silent_updates,
                    'max_category_changes': '10' if spider.account.member_id
                                                    in check_category_changes_members else '',
                    'max_image_url_changes': spider.image_url_perc or '50',
                    'max_sku_changes': spider.sku_change_perc or '50'
                    }

        fields = []
        if spider.additional_fields_group_id:
            additional_fields_group = db_session.query(AdditionalFieldsGroup)\
                .get(spider.additional_fields_group_id)

            # if weekly updates enabled, then choose sunday
            if not additional_fields_group.enable_weekly_updates or datetime.now().weekday() != 6:
                fields = ['identifier', 'shipping_cost', 'sku', 'stock', 'dealer']
                if additional_fields_group.enable_url:
                    fields.append('url')
                if additional_fields_group.enable_image_url:
                    fields.append('image_url')
                if additional_fields_group.enable_brand:
                    fields.append('brand')
                if additional_fields_group.enable_category:
                    fields.append('category')
                if additional_fields_group.enable_name:
                    fields.append('name')

        settings['additional_fields'] = fields

        return settings

    def retrieve_all_products_website(self, spider, upload_dst, path):
        api_root = config.new_system_api_roots.get(upload_dst)
        if api_root:
            api = Compmon2API(api_root, config.api_key)
            api.retrieve_all_products_website(spider.website_id, path)


    def spider_closed_new(self, spider, spider_stats):
        postprocess_start = time.time()
        db_session = Session()
        db_spider_expunged = db_session.query(Spider).filter(Spider.name == spider.name).first()
        upload_dst = ''
        for dst in db_spider_expunged.account.upload_destinations:
            upload_dst = dst.name
            break

        db_session.expunge(db_spider_expunged)
        db_session.commit()

        current_crawl = db_session.query(Crawl).get(spider.crawl_id)
        # write crawl stats
        if not current_crawl.stats:
            current_crawl.stats = CrawlStats()
        current_crawl.stats.request_count = spider_stats.get('downloader/request_count', 0)
        current_crawl.stats.request_bytes = spider_stats.get('downloader/request_bytes', 0)
        current_crawl.stats.response_count = spider_stats.get('downloader/response_count', 0)
        current_crawl.stats.response_bytes = spider_stats.get('downloader/response_bytes', 0)
        current_crawl.stats.item_scraped_count = spider_stats.get('item_scraped_count', 0)
        current_crawl.stats.item_dropped_count = spider_stats.get('item_dropped_count', 0)
        stats = spider_stats
        stats['antibot_blocked_count'] = spider.antibot_blocked_count \
            if hasattr(spider, 'antibot_blocked_count') else 0
        if hasattr(spider, '_proxies_list'):
            stats['proxies'] = ';'.join(spider._proxies_list)
        if hasattr(spider, 'full_run'):
            stats['BSM'] = True
            if spider.full_run:
                stats['full_run'] = True
            else:
                stats['full_run'] = False

        current_crawl.stats.stats_json = json.dumps(stats, cls=DatetimeJSONEncoder)

        db_session.add(current_crawl.stats)
        db_session.commit()

        previous_crawl = db_session.query(Crawl)\
                                   .filter(and_(Crawl.spider_id == db_spider_expunged.id,
                                                Crawl.id < spider.crawl_id))\
                                   .order_by(desc(Crawl.crawl_date), desc(Crawl.id)).first()

        crawl_dir = os.path.join(tempfile.gettempdir(), '{}_changes_updater'.format(current_crawl.id))
        os.mkdir(crawl_dir)
        import logging

        if previous_crawl:
            shutil.copy(os.path.join('data', '{}_products.csv'.format(previous_crawl.id)),
                        os.path.join(crawl_dir, 'old_products.csv'))
            logging.info('Getting all products from api')
            try:
                self.retrieve_all_products_website(db_spider_expunged, upload_dst,
                                                   os.path.join(crawl_dir, 'all_products.csv'))
                logging.info('Done')
            except Exception:
                logging.info('Could not retrieve the products')

        shutil.copy(os.path.join('data', '{}_products.csv'.format(current_crawl.id)),
                    os.path.join(crawl_dir, 'new_products.csv'))

        if spider.enable_metadata:
            if previous_crawl:
                meta_f = os.path.join('data/meta', '{}_meta.json-lines'.format(previous_crawl.id))
                if os.path.exists(meta_f):
                    shutil.copy(meta_f, os.path.join(crawl_dir, 'old_meta.json-lines'))
            shutil.copy(os.path.join('data/meta', '{}_meta.json-lines'.format(current_crawl.id)),
                        os.path.join(crawl_dir, 'new_meta.json-lines'))

        products_updater = ProductsUpdater(db_session, None)
        settings = self.get_spider_settings(db_spider_expunged, db_session)
        changes_updater = ChangesUpdater(settings=settings)
        change_stats = changes_updater.update(crawl_dir)

        if os.path.exists(os.path.join(crawl_dir, 'old_products.csv')) and previous_crawl:
            shutil.copy(os.path.join(crawl_dir, 'old_products.csv'),
                        'data/{}_products.csv'.format(previous_crawl.id))
        if os.path.exists(os.path.join(crawl_dir, 'new_products.csv')):
            shutil.copy(os.path.join(crawl_dir, 'new_products.csv'),
                        'data/{}_products.csv'.format(current_crawl.id))

        shutil.copy(os.path.join(crawl_dir, 'changes.csv'), 'data/{}_changes_new.csv'.format(current_crawl.id))
        shutil.copy(os.path.join(crawl_dir, 'additional_changes.json-lines'),
                    'data/additional/{}_changes.json-lines'.format(current_crawl.id))
        if spider.enable_metadata:
            if previous_crawl:
                meta_f = os.path.join('data/meta', '{}_meta.json-lines'.format(previous_crawl.id))
                if os.path.exists(meta_f):
                    shutil.copy(os.path.join(crawl_dir, 'old_meta.json-lines'), meta_f)
            shutil.copy(os.path.join(crawl_dir, 'meta_changes.json-lines'),
                        'data/meta/{}_meta_changes.json-lines'.format(current_crawl.id))
            shutil.copy(os.path.join(crawl_dir, 'new_meta.json-lines'),
                        'data/meta/{}_meta.json-lines'.format(current_crawl.id))

        path_errors = os.path.join('data', '{}_errors.csv'.format(current_crawl.id))
        shutil.copy(os.path.join(crawl_dir, 'errors.csv'), path_errors)

        ident_changes_f = os.path.join(crawl_dir, 'identifier_changes.csv')
        if os.path.exists(ident_changes_f):
            shutil.copy(ident_changes_f,
                        'data/{}_{}_delisted_duplicate_errors.csv'.format(db_spider_expunged.website_id,
                                                                          current_crawl.id))
            with open(ident_changes_f) as ifd:
                ifd_reader = csv.DictReader(ifd)
                errors_count = 0
                for _ in ifd_reader:
                    errors_count += 1
                if errors_count:
                    export_delisted_duplicate_errors_new(current_crawl,
                                                         '{}_{}_delisted_duplicate_errors.csv'.\
                                                         format(db_spider_expunged.website_id, current_crawl.id))

        shutil.rmtree(crawl_dir)
        current_crawl.products_count = change_stats['products']
        current_crawl.additions_count = change_stats['new_products']
        current_crawl.deletions_count = change_stats['old_products']
        current_crawl.updates_count = change_stats['price_changes']
        current_crawl.additional_changes_count = change_stats['additional_changes']
        current_crawl.changes_count = current_crawl.additions_count + current_crawl.deletions_count + \
                                      current_crawl.updates_count
        db_session.add(current_crawl)
        db_session.commit()

        errors = []

        # spider error alerts
        if hasattr(spider, 'errors'):
            spider_error_alerts = spider.errors
        else:
            spider_error_alerts = None

        for error in spider_error_alerts or []:
            errors.append((21, escape("Spider error alert: {}".format(error.encode('ascii', 'ignore')))))

        # Connection errors
        if spider_stats:
            max_errors_perc = 10
            errors_code = [403, 408, 500, 502, 503, 504]
            total_response = spider_stats.get('downloader/response_count', 0)
            if not total_response:
                errors.append((20, 'The crawler has received no response from the server'))
            total_error_response = spider_stats.get('downloader/exception_type_count/twisted.internet.error.TimeoutError', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.defer.TimeoutError', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.error.ConnectionDone', 0)
            total_error_response += spider_stats.get('downloader/exception_type_count/twisted.internet.error.ConnectionRefusedError', 0)
            for code in errors_code:
                total_error_response += spider_stats.get('downloader/response_status_count/%s' % code, 0)
            if total_response and (float(total_error_response) / float(total_response) * 100 > max_errors_perc) \
               and not db_spider_expunged.ignore_connection_errors:
                errors.append((19, 'Too many responses with error code'))

            exceptions = []
            exc_count = 0
            db_session.query(SpiderException).filter(SpiderException.spider_id == db_spider_expunged.id).delete()
            for stat in spider_stats:
                if 'spider_exceptions' in stat and "/" in stat:
                    exception = stat.split("/")[1]
                    exceptions.append(exception)
                    exc_count += spider_stats[stat]
                    # errors.append("Exception raised when crawling: %s" % exception)

            if exceptions:
                s = SpiderException()
                s.spider_id = db_spider_expunged.id
                s.date = datetime.today().date()
                s.exceptions = '\n'.join(exceptions)
                s.log_name = current_crawl.jobid + '.log'
                # s.total = spider_stats.get('downloader/exception_count', 0)
                s.total = exc_count
                db_session.add(s)
                here = os.path.abspath(os.path.dirname(__file__))
                root = os.path.dirname(here)
                dst = os.path.join(root, 'data/exceptions')
                src = _get_crawl_log_file_path(spider.name, s.log_name)
                if src is None:
                    logging.error("Can't find log file for spider %s crawl %s" % (spider.name, current_crawl.jobid))
                else:
                    try:
                        shutil.copy(src, dst)
                    except IOError, e:
                        logging.error("Error copying log file %s to %s: %s" % (src, dst, e.message))

                db_session.commit()

        with open(path_errors, 'a') as f:
            writer = csv.writer(f)
            for code, msg in errors:
                writer.writerow([str(code), msg])

        if errors or change_stats['errors_found']:
            products_updater.set_with_errors(spider.crawl_id, errors)
        else:
            products_updater.set_finished(spider.crawl_id)

        if 'old_dups_count' in change_stats and change_stats['old_dups_count'] > 0:
            logging.error('Found {} duplicates in previous crawl results'.format(change_stats['old_dups_count']))
        if 'new_dups_count' in change_stats and change_stats['new_dups_count'] > 0:
            logging.error('Found {} duplicates in previous crawl results'.format(change_stats['new_dups_count']))
        if 'old_meta_dups_count' in change_stats and change_stats['old_meta_dups_count'] > 0:
            logging.error('Found {} duplicates in previous crawl results'.format(change_stats['old_meta_dups_count']))
        if 'new_meta_dups_count' in change_stats and change_stats['new_meta_dups_count'] > 0:
            logging.error('Found {} duplicates in previous crawl results'.format(change_stats['new_meta_dups_count']))

        stats['old_dups_count'] = change_stats.get('old_dups_count')
        stats['new_dups_count'] = change_stats.get('new_dups_count')
        stats['old_meta_dups_count'] = change_stats.get('old_meta_dups_count')
        stats['new_meta_dups_count'] = change_stats.get('new_meta_dups_count')

        logging.error('Finished validation')

        # Save crawl history
        crawl_history = CrawlHistory(current_crawl)
        db_session.add(crawl_history)
        db_session.commit()

        # Should retry crawl?
        if SpiderRetryManager.spider_should_retry_on_deletions(db_session, errors):
            SpiderRetryManager.retry_spider(db_session, spider.crawl_id, reason='Too many deletions')

        postprocess_end = time.time()
        stats['postprocess_time'] = str(postprocess_end - postprocess_start)
        stats['run_method'] = 'new'
        current_crawl.stats.stats_json = json.dumps(stats, cls=DatetimeJSONEncoder)
        db_session.add(current_crawl.stats)
        db_session.commit()

        # send notification
        self._send_notification(current_crawl, spider, errors)

        db_session.close()

    def _get_products(self, path):
        with open(path) as f:
            reader = csv.DictReader(f)
            order = reader.fieldnames

            products = []
            for product in reader:
                products.append({'url': product['url'],
                                 'name': product['name'],
                                 'price': Decimal(product['price'])
                                 if product['price'] else Decimal(0),
                                 'sku': product['sku'] if 'sku' in order else '',
                                 'identifier': product['identifier'] if 'identifier' in order else '',
                                 'category': product['category'] if 'category' in order else '',
                                 'brand': product['brand'] if 'brand' in order else '',
                                 'image_url': product['image_url'] if 'image_url' in order else '',
                                 'shipping_cost': Decimal(product['shipping_cost'] or 0) if 'shipping_cost'
                                                  in order and product['shipping_cost'] != '' else '',
                                 'stock': int(product['stock'])
                                 if 'stock' in order and product['stock'] is not None and product['stock'] != '' else '',
                                 'dealer': product['dealer'] if 'dealer' in order else ''})

        return products

    def _get_products_metadata(self, path, file_type="json", metadata_db=None, crawl_id=None):
        try:
            if file_type == "json":
                with open(path) as f:
                    data = json.load(f)
                    products = []
                    for product in data:
                        product['price'] = Decimal(product['price'] if product.get('price')
                                                   and product['price'] != 'None' else 0)
                        product['identifier'] = product.get('identifier', '')
                        product['sku'] = product.get('sku', '')
                        products.append(product)

                    return products
            elif file_type == "json-lines":
                products = []
                seen = set()
                from product_spiders.utils import read_json_lines_from_file_generator
                for i, product in enumerate(read_json_lines_from_file_generator(path)):
                    product['price'] = Decimal(product['price'] if product.get('price')
                                                   and product['price'] != 'None' else 0)
                    product['identifier'] = product.get('identifier', '')
                    product['sku'] = product.get('sku', '')
                    if metadata_db and product['identifier'] not in seen:
                        seen.add(product['identifier'])
                        metadata_db.set_metadata(product['identifier'], crawl_id, product['metadata'], insert=True)
                        product['metadata'] = None

                    products.append(product)
                    if i % 1000 == 0:
                        metadata_db.db_session.flush()

                metadata_db.db_session.flush()
                return products
            else:
                raise ValueError("Unknown metadata file format: %s" % file_type)
        except IOError:
            return []

    def _send_notification(self, crawl, spider, errors=None):
        receivers = get_receivers(crawl.spider, crawl.status)
        if receivers:
            subject = config.EMAIL_MESSAGES[crawl.status]['subject'] % {'spider': spider.name}
            body = config.EMAIL_MESSAGES[crawl.status]['body'] % {'spider': spider.name}
            if errors:
                for code, error in errors:
                    body += '\n' + error.decode('utf-8')
            try:
                self.notifier.send_notification(receivers, subject, body)
            except EmailNotifierException, e:
                print "Failed sending notification: %s" % e

class IdleSpiderExtension(object):
    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def __init__(self, crawler):
        self.crawler = crawler
        self.last_action_time = {}
        self.max_spider_idle = timedelta(seconds=config.MAX_SPIDER_IDLE)

        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed,
                           signal=signals.spider_closed)
        dispatcher.connect(self.item_scraped,
                           signal=signals.item_scraped)
        dispatcher.connect(self.item_dropped,
                           signal=signals.item_dropped)
        dispatcher.connect(self.engine_started,
                           signal=signals.engine_started)

    def engine_started(self):
        self.tsk = task.LoopingCall(self.close_idle_spiders)
        self.tsk.start(60)

    def spider_opened(self, spider):
        self.last_action_time[spider] = datetime.now()

    def spider_closed(self, spider):
        del self.last_action_time[spider]

    def close_idle_spiders(self):
        for spider in self.last_action_time:
            last_action_time = self.last_action_time[spider]
            if datetime.now() - last_action_time > self.max_spider_idle:
                self.crawler.engine.close_spider(spider, reason='idle_finished')

    def item_scraped(self, item, response, spider):
        self._item_found(spider)

    def item_dropped(self, item, spider, exception):
        self._item_found(spider)

    def _item_found(self, spider):
        self.last_action_time[spider] = datetime.now()


class MAPDeviationScreenshotExtension(object):

    def __init__(self, crawler):
        self.crawler = crawler
        self.datadir = os.path.join(config.DATA_DIR, 'map_data')
        self.imagesdir = os.path.join(config.DATA_DIR, 'map_images')
        self.datadir = os.path.join(config.DATA_DIR, 'map_data')
        self.celery = Celery(broker=config.BROKER_URL)

        if not os.path.exists(self.imagesdir):
            os.mkdir(self.imagesdir)

        if not os.path.exists(self.datadir):
            os.mkdir(self.datadir)

        self._init_signals()

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler)

    def spider_opened(self, spider):
        self._init_map_deviation(spider)

    def spider_closed(self, spider):
        if self._map_deviation_detection_active(spider):
            import pandas as pd

            # MAP deviation old data backup
            if os.path.exists(spider.map_deviation_csv):
                shutil.copy(spider.map_deviation_csv, spider.map_deviation_csv + '.bak')

            new_data = pd.concat([spider.new_map_deviation_data,
                spider.map_deviation_data[spider.map_deviation_data['identifier']
                                         .isin(spider.new_map_deviation_data['identifier']) == False]],
                      ignore_index=True)

            # MAP deviation new data exported to csv
            new_data.to_csv(spider.map_deviation_csv, index=False)

            self._clean_unused_data(spider)

    def item_scraped(self, item, response, spider):
        if self._map_deviation_detection_active(spider) and item.get('price'):
            spider.log('>>> MAP Extension: GET MATCH > %r' % item)
            match = self._get_match(item, spider)
            if match:
                spider.log('>>> MAP Extension: match found > %r' % match)
                already_exists = self.deviation_already_exists(item, spider)
                if self.is_below_map(item, match, spider):
                    ignore = False
                    if already_exists:
                        # If deviation already exists and the price is the same or above then it will be ignored.
                        # If 'ignore' is True it's going to consider that the page has not changed and the previous
                        # screenshot is still valid.
                        mapdev_data = spider.map_deviation_data
                        old_price = Decimal(mapdev_data[mapdev_data['identifier'] == item['identifier']].price.iloc[0])
                        new_price = Decimal(item['price'])
                        if old_price <= new_price:
                            ignore = True
                    # If ignore is True the screenshot will not be taken
                    spider.log('>>> MAP Extension: set below map item > %r | Ignore screenshot: %s' % (item, ignore))
                    self.set_below_map_item(item, response, spider, ignore)
                elif already_exists:
                    # If already exists and current price is above to MAP it's considered as "MAP deviation resolved"
                    spider.log('>>> MAP Extension: set item as resolved > %r' % item)
                    self.set_back_map_item(item, response, spider)
                else:
                    pass

    def is_below_map(self, item, match, spider):
        if hasattr(spider, 'map_price_field'):
            price_field = spider.map_price_field
            if match and (match[price_field] and Decimal(str(match[price_field])) > Decimal(str(item['price']))):
                return True
        else:
            if match and match['msrp']:
                spider.log('MAP Extension: check if %s > %s for sku %s' % (match['msrp'], item['price'], match['sku']))
                if Decimal(str(match['msrp'])) > Decimal(str(item['price'])):
                    return True
            elif match and match['price']:
                spider.log('MAP Extension: check if %s > %s for sku %s' % (match['price'], item['price'], match['sku']))
                if Decimal(str(match['price'])) > Decimal(str(item['price'])):
                    return True
        return False

    def deviation_already_exists(self, item, spider):
        mapdev_data = spider.map_deviation_data
        return not mapdev_data[mapdev_data['identifier'] == item['identifier']].empty

    def set_below_map_item(self, item, response, spider, ignore=False):
        # Save item data
        spider.new_map_deviation_data = \
            spider.new_map_deviation_data.append(
                [{'identifier': item['identifier'],
                  'price': item['price'],
                  'timestamp': datetime.now()}])

        # Take screenshot only if ignore is False
        if not ignore:
            if not hasattr(spider, 'errors'):
                spider.errors = []
            # spider.errors.append('MAP deviation detected => %s' % item['url'])

            self._take_screenshot(item, response, spider)

    def set_back_map_item(self, item, response, spider):
        # Remove item from map deviation data
        spider.map_deviation_data = spider.map_deviation_data[
            spider.map_deviation_data['identifier'] != item['identifier']]
        # Take screenshot
        self._take_screenshot(item, response, spider, 'back')

    def _take_screenshot(self, item, response, spider, prefix='below'):
        spider.log('>>> MAP Deviation: take screenshot > %r' % item)
        filename = ('%(prefix)s_%(website_id)s_%(crawl_id)s_%(timestamp)s_%(price)s__%(identifier)s' %
                     {'identifier': item['identifier'],
                      'timestamp': datetime.now(),
                      'website_id': spider.website_id,
                      'crawl_id': spider.crawl_id,
                      'prefix': prefix,
                      'price': item['price']})
        imageext = 'jpg'
        imagename = '%s.%s' % (filename, imageext)
        method = getattr(spider, 'map_screenshot_method', 'phantomjs')
        page_url = self._get_page_url(item, response, spider, filename, method)
        proxy = {}
        task_params = [page_url, imagename, method, proxy]
        if method != 'scrapy_response':
            req_proxy = response.request.meta.get('proxy')
            if req_proxy:
                proxy['host'] = req_proxy.split('http://')[-1]
            retry_blocked = getattr(spider, 'map_retry_blocked', False)
            task_params.append(retry_blocked)
            if retry_blocked and hasattr(spider, 'proxy_service_target_id'):
                task_params.append(spider.proxy_service_target_id)
                task_params.append(spider.proxy_service_profile)
                task_params.append(spider.proxy_service_types)
                task_params.append(spider.proxy_service_locations)
        self.celery.send_task('product_spiders.tasks.screenshots.take_screenshot',
                              task_params,
                              queue='screenshot')

    def _get_page_url(self, item, response, spider, filename, method):
        if method == 'scrapy_response':
            if hasattr(spider, 'map_screenshot_html_files'):
                html_path = spider.map_screenshot_html_files[item['identifier']]
                new_path = os.path.join(self.imagesdir, '%s.html' % filename)
                if html_path != new_path:
                    shutil.copy(html_path, new_path)
                    try:
                        os.unlink(html_path)
                    except:
                        pass
            else:
                html_path = os.path.join(self.imagesdir, '%s.html' % filename)
                with open(html_path, 'w') as f_html:
                    f_html.write(response.body)
            return filename + '.html'
        return item['url']

    def _init_signals(self):
        dispatcher.connect(self.spider_opened, signal=signals.spider_opened)
        dispatcher.connect(self.spider_closed, signal=signals.spider_closed)
        dispatcher.connect(self.item_scraped, signal=signals.item_scraped)

    def _init_map_deviation(self, spider):
        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).first()
        db_account = db_session.query(Account).get(db_spider.account_id)

        self._api_url = self._get_api_url(db_account)

        if db_account.map_screenshots or (hasattr(db_spider, 'map_screenshots') and db_spider.map_screenshots) \
           or (hasattr(spider, 'map_deviation_detection') and spider.map_deviation_detection):

            spider.map_deviation_detection = True

            try:
                import pandas as pd
            except ImportError:
                spider.log('MAPDeviationScreenshotExtension: pandas not found')
                spider.map_deviation_detection = False
                db_session.close()
                return

            spider.account_id = db_account.member_id
            # Get crawl id and website id
            if not hasattr(spider, 'crawl_id') or not hasattr(spider, 'website_id'):
                crawl = db_session.query(Crawl).filter(and_(Crawl.spider_id == db_spider.id)).order_by(desc(Crawl.id)).first()
                spider.crawl_id = crawl.id
                spider.website_id = db_spider.website_id

            if self._is_main_site(spider):
                spider.map_deviation_detection = False
                db_session.close()
                spider.log('>>> MAP Screenshots Extension: main site ignored')
                return

            try:
                spider.map_products_data = self._get_map_products(spider)
            except Exception, e:
                db_session.close()
                self.crawler.engine.close_spider(spider,
                    reason='MAPDeviationScreenshotExtension: error trying to get map prices data')
                raise e

            try:
                spider.map_matched_products = self._get_matched_products(spider, pd)
            except Exception, e:
                db_session.close()
                self.crawler.engine.close_spider(spider,
                    reason='MAPDeviationScreenshotExtension: error trying to get matched products')
                raise e

            try:
                spider.map_matches = self._get_matches(spider, pd)
            except Exception, e:
                db_session.close()
                self.crawler.engine.close_spider(spider,
                    reason='MAPDeviationScreenshotExtension: error trying to get matches')
                raise e

            spider.map_deviation_csv = self._get_map_deviation_filename(spider)
            if os.path.exists(spider.map_deviation_csv):
                try:
                    spider.map_deviation_data = pd.read_csv(spider.map_deviation_csv, dtype=pd.np.str)
                except Exception, e:
                    db_session.close()
                    self.crawler.engine.close_spider(spider,
                        reason='MAPDeviationScreenshotExtension: error trying to read "%s"' % spider.map_deviation_csv)
                    raise e
            else:
                spider.map_deviation_data = pd.DataFrame(columns=['identifier', 'price', 'timestamp'])

            if not hasattr(spider, 'map_join_on'):
                spider.map_join_on = [('sku', 'sku')]  # default

            spider.new_map_deviation_data = pd.DataFrame(columns=['identifier', 'price', 'timestamp'])
        else:
            spider.map_deviation_detection = False

        db_session.close()

    def _get_api_url(self, account):
        for upload_dst in account.upload_destinations:
            if upload_dst.name in config.new_system_api_roots:
                url = '%s/api/' % config.new_system_api_roots[upload_dst.name]
                return url

        return '%s/api/' % config.new_system_api_roots['new_system']

    def _get_map_products(self, spider):
        if hasattr(spider, 'map_products_csv'):
            if os.path.exists(spider.map_products_csv):
                try:
                    import pandas as pd
                    return pd.read_csv(spider.map_products_csv, dtype=pd.np.str)
                except Exception, e:
                    self.crawler.engine.close_spider(spider,
                        reason='MAPDeviationScreenshotExtension: error trying to read "%s"' % spider.map_products_csv)
                    raise e
        else:
            import pandas as pd
            from urllib2 import urlopen

            url = (self._api_url + 'get_map_prices.json?'
                'member_id=%(account_id)s&api_key=3Df7mNg' % {'account_id': spider.account_id})

            spider.log('>>> MAP Screenshots Extension: GET MAP PRICES => %s' % url)

            return pd.read_json(urlopen(url), dtype=pd.np.str)

    def _get_matched_products(self, spider, pd):
        page = 0
        count = 1000
        continue_next_page = True
        matches = []
        while continue_next_page:
            url = (self._api_url + 'get_matched_products_paged.json?'
                   'website_id=%(website_id)s&api_key=3Df7mNg&start=%(start)s&count=%(count)s' %
                   {'website_id': spider.website_id,
                    'start': page * count,
                    'count': count})
            spider.log('>>> MAP Screenshots Extension: GET MATCHED PRODUCTS => %s' % url)

            try:
                response = urllib2.urlopen(url, timeout=300)
                data = response.read()
                f = StringIO.StringIO(data)
                products = json.load(f)
                new_matches = products.get('matches', [])
            except Exception:
                continue_next_page = False
            else:
                matches.extend(new_matches)
                if len(new_matches) < count:
                    continue_next_page = False
                else:
                    page += 1

        spider.log('>>> MAP Screenshots Extension: %s MATCHED PRODUCTS LOADED' % len(matches))

        return pd.DataFrame(matches)

    def _get_matches(self, spider, pd):
        url = (self._api_url + 'get_matches.csv?'
            'member_id=%(member_id)s&website_id=%(website_id)s&api_key=3Df7mNg' %
            {'member_id': spider.account_id, 'website_id': spider.website_id})
        spider.log('>>> MAP Screenshots Extension: GET MATCHES => %s' % url)

        try:
            response = urllib2.urlopen(url)
            data = response.read()
            f = StringIO.StringIO(data)
            return pd.read_csv(f, dtype=pd.np.str)
        except Exception:
            if not hasattr(spider, 'errors'):
                spider.errors = []
            spider.errors.append('MAP Screenshots Extension: Could not get the matches')

        return pd.DataFrame()

    def _is_main_site(self, spider):
        from urllib2 import urlopen

        url = (self._api_url + 'get_account_info.json?'
            'member_id=%(account_id)s&api_key=3Df7mNg' % {'account_id': spider.account_id})

        spider.log('>>> MAP Screenshots Extension: GET ACCOUNT INFO => %s' % url)

        account_info = json.load(urlopen(url))
        if int(account_info['main_site']) == spider.website_id:
            return True

        return False

    def _get_map_deviation_filename(self, spider):
        return os.path.join(self.datadir, '%s_%s.csv' % (spider.account_id, spider.website_id))

    def _map_deviation_detection_active(self, spider):
        return spider.map_deviation_detection

    def _get_match(self, item, spider):
        if spider.account_id not in (2411, 12):
            matched_products = spider.map_matched_products
            if not matched_products.empty:
                matched = matched_products[matched_products['identifier'] == item['identifier']]
                if not matched.empty:
                    matches = spider.map_matches
                    matches_info = matches[matches['second_identifier'] == item['identifier']]
                    map_data = spider.map_products_data
                    match = map_data[map_data['identifier'] == matches_info['first_identifier'].iloc[0]]
                    if (not match.empty):
                        dict_match = dict(match.iloc[0])
                        if spider.account_id != 185 or dict_match['msrp']:
                            return dict_match

        if spider.account_id in (185, 153):
            # Only look at matched products if account is Household Essentials
            return None

        join_on = spider.map_join_on
        for join_main, join_comp in join_on:
            join_value = item.get(join_main)
            if join_value:
                map_data = spider.map_products_data
                match = map_data[map_data[join_comp] == join_value]
                if not match.empty:
                    dict_match = dict(match.iloc[0])
                    if spider.account_id not in (2411, 12, 185):
                        return dict_match
                    elif spider.account_id == 2411:
                        product_tags = str(match.tags.iloc[0]).split(',')
                        if dict_match['msrp']:
                            if 'MAP' in product_tags:
                                dict_match['msrp'] = round(Decimal(dict_match['msrp']) * Decimal('0.8'), 2)
                            return dict_match
                    elif spider.account_id in (12, 185) and dict_match['msrp']:
                        return dict_match
        return None

    def _clean_unused_data(self, spider):
        method = getattr(spider, 'map_screenshot_method', 'phantomjs')
        if method == 'scrapy_response':
            if hasattr(spider, 'map_screenshot_html_files'):
                for ident, filename in spider.map_screenshot_html_files.items():
                    if os.path.exists(filename):
                        os.unlink(filename)


class MethodDetectExtension(object):
    def __init__(self):
        dispatcher.connect(self.spider_opened,
                           signal=signals.spider_opened)

    def spider_opened(self, spider):
        from product_spiders.base_spiders.localspider import LocalSpider
        from product_spiders.base_spiders.bigsitemethodspider import BigSiteMethodSpider
        from product_spiders.base_spiders.primary_spider import PrimarySpider
        from product_spiders.base_spiders.secondary_spider import SecondaryBaseSpider
        try:
            from product_spiders.base_spiders.scrapelyxpathspider.spider import ScrapelySpider
        except ImportError:
            ScrapelySpider = None

        method_used = 'Normal'

        if isinstance(spider, BigSiteMethodSpider):
            method_used = 'BSM'
        elif isinstance(spider, LocalSpider):
            method_used = 'FMS'
        elif isinstance(spider, PrimarySpider):
            method_used = 'Primary'
        elif isinstance(spider, SecondaryBaseSpider):
            method_used = 'Secondary'
        elif ScrapelySpider is not None and isinstance(spider, ScrapelySpider):
            method_used = 'Scrapely'

        db_session = Session()
        db_spider = db_session.query(Spider).filter(Spider.name == spider.name).first()

        if db_spider.parse_method != method_used:
            db_spider.parse_method = method_used
            db_session.add(db_spider)
            db_session.commit()

        db_session.close()

class LogStatsExtension(object):
    """Log basic scraping stats periodically"""

    def __init__(self, stats, interval=60.0):
        self.stats = stats
        self.interval = interval
        self.multiplier = 60.0 / self.interval

    @classmethod
    def from_crawler(cls, crawler):
        interval = crawler.settings.getfloat('LOGSTATS_INTERVAL')
        if not interval:
            raise NotConfigured
        o = cls(crawler.stats, interval)
        dispatcher.connect(o.spider_opened,
                           signal=signals.spider_opened)
        dispatcher.connect(o.spider_closed,
                           signal='export_finished')
        return o

    def spider_opened(self, spider):
        try:
            self.filename = os.path.join('data', '%s_crawl_stats.csv' % spider.crawl_id)
            self.file = open(self.filename, 'w')
        except Exception:
            pass
        
        self.pagesprev = 0
        self.itemsprev = 0

        self.task = task.LoopingCall(self.log, spider)
        self.task.start(self.interval)

    def log(self, spider):
        try:
            items = self.stats.get_value('item_scraped_count', 0)
            pages = self.stats.get_value('response_received_count', 0)
            irate = (items - self.itemsprev) * self.multiplier
            prate = (pages - self.pagesprev) * self.multiplier
            self.pagesprev, self.itemsprev = pages, items
            self.file.write('{},{},{},{}\n'.format(items, pages, irate, prate))
            self.file.flush()
        except Exception:
            pass

    def spider_closed(self, spider, reason):
        try:
            self.file.close()
        except Exception:
            pass
        
        if self.task.running:
            self.task.stop()
