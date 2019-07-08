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
from werkzeug.utils import secure_filename
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
	
	
	# 获取 h5 页面
	@app.route( '/h5/<string:id>', methods = ['GET'] )
	def get_h5( id ):
		h5_page = 'h5_pages/h5_%s.html' %id
		return app.send_static_file( h5_page )
		
	
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
				elif type=='h5':
					smallpicture = os.path.join( app.config['HTTP_ADDR'], 'upload/product/xingxuan/banner/h5/%d/banner.jpg' %id )	
					mid = { 'h5_id':id, 'smallpicture':smallpicture, 'url':'/h5/%d' %id }
			else:				# 为产品id
				mid = mysql_db.get_products_info( app.config['mysql_pool'], [p] )
				mid = mid[0]
				mid['smallpicture'] = os.path.join( os.path.dirname(mid['smallpicture']), 'banner.jpg' )
			res.append( mid )			
		return res
	
	
	block_a = [ 7158, 7170, 7195, 7172, 7189, 7192 ]
	block_b = [ 7116, 7118, 7119, 7122, 7121, 7129, 7212 ]
	block_c = [ 7047, 7046, 7014, 7045, 7049, 7062, 7065,7031 ]
	block_d1 = [ 7099, 7137, 7141, 7144, 7145, 7154, 7225, 7166, 7147,7270,7269,7008,7267,7265,7266]
	block_d2 = [ 7070, 7117, 7120, 7043, 7109,7261,7258,7256,7279,7284,7285,7288,7292,7290,7295]	
	#banner = [ 7162, 'c_98' ]
	banner = [ 7162, 'h5_1' ]
	all_products = [ block_a, block_b, block_c, block_d1, block_d2 ]
	
	# [ {product_id, name, smallpicture, sp_n, sp_v}, {category_id:xxx, smallpicture:xxx}, {zone_id:xxx,smallpicture:xxx}, {h5_id:xx,smallpicture:xx,url:xx}... ]
	# banner -  [ 7162, 7062 ]	产品id
	#			[ c_90, xxx ]	类id，要跳转到类中， 图片默认地址为: app.config['HTTP_ADDR'] + upload/product/xingxuan/banner/category/90/banner.jpg
	#			[ z_89, xx ]	专区id，要跳转到专区中，图片默认地址为:  app.config['HTTP_ADDR'] + upload/product/xingxuan/banner/zone/89/banner.jpg
	#			[ h5_1, xx]		h5页面跳转，图片默认地址为: app.config['HTTP_ADDR'] + upload/product/xingxuan/banner/h5/1/banner.jpg、
	#							url 默认为: /h5/<string:id>, 文件保存在 flasker/static/h5_pages/内，命名方式为 h5_<id>.html 
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
				res = get_banner_info( product_ids )
					
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
	
	
	@app.route( '/api/goods/get_stav_v/<int:pid>', methods = ['GET'] )
	def get_star_v( pid ):
		res = mysql_db.get_star_v( app.config['mysql_pool'], pid )
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
		res, _ = mysql_db.get_zone_goods( app.config['mysql_pool'], z_id )
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
	
	
	# { card_id, g_sp_list:json-str, uid, addr, phone, consignee }
	# g_sp_list - [ [产品id,产品规格名称,num,z_id], [产品id,产品规格名称,num,z_id]....], json-str
	# 非专区产品，z_id = -1	(产品id,num,z_id 都为整数类型)
	@app.route( '/api/pay_by_card/', methods = ['POST'] )
	def pay_by_card():
		g_sp_list = json.loads( request.form['g_sp_list'] )
		uid = request.form['uid']
		
		# 判断卡是否属于uid、是否过期或被禁止
		now, the_card = time.time(), None
		if 'card_id' in request.form:
			card_id = request.form['card_id']
			cds_info = mysql_db.get_my_cards( app.config['mysql_pool'], uid )
			for c in cds_info:
				if c['card_id']==card_id and c['t1']<=now and c['t2']>=now and c['rest']>0:
					the_card = c
					break
			del cds_info
			if the_card is None:
				res = { 'res':'NO', 'reason':'此卡号不存在或已经作废' }
				return json.dumps( res )
		
		# 判断产品是否在指定专区中
		pid_list, g_num_dict, mid_g_sp_list, zid_pid_dict = [], {}, [], {}
		for g in g_sp_list:
			pid_list.append( g[0] )
			g_num_dict[str(g[0])] = g[2]
			mid_g_sp_list.append( [g[0],g[1]] )
			z_id_str = str( g[3] )
			if z_id_str not in zid_pid_dict:
				zid_pid_dict[ z_id_str ] = [ g[0] ]
			else:
				zid_pid_dict[ z_id_str ].append( g[0] )
		
		pid_to_the_card = []			# 能用给定卡支付的产品pid [ xx,xx,xx ]
		for k, v in zid_pid_dict.items():
			if int(k)<0:
				continue
			goods_ids, cards_type = mysql_db.get_zone_goods( app.config['mysql_pool'], int(k) )
			set_v, set_goods_ids = set( v ), set( goods_ids )
			if not set_v.issubset( set_goods_ids ):		# 商品不是全部在给定专区中
				res = { 'res':'NO', 'reason':'有产品与其专区不符' }
				return json.dumps( res )
			else:
				if the_card is not None and the_card['type'] in cards_type:
					pid_to_the_card.extend( v )
			
		pid_to_the_card = list( set(pid_to_the_card) )
		# 判断结算产品中是否至少一种能用此卡
		if the_card is not None and len(pid_to_the_card)<=0:
			res = { 'res':'NO', 'reason':'卡券不适用于该批产品' }
			return json.dumps( res )
	
		# 计算卡券金额。卡券仅能抵扣对应产品，其它产品使用余额支付
		# 根据订单统计产品总金额; SUM 为订单总金额
		# card_cost 为能用卡券抵扣的产品的总价
		suc_goods = mysql_db.get_products_the_sp_info( app.config['mysql_pool'], mid_g_sp_list )
		SUM, sp_info_dict, card_cost = 0, {}, 0
		for g in suc_goods:
			pid = str( g['product_id'] )
			SUM += g['price'] * g_num_dict[ pid ]
			sp_info_dict[ pid ] = [ g['price'], g['product_price_id'] ]
			if int(pid) in pid_to_the_card:
				card_cost += g['price'] * g_num_dict[ pid ]
		
		if the_card is not None:
			if card_cost>=the_card['rest']:
				card_cost = the_card['rest']
		else:
			card_cost = 0
		rest_cost = SUM - card_cost	
		if rest_cost>0:
			# 判断余额金额是否足够
			money = mysql_db.get_user_money( app.config['mysql_pool'], uid )
			if rest_cost>money:
				res = { 'res':'NO', 'reason':'金额不足' }
				return json.dumps( res )
				
		# 进行交易
		order_info = dict( request.form )	
		for g in g_sp_list:		
			g.extend( sp_info_dict[ str(g[0]) ] )
		order_info['g_sp_list'] = g_sp_list
		
		# 记录订单，修改金额，记录消费记录
		mysql_db.gen_order_2( app.config['mysql_pool'], order_info, {'card_cost':card_cost, 'rest_cost':rest_cost} )
			
		return json.dumps( {'res':'OK'} )
		

	# zone_ids - xxxx,xxx,xxx
	@app.route( '/api/available_cards/<string:uid>/<string:zone_ids>', methods = ['GET'] )
	def available_cards( uid, zone_ids ):
		zone_ids_list = zone_ids.split( ',' )
		res = mysql_db.available_cards( app.config['mysql_pool'], uid, zone_ids_list )
		return json.dumps( res )
	
	
	# [ {'c_id':xx, 'pic':类图片url, 'name':xxx}, {'c_id':xx, 'name':xxx} ]
	# 返回中必有 c_id、name 键; 如没有 pic 则使用默认图
	# 类图标存储路径为 app.config['HTTP_ADDR'] + upload/product/xingxuan/category/<类id号>/banner.jpg 
	categories = [ 
		{'c_id':90, 'name':'新鲜水果' },
		{'c_id':91, 'name':'即食果蔬' },
		{'c_id':92, 'name':'星选果蔬' },
		{'c_id':93, 'name':'半成品食材' },
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
				if the_info['type']=='' or the_info['type']=='通用卡':
					# 给客户账户充值
					new_info = { 'amount':the_info['price'], 'description':'星选卡充值' }
					mysql_db.add_money( app.config['mysql_pool'],user_id, new_info )
					res = {'res':'OK', 'reason':'成功充值%s元' %the_info['price'] }
				else:
					res = {'res':'OK', 'reason':'成功添加1张%s卡' %the_info['name'] }

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
	
	# [ {'price': 100.0, 'rest': 0.0, 'description':x, 'name':x, 'type':x, 't1':x, 't2':x, 'card_id':x, 'status': 'norm', 'image':x} ]
	# image - 卡券图像，默认地址为: app.config['HTTP_ADDR'] + upload/product/xingxuan/cards/<type>.jpg
	# 蛋糕卡-cake.jpg	中秋-ma.jpg
	@app.route( '/api/my_cards/<string:uid>', methods = ['GET'] )
	def get_all_my_cards( uid ):
		res = mysql_db.get_my_cards( app.config['mysql_pool'], uid )
		card_type = { '蛋糕卡':'cake.jpg', '中秋卡':'ma.jpg' }
		for r in res:
			if r['type'] in card_type:
				r['image'] = app.config['HTTP_ADDR'] + 'upload/product/xingxuan/cards/' + card_type[r['type']]
				
		return json.dumps( res )
	
	
	# /api/cart/inc/205/7298/7299/1/10
	# 增加产品至购物车（数量增加或新品）
	# res - {'res':'OK'}, {'res':'NO', 'reason':xx}
	# z_id<0 表示不存在
	@app.route( '/api/cart/inc/<string:uid>/<string:pid>/<string:product_price_id>/<string:z_id>/<int:num>', methods = ['GET'] )
	def cart_inc( uid, pid, product_price_id, z_id, num ):
		try:
			z_id = int( z_id )
		except:
			z_id = -1
		res = mysql_db.cart_add( app.config['mysql_pool'], uid, pid, product_price_id, z_id, num )
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
	
	
	@app.route( '/api/addrs/get/<int:uid>', methods = ['GET'] )
	def get_addr( uid ):
		res = mysql_db.get_addrs( app.config['mysql_pool'], uid )
		return res
	
	
	@app.route( '/api/addrs/set/<int:uid>/<string:new_addr>', methods = ['GET', 'POST'] )
	def set_addr( uid, new_addr ):
		if new_addr=='none':
			new_addr = request.form['data']
		res = mysql_db.set_addr( app.config['mysql_pool'], uid, new_addr )
		return json.dumps( res )
		
	
	@app.route( '/api/addrs/set_default/<int:uid>/<int:addr_id>', methods = ['GET'] )
	def set_default_addr( uid, addr_id ):
		res = mysql_db.set_addr_default( app.config['mysql_pool'], uid, addr_id )
		return json.dumps( res )
	
	
	@app.route( '/api/addrs/del/<int:uid>/<int:addr_id>', methods = ['GET'] )
	def del_addr( uid, addr_id ):
		res = mysql_db.del_addrs( app.config['mysql_pool'], uid, addr_id )
		return json.dumps( res )
	
#------------------------------------------------------------------------------------------------
# 后台功能
#------------------------------------------------------------------------------------------------
	@app.route( '/api/goods/set/status/<int:pid>/<string:status_str>', methods = ['GET'] )
	def set_goods_status( pid, status_str ):
		if status_str=='on':
			status = 1
		else:
			status = 2
		res = mysql_db.set_goods_status( app.config['mysql_pool'], pid, status )

		return json.dumps( res )
	
	
	@app.route( '/edit', methods = ['GET'] )
	def edit_goods_info():
		return app.send_static_file( 'wdh_table.html' )
	
	
	# ('pid', ''), ('store_id', ''), ('name', ''), ('category', 'A'), ('sub_category', 'SA')
	@app.route( '/api/goods/set/g_info_1', methods = ['POST'] )
	def set_g_info_1():
		data, sig = dict( request.form ), False
		for c in categories:
			if c['name']==data['category']:
				data['category'] = c['c_id']
				sig = True
				break
		if sig==False:
			res = {'res':'NO', 'reason':'无此类别'}
		else:
			res = mysql_db.set_update_goods_info_1( app.config['mysql_pool'], goods_info_1 )
		return json.dumps( res )
	
	# {'sp_1': '', 'sp_2': '', 'sp_3': '', 'sp_4': '', 'sp_5': '', 'sp_6': ''}
	@app.route( '/api/goods/set/sps/<int:pid>', methods = ['POST'] )
	def set_sps( pid ):
		data = dict( request.form )
		res = mysql_db.set_goods_sps( app.config['mysql_pool'], pid, data )
		return json.dumps( res )
	
	
	# introduction - string
	@app.route( '/api/goods/set/introduction/<int:pid>', methods = ['POST'] )
	def set_introduction( pid ):
		data = request.form['data']
		res = mysql_db.set_goods_introduction( app.config['mysql_pool'], pid, data )
		return json.dumps( res )
	
	
	def allowed_file( filename ):
		ALLOWED_EXTENSIONS = set( ['png', 'jpg', 'jpeg', 'gif'] )
		return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
	
	
	# 数据库中存储地址 upload/product/xingxuan/7000/7033/lg_2.jpg
	# 产品图片存储路径
	database_path = 'upload/product/xingxuan'
	icon_path = '.'
	# type - icon, details
	@app.route( '/api/images/upload/<string:pid>/<string:store_id>/<string:type>', methods = ['GET', 'POST'] )
	def uploaded_file( pid, store_id, type ):
		if request.method == 'POST':
			if 'file' not in request.files:
				return json.dumps( {'res':'NO', 'reason':'POST请求中无文件数据'} )
				
			file = request.files['file']
			if file.filename == '':
				return json.dumps( {'res':'NO', 'reason':'请选择上传文件'} )
				
			if file and allowed_file( file.filename ):
				suffix = os.path.splitext( file.filename )[-1]			
				if type=='icon':
					save_path = icon_path
					filename = 'small_%d' % time.time() + suffix
					key_wd = 'small'
				elif type=='details':
					save_path = icon_path
					filename = 'lg_%s_%d%s' %(request.form['index'], time.time(), suffix) 
					key_wd = 'lg_' + request.form['index']
						
				save_path_full = os.path.join( icon_path, filename )	
				file.save( save_path_full )
				
				# 数据库中删除相关图片, 文件夹内删除对应文件，文件要更换名称
				# 仅处理 详情图
				if type=='icon':
					res = mysql_db.get_icon( app.config['mysql_pool'], pid )
					pass
				else:
					res = mysql_db.get_pictures( app.config['mysql_pool'], pid )
					for r in res:
						fn = os.path.basename( r['photo_url'] )
						if key_wd in fn:
							ids = [ r['product_price_id'] ]
							mysql_db.del_pictures( app.config['mysql_pool'], ids )
							try:
								os.remove( os.path.join(save_path, fn) )
							except:
								pass
							file_path = os.path.join( database_path, store_id, pid, filename )
							mysql_db.set_pictures( app.config['mysql_pool'], pid, file_path )
				
			else:
				return json.dumps( {'res':'NO', 'reason':'不支持的文件格式'} )
			
		return json.dumps( {'res':'OK'} )
		
		
	return app