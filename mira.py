from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time, os, datetime, json, threading, boto3
from peripherals import Motor, Temperature, Camera
from gpiozero import OutputDevice, LED
from awsiot import mqtt5_client_builder
from awscrt import mqtt5, http
from concurrent.futures import Future
import cv2

future_stopped = Future()
future_connection_success = Future()
received_count = 0

class Incubator():
	def __init__(self):
		self.mqtt_client = self.establish_mqtt()
		self.dtFormat = '%Y-%m-%d %H:%M:%S'
		self.name = os.environ["INCUBATOR"]
		self.led = LED(18)
		self.motor = Motor([12,16,20,21])
		self.heater = OutputDevice(13)
		self.fan = OutputDevice(23)
		self.camera = Camera()
		self.temperature = Temperature()
		self.experiment = None
		self.stop_temp_event = threading.Event()
		self.stop_temp_event.set()
		
		#threading.Thread(target=self.status_message, daemon=True).start()
	
	def establish_mqtt(self):
		client = mqtt5_client_builder.mtls_from_path(
        endpoint=os.getenv("ENDPOINT"),
        port=8883,
        cert_filepath=os.getenv("CERTIF"),
        pri_key_filepath=os.getenv("PRIVKEY"),
        ca_filepath=os.getenv("ROOTCA"),
        on_publish_received=self.on_publish_received,
        on_lifecycle_stopped=self.on_lifecycle_stopped,
        on_lifecycle_connection_success=self.on_lifecycle_connection_success,
        on_lifecycle_connection_failure=self.on_lifecycle_connection_failure,
        client_id=os.getenv("INCUBATOR"))
		client.start()
		sub_future = client.subscribe(subscribe_packet=mqtt5.SubscribePacket(subscriptions=[mqtt5.Subscription(topic_filter="request/led",qos=mqtt5.QoS.AT_LEAST_ONCE), 
																							mqtt5.Subscription(topic_filter="request/motor",qos=mqtt5.QoS.AT_LEAST_ONCE),
																							mqtt5.Subscription(topic_filter="request/temperature",qos=mqtt5.QoS.AT_LEAST_ONCE),
																							mqtt5.Subscription(topic_filter="request/status",qos=mqtt5.QoS.AT_LEAST_ONCE),
																							mqtt5.Subscription(topic_filter="request/experiment",qos=mqtt5.QoS.AT_LEAST_ONCE)
																							]))
		#mqtt_client.subscribe("request/led", 1, self.led_message)
		#mqtt_client.subscribe("request/motor", 1, self.motor_message)
		#mqtt_client.subscribe("request/image", 1, self.image_message)
		#mqtt_client.subscribe("request/status", 1, self.status_message)
		#mqtt_client.subscribe("request/experiment", 1, self.experiment_message)
		suback = sub_future.result(100)
		return client
	
	# Callback when any publish is received
	def on_publish_received(self, publish_packet_data):
		publish_packet = publish_packet_data.publish_packet
		assert isinstance(publish_packet, mqtt5.PublishPacket)
		print("Received message from topic'{}':{}".format(publish_packet.topic, publish_packet.payload))
		global received_count
		received_count += 1
		if publish_packet.topic == "request/led":
			self.led_message(publish_packet.payload)
			
		elif publish_packet.topic == "request/motor":
			self.motor_message(publish_packet.payload)
			
		elif publish_packet.topic == "request/temperature":
			self.temp_message(publish_packet.payload)
			
		elif publish_packet.topic == "request/status":
			self.status_message(publish_packet.payload)
			
		elif publish_packet.topic == "request/experiment":
			self.experiment_message(publish_packet.payload)

	# Callback for the lifecycle event Stopped
	def on_lifecycle_stopped(self, lifecycle_stopped_data: mqtt5.LifecycleStoppedData):
		print("Lifecycle Stopped")
		global future_stopped
		future_stopped.set_result(lifecycle_stopped_data)


	# Callback for the lifecycle event Connection Success
	def on_lifecycle_connection_success(self, lifecycle_connect_success_data: mqtt5.LifecycleConnectSuccessData):
		print("Lifecycle Connection Success")
		global future_connection_success
		future_connection_success.set_result(lifecycle_connect_success_data)


	# Callback for the lifecycle event Connection Failure
	def on_lifecycle_connection_failure(self, lifecycle_connection_failure: mqtt5.LifecycleConnectFailureData):
		print("Lifecycle Connection Failure")
		print("Connection failed with exception:{}".format(lifecycle_connection_failure.exception))
    
	def led_message(self, payload):
		#print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {payload}")
		command = payload.decode()
		print(command)
		if command == "on":
			self.led.on()
		elif command == "off":
			self.led.off()
	
	def motor_message(self, payload):
		#print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {payload}")
		command = payload.decode()
		if command == 'clockwise':
			self.motor.rotate(60)
		elif command == 'anticlockwise':
			self.motor.rotate(60, clockwise=False)
    
	def temp_message(self, payload):
		#print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
			
		#self.mqtt_client.publish(mqtt5.PublishPacket(topic="response/image", payload=json.dumps(payload), qos=mqtt5.QoS.AT_LEAST_ONCE))
	def generate_presigned_url(self, object_name, expiration=3600):
		response = self.s3.generate_presigned_url('get_object', Params={'Bucket':self.bucket_name, 'Key': object_name}, ExpiresIn=expiration)
		return response
		
	def status_message(self, payload):
		#print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		#while self.stop_temp_event.is_set():
		temp_payload = self.temperature.capture()
		if self.experiment is not None:
			work_payload = self.experiment.status
			payload = {**work_payload, **temp_payload}
		else:
			payload = temp_payload
		print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Sending message: {payload}")
		self.mqtt_client.publish(mqtt5.PublishPacket(topic="response/status", payload=json.dumps(payload), qos=mqtt5.QoS.AT_LEAST_ONCE))
		#self.mqtt_client.publish("response/status", json.dumps(payload), 1)
		#time.sleep(3)
	
	def experiment_message(self, payload):
		#print(f"[{datetime.datetime.now().strftime(self.dtFormat)}]		Received message: {message.payload}")
		command = json.loads(payload.decode())
		if command['command'] == 'start':
			if self.experiment is None:
				Experiment(self, command["device_name"], command["duration"], command["interval"], command["experiment_file"], {1:command["sample_1"],2:command["sample_2"], 3:command["sample_3"], 4:command["sample_4"], 5:command["sample_5"], 6:command["sample_6"]})
			else:
				return
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

