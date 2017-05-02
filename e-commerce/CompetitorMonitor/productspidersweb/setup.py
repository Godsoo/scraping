import os
import sys

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

requires = [
    'nltk',
    'pyramid',
    'SQLAlchemy',
    'transaction',
    'pyramid_tm',
    'pyramid_debugtoolbar',
    'zope.sqlalchemy',
    'Paste',
    'pyramid_simpleform',
    'scrapy==1.0.5',
    'paramiko',
    'fabric>=1.5',
    'requests',
    'WebTest',
    'selenium',
    'pyramid_mako',
    'redis',
    'celery',
    'python-amazon-simple-product-api',
    'click',
    'scrapely',
    'XlsxWriter',
    'xlrd',
    'demjson',
    'pandas==0.16.0',
    'demjson',
    'psycopg2',
    'Pillow==2.4.0',
    'scrapyd',
    'extruct',
    'mock',
    'ssdb'
    ]

if sys.version_info[:3] < (2, 5, 0):
    requires.append('pysqlite')

setup(name='productspidersweb',
      version='0.0',
      description='productspidersweb',
      long_description=README + '\n\n' + CHANGES,
      classifiers=[
        "Programming Language :: Python",
        "Framework :: Pylons",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        ],
      author='',
      author_email='',
      url='',
      keywords='web wsgi bfg pylons pyramid',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      test_suite='productspidersweb.tests',
      install_requires=requires,
      entry_points="""\
      [paste.app_factory]
      main = productspidersweb:main
      """,
      paster_plugins=['pyramid'],
      )
