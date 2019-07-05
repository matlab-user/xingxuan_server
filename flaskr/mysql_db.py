import pymysql, random
from pymysqlpool.pool import Pool
from flask import current_app
import time, json
#import sms_tools
from . import sms_tools

	
def create_conn_pool( db_host, db_user, db_passwd, db_name ):
	pool = Pool( host=db_host, user=db_user, password=db_passwd, db=db_name )
	return pool


# [ {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx, 'sp_id':xx}, ... ]
# sp_n - 规格名称;	sp_v - 价格;	sp_id - 规格id
def get_products_info( pool, pids_list ):
	conn = pool.get_conn()
	cur = conn.cursor()
	out_res = []
	
	sql_str = 'SELECT gk_product.product_id, name, smallpicture, attribute, price, gk_specifications.product_price_id FROM gk_product \
				LEFT JOIN gk_specifications ON gk_product.product_id=gk_specifications.product_id WHERE '
	for pid in pids_list:
		sql_str += 'gk_product.product_id=%s OR '
		
	sql_str = sql_str[0:-3]
	cur.execute( sql_str, pids_list )
	res = cur.fetchall()
	
	for pid in pids_list:
		for r in res:
			if r['product_id']==pid:
				r['smallpicture'] = current_app.config['HTTP_ADDR'] + r['smallpicture']
				r['sp_n'], r['sp_v'] = r['attribute'], r['price']
				del r['attribute'], r['price']
				r['sp_id'] = r['product_price_id']
				out_res.append( r )
				break

	cur.close()
	pool.release( conn )
	return out_res

	
