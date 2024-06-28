from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time, os, datetime, json, threading
from peripherals import Motor, Temperature, Camera
from gpiozero import OutputDevice, LED
from routines import Experiment

class Incubator():
	def __init__(self):
		self.mqtt_client = self.establish_mqtt()
		self.dtFormat = '%Y-%m-%d %H:%M:%S'
		self.name = os.getenv("Incubator")
		self.led = LED(18)
		self.motor = Motor([21,20,16,7])
		self.heater = OutputDevice(13)
		self.fan = OutputDevice(23)
		self.camera = Camera()
		self.temperature = Temperature()
		self.experiment = None
		self.stop_temp_event = threading.Event()
		self.stop_temp_event.set()
		threading.Thread(target=self.temperature_stream, daemon=True).start()
	
	def establish_mqtt(self):
		mqtt_client = AWSIoTMQTTClient(os.getenv("INCUBATOR"))
		mqtt_client.configureEndpoint(os.getenv("ENDPOINT"), 8883)
		mqtt_client.configureCredentials(os.getenv("ROOTCA"), os.getenv("PRIVKEY"), os.getenv("CERTIF"))

		mqtt_client.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
		mqtt_client.configureDrainingFrequency(2)  # Draining: 2 Hz
		mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
		mqtt_client.configureMQTTOperationTimeout(5)  # 5 sec

		mqtt_client.connect()

		mqtt_client.subscribe("request/led", 1, self.led_message)
		mqtt_client.subscribe("request/motor", 1, self.motor_message)
		mqtt_client.subscribe("request/image", 1, self.image_message)
		mqtt_client.subscribe("request/status", 1, self.status_message)
		mqtt_client.subscribe("request/experiment", 1, self.experiment_message)
		
		return mqtt_client
		
	def led_message(self, client, userdata, message):
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		command = message.payload.decode()
		if command == 'on':
			self.led.on()
		elif command == 'off':
			self.led.off()
	
	def motor_message(self, client, userdata, message):
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		command = message.payload.decode()
		if command == 'clockwise':
			self.motor.rotate(60)
		elif command == 'anticlockwise':
			self.motor.rotate(60, clockwise=False)
    
	def image_message(self, client, userdata, message):
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		payload = self.camera.snapshot()		#TODO
		self.mqtt_client.publish("response/image", json.dumps(payload), 1)
	
	def status_message(self, client, userdata, message):
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		temp_payload = self.temperature.capture()
		work_payload = 
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Sending message: {payload}")
		self.mqtt_client.publish("response/status", json.dumps(payload), 1)
	
	def experiment_message(self, client, userdata, message):
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		#command = message.payload.decode()
		if message.payload["command"] == 'start':
			if self.experiment is None:
				Experiment(self, message.payload["device_name"], message.payload["duration"], message.payload["interval"], message.payload["exp_file"], message.payload["samples"])
			else:
				break
		elif command == 'stop':
			self.experiment.stop_experiment()
		
	def stop_temp():
		self.stop_temp_event.clear()
	
	def start_temp():
		self.stop_temp_event.set()
		self.temperature_stream()
		
	def publish_image():
		pass
	
	def publish_status():
		pass
		
	def start_experiment():
		pass
	
	def stop_experiment():
		pass
	
	def update_shadow():
		pass
				
if __name__ == "__main__":
	session = Incubator()
	
	while True:
		time.sleep(1)
