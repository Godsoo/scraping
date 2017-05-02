#encoding: utf8

import sys, os, json, re, random, time, datetime

from scrapex import *


def scrape_all_plans(target_csv_file='plans.csv'):
	
	"""
	readable url:
	https://www.whistleout.com.au/Broadband/Search?customer=Personal&showlessresults=false

	ajax url:
	
	https://www.whistleout.com.au/Ajax/Broadband/SearchResults/PagedResults?customer=Personal&current=0

	"""
	

	#the actual number of listings are much less than the stats say	
	base_ajax_url = 'https://www.whistleout.com.au/Ajax/Broadband/SearchResults/PagedResults?customer=Personal&current={current}'

	page = 0

	pagesize = 20

	while True:
		page += 1
		logger.info('plans page: %s', page)
		current = (page-1) * pagesize
		page_url = base_ajax_url.format(current=current)
		
		doc = s.load(page_url, ajax=True)
		if doc.status.code != 200:
			raise Exception('failed page: %s', page)

		plans = doc.q("//div[contains(@class,'results-item results-item-singleline')]")
		logger.info('plans: %s', len(plans))
		
		for plan in plans:
			plan_name = plan.x(".//a[h2]").rr('\s+',' ').trim()

			_id = plan.x(".//a[h2]/@href").rr('&search=\d+')
			
			assert _id, 'no _id: %s -- %s -- page %s' %( plan_name, plan.x(".//a[h2]/@href"), page)

			#modem options
			
			modem_options = _scrape_modem_options(plan.x(".//a[h2]/@href"))

			s.save([
				'_id', _id,
				'plan_name', plan_name,
				'supplier', plan.x(".//img[contains(@class,'brand-equalizer')]/@alt"),
				'contract', plan.x(".//button[strong[.='Contract']]/text()[last()]").replace('(').replace(')'),
				
				'features', plan.q(".//a[h2]/following-sibling::ul/li").join('\n'),
				'deal', plan.x(".//strong[.='Deal: ']/following-sibling::text()"),
				'connection', plan.x(".//div[@class='[ col-xs-12 ] [ sep-l-1 sep-l-0-xs position-static ]']//span[@class='label label-default font-5 c-brand-primary text-break']"),
				'data', plan.x(".//div[@class='[ col-xs-12 ] [ sep-l-1 position-static ]']//div[@class='font-6 font-7-xs mar-b-1 font-600']"),
				'data_note', plan.q(".//div[@class='[ col-xs-12 ] [ sep-l-1 position-static ]']//div[@class='font-6 font-7-xs mar-b-1 font-600']/following-sibling::div[not(contains(text(),'Data'))]").join('\n'),
				
				'price', plan.x(".//strong[@class='product-price font-9']"), #.rr('\s+',' '),
	
				'min_total_cost', plan.x(".//text()[contains(.,'Min. total cost')]").replace('Min. total cost'),


			] + modem_options	, 

			target_csv_file)	



		if len(plans) < pagesize:
			break

def _today():
	return time.strftime('%Y-%m-%d')

def _yesterday():
	now = datetime.datetime.now()

	yesterday = now - datetime.timedelta(days=1)
	
	yesterday = "{:%Y-%m-%d}".format(yesterday)

	return yesterday

def _latest_file():
	now = datetime.datetime.now()
	for i in xrange(1,1000):
		preday = now - datetime.timedelta(days=i)
		preday = "{:%Y-%m-%d}".format(preday)
		prefile = s.join_path( 'history/%s.csv'%preday)

		if os.path.exists(prefile):
			return prefile

	return None	#not found
	
def _record_key(r):
	# plan_name, supplier = r['plan_name'], r['supplier']
	# return slugify(u'%s %s' % (supplier, plan_name))

	return r['_id']

def _keys(records):
	keys = []
	for r in records:
		key = _record_key(r)
		if key in keys:
			logger.warn('duplicated key: %s -- %s', r['supplier'], r['plan_name'])
			continue

		keys.append(key)
	
	return keys

def _find_record(records, key):
	for r in records:
		_key = _record_key(r)
		if _key == key:
			return r

	return None	#not found

			
def compare_two_files(oldfile, currentfile):
	
	oldrecords = [r for r in common.read_csv(oldfile, 'dict')]

	currentrecords = [r for r in common.read_csv(currentfile, 'dict')]

	if test_mode:
		currentrecords = currentrecords[5:] #to create removed records

		for i, r in enumerate( currentrecords ):

			r['price'] = 'new price'
			r['connection'] = 'some new connection'

			if i == 10:
				break

	oldkeys = _keys(oldrecords)
	currentkeys = _keys(currentrecords)

	#outputs
	newrecords = []
	removedrecords = []
	changedrecords = []

	#looking for new records
	for r in currentrecords:
		key = _record_key(r)
		if key not in oldkeys:
			#new
			newrecords.append(r)

	#lookinf for removed records		
	for r in oldrecords:
		key = _record_key(r)
		if key not in currentkeys:
			#removed
			removedrecords.append(r)


	#looking for changed records
	
	headers = required_headers()


	allchanges = []
	for n in currentrecords:
		key = _record_key(n)
		
		o = _find_record(oldrecords, key)

		if o is None:
			#newly-added, ignore
			continue

		#ok, now the record is existing in both datasets
		changes = [] #changes of one record
		for h in headers:
			value_old = o[h]
			value_new = n[h]
			
			if value_new != value_old:
				#changed
			
				change = dict(
					header = h,
					value_old = value_old,
					value_new = value_new,


					)
				changes.append(change)
		if changes:
			allchanges.append(dict(
				full_name = u'%s %s'%(n['supplier'], n['plan_name']),
				url = n['_id'],
				changes = changes

				))


	logger.info('newrecords: %s', len(newrecords))
	logger.info('removedrecords: %s', len(removedrecords))
	logger.info('allchanges: %s', len(allchanges))

	_html_changes = format_changed_records(allchanges) if allchanges else """<b style="color: orange;">No records with changes found</b>"""
	_html_newrecords = format_new_or_removed_records(newrecords) if newrecords else """<b style="color: orange;">No new records found</b>"""
	_html_removedrecords = format_new_or_removed_records(removedrecords) if removedrecords else """<b style="color: orange;">No removed records found</b>"""

	html_all = u"""
	<h2>New Records</h2>
	{_html_newrecords}

	<h2>Removed Records</h2>
	{_html_removedrecords}

	<h2>Changed Records</h2>
	{_html_changes}
	
	""".format(_html_changes=_html_changes, _html_newrecords = _html_newrecords, _html_removedrecords=_html_removedrecords)


	if test_mode:
		s.write_json('allchanges.json', allchanges)	

		s.put_file('all.htm', html_all)


	return html_all	


