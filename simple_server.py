# get state : http://192.168.1.98:8080/?action=get&pin=27&state=0
# set state : http://192.168.1.98:8080/?action=set&state=0&pin=5
# http://192.168.1.98:8070/?action=bulb_off&id=PER_01
#!/usr/bin/python3
import RPi.GPIO as GPIO
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
from urllib.parse import parse_qs
from yeelight import Bulb
from globals import *

def send_mail(msg):
	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.ehlo()
	server.starttls()
	server.login(MAIL_USERNAME, MAIL_PASSWORD)
	server.sendmail("radek@nakoukal.com", "radek@nakoukal.com", msg)
	server.quit()

def init_GPIO():
	GPIO.setwarnings(False)
	GPIO.setmode(GPIO.BCM)
	GPIO.setup(GPIO_OUT_LIST,GPIO.OUT,initial=0)

class MyRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		parsed = urlparse(self.path)
		qs = parse_qs(parsed.query)
		try:
			action = qs['action']
			if(action[0] == "set"):
				state = qs['state']
				pin   = qs['pin']
				delay = qs['delay']
				bulb  = qs['bulb']
			elif(action[0] == "get"):
				pin   = qs['pin']
			elif(action[0] == "bulb_on"):
				id    = qs['id']
			elif(action[0] == "bulb_off"):
                                id    = qs['id']
			elif(action[0] == "bulb_color"):
				color = qs['color']				
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
			elif(action[0] == "bulb_on" and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				bulb.turn_on()
				message = "OK|BULB_ON|%s" % (id[0])
			elif(action[0] == "bulb_off" and id[0] in (BULB_DICT)):
				bulb = Bulb(BULB_DICT[id[0]])
				bulb.turn_off()
				message = "OK|BULB_OFF|%s" % (id[0])
			else:
				message = "ERR|NO_ACTION|NO_PIN"	

		self.send_response(200)
		# Custom headers, if need be
		self.send_header('Content-type', 'text/html')
		self.end_headers()
		# Custom body
		self.wfile.write(bytes(message, "utf8"))
		return

def init_webserver():
	httpd = HTTPServer(('0.0.0.0', MYPORT), MyRequestHandler)
	httpd.serve_forever()

if __name__ == "__main__":
	init_GPIO()
	init_webserver()
