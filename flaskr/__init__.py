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
	
	
	def get_banner_info( banner_ids ):
		res = []
		for p in banner_ids:
			if isinstance(p, str) and '_' in p:		# 为类 id 或 专区 id
				type, id = p.split( '_' )
				id = int( id )
				if type=='c':
					smallpicture = os.path.join( app.config['HTTP_ADDR'], 'upload/product/xingxuan/banner/category/%d/banner.jpg' %id )
					mid = { 'category_id':id, 'smallpicture':smallpicture }
				elif type=='z':
					smallpicture = os.path.join( app.config['HTTP_ADDR'], 'upload/product/xingxuan/banner/zone/%d/banner.jpg' %id )
					mid = { 'zone_id':id, 'smallpicture':smallpicture }
			else:				# 为产品id
				mid = mysql_db.get_products_info( app.config['mysql_pool'], [p] )
				mid = mid[0]
				mid['smallpicture'] = os.path.join( os.path.dirname(mid['smallpicture']), 'banner.jpg' )
			res.append( mid )			
		return res
	
	
	block_a = [ 7011, 7060, 7223, 7064, 7119, 7142, 7147 ]
	block_b = [ 7081, 7222, 7043, 7122, 7063, 7085, 7128 ]
	block_c = [ 7215, 7218, 7229, 7230, 7232, 7155, 7151, 7216, 7212, 7010 ]
	block_d1 = [ 7058, 7013, 7034, 7036, 7038, 7044, 7046, 7079, 7081, 7085 ]
	block_d2 = [ 7014, 7012, 7035, 7037, 7043, 7045, 7048, 7080, 7082, 7086]
	banner = [ 7162, 'c_98' ]
	all_products = [ block_a, block_b, block_c, block_d1, block_d2 ]
	
	# [ {product_id, name, smallpicture, sp_n, sp_v}, {category_id:xxx, smallpicture:xxx}, {zone_id:xxx,smallpicture:xxx}... ]
	# banner -  [ 7162, 7062 ]	产品id
	#			[ c_90, xxx ]	类id，要跳转到类中， 图片默认地址为: app.config['HTTP_ADDR'] + upload/product/xingxuan/banner/category/90/banner.jpg
	#			[ z_89, xx ]	专区id，要跳转到专区中，图片默认地址为:  app.config['HTTP_ADDR'] + upload/product/xingxuan/banner/zone/89/banner.jpg
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
		elif b_name=='banner' or b_name=='banner_force':
			product_ids = banner
			field = 'banner'
		else:
			field = 'a'
	
		res = db.get_main_page_info( app.config['pool'], field )
		if res is None:
			if field!='banner':
				res = mysql_db.get_products_info( app.config['mysql_pool'], product_ids )
			else:		# 处理 banner 类型
				get_banner_info( product_ids )
					
			db.set_main_page_info( app.config['pool'], field, res )
			res = json.dumps( res )			
		else:
			res = res.decode( 'utf-8' )
	
		if b_name=='banner_force':
			res = get_banner_info( product_ids )
			db.set_main_page_info( app.config['pool'], field, res )
			res = json.dumps( res )	
				
		if b_name=='force':
			out_res = []
			for i, f in enumerate( ['a','b','c', 'd1', 'd2'] ):
				res = mysql_db.get_products_info( app.config['mysql_pool'], all_products[i] )
				db.set_main_page_info( app.config['pool'], f, res )
				out_res.extend( res )
			
			res = get_banner_info( banner )
			db.set_main_page_info( app.config['pool'], 'banner', res )
			out_res.extend( res )
			
			res = json.dumps( res )	
			
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
	
	
	# [ {zone_1_info}, {zone_2_info}..... ]
	# zone_1_info - { 'name':xx, 'icon':xxxx, 'id':xxxx }
	# 专区图像路径 默认为 app.config['HTTP_ADDR'] + upload/product/xingxuan/zone/90/banner.jpg
	@app.route( '/api/zone_page', methods = ['GET'] )
	def get_zones_info():
		res = []
		res = mysql_db.get_zones_info( app.config['mysql_pool'] )
		for r in res:
			r['icon'] = app.config['HTTP_ADDR'] + 'upload/product/xingxuan/zone/%s/banner.jpg' % r['id']
		return json.dumps( res )
	

	# [ {"product_id": xxx, "name": xxx, "smallpicture": xx, "sp_n": xx, "sp_v": xx}, {},.... ]
	@app.route( '/api/zone_page/goods/<string:z_id>', methods = ['GET'] )
	def get_the_zone_goods( z_id ):
		res = mysql_db.get_zone_goods( app.config['mysql_pool'], z_id )
		if res!=[]:
			gs_id = res
			res = mysql_db.get_products_info( app.config['mysql_pool'], gs_id )
		return json.dumps( res )
		
		
	# in - {'name':xx, 't1':xx, 't2':xx, 'goods':xx, 'cards_type':xx }
	@app.route( '/api/add_zone/', methods = ['POST'] )
	def add_the_zone( ):
		zone_info = request.form
		res = mysql_db.add_zone( app.config['mysql_pool'], zone_info )
		return json.dumps( res )
	
	
	# { z_id, card_id, g_sp_list:json-str, uid, addr, phone, consignee }
	# g_sp_list - [ [产品id,产品规格名称,num], [产品id,产品规格名称,num]....], json-str
	@app.route( '/api/pay_by_card/', methods = ['POST'] )
	def pay_by_card():
		g_sp_list = json.loads( request.form['g_sp_list'] )
		uid, z_id, card_id = request.form['uid'], request.form['z_id'], request.form['card_id']
		goods_list, g_num_dict, mid_g_sp_list = [], {}, []
		for g in g_sp_list:
			goods_list.append( g[0] )
			g_num_dict[ g[0] ] = g[2]
			mid_g_sp_list.append( [g[0],g[1]] )
		
		# 根据订单统计产品总金额; sum 为订单总金额
		suc_goods = mysql_db.get_products_the_sp_info( app.config['mysql_pool'], mid_g_sp_list )
		sum, sp_info_dict = 0, {}
		for g in suc_goods:
			sum += g['price'] * g_num_dict[ g['product_id'] ]
			sp_info_dict[ g['product_id'] ] = [ g['price'], g['product_price_id'] ]
			
		now, the_card = time.time(), None
		order_info = dict( request.form )
		order_info['amount'] = sum
			
		if z_id!='-1':
			# 判断卡类型、专区和产品类型是否匹配
			cds_info = mysql_db.get_my_cards( app.config['mysql_pool'], uid )
			for c in cds_info:
				if c['card_id']==card_id and c['t1']<=now and c['t2']>=now and c['rest']>0:
					the_card = c
					break
			del cds_info
			if the_card is None:
				res = { 'res':'NO', 'reason':'此卡号不存在或已经作废' }
				return json.dumps( res )
			
			failed = []
			goods_ids = mysql_db.get_zone_goods( app.config['mysql_pool'], z_id )
			for g in goods_list:
				if g not in goods_ids:
					failed.append( g )
					
			if failed!=[]:
				failed_goods = mysql_db.get_products_info( app.config['mysql_pool'], failed )
				f_names = []
				for f in failed_goods:
					f_names.append( f['name'] )
				failed = ','.join( f_names )
				res = { 'res':'NO', 'reason':failed+' 不能使用该卡券进行购买' }
				return json.dumps( res )
			
			# 判断金额是否足够
			if sum>the_card['rest']:
				res = { 'res':'NO', 'reason':'金额不足' }
				return json.dumps( res )
				
		else:			# 使用通用卡余额支付
			# 判断金额是否足够
			money = mysql_db.get_user_money( app.config['mysql_pool'], uid )
			if sum>money:
				res = {'res':'NO', 'reason':'金额不足' }
				return json.dumps( res )
		
		for g in g_sp_list:		
			g.extend( sp_info_dict[ g[0] ] )
		order_info['g_sp_list'] = g_sp_list
		
		# 记录订单，修改金额，记录消费记录
		mysql_db.gen_order( app.config['mysql_pool'], order_info )
			
		return json.dumps( {'res':'OK'} )
		
		
	# [ {'c_id':xx, 'pic':类图片url, 'name':xxx}, {'c_id':xx, 'name':xxx} ]
	# 返回中必有 c_id、name 键; 如没有 pic 则使用默认图
	# 类图标存储路径为 app.config['HTTP_ADDR'] + upload/product/xingxuan/category/<类id号>/banner.jpg 
	categories = [ 
		{'c_id':90, 'name':'新鲜水果' },
		{'c_id':91, 'name':'即食果蔬' },
		{'c_id':92, 'name':'星选果蔬' },
		{'c_id':93, 'name':'白成品食材' },
		{'c_id':94, 'name':'星选零食' },
		{'c_id':95, 'name':'肉禽蛋类' },
		{'c_id':96, 'name':'水产海鲜' },
		{'c_id':97, 'name':'安心乳品' },
		{'c_id':98, 'name':'蛋糕甜点' },
		{'c_id':99, 'name':'熟食-地方特色' }
	]
	@app.route( '/api/get_categories', methods = ['POST', 'GET'] )
	def get_categories():
		return json.dumps( categories )
		
	
	# 成功充值xx元、此卡号不存在、此卡已使用、此卡已过期、此卡已作废
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
	
	
	@app.route( '/api/transfer/<string:uid>/<string:from_card_id>/<string:to_who>/<float:sum>', methods = ['POST', 'GET'] )
	def transfer( uid, from_card_id, to_who, sum ):
		pass
	
	
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
	

	@app.route( '/api/my_cards/<string:uid>', methods = ['GET'] )
	def get_all_my_cards( uid ):
		res = mysql_db.get_my_cards( app.config['mysql_pool'], uid )
		return json.dumps( res )
	
	
	# /api/cart/inc/205/7298/7299/1
	# 增加产品至购物车（数量增加或新品）
	# res - {'res':'OK'}, {'res':'NO', 'reason':xx}
	# z_id<0 表示不存在
	@app.route( '/api/cart/inc/<string:uid>/<string:pid>/<string:product_price_id>/<string:z_id>', methods = ['GET'] )
	def cart_inc( uid, pid, product_price_id, z_id ):
		try:
			z_id = int( z_id )
		except:
			z_id = -1
		res = mysql_db.cart_add( app.config['mysql_pool'], uid, pid, product_price_id, z_id )
		return json.dumps( res )
	
	
	# /api/cart/minus/205/7298/7299/1
	@app.route( '/api/cart/minus/<string:uid>/<string:pid>/<string:product_price_id>/<string:z_id>', methods = ['GET'] )	
	def cart_minus( uid, pid, product_price_id, z_id ):
		try:
			z_id = int( z_id )
		except:
			z_id = -1	
		res = mysql_db.cart_minus( app.config['mysql_pool'], uid, pid, product_price_id, z_id )
		return json.dumps( res )
	
	'''
	# /api/cart/del/205/7298/7299/1
	@app.route( '/api/cart/del/<string:uid>/<string:pid>/<string:product_price_id>/<string:z_id>', methods = ['GET'] )	
	def cart_del( uid, pid, product_price_id, z_id ):
		res = mysql_db.cart_del( app.config['mysql_pool'], uid, pid, product_price_id, z_id )
		return json.dumps( res )
	'''
	
	# /api/cart/del/205
	# post data: [ [pid,product_price_id,z_id], []... ] json-str
	@app.route( '/api/cart/del/<string:uid>', methods = ['GET', 'POST'] )	
	def cart_del( uid ):
		try:
			g_info_list = json.loads( request.form['data'] )
		except:
			return json.dumps( {'res':'NO','reason':'invalid data'} )
		res = mysql_db.cart_del( app.config['mysql_pool'], uid, g_info_list )
		return json.dumps( res )
		
		
	@app.route( '/api/cart/get/<string:uid>', methods = ['GET'] )	
	def cart_get( uid ):
		res = mysql_db.cart_get( app.config['mysql_pool'], uid )
		return json.dumps( res )
	
	
	# status - 1:待付款，2:待发货，3:已发货，4:已完成，5:已取消
	@app.route( '/api/orders/get/<string:offset>/<string:status>', methods = ['GET'] )
	def get_order( offset, status ):
		res = mysql_db.orders_get( app.config['mysql_pool'], offset, status )
		return json.dumps( res )
	
	
	return app