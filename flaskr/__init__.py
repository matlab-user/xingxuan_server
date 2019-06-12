'''
	export FLASK_APP=flaskr
	export FLASK_ENV=development
	flask run
	
	flask run --host=0.0.0.0 --port=xxxx
	
	
	pip install pymysql-pooling
	
	图片存放地址
	/usr/local/tomcat-youcheng/webapps/guocool/upload/product
'''

import os, re
import time, json
from flask import Flask, g, request, session, send_file, redirect, url_for, abort
import hashlib, redis
import logging
import logging.handlers

from . import db
from . import mysql_db
from . import sms_tools


def create_app( test_config=None ):
	# create and configure the app
	app = Flask( __name__, instance_relative_config=True )
	
	if test_config is None:
		# load the instance config, if it exists, when not testing
		app.config.from_pyfile( 'config.py', silent=True )
	else:
		# load the test config if passed in
		app.config.from_mapping( test_config )

	# ensure the instance folder exists
	try:
		os.makedirs( app.instance_path )
	except OSError:
		pass
		
	app.config['JSON_AS_ASCII'] = False
	
	m = re.search( r'redis://:(?P<password>\S*)@(?P<ip>\S+):(?P<port>\d+)/(?P<db>\d+)', app.config['REDIS_URL'] )
	if m is not None:
		app.config['db_password'] = m['password']
		app.config['db_ip'] = m['ip']
		app.config['db_port'] = m['port']
		app.config['db_id'] = m['db']
				
		app.config['pool'] = redis.ConnectionPool( host=app.config['db_ip'], port=app.config['db_port'], db=app.config['db_id'] )
		r = redis.Redis( connection_pool=app.config['pool'] )
		t = time.strftime( '%Y-%m-%d %H:%M:%S', time.localtime() )
		r.set( 'start', t )	
	
	app.config['mysql_pool'] = mysql_db.create_conn_pool( app.config['MYSQL_DB_HOST'], app.config['MYSQL_DB_USR'], app.config['MYSQL_DB_PASSWD'], app.config['MYSQL_DB_NAME'] )
	
	logger = logging.getLogger( 'wdh' )
	logger.setLevel( logging.DEBUG )
	rh = logging.handlers.RotatingFileHandler( 'logs/wdh.log', maxBytes=800*1024*1024, backupCount=1024 )
	fm = logging.Formatter( '%(asctime)s  %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S' )
	rh.setFormatter( fm )
	logger.addHandler( rh )


	# a simple page that says hello
	@app.route( '/hello', methods = ['POST', 'GET'] )
	def hello():
		return 'Hello, World!</br></br>'
	
	
	block_a = [ 7011, 7060, 7223, 7064, 7119, 7142, 7147 ]
	block_b = [ 7081, 7222, 7043, 7122, 7063, 7085, 7128 ]
	block_c = [ 7215, 7218, 7229, 7230, 7232, 7155, 7151, 7216, 7212, 7010 ]
	block_d1 = [ 7058, 7013, 7034, 7036, 7038, 7044, 7046, 7079, 7081, 7085 ]
	block_d2 = [ 7014, 7012, 7035, 7037, 7043, 7045, 7048, 7080, 7082, 7086]
	banner = [ 7162, 7062 ]
	all_products = [ block_a, block_b, block_c, block_d1, block_d2 ]
	
	@app.route( '/api/main_page/block/<string:b_name>', methods = ['POST', 'GET'] )
	def get_the_block_products( b_name ):
		res = ''
		if b_name=='a':
			product_ids = block_a
			field = 'a'
		elif b_name=='b':
			product_ids = block_b
			field = 'b'
		elif b_name=='c':
			product_ids = block_c
			field = 'c'
		elif b_name=='d1':
			product_ids = block_d1
			field = 'd1'
		elif b_name=='d2':
			product_ids = block_d1
			field = 'd2'
		elif b_name=='banner' or b_name=='banner_f':
			product_ids = banner
			field = 'banner'
		else:
			field = 'a'
	
		res = db.get_main_page_info( app.config['pool'], field )
		if res is None:
			res = mysql_db.get_products_info( app.config['mysql_pool'], product_ids )
			if field=='banner':
				for r in res:
					r['smallpicture'] = os.path.join( os.path.dirname(r['smallpicture']), 'banner.jpg' )
		
			db.set_main_page_info( app.config['pool'], field, res )
			res = json.dumps( res )	
				
		else:
			res = res.decode( 'utf-8' )
	
	
		if b_name=='banner_f':
			res = mysql_db.get_products_info( app.config['mysql_pool'], product_ids )
			for r in res:
				r['smallpicture'] = os.path.join( os.path.dirname(r['smallpicture']), 'banner.jpg' )
			db.set_main_page_info( app.config['pool'], field, res )
			res = json.dumps( res )	
				
		if b_name=='force':
			out_res = []
			for i, f in enumerate( ['a','b','c', 'd1', 'd2'] ):
				res = mysql_db.get_products_info( app.config['mysql_pool'], all_products[i] )
				db.set_main_page_info( app.config['pool'], f, res )
				out_res.extend( res )
		
			res = mysql_db.get_products_info( app.config['mysql_pool'], banner )
			for r in res:
				r['smallpicture'] = os.path.join( os.path.dirname(r['smallpicture']), 'banner.jpg' )
			db.set_main_page_info( app.config['pool'], 'banner', res )
			out_res.extend( res )
			res = json.dumps( out_res )
		
		return res
	
	
	# 类从 90-99
	@app.route( '/api/category_page/<string:category_id>', methods = ['POST', 'GET'] )
	def get_category( category_id ):	
		# <category_id>_f  # 强制从mysql数据库中-》redis
		if category_id=='f_all':
			for c_id in range( 90, 100 ):
				res = mysql_db.get_category_goods( app.config['mysql_pool'], str(c_id) )
				db.set_category_page_info( app.config['pool'], str(c_id), res )
			res = json.dumps( res )
			
		elif '_f' in category_id:	
			category_id = category_id[0:-2]
			res = mysql_db.get_category_goods( app.config['mysql_pool'], category_id )
			db.set_category_page_info( app.config['pool'], category_id, res )
			res = json.dumps( res )
			
		elif int(category_id)>=90 and int(category_id)<=102:
			res = db.get_category_page_info( app.config['pool'], category_id )
			if res is None or res==b'[]':
				res = mysql_db.get_category_goods( app.config['mysql_pool'], category_id )
				db.set_category_page_info( app.config['pool'], category_id, res )
				res = json.dumps( res )
			else:
				res = res.decode( 'utf-8' )
		
		return res
		
	
	# 成功充值xx元
	# 此卡号不存在
	# 此卡已使用
	# 此卡已过期
	# 此卡已作废
	@app.route( '/api/card/recharge/<string:user_id>/<string:card_id>', methods = ['POST', 'GET'] )
	def recharge( user_id, card_id ):
		the_info = mysql_db.get_card_info( app.config['mysql_pool'], card_id )
		
		if the_info is None:
			res = {'res':'NO', 'reason':'此卡号不存在' }
		elif the_info['status']=='used':
			res = {'res':'NO', 'reason':'此卡已使用' }
		elif the_info['status']=='ban':			# norm，，expired，
			res = {'res':'NO', 'reason':'此卡已作废' }
		else:
			now, t2 = time.time(), float( the_info['t2'] )
			if t2<now:
				res = {'res':'NO', 'reason':'此卡已过期' }
			else:
				# 更改卡状态
				mysql_db.set_card_status( app.config['mysql_pool'], card_id, {'user':user_id,'status':'used'} )
				# 给客户账户充值
				new_info = { 'amount':the_info['price'], 'description':'星选卡充值' }
				mysql_db.add_money( app.config['mysql_pool'],user_id, new_info )
				res = {'res':'OK', 'reason':'成功充值%s元' %the_info['price'] }

		return  json.dumps( res )
	
	
	@app.route( '/api/user/shortmessage/<string:phone>/<string:password>', methods = ['POST', 'GET'] )
	def user_shortmessage( phone, password ):
		res = mysql_db.user_reg_shortmessage( app.config['mysql_pool'], phone, password )
		return  json.dumps( res )
	

	@app.route( '/api/user/reg/<string:phone>/<string:code>', methods = ['POST', 'GET'] )
	def user_reg( phone, code ):
		res = mysql_db.user_reg_verify( app.config['mysql_pool'], phone, code )
		return  json.dumps( res )

	
	@app.route( '/api/search_tools/save_goods_names', methods = ['POST', 'GET'] )
	def goods_names_to_redis():
		names_list = mysql_db.read_all_goods_names( app.config['mysql_pool'] )
		db.goods_names_to_redis( app.config['pool'], names_list )
		return 'OK'
	
	
	@app.route( '/api/user/search/<string:key_wd>', methods = ['POST', 'GET'] )
	def user_search( key_wd ):
		goods_names = db.goods_names_read( app.config['pool'] )
		if goods_names is not None:
			goods_names = goods_names.decode( 'utf-8' )
			g_name_list = goods_names.split( ',' )
			res, base = {}, len(key_wd)
			for gn in g_name_list:
				try:
					ind = gn.index( key_wd )
					res[gn] = base
				except:
					res[gn] = 0
					
				for w in key_wd:
					try:
						ind = gn.index( w )
						res[gn] += 1
					except:
						continue
			res = sorted( res.items(), key=lambda d:d[1], reverse=True )[0:10]
			if res[0][1]==0:
				return json.dumps( [] )
			goods_names = list( dict(res).keys() )
			res = mysql_db.get_products_info_by_names( app.config['mysql_pool'], goods_names )
			
			return json.dumps( res )
		else:
			return json.dumps( [] )
	
	'''
	/api/main_page/block/<栏目名>
	/api/main_page/banner/<1/2>
	
	'''		
	
	return app