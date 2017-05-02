from __future__ import print_function
from scrapy.commands import ScrapyCommand
import pdb
import sys

class Command(ScrapyCommand):

    requires_project = True
    default_settings = {'LOG_ENABLED': False}

    def short_desc(self):
        return "List available spiders"

    def run(self, args, opts):
        sys.stdout = sys.__stdout__
        for s in sorted(self.crawler_process.spider_loader.list()):
            print(s)
