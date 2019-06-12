import pymysql, random
from pymysqlpool.pool import Pool
import time, sys


	
def create_conn_pool( db_host, db_user, db_passwd, db_name ):
	pool = Pool( host=db_host, user=db_user, password=db_passwd, db=db_name )
	return pool


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

# python3 create_new_cards.py 99.9 10

if __name__=='__main__':

	db_user = 'guocool'
	db_passwd = 'aZuL2H58CcrzhTdt'
	db_host = '101.200.233.199'
	db_name = 'guocoolv2.0'
	
	money = float( sys.argv[1] )
	num = int( sys.argv[2] )
	
	POOL = create_conn_pool( db_host, db_user, db_passwd, db_name )
	gen_and_save_new_cards( POOL, money, num=num )
