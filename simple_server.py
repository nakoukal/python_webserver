# get state : http://192.168.1.98:8080/?action=get&pin=27&state=0
# set state : http://192.168.1.98:8080/?action=set&state=0&pin=5
# http://192.168.1.98:8070/?action=bulb_off&id=PER_01
# https://192.168.1.98:4443/?action=set_rel_state&id=C44BB4010000&pin=22&state=1&dat=2020-04-01 00:00
#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import ssl  
import socketserver
import base64
import json
import pymysql.cursors
from urllib.parse import urlparse
from urllib.parse import parse_qs
from yeelight import Bulb
from globals import *

#set gpio pin lists in out
GPIO_OUT_LIST=[5,6,12,13,17,18,19,20,21,22,23,24,25,26,27]
GPIO_IN_LIST=[16]

#set bulb ip dict
BULB_DICT={"DIN01": "192.168.4.157",
        "DIN02": "192.168.4.245",
        "DIN03": "192.168.4.152",
        "OBY01": "192.168.6.243",
        "OBY02": "192.168.6.126",
        "PER01": "192.168.6.204",
        "PER02": "192.168.6.241",
        "LED": "192.168.6.198",
        }

#set webserverport
MYPORT=4443
key = ""

#set sql queries
SQL_GET_REL="call get_releay();"
SQL_GET_TEMP="call get_last_temp('');"
SQL_UPD_REL="update rel_remote set state_extra=%s , state_extra_time=%s where sensorID=%s and releay_number=%s;"

def send_mail(msg):
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.login(MAIL_USERNAME, MAIL_PASSWORD)
	server.sendmail("@.com", "@.com", msg)
	server.quit()

def init_GPIO():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(GPIO_OUT_LIST,GPIO.OUT,initial=0)

def sel_tab(sql):
	connection = pymysql.connect(host=DB_HOST,
					user=DB_USER,
					password=DB_PSWD,
					db=DB_NAME,
					charset=DB_CHAR,
					cursorclass=pymysql.cursors.DictCursor)

	try:
		with connection.cursor() as cursor:
			cursor.execute(sql);
			results = cursor.fetchall()
		return json.dumps(results)
	finally:
		connection.close()	

def upd_rel_state(state,dat,id,pin):
	connection = pymysql.connect(host=DB_HOST,
		user=DB_USER,
		password=DB_PSWD,
		db=DB_NAME,
		cursorclass=pymysql.cursors.DictCursor)
	try:
		with connection.cursor() as cursor:
			result = cursor.execute(SQL_UPD_REL,(state,dat,id,pin));
			connection.commit();
		
		return "OK|UPDATE_REL_STATE"
	
	except pymysql.InternalError as error:	
		code, message = error.args
		return message

	finally:
		connection.close()


class MyRequestHandler(BaseHTTPRequestHandler):
	def do_HEAD(self):
        	print ("send header")
        	self.send_response(200)
        	self.send_header('Content-type', 'text/html')
        	self.end_headers()
	
	def do_AUTHHEAD(self):
		print ("send header")
		self.send_response(401)
		self.send_header('WWW-Authenticate', 'Basic realm=\"Test\"')
		self.send_header('Content-type', 'text/html')
		self.end_headers()


	def end_headers (self):
		self.send_header('Access-Control-Allow-Origin', '*')
		BaseHTTPRequestHandler.end_headers(self)

	def do_REQUEST(self):
		parsed = urlparse(self.path)
		qs = parse_qs(parsed.query)
		try:
			action = qs['action']
			if(action[0] == "set"):
				state = qs['state']
				pin   = qs['pin']
				delay = qs['delay']
			elif(action[0] == "get"):
				pin   = qs['pin']
			elif(action[0] == "get_bulb_state"):
				id    = qs['id']
			elif(action[0] == "set_bulb_state"):
				id    = qs['id']
				state = qs['state']
			elif(action[0] == "bulb_color"):
				id    = qs['id']
				red   = qs['r']
				green = qs['g']
				blue  = qs['b']
			elif(action[0] == 'set_rel_state'):
				id     = qs['id']
				pin    = qs['pin']
				state  = qs['state']
				dat   = qs['dat']
		except KeyError:
			message = "<p>No commands processed</p>"

		else:
			message = "."
			if (action[0] == "set" and state in (["1"], ["0"]) and int(pin[0]) in (GPIO_OUT_LIST) and int(delay[0]) == 0):
				GPIO.output(int(pin[0]), state == ["1"])
				message = "OK|SET|%d|%d" % (int(pin[0]),int(state[0]))
			elif (action[0] == "set" and state in (["1"], ["0"]) and int(pin[0]) in (GPIO_OUT_LIST) and int(delay[0]) > 0):
				message = "OK|SETDELAY|%d|%d|%d" % (int(pin[0]),int(state[0]),int(delay[0]))
				GPIO.output(int(pin[0]), state == ["1"])
				time.sleep(int(delay[0]))
				GPIO.output(int(pin[0]), state == ["0"])
				message = "OK|SETDELAY|%d|%d" % (int(pin[0]),int(state[0]))			
			elif(action[0] == "get" and int(pin[0]) in (GPIO_OUT_LIST)):
				message = "OK|GET|%d|%s" % (int(pin[0]),GPIO.input(int(pin[0])))
			elif(action[0] == "bulb" and state[0] == "1" and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				bulb.turn_on()
				message = "OK|BULB_ON|%s" % (id[0])
			elif(action[0] == "get_bulb_state" and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				status = bulb.get_properties()
				message = "OK|%s|%s" % (id[0],status.get('power'))
			elif(action[0] == "set_bulb_state" and state[0] == "0"  and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				bulb.turn_off()
				message = "OK|BULB_OFF|%s" % (id[0])
			elif(action[0] == "bulb_color" and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				bulb.set_rgb(int(red[0]),int(green[0]),int(blue[0]));
			elif(action[0] == "get_rel"):
				message = sel_tab(SQL_GET_REL);
			elif(action[0] == "get_temp"):
				message = sel_tab(SQL_GET_TEMP);
			elif(action[0] == "set_rel_state"):
				message =  upd_rel_state(state,dat,id,pin)
			else:
				message = "ERR|NO_ACTION|NO_PIN"	

		self.send_response(200)
		# Custom headers, if need be
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		# Custom body
		self.wfile.write(bytes(message, "utf8"))
		return 				
	
	def do_GET(self):
		global key
		if self.headers.get('Authorization') == None:
			self.do_AUTHHEAD()
			self.wfile.write(bytes('no auth header received', "utf8"))
			pass
		elif self.headers.get('Authorization') == 'Basic '+key.decode('ascii'):
			#self.do_AUTHHEAD()
			self.do_REQUEST()
			pass
		

def init_webserver():
	httpd = HTTPServer(('0.0.0.0', MYPORT), MyRequestHandler)
	httpd.socket = ssl.wrap_socket (httpd.socket, certfile='/home/pi/scripts/server.pem', server_side=True)
	print('Started httpserver on port ' , MYPORT)
	
	#Wait forever for incoming htto requests
	httpd.serve_forever()

if __name__ == "__main__":
	init_GPIO()
	key = base64.b64encode(HTTP_KEY.encode('ascii'))
	init_webserver()
