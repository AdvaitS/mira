import subprocess, threading, datetime
import board
import busio
from adafruit_ahtx0 import AHTx0

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
                
class Camera():
    def __init__(self, shutter = "1000"):
        self.camera_lock = threading.Lock()
        self.snap_filename = "/tmp/image.jpg"
        self.shutter_time = shutter
	
    def take_snapshot(self):
        subprocess.run(["libcamera-still", "-o", self.snap_filename,"--shutter", self.shutter_time])
    
    def startCameraStream(self):
        pass
		
    def stopCameraStream(self):
        pass
    

class Temperature():
    def __init__(self, multiplexer_address = 0x70, sensor_address = 0x38, channel = 0):
        self.multiplexer_address = multiplexer_address       
        self.sensor_address = sensor_address
        self.channel = channel
        self.dtFormat = '%Y-%m-%d %H:%M:%S'
	
    def capture(self):
        try:
            with busio.I2C(board.SCL, board.SDA) as i2c:
                i2c.writeto(self.multiplexer_address, bytes([1 << self.channel]))
                sensor = AHTx0(i2c, self.sensor_address)
                temperature = round(sensor.temperature,2)
                humidity = round(sensor.relative_humidity,2)
                return {"success": "1", "timestamp": f"{datetime.datetime.now().strftime(self.dtFormat)}", "temperature": f"{temperature}", "humidity": f"{humidity}"}
        except Exception as e:
            return {"success": "0", "error": f"{e}"}


	    
		
	
		

