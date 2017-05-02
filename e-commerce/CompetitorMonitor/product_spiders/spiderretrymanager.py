# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from productspidersweb.models import (
    Spider,
    Crawl,
    CrawlHistory,
    UserLog,
)


class SpiderRetryManager(object):
    @classmethod
    def spider_should_retry_on_deletions(cls, db_session, errors):
        """
        Check if the spider should retry.
        """
        # FIXME: should not this method be somewhere in validation module?
        too_many_deletions = len(filter(lambda e: e[0] in (2, 20, 22), errors)) > 0
        if too_many_deletions:
            return True
        return False

    @classmethod
    def can_retry(cls, db_session, crawl_id):
        """
        Checks if spider can be retried (autoretry is enabled and number of retries is fine)
        """
        crawl = db_session.query(Crawl).get(crawl_id)
        if not crawl:
            return False
        spider = db_session.query(Spider).get(crawl.spider_id)
        if not spider:
            return False
        if spider.automatic_retry_enabled:
            max_retry_times = int(spider.automatic_retries_max or 3)
            first_crawl_history = db_session.query(CrawlHistory) \
                .filter(CrawlHistory.crawl_id == crawl_id) \
                .order_by(CrawlHistory.end_time.asc()) \
                .first()
            crawl_run_times = db_session.query(CrawlHistory) \
                .filter(CrawlHistory.crawl_id == crawl_id) \
                .count()
            if first_crawl_history and first_crawl_history.start_time:
                if ((datetime.now() - first_crawl_history.start_time) < timedelta(hours=6)) and \
                                (crawl_run_times - 1) < max_retry_times:
                    return True
        return False

    @classmethod
    def retry_spider(cls, db_session, crawl_id, reason):
        """
        Sets crawl for retry (if it can be retried)
        """
        if not cls.can_retry(db_session, crawl_id):
            return False
        crawl = db_session.query(Crawl).get(int(crawl_id))
        crawl.retry = True
        crawl.status = 'retry'
        crawl_history = db_session.query(CrawlHistory) \
            .filter(CrawlHistory.crawl_id == crawl.id) \
            .order_by(CrawlHistory.start_time.desc()).first()
        if crawl_history:
            discarted_reason = '[SpiderRetryManager] - Automatic retry - {}'.format(reason)
            crawl_history.discarted = True
            crawl_history.discarted_reason = discarted_reason
            db_session.add(crawl_history)
            db_session.commit()

            user_activity = UserLog()
            user_activity.username = 'system'
            user_activity.name = 'System'
            user_activity.spider_id = crawl.spider_id
            user_activity.activity = 'Automatic retry ({})'.format(reason)
            user_activity.date_time = datetime.now()
            db_session.add(user_activity)
            db_session.commit()

        return True
