import urllib
import urllib.request
import json


if __name__=='__main__':
	URL = 'http://127.0.0.1:5001/api/pay_by_card/'
	z_id = 1
	g_sp_list = json.dumps( [[7290,'13*13*4',1], [7291,'13*13*5',1]] )
	uid = 205
	card_id = '869BIO'
	
	data = { 'z_id':z_id, 'g_sp_list':g_sp_list, 'uid':uid, 'card_id':card_id, 'addr':'the_place', 'phone':'213455', 'consignee':'wdh' }
	data = urllib.parse.urlencode( data )
	#data = json.dumps( data )
	
	request = urllib.request.Request( URL, data.encode('utf8') )
	response = urllib.request.urlopen( request )
	resp = response.read().decode('utf8')
	print( json.loads(resp) )
	
	

	
	
	