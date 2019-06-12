import os

basedir = os.path.abspath( os.path.dirname(__file__) )

SECRET_KEY = os.getenv( 'SECRET_KEY', 'hdhyri19979klcm g==0kkg,czhui=' )
ITEMS_PER_PAGE = 10
DEBUG = True
REDIS_URL = 'redis://:password@localhost:6379/0'

HTTP_ADDR = 'http://www.guocool.com/guocool/'

'''
MYSQL_DB_USR = 'guocool'
MYSQL_DB_PASSWD = 'aZuL2H58CcrzhTdt'
MYSQL_DB_HOST = '101.200.233.199'
MYSQL_DB_NAME = 'guocoolv2.0'
'''

MYSQL_DB_USR = 'blue'
MYSQL_DB_PASSWD = 'blue'
MYSQL_DB_HOST = '127.0.0.1'
MYSQL_DB_NAME = 'guocoolv2.0'

# sms
SMS_HOST = 'smssh1.253.com'
SMS_PORT = 80
SMS_SEND_URI = '/msg/send/json'
SMS_ACCOUNT = 'N9951173'
SMS_PASSWORD = '8cgvzlbhQ'

'''

class BaseConfig:  # 基本配置类
	SECRET_KEY = os.getenv( 'SECRET_KEY', 'some secret words' )
	ITEMS_PER_PAGE = 10


class DevelopmentConfig( BaseConfig ):
	DEBUG = True
	SQLALCHEMY_DATABASE_URI = os.getenv( 'DEV_DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'data-dev.sqlite' )


class TestingConfig(BaseConfig):
	TESTING = True
	SQLALCHEMY_DATABASE_URI = os.getenv( 'TEST_DATABASE_URL', 'sqlite:///' + os.path.join(basedir, 'data-test.sqlite' )
	WTF_CSRF_ENABLED = False


config = {
	'development': DevelopmentConfig,
	'testing': TestingConfig,
	'default': DevelopmentConfig
}
'''