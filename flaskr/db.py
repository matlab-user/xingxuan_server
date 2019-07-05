import redis
import time, json
from flask import current_app
import fcntl, os

# redis 结构:
#	main_page		a:[ {‘product_id’:xx,’name’:xxx,’smallpicture’:xxx,’sp_n’:xx,’sp_v’:xxx},... ],  b:[.......]
#	category_page	类id:[ {product_id:xxx, name:xxx, smallpicture:xxx, listpicture:xxx, sp_n:xx, sp_v:xx}, .... ] ]
#	goods_names		所有产品名称，用,号间隔保存成字符串，用于搜索

# 无则返回 None
def get_main_page_info( pool, b_name ):
	r = redis.Redis( connection_pool=pool )
	res = r.hget( 'main_page', b_name )
	return res

	
def set_main_page_info( pool, b_name, val ):
	r = redis.Redis( connection_pool=pool )
	if not isinstance(val, str):
		val = json.dumps( val )
	r.hset( 'main_page', b_name, val )


def get_category_page_info( pool, category_id ):
	r = redis.Redis( connection_pool=pool )
	res = r.hget( 'category_page', category_id )
	return res


def set_category_page_info( pool, category_id, val ):
	r = redis.Redis( connection_pool=pool )
	if not isinstance(val, str):
		val = json.dumps( val )
	r.hset( 'category_page', category_id, val )


def goods_names_to_redis( pool, names_list ):
	nstr = ','.join( names_list )
	r = redis.Redis( connection_pool=pool )
	r.set( 'goods_names', nstr )


def goods_names_read( pool ):
	r = redis.Redis( connection_pool=pool )
	res = r.get( 'goods_names' )
	return res
	
'''
def set_info_with_id( the_id, j_str ):
	r = redis.Redis( connection_pool=current_app.config['pool'] )
	res = r.hset( 'ids', the_id, j_str )
	return res


# 不存在返回 None
def get_info_with_id( the_id ):
	r = redis.Redis( connection_pool=current_app.config['pool'] )
	res = r.hget( 'ids', the_id )
	return res


# 返回成功写入的数量
def gen_ids( num ):
	r = redis.Redis( connection_pool=current_app.config['pool'] )
	ids = wdh_tools.gen_code( 8, num )
	pipe = r.pipeline()
	for id in ids:
		pipe.hsetnx( 'ids', id, '' )
	res = pipe.execute()
	return	sum(res)
	

def key_fiels( key ):
	r = redis.Redis( connection_pool=current_app.config['pool'] )
	return r.hlen( key )
	

def get_all_info():
	r = redis.Redis( connection_pool=current_app.config['pool'] )
	ids = r.hkeys( 'ids' )
	
	orders_list = []
	for id in ids:
		id = id.decode( 'utf-8' )
		info = r.hget( 'ids', id )
		info = info.decode( 'utf-8' )
		if info!='':
			orders_list.append( info )
	return orders_list
'''


if __name__=='__main__':
	POOL = redis.ConnectionPool( host='localhost', port=6379, db=0 )
	res = get_main_page_info( POOL, 'a' )
	print( res )