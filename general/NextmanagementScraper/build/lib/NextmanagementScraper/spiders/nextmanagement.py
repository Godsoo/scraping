# -*- coding: utf-8 -*-
import scrapy
from scrapy.http import Request
from NextmanagementScraper.items import NextmanagementscraperItem
from scrapy.selector import Selector
import requests

class NextmanagementSpider(scrapy.Spider):
    name = "nextmanagement"
    start_urls = (
                    # 'http://www.nextmanagement.com/',
                    "http://www.nextmanagement.com/new-york",
                    "http://www.nextmanagement.com/paris",
                    "http://www.nextmanagement.com/london",
                    "http://www.nextmanagement.com/milan",
                    "http://www.nextmanagement.com/los-angeles",
                    "http://www.nextmanagement.com/miami",
    )

    def parse(self, response):
        for subcat_url in response.xpath("//nav[@id='occupation_nav']/ul/li/div/ul/li/a/@href").extract():
            yield Request(url=response.urljoin(subcat_url), callback=self.parse_subcategory)

    def parse_subcategory(self, response):
        item = NextmanagementscraperItem()
        item["subcategory_name"] = response.xpath("//section[@id='talents_index']/section/nav/a[@class='cur']/span/text()").extract_first()
        item["city"] = response.xpath("//div[@id='nav_btn_city']/a[@class='open location cur']/text()").extract_first()

        for portfolio in response.xpath("//section[@id='talents_index']/article/a"):
            item["portfolio_url"] = response.urljoin(portfolio.xpath("@href").extract_first())
            item["artist_name"] = portfolio.xpath(".//div[@class='meta']/h2[@class='name']/text()").extract_first()

            yield Request(url=item["portfolio_url"], callback=self.parse_detail, meta={"item": item})

    def parse_detail(self, response):
        csrf_token = response.xpath("//meta[@name='csrf-token']/@content").extract_first()
        item = response.meta["item"]

        item["biography_text"] = ""
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Bio')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/bio.json?undefined", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["biography_text"] = ' '.join(sel.xpath("//article//text()").extract()).strip()
            except:
                pass

        item["instagram_username"] = response.xpath("//ul[@id='attributes']/li[@class='follow']//span/a[contains(@href,'instagr.am')]/text()").extract_first()
        if item["instagram_username"] is None:
            item["instagram_username"] = ""

        item["img_urls"] = {"Portfolio": response.xpath("//ul[@class='images']/li/img/@src").extract()}
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Press')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/press.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Press"] = sel.xpath("//article//img/@src").extract()
            except:
                pass
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Polaroids')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/polaroids.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Polaroids"] = sel.xpath("//article//img/@src").extract()
            except:
                pass
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Editorial')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/editorial.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Editorial"] = sel.xpath("//article//img/@src").extract()
            except:
                pass
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Covers')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/covers.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Covers"] = sel.xpath("//article//img/@src").extract()
            except:
                pass
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Campaigns')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/campaigns.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Campaigns"] = sel.xpath("//article//img/@src").extract()
            except:
                pass
        if response.xpath("//nav[@id='filter_horizontal']/a/span[contains(text(),'Video')]"):
            try:
                sel = Selector(text=requests.get(url=response.url + "/video.json", headers={"X-CSRF-Token": csrf_token, "X-Requested-With": "XMLHttpRequest"}).json()["content"])
                item["img_urls"]["Video"] = sel.xpath("//article//iframe/@src").extract()
            except:
                pass

        yield item
