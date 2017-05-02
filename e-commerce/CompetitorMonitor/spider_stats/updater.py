class SpiderStatsUpdater(object):
    def __init__(self, stats_db, stats_collector):
        self.stats_db = stats_db
        self.stats_collector = stats_collector

    def update_stats(self, servers):
        stats = self.stats_collector.get_global_stats_summary(servers)
        self.stats_db.insert_historical_stats(stats)