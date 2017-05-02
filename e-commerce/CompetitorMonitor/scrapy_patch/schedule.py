import uuid
from scrapyd.webservice import WsResource

class Schedule(WsResource):

    def render_POST(self, txrequest):
        settings = txrequest.args.pop('setting', [])
        settings = dict(x.split('=', 1) for x in settings)
        args = dict((k, v[0]) for k, v in txrequest.args.items())
        project = args.pop('project')
        spider = args.pop('spider')
        #spiders = get_spider_list(project)
        #if not spider in spiders:
        #    return {"status": "error", "message": "spider '%s' not found" % spider}
        args['settings'] = settings
        jobid = args.pop('jobid', uuid.uuid1().hex)
        args['_job'] = jobid
        self.root.scheduler.schedule(project, spider, **args)
        return {"node_name": self.root.nodename, "status": "ok", "jobid": jobid}
