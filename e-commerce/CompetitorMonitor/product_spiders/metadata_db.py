import json
from json import encoder
from decimal import Decimal

from sqlalchemy.sql import text


class MetadataDB(object):
    def __init__(self, db_session, crawl_id, commit=True):
        self.crawl_id = crawl_id
        self.db_session = db_session
        self.db_session.execute('''create temp table metadata_%s (
                                   identifier varchar(256),
                                   crawl_id integer not null,
                                   meta text,
                                   CONSTRAINT identifier_crawl_id PRIMARY KEY(identifier,crawl_id))
                                   ON COMMIT preserve ROWS;''' % crawl_id)

        self.db_session.flush()

    def get_metadata(self, product_id, crawl_id):
        r = self.db_session.execute('select meta from metadata_%s where identifier'
                                    ' = :product_id and crawl_id= :crawl_id' % self.crawl_id, {'product_id': product_id,
                                                                                               'crawl_id': crawl_id}).fetchall()
        if r:
            meta = r[0][0]
            return json.loads(meta)
        else:
            return {}

    def set_metadata(self, product_id, crawl_id, metadata, insert=False):
        meta = json.dumps(metadata)

        if insert:
            self.db_session.execute('insert into metadata_%s values (:identifier, :crawl_id, :meta)' % self.crawl_id,
                {'identifier': product_id, 'crawl_id': crawl_id, 'meta': meta})
        else:
            self.db_session.execute('update metadata_%s set meta=:meta where identifier= :identifier '
                                    'and crawl_id= :crawl_id' % self.crawl_id, {'identifier': product_id,
                                                                'crawl_id': crawl_id, 'meta': meta})