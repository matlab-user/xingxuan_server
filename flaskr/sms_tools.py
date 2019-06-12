import urllib, json
import http.client
#from flask import current_app


def send_sms( phone, text ):
	SMS_HOST = 'smssh1.253.com'
	SMS_PORT = 80
	SMS_SEND_URI = '/msg/send/json'
	SMS_ACCOUNT = 'N9951173'
	SMS_PASSWORD = '8cgvzlbhQ'


	sms_account, sms_password = SMS_ACCOUNT, SMS_PASSWORD
	params = {'account':sms_account , 'password' :sms_password, 'msg': urllib.parse.quote('【果酷】'+text), 'phone':phone, 'report' : 'false' }
	params=json.dumps( params )

	headers = { 'Content-type': 'application/json' }
	conn = http.client.HTTPConnection( SMS_HOST, port=SMS_PORT, timeout=10 )
	conn.request( 'POST', SMS_SEND_URI, params, headers )
	response = conn.getresponse()
	response_str = response.read()
	conn.close()
	response_json = json.loads( response_str )
	return response_json 


if __name__=='__main__':
	text = '星选注册验证码为: %s。请在10分钟内进行验证。' % '123fgh'
	print( text )
	res = send_sms( '15510192330', text )
	print( res )
