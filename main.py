import json
import asyncio
import time
import board
import busio
import adafruit_tsl2561
import Adafruit_DHT
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message


CONNECTION_STRING = 'HostName=AlexGreenhouse.azure-devices.net;DeviceId=AlexRaspberryPi;SharedAccessKey=x9lDlHvpsHdijhcOHmr229N6j9YNJcGY0AIoTAdLRNY='
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 16
servo_pin = 21
RELAYS = {"fan1": 5, "fan2": 18, "water_pump": 6}
SENSOR_VALUES = {"fan1": False, "fan2": False, "water_pump": False, "openWindow":False, "temperature": None, "humidity": None, "light": None, "soil_humidity":None}


GPIO.setmode(GPIO.BCM)
GPIO.setup(servo_pin, GPIO.OUT)
pwm = GPIO.PWM(servo_pin, 50)
pwm.start(0)


GPIO.setwarnings(False)


def read_temperature():
    humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
    if humidity is not None and temperature is not None:
        SENSOR_VALUES["temperature"] = temperature
        SENSOR_VALUES["humidity"] = humidity
    else:
        
        print("Error reading temperature and humidity.")

def read_lux():
    i2c = busio.I2C(board.SCL, board.SDA)
    sensor = adafruit_tsl2561.TSL2561(i2c)
    sensor.gain = 16  
    lux = sensor.lux
    if lux is not None:
        SENSOR_VALUES["light"] = round(lux,2)
    else:
        print("Error reading light")


def toggle_relay(pin, value, key):
    
    try:
        if GPIO.gpio_function(pin) != GPIO.OUT:
            GPIO.setup(pin, GPIO.OUT)

        GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
        
        SENSOR_VALUES[key] = not value
                
    except Exception as e:
        logging.error(f"Error toggling relay {key} on pin {pin}: {e}")

def move_forward():
    pwm.ChangeDutyCycle(10)  
    time.sleep(7)
    pwm.ChangeDutyCycle(0)
    SENSOR_VALUES["openWindow"]=True  

def move_backward():

    pwm.ChangeDutyCycle(5)   
    time.sleep(7)
    pwm.ChangeDutyCycle(0)
    SENSOR_VALUES["openWindow"]=False  


def read_soil_moisture():
    
    i2c = busio.I2C(board.SCL, board.SDA)

    
    ads = ADS.ADS1115(i2c, address=0x48)

   
    chan = AnalogIn(ads, ADS.P0)

    
    MIN_RAW_VALUE = 8000  # Minimum raw ADC value (full water)
    MAX_RAW_VALUE = 20000  # Maximum raw ADC value (no moisture)

    
    raw_value = chan.value

   
    raw_value = min(max(raw_value, MIN_RAW_VALUE), MAX_RAW_VALUE)

    
    percentage = 100 - ((raw_value - MIN_RAW_VALUE) / (MAX_RAW_VALUE - MIN_RAW_VALUE)) * 100

    SENSOR_VALUES["soil_humidity"]=percentage

def get_sensor_values():
    read_temperature()
    read_lux()
    read_soil_moisture()
    return SENSOR_VALUES


async def send_message(client):
    while True:
        data = get_sensor_values()
        message = Message(json.dumps(data))

        try:
            await client.send_message(message)
            print("Message sent!")
        except Exception as e:
            print(f"Error sending message: {e}")

        await asyncio.sleep(10)


async def receive_message_handler(message):
    print("Received message:\n\t", message.data)
    command = json.loads(message.data.decode('utf-8'))
    print(command)

    for key, value in command.items():
        print(key, value)
        if key in RELAYS:
            toggle_relay(RELAYS[key], value, key)
        elif key == 'openWindow':
            print(key, value)
            move_forward() if value == True else move_backward()
        elif key == 'stop' and value: 
            for relay_key in RELAYS:
                toggle_relay(RELAYS[relay_key], False, relay_key)

    await client.complete_message(message)  


async def main():
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    await client.connect()

    client.on_message_received = receive_message_handler

    send_task = asyncio.create_task(send_message(client))

    await asyncio.gather(send_task)

    await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program interrupted")
    finally:
        GPIO.cleanup()