class Experiment(Incubator):
	def __init__(self, incubator, device_name, duration, interval, exp_file, samples):
		#super().__init__()
		self.incubator = incubator
		self.incubator.experiment = self
		self.device_name = device_name
		self.duration = float(duration)
		self.interval = int(interval)
		self.exp_file = exp_file
		self.samples = samples
		self.status = {'experiment_running': 'False', 
						'device_name': f"{self.device_name}", 
						'duration':f"{self.duration}", 
						'interval':f"{self.interval}", 
						'exp_file':f"{self.exp_file}", 
						'sample_names':f"{self.samples}", 
						'iterations': '0'}
		self.local_dir = self.make_unique_dir(self.status['exp_file'])
		self.start_experiment_thread = threading.Thread(target=self.start_experiment, daemon=True)
		self.experiment_flag = threading.Event()
		self.start_time = datetime.datetime.now()
		self.end_time = self.start_time + datetime.timedelta(hours=self.duration)
		self.start_experiment_thread.start()
		self.status["start_time"] = self.start_time.strftime('%Y-%m-%d %H:%M:%S')
		
	def make_unique_dir(self, base):
		unique_dir = None
		if not os.path.exists(base):
			os.makedirs(base)
			unique_dir = base
		else:
			subscript=1
			unique_dir = f"{base}_{subscript}"
			while os.path.exists(unique_dir):
				subscript += 1
				unique_dir = f"{base}_{subscript}"
			os.makedirs(unique_dir)
		for dish, name in self.samples.items():
			os.makedirs(os.path.join(unique_dir, f"{dish}-{name}"))
		return unique_dir
		
		
	def start_experiment(self):
		
		self.status["experiment_running"] = "True"
		self.experiment_flag.set()
		
		while self.experiment_flag.is_set():
			self.status["iterations"] = str(int(self.status["iterations"])+1)
			if not self.incubator.motor.isAtHome():
				self.status["task"] = "Moving to Plate 1"
				self.incubator.motor.turn(self.incubator.motor.home_plate, 1)
				self.incubator.motor.turnThread.join()
			
			self.run_iteration()
			
			if datetime.datetime.now() > end_time:
				break
			else:
				self.status["task"] = "Waiting for next iteration"
				time.sleep(self.interval * 60)
			
		self.stop_experiment()

	def run_iteration(self):
		
		for dish in range(1, 7):
				self.incubator.led.on()
				self.status["task"] = "Taking Image"
				image = self.incubator.camera.take_snapshot()
				self.incubator.led.off()
				
				self.status["task"] = "Sending Image"
				image_name = f"{self.incubator.name}_{dish}_{datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.jpg"
				exp_image_path = os.path.join(self.local_dir, f"{dish}-{self.samples[dish]}", image_name)
				self.incubator.camera.send_image(image, exp_image_path)
				
				self.status["task"] = f"Moving to Plate {(dish%6)+1}"
				self.incubator.motor.turn(self.incubator.motor.next_plate, 1)
				self.incubator.motor.turnThread.join()
		
		
	def stop_experiment(self):
		self.experiment_flag.clear()
		self.status["experiment_running"] = "False"
		self.status["task"] = "Idle"
		self.led.off()
		self.heater.off()
		time.sleep(60)
		self.fan.off()
		self.incubator.experiment = None
		del self
		

if __name__ == "__main__":
	session = Incubator()
	
	while True:
		time.sleep(1)