# 按照指定的产品id、规格 取对应的价格信息
# pid_sp_list - [ [pid, sp], [pid,sp]..... ]
def get_products_the_sp_info( pool, pid_sp_list ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT product_id, price, product_price_id FROM gk_specifications WHERE '
	data = []
	for e in pid_sp_list:
		sql_str += '(product_id=%s AND attribute=%s) OR '
		data.extend( e )
	sql_str = sql_str[0:-3]
	
	cur.execute( sql_str, data )			
	res = cur.fetchall()

	cur.close()
	pool.release( conn )
	return res
	
	
# [ {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx}, ... ]
# names_list 中名称的顺序很关键
def get_products_info_by_names( pool, names_list ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	out_res = []
	sql_str = 'SELECT gk_product.product_id, smallpicture, name, price, attribute FROM gk_product LEFT JOIN gk_specifications \
				ON gk_product.product_id=gk_specifications.product_id WHERE gk_product.product_id>=7000 AND ( '
	for n in names_list:
		sql_str += 'name=%s OR '
	sql_str = sql_str[0:-4] + ' )'
	
	cur.execute( sql_str, names_list )
	res = cur.fetchall()
	
	for n in names_list:
		for r in res:
			if r['name']==n:
				r['smallpicture'] = current_app.config['HTTP_ADDR'] + r['smallpicture']
				r['sp_n'], r['sp_v'] = r['attribute'], r['price']
				del r['attribute'], r['price']
				out_res.append( r )
				
	cur.close()
	pool.release( conn )
	return out_res


# res - [ {product_id:xxx, name:xxx, smallpicture:xxx, sp_n:xx, sp_v:xx, sp_id:xx}, .... ]
# sp_v 该规格的价格
def get_category_goods( pool, category_id, limit=50 ):
	res, pids_list = {}, []
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT product_id, name, smallpicture FROM gk_product WHERE category_id=%s AND status=1 LIMIT ' + str(limit)
	cur.execute( sql_str, category_id )
	goods_list = cur.fetchall()
	for g in goods_list:
		res[str(g['product_id'])] = { 'product_id':g['product_id'], 'name':g['name'], 'smallpicture':current_app.config['HTTP_ADDR']+g['smallpicture'] }
		pids_list.append( g['product_id'] )
	
	if pids_list==[]:
		cur.close()
		pool.release( conn )
		return []
			
	sql_str = 'SELECT product_id, attribute, price, product_price_id FROM gk_specifications WHERE '
	for pid in pids_list:
		sql_str += 'product_id=%s OR '
	sql_str = sql_str[0:-4]
	cur.execute( sql_str, pids_list )
	spcs_list = cur.fetchall()
	for v in spcs_list:
		pid_str = str( v['product_id'] )
		res[pid_str]['sp_n'] = v['attribute']
		res[pid_str]['sp_v'] = v['price']
		res[pid_str]['sp_id'] = v['product_price_id']
		
	cur.close()
	pool.release( conn )
	return list( res.values() )
	

# 尽最大可能返回 lens长度， num个 code 集合
def choice_from( lens, num ):
	chrs = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	res = set()
	
	for j in range(10):
		loop = num - len(res)
		if loop==0:
			break;
		
		mid = ''
		for i in range( lens*loop ):
			mid += random.choice( chrs )
			
		for i in range( loop ):
			res.add( mid[i*lens:(i+1)*lens] )		
	return res
	

# 尽最大可能返回 lens长度， num个 code 集合
def choice_from_v2( lens, num ):
	chrs = '0123456789'
	res = set()
	
	for j in range(10):
		loop = num - len(res)
		if loop==0:
			break;
		
		mid = ''
		for i in range( lens*loop ):
			mid += random.choice( chrs )
			
		for i in range( loop ):
			res.add( mid[i*lens:(i+1)*lens] )			
	return list(res)

	
'''
wdh_cards
	card_id
	price			元
	t1				申请时间
	t2				截至时间
	status			正常，已使用、失效（过期未用的）、作废（人为指定的）。norm，used，expired，ban
	user			使用人uid
	t3				开通时间
	if_print		是否已经印刷	
'''
def gen_and_save_new_cards( pool, price, name='星选卡', description='',  valid=730, num=1000 ):
	codes = choice_from( 6, num )
	
	ds, t1 = [], time.time()
	t2 = t1 + valid*24*3600
	for code in codes:
		ds.append( (code, price, t1, t2, name, description) )
		
	sql_str = 'INSERT INTO wdh_cards (card_id, price, t1, t2, status, name, description) VALUES (%s,%s,%s,%s,"norm",%s,%s)'
	conn = pool.get_conn()
	cur = conn.cursor()
	succ = cur.executemany( sql_str, ds )
	conn.commit()
	cur.close()
	pool.release( conn )
	
	return succ


# res -
# 	{'price': 100.0, 't1': 1559021432.0, 't2': 1622093432.0, 't3': None, 'if_print': None, 'card_id': '5IWDSW', 'user': None, 'status': 'norm'}
def get_card_info( pool, card_id ):
	res = {}
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT * FROM wdh_cards WHERE card_id=%s'
	cur.execute( sql_str, card_id )
	res = cur.fetchone()
	cur.close()
	pool.release( conn )

	return res
	

# res - [ {}, {}, {}....]
# 增加 icon 字段
# [ {'price': 100.0, 'rest': 0.0, 'description':xxx, 'name':xxx, 'type':xxx, 't1': 1559021432.0, 't2': 1622093432.0, 'card_id': '5IWDSW', 'status': 'norm'} ]
def get_my_cards( pool, uid ):
	res = []
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT price, rest, name, type, t1, t2, card_id, status, description FROM wdh_cards WHERE user=%s limit 50'
	cur.execute( sql_str, uid )
	res = cur.fetchall()
	cur.close()
	pool.release( conn )
	
	return res


# 如果 new_status = 'used' - 
# new_info - { 'status':'used', 'user':xxx }
# 		   - { 'status':'ban' }
def set_card_status( pool, card_id, new_info ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	if new_info['status']=='used':
		t3 = time.time()
		sql_str = 'UPDATE wdh_cards SET user=%s, t3=%s, status=%s WHERE card_id=%s'
		mid = ( new_info['user'], t3, new_info['status'], card_id )
	else:
		sql_str = 'UPDATE wdh_cards SET status=%s WHERE card_id=%s'
		mid = ( new_info['status'], card_id )
		
	res= cur.execute( sql_str, mid )
	conn.commit()
	cur.close()
	pool.release( conn )

	return res

	
'''
gk_client
	id
	status
	money
	
gk_client_money
	money
	client_id
	description
	money_time			varchar 消费时间
	consume_type		消费项目类型0为 充值, 1为 消费, 2为 分配  3为退款
	voucher_no
	charge_way			收款途径
	account_type		账户类型1为父账号，2为子账号
'''
# new_info - { amount:xx, description:xxx }
def add_money( pool, user, new_info ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'UPDATE gk_client SET money=money+%s WHERE id=%s AND status=1'
	res= cur.execute( sql_str, (new_info['amount'], user) )
	conn.commit()
	if res==0:
		cur.close()
		pool.release( conn )
		return { 'res':'NO', 'reason':'用户不存在' }
		
	ts = time.localtime()
	money_time = time.strftime( '%Y-%m-%d %H:%M:%S', ts )
	voucher_no = time.strftime( '%Y%m%d_%H%M%S', ts )
	
	sql_str = 'INSERT INTO gk_client_money (money,client_id,description,money_time,consume_type,voucher_no,charge_way,\
				account_type) VALUE ( %s,%s,%s,%s,0,%s,%s,1)'
	
	cur.execute( sql_str, (new_info['amount'],user,new_info['description'],money_time,voucher_no,'卡充值') )
	conn.commit()
	cur.close()
	pool.release( conn )

	return {'res':'OK'}


# wdh_verify
#	phone
#	code
#	t
#	password
def user_reg_shortmessage( pool, phone, password ):
	conn = pool.get_conn()
	cur = conn.cursor()
	code = choice_from_v2( 4, 1 )[0]
	
	sql_str = 'SELECT * FROM wdh_verify WHERE phone=%s'
	cur.execute( sql_str, [phone] )
	res = cur.fetchone()
	if res is not None:
		if res['status']=='ban':
			cur.close()
			pool.release( conn )
			return {'res':'NO','reason':'the number has been banned'}
			
		now = time.time()
		if now-res['t']>30:
			sql_str = 'UPDATE wdh_verify SET password=md5(%s), code=%s, t=%s WHERE phone=%s'
			cur.execute( sql_str, [password, code, time.time(), phone] )
			conn.commit()
			# 发送短信
			sms_tools.send_sms( phone, '星选注册验证码为: %s。请在10分钟内进行验证。' % code )
			out_res = {'res':'OK', 'reason':'验证短信已发送'}
		else:
			out_res = {'res':'NO','reason':'too frequent'}
	else:
		sql_str = 'INSERT INTO wdh_verify (phone, password, code, t) VALUES (%s, md5(%s), %s, %s)'
		cur.execute( sql_str, [phone, password, code, time.time()] )
		conn.commit()
		# 发送短信
		sms_tools.send_sms( phone, '星选注册验证码为: %s。请在10分钟内进行验证。' % code )
		out_res = {'res':'OK', 'reason':'验证短信已发送'}
		
	cur.close()
	pool.release( conn )
	
	return out_res
	

'''
gk_client
	name
	password
	status				账号状态1. 正常 2.禁用
	money
	create_time
'''
# password 已经是md5加密后的结果
def user_add_new( pool, name, password ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT name FROM gk_client WHERE name=%s'
	res = cur.execute( sql_str, [name] )
	lt_str = time.strftime( '%Y-%m-%d %H:%M:%S', time.localtime() )
	
	if res==1:		# 已存在该用户名
		sql_str = 'UPDATE gk_client SET password=%s, update_time=%s WHERE name=%s'
		data = [ password, lt_str, name ]	
	else:
		sql_str = 'INSERT INTO gk_client (name, password, status, money, create_time, deleted) VALUES (%s,%s,1,0,%s,0)'
		data = [name, password, lt_str]
		
	res = cur.execute( sql_str, data )
	conn.commit()
	
	cur.close()
	pool.release( conn )
	return res


def user_reg_verify( pool, phone, code ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT * FROM wdh_verify WHERE phone=%s'
	cur.execute( sql_str, [phone] )
	res = cur.fetchone()
	if res is not None:
		if time.time()-res['t'] > 60000:
			out_res = { 'res':'NO', 'reason':'验证码已失效，请重新申请' }
		elif res['code']==code:
			# 新用户记录进 gk_client 数据库中
			user_add_new( pool, res['phone'], res['password'] )
			out_res = { 'res':'OK', 'reason':'注册成功' }
		else:	
			out_res = { 'res':'NO', 'reason':'验证码不匹配' }
	else:
		out_res = { 'res':'NO', 'reason':'无效的手机号' }
	
	cur.close()
	pool.release( conn )
	return out_res


def read_all_goods_names( pool ):
	conn = pool.get_conn()
	cur = conn.cursor()
	out_res = []
	
	sql_str = 'SELECT name FROM gk_product WHERE status=1 AND product_id>=7000 LIMIT 2000'
	cur.execute( sql_str )
	res = cur.fetchall()
	for r in res:
		out_res.append( r['name'] )
	
	cur.close()
	pool.release( conn )
	return out_res
	

# zone_info - {'name':xx, 't1':xx, 't2':xx, 'goods':xx, 'cards_type':xx }
def add_zone( pool, z_info ):
	conn = pool.get_conn()
	cur = conn.cursor()
	sql_str = 'INSERT INTO wdh_zone (name, t1, t2, goods, cards_type, status) VALUES ( %s, %s, %s, %s, %s, "norm" )'
	try:
		exe_res = cur.execute( sql_str, [z_info['name'], z_info['t1'], z_info['t2'], z_info['goods'], z_info['cards_type']] )
	except Exception as e:
		exe_res = 0		

	if exe_res==1:
		res = { 'res':'OK' }
	else:
		res = { 'res':'NO' }
		
	cur.close()
	pool.release( conn )
	return res
	

def get_zones_info( pool ):
	now, res = time.time(), []
	
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT id, name FROM wdh_zone WHERE t1<=%s AND t2>=%s AND status<>"ban"'
	cur.execute( sql_str, (now, now) )
	res = cur.fetchall()
	
	cur.close()
	pool.release( conn )
	return res

	
# [ xx, xx, xx ]
def get_zone_goods( pool, z_id ):
	now, res = time.time(), []
	
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT cards_type, goods FROM wdh_zone WHERE t1<=%s AND t2>=%s AND status<>"ban" AND id=%s'
	cur.execute( sql_str, (now, now, z_id) )
	res = cur.fetchall()
	if len(res)>0:
		goods = json.loads( res[0]['goods'] )
		cards_type = json.loads( res[0]['cards_type']  )
	else:
		goods = []
		cards_type = []

	cur.close()
	pool.release( conn )
	return goods, cards_type
	

# o_info - {z_id, card_id, g_sp_list:[[gid,sp,num,price,price_id]...], uid, addr, phone, amount, consignee }
# gk_order:
#	order_amount		无运费总金额
#	client_id			下单人id
#	status				2-待发货
#	order_time			下单时间
#	order_no			订单id
#	shipping_address	收货地址
#	payUp_mode			3-卡券结帐
#	consignee			收货人
#	telephone			联系电话
#	store_id			产品商家id
#
# gk_order_product
#	product_id			产品id
#	product_price_id	gk_specifications 中对应的价格
#	product_name		产品名称
#	product_attribute	产品规格
#	product_price		产品价格
#	number				数量
#	order_id			订单id
#	business_id			客户id
#
# gk_order_log
#	order_state			订单已支付，3
#	order_flow_time
#	opration_desc
#	order_id

# o_info - {card_id, g_sp_list:[[gid,sp,num,z_id,price,price_id]...], uid, addr, phone, amount, consignee }	
# COST - {'card_cost':card_cost, 'rest_cost':rest_cost}
def gen_order_2( pool, o_info, COST ):
	now, res = time.time(), []
	conn = pool.get_conn()
	cur = conn.cursor()

	lt, uid = time.localtime( now ), o_info['uid']
	tstr_sec = time.strftime( '%Y-%m-%d %H:%M:%S', lt )
	 
	sql_str = 'SELECT product_id, store_id, name FROM gk_product WHERE '
	g_ids, g_info_dict = [], {}
	for g in o_info['g_sp_list']:
		sql_str += 'product_id=%s OR '
		pid = str( g[0] )
		g_ids.append( g[0] )
		g_info_dict[ pid ] = { 'sp':g[1], 'num':g[2], 'p':g[4], 'price_id':g[5] }	
	sql_str = sql_str[0:-3]	
	
	cur.execute( sql_str, g_ids )
	res = cur.fetchall()
	g_store_id = {}
	for r in res:
		pid, store_id, name = str(r['product_id']), str(r['store_id']), r['name']
		sp, num, p, price_id = g_info_dict[pid]['sp'], g_info_dict[pid]['num'], g_info_dict[pid]['p'], g_info_dict[pid]['price_id']
		mid = { 'pid':int(pid), 'sp':sp, 'num':num, 'p':p, 'price_id':price_id, 'name':name }
		if store_id not in g_store_id:
			g_store_id[store_id] = {}
			g_store_id[store_id]['g'] = [ mid ]
			g_store_id[store_id]['sum'] = mid['num'] * mid['p']
		else:
			g_store_id[store_id]['g'].append( mid )	
			g_store_id[store_id]['sum'] += mid['num'] * mid['p']

	# 写订单数据
	# g_store_id - { store_id:{'g':[{'pid':x, 'sp':x, 'num':x, 'p':x, 'price_id':x, 'name':x}...],'sum':x},... }
	sql_str = 'SELECT order_id FROM gk_order WHERE order_no=%s'
	sql_str_1 = 'INSERT INTO gk_order (order_amount,client_id,status,order_time,order_no,shipping_address,payUp_mode, \
			consignee, telephone, store_id ) VALUES ( %s, %s, 2, %s, %s, %s, 3, %s, %s, %s )'
	sql_str_2 = 'INSERT INTO gk_order_product (product_id, product_price_id, product_name, product_attribute, \
			product_price, number, order_id, business_id) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s )'
	for k, v in g_store_id.items():
		order_no = '%d_%s_%s' %( int(now*1000), o_info['uid'], k )
		data = [ v['sum'], o_info['uid'], lt, order_no, o_info['addr'], o_info['consignee'], o_info['phone'], k ]
		cur.execute( sql_str_1, data )
		conn.commit()
		
		cur.execute( sql_str, order_no )
		the_id = cur.fetchone()
		the_id = the_id['order_id']
		
		data = []
		for g in v['g']:
			mid = ( g['pid'], g['price_id'], g['name'], g['sp'], g['p'], g['num'], the_id, o_info['uid'] )
			data.append( mid )
		cur.executemany( sql_str_2, data )
		conn.commit()
	
	if COST['card_cost']>0:
		# 减去卡金额
		sql_str = 'SELECT rest FROM wdh_cards WHERE card_id=%s'
		cur.execute( sql_str, o_info['card_id'] )
		rest = cur.fetchone()
		rest = rest['rest']

		rest -= COST['card_cost']
		if rest>0:
			sql_str = 'UPDATE wdh_cards SET rest=%s WHERE card_id=%s'
			data = [ rest, o_info['card_id'] ]
		else:	
			sql_str = 'UPDATE wdh_cards SET rest=0, status="used" WHERE card_id=%s'
			data = o_info['card_id']	
		cur.execute( sql_str, data )
		conn.commit()
	
	if COST['rest_cost']>0:
		# 减去余额金额(已经保证有足够的金额)
		sql_str = 'UPDATE gk_client	SET money=money-%s WHERE id=%s'
		data = ( COST['rest_cost'], uid )
		cur.execute( sql_str, data )
		conn.commit()
	
	# 记录消费记录
	sql_str = 'INSERT INTO gk_order_log (order_state, order_flow_time, opration_desc, order_id) VALUES (3, %s,"订单已支付", %s)'
	cur.execute( sql_str, (tstr_sec,the_id) )
	conn.commit()
	
	# 清理购物车
	# o_info - {card_id, g_sp_list:[[gid,sp,num,z_id, price,price_id]...], uid, addr, phone, amount, consignee }
	g_info_list = []
	for g in o_info['g_sp_list']:
		pid, sp_id = g[0], str(g[-1])
		g_info_list.append( [pid, int(sp_id), g[3]] )
	# g_info_list: [ [pid,product_price_id,z_id], []... ] 
	cart_del( pool, uid, g_info_list )
		
	cur.close()
	pool.release( conn )
	return {'res':'OK'}
		
'''		
# o_info - {z_id, card_id, g_sp_list:[[gid,sp,num,price,price_id]...], uid, addr, phone, amount, consignee }		
def gen_order( pool, o_info, api_type=1 ):
	now, res = time.time(), []
	conn = pool.get_conn()
	cur = conn.cursor()

	lt = time.localtime( now )
	tstr_sec = time.strftime( '%Y-%m-%d %H:%M:%S', lt )
	uid, z_id = o_info['uid'], o_info['z_id']
		
	sql_str = 'SELECT product_id, store_id, name FROM gk_product WHERE '
	g_ids, g_info_dict = [], {}
	for g in o_info['g_sp_list']:
		sql_str += 'product_id=%s OR '
		g_ids.append( g[0] )
		g_info_dict[ g[0] ] = { 'sp':g[1], 'num':g[2], 'p':g[3], 'price_id':g[4] }
	
	sql_str = sql_str[0:-3]	
	cur.execute( sql_str, g_ids )
	res = cur.fetchall()
	g_store_id = {}
	for r in res:
		pid, store_id, name = r['product_id'], str(r['store_id']), r['name']
		sp, num, p, price_id = g_info_dict[pid]['sp'], g_info_dict[pid]['num'], g_info_dict[pid]['p'], g_info_dict[pid]['price_id']
		mid = { 'pid':pid, 'sp':sp, 'num':num, 'p':p, 'price_id':price_id, 'name':name }
		if store_id not in g_store_id:
			g_store_id[store_id] = {}
			g_store_id[store_id]['g'] = [ mid ]
			g_store_id[store_id]['sum'] = mid['num'] * mid['p']
		else:
			g_store_id[store_id]['g'].append( mid )	
			g_store_id[store_id]['sum'] += mid['num'] * mid['p']
	
	# 写订单数据
	# g_store_id - { store_id:{'g':[{'pid':x, 'sp':x, 'num':x, 'p':x, 'price_id':x, 'name':x}...],'sum':x},... }
	sql_str = 'SELECT order_id FROM gk_order WHERE order_no=%s'
	sql_str_1 = 'INSERT INTO gk_order (order_amount,client_id,status,order_time,order_no,shipping_address,payUp_mode, \
			consignee, telephone, store_id ) VALUES ( %s, %s, 2, %s, %s, %s, 3, %s, %s, %s )'
	sql_str_2 = 'INSERT INTO gk_order_product (product_id, product_price_id, product_name, product_attribute, \
			product_price, number, order_id, business_id) VALUES ( %s, %s, %s, %s, %s, %s, %s, %s )'
	for k, v in g_store_id.items():
		order_no = '%d_%s_%s' %( int(now*1000), o_info['uid'], k )
		data = [ v['sum'], o_info['uid'], lt, order_no, o_info['addr'], o_info['consignee'], o_info['phone'], k ]
		cur.execute( sql_str_1, data )
		conn.commit()
		
		cur.execute( sql_str, order_no )
		the_id = cur.fetchone()
		the_id = the_id['order_id']
		
		data = []
		for g in v['g']:
			mid = ( g['pid'], g['price_id'], g['name'], g['sp'], g['p'], g['num'], the_id, o_info['uid'] )
			data.append( mid )
		cur.executemany( sql_str_2, data )
		conn.commit()
	
	if api_type==1:
		if z_id!='-1':
			# 减去券金额
			sql_str = 'SELECT rest FROM wdh_cards WHERE card_id=%s'
			cur.execute( sql_str, o_info['card_id'] )
			rest = cur.fetchone()
			rest = rest['rest']

			rest -= o_info['amount']
			if rest>0:
				sql_str = 'UPDATE wdh_cards SET rest=%s WHERE card_id=%s'
				data = [ rest, o_info['card_id'] ]
			else:	
				sql_str = 'UPDATE wdh_cards SET rest=0, status=used WHERE card_id=%s'
				data = o_info['card_id']
		else:
			# 减去通用卡金额
			money = get_user_money( pool, uid )
			money -= o_info['amount']
			if money>0:
				sql_str = 'UPDATE gk_client	SET money=%s WHERE id=%s'
				data = ( money, uid )
	else:
		# 使用卡和余额共同支付
		sql_str = 'SELECT rest FROM wdh_cards WHERE card_id=%s'
		cur.execute( sql_str, o_info['card_id'] )
		rest = cur.fetchone()
		rest = rest['rest']
		
		sub_money = o_info['amount'] - rest
		
		# 卡金额减到 0
		sql_str = 'UPDATE wdh_cards SET rest=0, status=used WHERE card_id=%s'
		data = o_info['card_id']	
		cur.execute( sql_str, data )
		conn.commit()
	
		sql_str = 'UPDATE gk_client	SET money=money-%s WHERE id=%s'
		data = ( sub_money, uid )
			
	cur.execute( sql_str, data )
	conn.commit()
		
	# 记录消费记录
	sql_str = 'INSERT INTO gk_order_log (order_state, order_flow_time, opration_desc, order_id) VALUES (3, %s,"订单已支付", %s)'
	cur.execute( sql_str, (tstr_sec,the_id) )
	conn.commit()
	
	# 清理购物车
	# o_info - {z_id, card_id, g_sp_list:[[gid,sp,num,price,price_id]...], uid, addr, phone, amount, consignee }
	g_info_list = []
	for g in o_info['g_sp_list']:
		pid, sp_id = g[0], str(g[-1])
		#res = cart_minus( pool, uid, pid, sp_id, z_id )
		g_info_list.append( [pid, int(sp_id), int(o_info['z_id'])] )
	
	# g_info_list: [ [pid,product_price_id,z_id], []... ] 
	cart_del( pool, uid, g_info_list )
		
	cur.close()
	pool.release( conn )
	return {'res':'OK'}
'''

# wdh_cart
#	uid
#	goods		{ sp_id_1:{'sp':xx, 'p':xx, 'num':xx}, sp_id_2:{}... }	
#	t
#	pid
#	store_id
#	store_name
#	z_id
# 产品增加数量，增加新产品
# in - z_id int 类型
def cart_add( pool, uid, pid, sp_id, z_id ):
	now, mid_res = time.time(), { 'res':'OK' }
	conn = pool.get_conn()
	cur = conn.cursor()
	
	if z_id>=0:
		# 判断专区和商品是否存在
		sql_str = 'SELECT goods FROM wdh_zone WHERE id=%s AND status="norm"'
		cur.execute( sql_str, (z_id,) )
		res = cur.fetchone()
		if res is None:
			mid_res = { 'res':'NO', 'reason':'no this zone' }
		else:
			goods = json.loads( res['goods'] )
			if int(pid) not in goods:
				mid_res = { 'res':'NO', 'reason':'no this product' }
			
		if mid_res['res']=='NO':
			cur.close()
			pool.release( conn )
			return mid_res
	
	sql_str = 'SELECT goods, z_id FROM wdh_cart WHERE uid=%s AND pid=%s AND z_id=%s'
	cur.execute( sql_str, (uid, pid, z_id) )
	res = cur.fetchone()
	if res is None:		# 添加新产品
		sql_str = 'SELECT store_id, attribute, gk_specifications.price FROM gk_product LEFT JOIN gk_specifications \
				ON gk_product.product_id=gk_specifications.product_id WHERE gk_product.product_id=%s AND gk_specifications.product_price_id=%s'
		cur.execute( sql_str, (pid,sp_id) )
		res = cur.fetchone()
		if res is None:
			mid_res = { 'res':'NO', 'reason':'goods info err' }
			cur.close()
			pool.release( conn )
			return mid_res
			
		store_id, sp, p = res['store_id'], res['attribute'], res['price']
		
		sql_str = 'SELECT store_name FROM gk_store_info WHERE store_id=%s'
		cur.execute( sql_str, (store_id,) )
		res = cur.fetchone()
		store_name = res['store_name']
		
		goods = { sp_id: {'sp':sp, 'p':p, 'num':1} }
		goods = json.dumps( goods )
		sql_str = 'INSERT INTO wdh_cart (uid,goods,t,pid,store_id,store_name,z_id) VALUES (%s,%s,%s,%s,%s,%s,%s)' 
		cur.execute( sql_str, (uid, goods, now, pid, store_id, store_name, z_id) )
		conn.commit()
		
		mid_res = { 'res':'OK' }
		
	else:				# 更新产品数量
		goods = json.loads( res['goods'] )
		if sp_id in goods:
			goods[sp_id]['num'] += 1
		else:
			sql_str = 'SELECT attribute, price FROM gk_specifications WHERE product_id=%s AND product_price_id=%s'
			cur.execute( sql_str, [pid, sp_id] )
			res = cur.fetchone()
			if res is None:
				mid_res = { 'res':'NO', 'reason':'no this sp_id' }
				cur.close()
				pool.release( conn )
				return mid_res
			else:
				mid = { 'sp': res['attribute'], 'p':res['price'], 'num':1 }
				goods[sp_id] = mid
				
		goods = json.dumps( goods )
		sql_str = 'UPDATE wdh_cart SET goods=%s WHERE uid=%s AND pid=%s AND z_id=%s'
		cur.execute( sql_str, (goods, uid, pid, z_id) )
		conn.commit()
		mid_res = { 'res':'OK' }
		
	cur.close()
	pool.release( conn )
	return mid_res

	
# sp_id  - string
def cart_minus( pool, uid, pid, sp_id, z_id ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT goods, z_id FROM wdh_cart WHERE uid=%s AND pid=%s AND z_id=%s'
	cur.execute( sql_str, (uid, pid, z_id) )
	res = cur.fetchone()
	if res is None:	
		out_res = { 'res':'NO', 'reason':'no this product' }
	else:
		goods = json.loads( res['goods'] )
		if sp_id in goods:
			goods[sp_id]['num'] -= 1
			if goods[sp_id]['num']==0:
				del goods[sp_id]
				if goods=={}:
					sql_str = 'DELETE FROM wdh_cart WHERE uid=%s AND pid=%s AND z_id=%s'
					data = ( uid, pid, z_id )
				else:
					goods = json.dumps( goods )
					sql_str = 'UPDATE wdh_cart SET goods=%s WHERE uid=%s AND pid=%s AND z_id=%s'
					data = ( goods, uid, pid, z_id )
			else:
				goods = json.dumps( goods )
				sql_str = 'UPDATE wdh_cart SET goods=%s WHERE uid=%s AND pid=%s AND z_id=%s'
				data = ( goods, uid, pid, z_id )
					
			cur.execute( sql_str, data )
			conn.commit()
			out_res = { 'res':'OK' }
		else:
			out_res = { 'res':'NO', 'reason':'no the sp_id' }
			
	cur.close()
	pool.release( conn )
	return out_res


# g_info_list: [ [pid,product_price_id,z_id], []... ]
# [pid, product_price_id, z_id] - 都为 int 类型
def cart_del( pool, uid, g_info_list ):

	data, out_res = [], { 'res':'OK' }
	sql_str = 'SELECT pid, goods, z_id FROM wdh_cart WHERE '
	try:
		for g in g_info_list:
			sql_str += '(uid=%s AND pid=%s AND z_id=%s) OR '
			data.extend( [uid, g[0], g[2]] )
	except:
		return { 'res':'NO', 'reason':'传入参数错误' }
	
	conn = pool.get_conn()
	cur = conn.cursor()

	sql_str = sql_str[0:-4]
	cur.execute( sql_str, data )
	res = cur.fetchall()

	if res==():
		out_res = { 'res':'NO', 'reason':'no this product' }		
	else:
		for g in g_info_list:
			pid, z_id = g[0], g[2]
			try:
				sp_id = str( g[1] )
			except:
				continue

			for r in res:
				if pid!=r['pid'] or z_id!=r['z_id']:
					continue

				goods = json.loads( r['goods'] )
				if sp_id not in goods:
					continue
				else:
					del goods[sp_id]
					if goods=={}:
						sql_str = 'DELETE FROM wdh_cart WHERE uid=%s AND pid=%s AND z_id=%s'
						data = ( uid, pid, z_id )
					else:
						goods = json.dumps( goods )
						sql_str = 'UPDATE wdh_cart SET goods=%s WHERE uid=%s AND pid=%s AND z_id=%s'
						data = ( goods, uid, pid, z_id )
						
					cur.execute( sql_str, data )
					conn.commit()	
					out_res = { 'res':'OK' }
					
	cur.close()
	pool.release( conn )
	return out_res
	

# [ {cell_1}, {cell_2}... ]
# cell_x:
#	store_id、store_name、goods---list类型， [ {g_1}, {}... ]
#	
# g_x
#	pid、name、pic、g_info---list, [ {sp1}, {} ]
#
# sp_x
#	sp_id、sp、p、z_id、num
#
#  最终输出结构，例: 
#	[ {'store_id':x, 'store_name':x, 'goods':[ {'pid':x,'name':x,'pic':x, 'g_info':{'sp_id':x,'sp':x, 'p':x, 'z_id':x, 'num':z,'cards_type':x} }, {}...] }, {}...] }, ... ]
#	
#	处理过程的中间格式为:
#	{ <store_id1>:{'name':store_name, pid1:{ 'name':产品名称, 'pic':图标路径, 'sp_info':[ {g_info},...] }, pid2:{}... }, <store_id2>:{} }
#	g_info:
#		sp_id	产品规格id
#		sp		产品规格名称
#		p		产品价格
#		z_id	专区id
#		num		购买数量
def cart_get( pool, uid ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	out_res, pids_list = {}, []
	sql_str = 'SELECT pid, goods, store_id, store_name, z_id FROM wdh_cart WHERE uid=%s'
	cur.execute( sql_str, (uid,) )
	res = cur.fetchall()
	if len(res)==0:
		cur.close()
		pool.release( conn )
		return []
	
	z_ids, zone_id_type = set(), {}
	for r in res:
		z_ids.add( r['z_id'] )
		
	print( 'a'*8, list(z_ids) )
	
	sql_str = 'SELECT id, cards_type FROM wdh_zone WHERE '
	for z in z_ids:
		sql_str += 'id=%s OR '
	sql_str = sql_str[0:-4]
	
	cur.execute( sql_str, list(z_ids) )
	res_card_types = cur.fetchall()
	for r in res_card_types:
		zone_id_type[str(r['id'])] = json.loads( r['cards_type'] )
	
	print( 'l'*8, zone_id_type )
	
	for r in res:
		z_ids.add( r['z_id'] )
		store_id, goods, store_name, pid, z_id = r['store_id'], r['goods'], r['store_name'], r['pid'], r['z_id']
		pids_list.append( pid )
		
		goods = json.loads( goods )
		if store_id not in out_res:
			out_res[ store_id ] = { 'name':store_name }
			
		if str(pid) not in out_res[store_id]:
			out_res[ store_id ][str(pid)] = { 'sp_info': [] }

		for k, v in goods.items():
			v['z_id'] = z_id
			print( 'm'*8,  z_id, str(z_id) in zone_id_type )
			if str(z_id) in zone_id_type:
				v['cards_type'] = zone_id_type[ str(z_id) ]
			v['sp_id'] = k
			out_res[ store_id ][str(pid)]['sp_info'].append( v )
	
	sql_str = 'SELECT product_id, name, smallpicture, store_id FROM gk_product WHERE '
	for p in pids_list:
		sql_str += ' product_id=%s OR'
	sql_str = sql_str[0:-3]
	cur.execute( sql_str, pids_list )
	res = cur.fetchall()
	if len(res)==0:
		cur.close()
		pool.release( conn )
		return []

	for r in res:
		pid, name, pic, store_id = r['product_id'], r['name'], r['smallpicture'], r['store_id']
		out_res[ store_id ][str(pid)]['name'] = name
		out_res[ store_id ][str(pid)]['pic'] = current_app.config['HTTP_ADDR'] + pic

	cur.close()
	pool.release( conn )
	
	# 转成最终输出格式
	out = []
	for k, v in out_res.items():
		mid = { 'store_id':k, 'store_name':v['name'], 'goods':[] }
		del v['name']
		for k1, v1 in v.items():
			for sp_v in v1['sp_info']:
				mid_g_x = { 'pid':k1, 'name':v1['name'], 'pic':v1['pic'], 'g_info':{} }
				mid_g_x['g_info'] = sp_v
				mid['goods'].append( mid_g_x )
		out.append( mid )
	
	return out


def transfer( pool, uid, from_card_id, to_who, sum ):
	now, out_res = time.time(), { 'res':'OK' }
	conn = pool.get_conn()
	cur = conn.cursor()
	
	if from_card_id.count( '_' )>2:
		out_res = { 'res':'OK', 'reason':'too many transfers' }
	else:	
		sql_str = 'SELECT price, rest, name, type, t1, t2 FROM wdh_cards WHERE card_id=%s AND user=%s AND status=norm'
		cur.execute( sql_str, (from_card_id, uid) )
		res = fetchone()
		if res is None:
			out_res = { 'res':'NO', 'reason':'此卡已失效或不存在' }
		elif now>=t1 and now<=t2:
			if res['rest']>=sum:
				no = 1
				#sql_str = 'INSERT INTO wdh_cards () '
				for i in range(3):
					pass
			else:
				out_res = { 'res':'NO', 'reason':'余额不足' }
		else:
			out_res = { 'res':'NO', 'reason':'此卡已过期' }
		
		
	cur.close()
	pool.release( conn )
	return out_res


def orders_get( pool, offset, status ):
	out_res = []
	conn = pool.get_conn()
	cur = conn.cursor()
				
	sql_str = 'SELECT order_id, order_no, order_amount, fee, order_time, send_time, shipping_address, consignee, \
				telephone, gk_store_info.store_name FROM gk_order LEFT JOIN gk_store_info ON gk_store_info.store_id=gk_order.store_id \
				WHERE status=%s ORDER BY order_id DESC LIMIT %s, 50'
	cur.execute( sql_str, (status, int(offset)) )
	res = cur.fetchall()
	out_res = res
	
	cur.close()
	pool.release( conn )
	return out_res


def get_user_money( pool, user_id ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT money FROM gk_client WHERE id=%s'
	cur.execute( sql_str, (user_id,) )
	res = cur.fetchone()
	if res is None:
		money = -1
	else:
		money = res['money']
	cur.close()
	pool.release( conn )
	return money


# zone_ids_list - [xxx,xxx,xxx]
# out_res - [ {'enable':'Y'/'N', 'price': 100.0, 'rest': 0.0, 'description':xxx, 'name':xxx, 'type':xxx, 't1': 1559021432.0, 't2': 1622093432.0, 'card_id': '5IWDSW', 'status': 'norm'} ]
# 其中第一个为最快过期的卡券
def available_cards( pool, uid, zone_ids_list ):
	all_my_cards = get_my_cards( pool, uid )
	if all_my_cards==[]:
		return []
	
	now = time.time()
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT cards_type FROM wdh_zone WHERE t1<=%s AND t2>=%s AND status<>"ban" '
	for z in zone_ids_list:
		sql_str += 'OR id=%s '
	data = [ now, now ]
	data.extend( zone_ids_list )
	
	cur.execute( sql_str, data )
	res = cur.fetchall()
	cur.close()
	pool.release( conn )
	
	out_res, zone_cards, mid, mid_rest = [], set(), {}, []
	# cards_type - [xx,xx,xx..] 的 json-str
	for r in res:
		zone_cards.update( json.loads( r['cards_type'] ) )
	zone_cards = list( zone_cards )
		
	for mc in all_my_cards:
		if mc['type'] in zone_cards and mc['rest']>0:
			mc['enable'] = 'Y'
			mid[mc['t2']] = mc
		else:
			mc['enable'] = 'N'
			mid_rest.append( mc )
	
	keys = list( mid.keys() )
	keys.sort()
	out_res = [ mid[key] for key in keys ]
	out_res.extend( mid_rest )
	
	return out_res
	
	
if __name__=='__main__':
	'''
	db_user = 'guocool'
	db_passwd = 'aZuL2H58CcrzhTdt'
	db_host = '101.200.233.199'
	db_name = 'guocoolv2.0'
	'''	
	db_host = '127.0.0.1'
	db_user = 'blue'
	db_passwd = 'blue'
	db_name = 'guocoolv2.0'
	db_port = 3306
	db_charset = 'utf8'
	
	POOL = create_conn_pool( db_host, db_user, db_passwd, db_name )
	#get_products_info( POOL, [7249,218,971] )
	#res = read_all_goods_names( POOL )
	#get_products_info_by_names( POOL, ['水果礼盒','红枣姜茶','桂圆红枣盒装135g'] )
	#print( res )
	
	'''
	res = get_product_info( POOL, 971 )
	res = get_products_info( POOL, [218,971] )
	get_category_goods( POOL, 24 )
	gen_and_save_new_cards( POOL, 100, num=5 )
	res = get_card_info(POOL, '5IWDSWn' )
	res = add_money( POOL, 44, { 'amount':1, 'name':'test', 'description':'test recharge' } )
	'''
	#res = user_reg_verify( POOL, '15510192330', '123456' )
	#print( res )
	#user_reg_verify( POOL, '15510192330', '123456' )
	#user_add_new( POOL, '15510192330', '1234' )