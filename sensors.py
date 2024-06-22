import Adafruit_DHT
import RPi.GPIO as GPIO

sensors_values = {
    'fan1': False,
    'fan2': False,
    'water_pump': False,
    'temperature': None,
    'humidity': None
}

relays = {}

def read_temperature():
    sensor = Adafruit_DHT.DHT11
    pin = 4
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)
    if humidity is not None and temperature is not None:
        sensors_values['temperature'] = '{0:0.1f}'.format(temperature)
        sensors_values['humidity'] = '{0:0.1f}'.format(humidity)
        print(sensors_values)
    else:
        print('Error reading temperature and humidity.')

def toggle_relay(pin, value, key):
    if pin not in relays:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(pin, GPIO.OUT)
        relays[pin] = pin

    GPIO.output(pin, GPIO.HIGH if value else GPIO.LOW)
    sensors_values[key] = value

def get_sensors_values():
    read_temperature()
    return sensors_values