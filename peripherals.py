import subprocess, threading, datetime, time, base64
import board
import busio
from simple_pid import PID
from adafruit_ahtx0 import AHTx0
from gpiozero import OutputDevice
import cv2, boto3, os

class Motor():
    def __init__(self, pins):
        self.motor_pins = pins
        self.pins = [OutputDevice(self.motor_pins[0]), OutputDevice(self.motor_pins[1]), OutputDevice(self.motor_pins[2]), OutputDevice(self.motor_pins[3])]
        self.step_sequence = [
            [1, 0, 0, 1],
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
            [0, 0, 1, 1],
            [0, 0, 0, 1]
	]
        self.turnThread = None
        self.ps1 = None
        self.ps2 = None
        
    def rotate(self, degrees, clockwise=True):
        #rotates the motor
        steps = int(degrees / 360 * 512)  # Assuming 512 steps for a full 360 rotation
        if clockwise:
            step_seq = self.step_sequence
        else:
            step_seq = list(reversed(self.step_sequence))
        for _ in range(steps):
            for step in step_seq:
                for pin, state in zip(self.pins, step):
                    pin.value = state
                time.sleep(0.005)
    
    def turn(self, function, direction):
        self.turnThread = threading.Thread(target=function, args=(direction,), daemon=True)
        self.turnThread.start()
    
    def home_plate(self, direction):
        self.rotate(60, direction)
    
    def next_plate(self, direction):
        self.rotate(60, direction)
        
    def isAtHome(self):
        return False
    
    def isAtPlate(self):
        return True
        
class Camera():
    def __init__(self, shutter = "1000"):
        self.camera_lock = threading.Lock()
        self.image_path = "/tmp/image.jpg"
        self.shutter_time = shutter
        self.dtFormat = '%Y-%m-%d %H:%M:%S'
        self.s3 = boto3.client('s3')
        self.bucket_name = 'petriboothproject'
        self.aws_exp_folder = os.path.join(os.environ["BUCKETNAME"], 'Experiments')
	
    def take_snapshot(self):
        subprocess.run(["libcamera-still", "-o", self.image_path,"--shutter", self.shutter_time])
        image = cv2.imread(self.image_path) 
        return image
    
    def send_image(self, image, filename):
        try:
            key = os.path.join(self.aws_exp_folder, filename)
            image_string = cv2.imencode('.jpg', image)[1].tobytes()
            self.s3.put_object(Bucket=self.bucket_name, Key = key, Body=image_string)
            #s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{key}"
            #presigned_url = self.generate_presigned_url(key)
            #payload = {"status": "1", "image_url": presigned_url}

        except Exception as e:
            print(e)
            print(f"Saving Image {self.image_path} at {filename}")
            os.system(f"cp {self.image_path} {filename}")
        
    

class Temperature():
    def __init__(self, multiplexer_address = 0x70, sensor_address = 0x38, channel = 0):
        self.multiplexer_address = multiplexer_address       
        self.sensor_address = sensor_address
        self.channel = channel
        self.dtFormat = '%Y-%m-%d %H:%M:%S'
        self.setpoint = None
        self.pid_thread = threading.Thread(target=self.pid, daemon=True)
        self.fan = OutputDevice()
        self.heater = OutputDevice()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self.pid_thread_event = threading.Event()
        self.pid_thread_event.set()
	
    def capture(self):
        try:
            with busio.I2C(board.SCL, board.SDA) as i2c:
                i2c.writeto(self.multiplexer_address, bytes([1 << self.channel]))
                sensor = AHTx0(i2c, self.sensor_address)
                temperature = round(sensor.temperature,2)
                humidity = round(sensor.relative_humidity,2)
                return {"success": "1", "timestamp": f"{datetime.datetime.now().strftime(self.dtFormat)}", "temperature": f"{temperature}", "humidity": f"{humidity}"}
        except Exception as e:
            return {"success": "0", "error": f"{e}", "temperature": None, "humidity": None}
            
    def pid(self):
        print("[INFO] Setting the temperature to "+str(setpoint))
        pid = PID(1,0.5,0,float(self.setpoint))                                             #sets P,I,D values
        pid.output_limits = (0,204)                                                    #defines output values                               
        self.fan.on()
        while self.pid_thread_event.is_set():
            self._pause_event.wait()
            temp = self.capture()["temperature"]
            
            if temp is None:
                continue
            else:
                temp = float(temp)

            duty_cycle = pid(temp)
            if(setpoint > temp):
                self.gpio.heater.value =duty_cycle/255                                 #send the pid generated value to heater
            else: 
                self.gpio.heater.value = 0.01                                          #if temperature overshoots/ if the set temperature is achieved it will set the heater to fixed value to maintain that temperature 
            time.sleep(1)
        


	    
		
	
		

