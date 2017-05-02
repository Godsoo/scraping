import sys, logging, time, json
import MySQLdb
from scrapex import Scraper, common
s = Scraper(show_status_message=False, use_logging_config=False, use_cache=True)
logger = logging.getLogger(__name__)

config = json.loads(common.get_file(s.join_path('config.txt')))

class DB(object):
	"""responsile for db operations"""
	def __init__(self):
		self.conn = None
		self.connect()
		
	def connect(self):
		try:
			self.conn = MySQLdb.connect(
				host=config['db']['host'],
				port = config['db']['port'],
	            user= config['db']['user'],
	            passwd=config['db']['password'],
	            db=config['db']['dbname'])

			self.conn.autocommit(True)
		
		except Exception as e:
			logger.exception(e)	
			raise e

	def execute(self,sql,params=None, retryonfail=True):
		""" execute a sql without fetching data """
		if params:
			_params = []
			for value in params:
				if isinstance(value, unicode):
					value = value.encode('utf8')
				_params.append(value)
				
			params = _params		
		try:
			cur = self.conn.cursor()
			if params:
				res = cur.execute(sql, params)
			else:
				res = cur.execute(sql)

			self.conn.commit()	
			return res
			# logger.debug('executed sql: %s, %s, rows effected: %s', sql, params, res)

		except MySQLdb.OperationalError, e:
			logger.info('reconnecting to mysql server')
			self.connect()
			if retryonfail:
				self.execute(sql,params,retryonfail=False)
			else:
				raise e	
		except MySQLdb.IntegrityError, e:
			code, msg = e
			if code == 1062:
				# duplicate entry
				return 0
			else:
				raise e

		except Exception, e:
			
			logger.warn('failed to execute: %s, %s', sql, params)
			logger.exception(e)

		finally:
			try:
				cur.close()
			except:
				pass	

		return 0

	def fetch(self,sql,params=None, return_dict =False, retryonfail=True):
		""" execute a sql and fetching data """
		res = None
		try:
			cur = self.conn.cursor() if not return_dict else self.conn.cursor(MySQLdb.cursors.DictCursor)
			if params:
				cur.execute(sql, params)
			else:
				cur.execute(sql)

			res = cur.fetchall()

		except MySQLdb.OperationalError as e:
			logger.info('reconnecting to mysql server')
			self.connect()
			if retryonfail:
				res = self.execute(sql,params,retryonfail=False)
			else:
				raise e	
		except Exception as e:
			if retryonfail:
				logger.info('retrying sql execute...')
				res = self.execute(sql,params,retryonfail=False)

			else:
				raise e
		finally:
			try:
				cur.close()
			except:
				pass	

		#succsess		
		return res
		
	
	def fetch_first(self, sql, params=None, return_dict=False):
		rs = self.fetch(sql,params,return_dict=return_dict)
		if rs:
			return rs[0]
		else:
			return None	
	
	
		
if __name__ == '__main__':
	pass