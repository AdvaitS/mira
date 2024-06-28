import threading, datetime, json

class Experiment(Incubator):
    def __init__(self, incubator, device_name, duration, interval, exp_file, samples):
		super().__init__()
		self.incubator = incubator
		self.incubator.experiment = self
		self.device_name = device_name
		self.duration = duration
		self.interval = interval
		self.exp_file = exp_file
		self.samples = samples
		self.status = {'experiment_running': 'False', 
						'device_name': f"{self.device_name}", 
						'duration':f"{self.duration}", 
						'interval':f"{self.interval}", 
						'exp_file':f"{self.exp_file}", 
						'sample_names':f"{self.samples}", 
						'iterations': '0'}
		self.start_experiment_thread = threading.Thread(target=self.start_experiment, daemon=True)
		self.experiment_flag = threading.Event()
		self.start_experiment_thread.start()
		self.start_time = datetime.datetime.now().strftime(self.dtFormat)
		self.status["start_time"] = self.start_time
		
	def start_experiment(self):
		
		self.status["experiment_running"] = "True"
		self.experiment_flag.set()
		end_time = datetime.now() + datetime.timedelta(hours=self.duration)
		while self.experiment_flag.is_set():
			self.status["iterations"] = str(int(self.status["iterations"])+1)
			if not self.motor.isAtHome():
				self.status["task"] = "Moving to Plate 1"
				self.motor.turn(self.motor.home_plate, 1)
				self.motor.turnThread.join()
			
			for dish in range(1, 7):
				self.status["task"] = "Taking Image"
				self.camera.take_snapshot()
				
				self.status["task"] = "Sending Image"
				with open(self.camera.snap_filename, "rb") as image_file:
					image_data = base64.b64encode(image_file.read()).decode('utf-8')
				payload = {"image": image_data, "plate": f"{dish}", "timestamp":f"{datetime.datetime.now().strftime(self.dtFormat)}"}
				self.mqtt_client.publish("response/status", json.dumps(payload), 1)
				
				self.status["task"] = f"Moving to Plate {(dish%6)+1}"
				self.motor.turn(self.motor.next_plate, 1)
				self.motor.turnThread.join()
			
			if datetime.now() < end_time:
				break
			else:
				self.status["task"] = "Waiting for next iteration"
				time.sleep(self.interval * 60)
			
		self.stop_experiment()

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
		
