import urllib
import urllib.request
import time, json


if __name__=='__main__':
	URL = 'http://127.0.0.1:5001/api/add_zone/'
	
	t1 = time.time()
	t2 = t1 + 60*24*3600
	
	goods = [7290,7291,7292,7293]
	cards_type = ['蛋糕卡','甜品节卡']
	zone_info = { 'name':'wdh测试专区', 't1':t1, 't2':t2, 'goods':json.dumps(goods), 'cards_type':json.dumps(cards_type) }
	
	data = urllib.parse.urlencode( zone_info ).encode( 'utf-8' )
	req = urllib.request.Request( URL, data )
	response = urllib.request.urlopen( req )
	resp_t = response.read().decode( 'utf-8' )
	print( resp_t )