def format_changed_records(allchanges):
	html = """<table border="1">
	<tr><th width="30%">=== Plan Name ===</th><th>==== Changes ====</th></tr>"""

	for r in allchanges:
		full_name, url, changes = r['full_name'], r['url'], r['changes']
		_html_changes = "<table>"
		for change in changes:
			_html_changes += "\n<tr><td width='_width'><b>%s: </b> [%s] ==> [%s]</td></tr>\n" % (change['header'], change['value_old'], change['value_new'])

		_html_changes += "</table>"
			
		row = '\n<tr><td><a href="%s">%s</a></td><td>%s</td></tr>\n' % (url, full_name, _html_changes)
		html += row

	html += "</table>"	

	return html

def format_new_or_removed_records(records):
	
	headers = required_headers()

	html = """<table border="1"><tr>"""
	for h in headers:
		th = '<th>%s</th>' % h
		html += th
	html += "</tr>"
	
	for r in records:
		url = r['_id']
		row = []
		for h in headers:
			if h == 'plan_name':
				td = '<td><a href="%s">%s</a></td>' % (url, r['plan_name'])
			else:
				td = '<td>%s</td>' % r[h]	

			row.append(td)		

		row = '\n<tr>%s</tr>\n'	 % u' '.join(row)
		html += row

	html += "</table>"		
		
	return html


def send_mail(html, files=[], subject='Report'):
	import mail
	config = s.read_json('config.txt')
	mail.gmail_user = config['gmail_user']
	mail.gmail_pwd = config['gmail_pwd']

	mail.send_mail(
		send_from = config['gmail_user'],
		send_to = [config['send_to']],
		subject = subject,
		text = html,
		files = files

		)

def start():

	today_file = s.join_path('history/%s.csv'%_today())
	prefile = _latest_file()

	try:
		scrape_all_plans(today_file)
		
		if prefile:
			html = compare_two_files(prefile, today_file)
			#send email
			predate = common.DataItem(prefile).subreg('/([^/]+)\.csv')

			send_mail(
				html,
				subject = 'Broadband Plans Comparison Report: %s ==> %s' % (predate, _today())
				)

		else:

			send_mail(
				html = "<h3>First Run! Please see attached file</h3>",
				files = [today_file],
				subject = "Broadband Plans Comparison Report: First Run!"

				)
	except Exception as e:
		logger.exception(e)
		send_mail(
				html = "<h3>Failed to run the scrape today. See the attached log file for details.</h3>",
				files = [s.join_path('log.txt')],
				subject = "Failed to run Broadband Plans scrape"

				)


			

def _scrape_modem_options(url):
	""" capture the available modem options
		
	"""
	doc = s.load(url) if url else Doc(html='')
	rs = doc.q("//div[@id='modems']/div/div[@data-contract]") + [Node('') for i in xrange(max_no_of_modem_options)]
	rs = rs[0:max_no_of_modem_options]
	assert len(rs) == max_no_of_modem_options

	options = []
	i = 0
	for r in rs:
		i += 1

		options += [
			'modem_option%s_name' % i, r.x('.//div[@class="[ col-xs-16 ] [ col-sm-13 ] [ pad-y-3 ]"]/div/h4'),
			'modem_option%s_price' % i, r.x('.//strong[contains(@class,"product-price")]/..').rr('\s+',' '),
			'modem_option%s_desc' % i, r.x('.//div[@class="[ col-xs-16 ] [ col-sm-13 ] [ pad-y-3 ]"]/div/div[contains(@class,"text-muted")]'),

			
		]


	
	return options	


def required_headers():
	#--fields requiring compared
	headers = [
		"plan_name",
		"supplier",
		"contract",
		# "features",
		"deal",
		"connection",
		"data",
		"data_note",
		"price",
		"min_total_cost",

		
	]
	
	for i in range(1, max_no_of_modem_options + 1):
		headers += [
		'modem_option%s_name' % i,
		'modem_option%s_price' % i,
		'modem_option%s_desc' % i,

		]

	return headers	

#====setup====#


s = Scraper(use_cache=False, retries=1)

logger = s.logger

history_path = s.join_path('history')
if not os.path.exists(history_path):
	os.mkdir(history_path)

test_mode = False

max_no_of_modem_options = 15

if __name__ == '__main__':

	start()

	# compare_two_files('history/2016-11-11.csv', 'history/2016-11-15.csv')
	# scrape_all_plans('history/'+ _today())

	# print _latest_file()

	# print _scrape_modem_options('https://www.whistleout.com.au/Broadband/Providers/SpinTel/Mobile/SpinTel-4G-Mobile-Broadband-1GB?contract=0&modem=BYO-Modem&search=476854')
	

