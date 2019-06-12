import pymysql, random
from pymysqlpool.pool import Pool
from flask import current_app
import time
#import sms_tools
from . import sms_tools

	
def create_conn_pool( db_host, db_user, db_passwd, db_name ):
	pool = Pool( host=db_host, user=db_user, password=db_passwd, db=db_name )
	return pool

	
'''
# {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx}
def get_product_info( pool, pid ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT product_id, name, smallpicture FROM gk_product WHERE product_id=%s'
	cur.execute( sql_str, [ pid ] )
	res = cur.fetchone()

	sql_str = 'SELECT attribute, price FROM gk_specifications WHERE product_id=%s'
	cur.execute( sql_str, [ pid ] )
	mid = cur.fetchone()
	res['sp_n'], res['sp_v'] = mid['attribute'], mid['price']
	
	cur.close()
	pool.release( conn )
	
	return res
'''
	

# [ {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx}, ... ]
def get_products_info( pool, pids_list ):
	conn = pool.get_conn()
	cur = conn.cursor()
	out_res = []
	
	sql_str = 'SELECT gk_product.product_id, name, smallpicture, attribute, price FROM gk_product \
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
				out_res.append( r )
				break

	cur.close()
	pool.release( conn )
	return out_res

	
# [ {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx}, ... ]
# names_list 中名称的顺序很关键
def get_products_info_by_names( pool, names_list ):
	conn = pool.get_conn()
	cur = conn.cursor()
	
	out_res = []
	sql_str = 'SELECT gk_product.product_id, smallpicture, name, price, attribute FROM gk_product LEFT JOIN gk_specifications \
				ON gk_product.product_id=gk_specifications.product_id WHERE '
	for n in names_list:
		sql_str += 'name=%s OR '
	sql_str = sql_str[0:-4]
	
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


# res - [ {product_id:xxx, name:xxx, smallpicture:xxx, listpicture:xxx, sp_n:xx, sp_v:xx}, .... ]
# sp_v 该规格的价格
def get_category_goods( pool, category_id, limit=20 ):
	res, pids_list = {}, []
	conn = pool.get_conn()
	cur = conn.cursor()
	
	sql_str = 'SELECT product_id, name, smallpicture FROM gk_product WHERE category_id=%s AND status=1 LIMIT ' + str(limit)
	cur.execute( sql_str, category_id )
	goods_list = cur.fetchall()
	for g in goods_list:
		res[str(g['product_id'])] = { 'product_id':g['product_id'], 'name':g['name'], 'smallpicture':g['smallpicture'] }
		pids_list.append( g['product_id'] )
	
	if pids_list==[]:
		return []
	
	sql_str = 'SELECT business_id, photo_url, business_type FROM gk_picture WHERE ('
	for pid in pids_list:
		sql_str += 'business_id=%s OR '
	sql_str = sql_str[0:-4] + ') AND business_type=4'

	cur.execute( sql_str, pids_list )
	listps = cur.fetchall()
	for i, v in enumerate( listps ):
		pid_str = str( v['business_id'] )
		res[pid_str]['listpicture'] = current_app.config['HTTP_ADDR'] + v['photo_url']
			
	sql_str = 'SELECT product_id, attribute, price FROM gk_specifications WHERE '
	for pid in pids_list:
		sql_str += 'product_id=%s OR '
	sql_str = sql_str[0:-4]
	cur.execute( sql_str, pids_list )
	spcs_list = cur.fetchall()
	for v in spcs_list:
		pid_str = str( v['product_id'] )
		res[pid_str]['sp_n'] = v['attribute']
		res[pid_str]['sp_v'] = v['price']
		
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
	get_products_info_by_names( POOL, ['水果礼盒','红枣姜茶','桂圆红枣盒装135g'] )
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