import urllib
import urllib.request
import random, hashlib
import xml.etree.ElementTree as ET


'''
//secret 第三方用户唯一凭证密钥，即appsecret
WX_APP_SECRET = "c531344a52dfd6ef50b51e92ad3efe79";
//扫码回调地址(公众号里配置)
//WX_CALLBACK_URL = "http://guocool.com/weixin_code/weixinPay/callback";
//支付回调
WX_PAY_CALLBACK_URL = "http://www.guocool.com/";
'''

APP_ID = 'wxe74ba8a89308a8d5'
URL = 'https://api.mch.weixin.qq.com/pay/unifiedorder'
MCH_ID = '1410693902'
KEY = '87JUomnm3qrsdP840VCngty55Yixzon5'
	
# 尽最大可能返回 lens 长度的 code
def choice_from_v2( lens ):
	chrs = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
	res = ''
	for i in range( lens ):
		res += random.choice( chrs )
	return res
	

def to_xml( pay_info ):
	xml = '<xml>'
	for k, v in pay_info.items():
		xml += '<%s>%s</%s>' %( k, v, k )
	xml += '</xml>'
	return xml

	
def gen_sign( pay_info, key ):
	keys_list = list( pay_info.keys() )
	keys_list.sort()
	str_a = ''
	for k in keys_list:
		str_a += '%s=%s&' %( k, pay_info[k] )
	str_a += 'key=%s' % key
	res = hashlib.md5( str_a.encode('utf-8') ).hexdigest().upper()
	return res

	
# pay_info:	dict 类型, 保证值都不为空
#	body
#	out_trade_no
#	total_fee
#	trade_type
# appid、mch_id、nonce_str、spbill_create_ip、notify_url、sign 由函数内补齐
# trade_type			JSAPI--JSAPI支付（或小程序支付）、NATIVE--Native支付、APP--app支付，MWEB--H5支付	
def gen_pay_xml( pay_info ):
	pay_info['appid'] = APP_ID
	pay_info['mch_id'] = MCH_ID
	pay_info['nonce_str'] = choice_from_v2( 32 )
	pay_info['spbill_create_ip'] = '101.200.233.199'
	pay_info['notify_url'] = 'http://101.200.233.199/'
	
	pay_info['sign'] = gen_sign( pay_info, KEY )
	xml = to_xml( pay_info )	
	return xml


#以下字段在return_code为SUCCESS的时候有返回
#	appid
#	mch_id
#	nonce_str
#	sign
#	result_code
# 以下字段在return_code 和result_code都为SUCCESS的时候有返回
#	trade_type
#	prepay_id
def weixin_pay( pay_info ):
	xml = gen_pay_xml( pay_info )
	req = urllib.request.Request( URL, xml.encode('utf-8') )
	response = urllib.request.urlopen( req )
	resp_t = response.read().decode('utf-8')
	print( resp_t )
	
	root = ET.fromstring( resp_t )
	for child in root:
		print( child.tag,':', child.text ) 

	

if __name__=='__main__':
	pay_info = { 'body':'wdh充值', 'attach':'支付测试', 'out_trade_no':'20190612-5658', 'total_fee':'1', 'trade_type':'APP' }
	#pay_info = { 'appid':'wxd930ea5d5a258f4f', 'mch_id':'10000100', 'device_info':'1000', 'body':'test', 'nonce_str':'ibuaiVcKdpRxkhJA' }
	#print( gen_sign(pay_info, '192006250b4c09247ec02edce69f6a2d') )
	weixin_pay( pay_info )

