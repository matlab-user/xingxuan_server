import pymysql
import random, json


def conn_mysql( ip, user, passwd, db_name, db_port, db_charset ):
	try:
		conn = pymysql.connect( host=ip, user=user, password=passwd, db=db_name, port=db_port, charset=db_charset )
	except:
		conn = []	
	return conn
	

def get_set_the_store_all_goods( sql_conn, store_id, min, max ):
	mid_res = []
	
	cur = sql_conn.cursor()
	sql_str = 'SELECT gk_product.product_id, gk_specifications.price, product_price_id FROM gk_product \
				LEFT JOIN gk_specifications ON gk_product.product_id=gk_specifications.product_id WHERE store_id=%s'
	
	cur.execute( sql_str, (store_id,) )
	res = cur.fetchall()
	for r in res:
		mid = { 'pid':r[0], 'price':r[1], 'product_price_id':r[2] }
		plus = round( random.uniform(min, max), 1 )
		if mid['price'] is not None:
			mid['m_price'] = mid['price'] + plus
		mid_res.append( mid )
	
	sql_str = 'UPDATE gk_specifications SET m_price=%s WHERE product_price_id=%s'
	for r in mid_res:
		if 'm_price' in r:
			cur.execute( sql_str, (r['m_price'], r['product_price_id']) )
			sql_conn.commit()
	
	cur.close()	
	return res
	

# f-新鲜指数，d-美味指数，c-便捷指数，h-健康指数，p-流行指数
def set_star_v( sql_conn ):
	cur = sql_conn.cursor()
	sql_str = 'SELECT product_id FROM gk_product WHERE product_id>=7000'
	cur.execute( sql_str )
	res = cur.fetchall()
	
	sql_str = 'UPDATE gk_product SET star_v=%s WHERE product_id=%s'
	
	for r in res:
		pid = r[0]
		v1, v2, v3, v4, v5 = random.uniform(4, 5), random.uniform(4, 5), random.uniform(4, 5), random.uniform(4, 5), random.uniform(4, 5)
		mid = {'f':round(v1,1), 'd':round(v2,1), 'c':round(v3,1), 'h':round(v4,1), 'p':round(v5,1) }
		mid_str = json.dumps( mid )
		cur.execute( sql_str, (mid_str, pid) )
		sql_conn.commit()
		
	cur.close()	
	return 
	
	

if __name__=='__main__':

	db_ip = '101.200.233.199'
	db_user = 'guocool'
	db_passwd = 'aZuL2H58CcrzhTdt'
	db_port = 3306
	db_charset = 'utf8'
	db_name = 'guocoolv2.0'
	
	sql_conn = conn_mysql( db_ip, db_user, db_passwd, db_name, db_port, db_charset )
	#get_set_the_store_all_goods( sql_conn, 7005, 5, 10 )
	set_star_v( sql_conn )
	