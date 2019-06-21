import urllib
import urllib.request
import json


if __name__=='__main__':
	URL = 'http://127.0.0.1:5001/api/cart/del/205'
	
	g_str = json.dumps( [[7290,7291,1], [7290,7291,-1]] )
	data = urllib.parse.urlencode( { 'data':g_str } )
		
	request = urllib.request.Request( URL, data.encode('utf8') )
	response = urllib.request.urlopen( request )
	resp = response.read().decode('utf8')
	print( json.loads(resp) )