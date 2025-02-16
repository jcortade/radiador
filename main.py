import network
import socket
import machine
import time
import dht
import wifi, mqtt_secrets
from machine import Pin, Timer

led = Pin(5, Pin.OUT)
relay = Pin(16, Pin.OUT)
sensor = dht.DHT11(Pin(14))


### CONNECT TO WIFI ###
sta = network.WLAN(network.STA_IF)
sta.connect(wifi.SSID, wifi.PASSWORD)
while sta.isconnected() == False:
    print('Waiting for connection...')
    time.sleep_ms(1000)
ip = sta.ifconfig()[0]
print(f'Connected on {ip}')		#print(wlan.ifconfig()) -> For more complete info
    
t_on = 100
t_on_MAX = 100
t_on_MIN = 20
t_count = 0
t_cycle = 120
temp_sp = 22
temp = 21
temp_sp_old = temp_sp

# TIMERS
tim_30sec = Timer(1)

### DOWNLOAD DEPENDENCIES ###
import mip

try:
    import umqtt.simple
except:
    print("Exception: umqtt.simple not found. Trying to download...")
    mip.install('umqtt.simple')
    import umqtt.simple

# try:
#     import uhome
# except:
#     print("Exception: uhome not found. Trying to download...")
#     mip.install('github:ederjc/uhome/uhome/uhome.py')
import uhome

SUBSCRIBE_TOPIC = b"homeassistant/number/radiador_consigna_temperatura/set"
PUBLISH_TOPIC = b"homeassistant/number/radiador_consigna_temperatura/state"
# Función de callback para manejar los mensajes recibidos
def on_message(SUBSCRIBE_TOPIC, msg):
    print(f"Mensaje recibido en {SUBSCRIBE_TOPIC}: {msg}")
    global temp_sp
    temp_sp = int(msg)

    
    

# DEVICE SETUP
device = uhome.Device('Radiador')
mqttc = umqtt.simple.MQTTClient(device.id, mqtt_secrets.broker, user=mqtt_secrets.user, password=mqtt_secrets.password, keepalive=60)
device.connect(mqttc)


### DIAGNOSTIC ENTITIES ###
"""
These are some default entities that are useful for diagnostics.
"""
signal_strength = uhome.Sensor(device, 'Signal Strength', device_class="signal_strength", unit_of_measurement='dBm', entity_category="diagnostic")
wifi_ch = uhome.Sensor(device, 'WiFi Channel', device_class="enum", entity_category="diagnostic")
reset_cause = uhome.Sensor(device, 'Last Reset Cause', device_class="enum", entity_category="diagnostic")
ip_addr = uhome.Sensor(device, 'IP Address', device_class="enum", entity_category="diagnostic")

### SENSOR ENTITIES ###
"""
Entities for the connected sensors.
Look here for some docs:
- https://www.home-assistant.io/integrations/sensor.mqtt/
- https://www.home-assistant.io/integrations/sensor#device-class
"""
temperature = uhome.Sensor(device, 'Temperature', device_class="temperature", unit_of_measurement='C')
humidity = uhome.Sensor(device, 'Relative Humidity', device_class="humidity", unit_of_measurement='%')
time_on = uhome.Sensor(device, 'Tiempo ON', device_class="duration", unit_of_measurement='s')
#temperature_setpoint = uhome.Entity(device, name='Consigna temperatura', device_class="temperature", unit_of_measurement='C')
#temperature_setpoint = uhome.Sensor(device, 'Consigna temperatura', device_class="temperature", unit_of_measurement='C')
mqttc.set_callback(on_message)
mqttc.subscribe(SUBSCRIBE_TOPIC)

"""
The uhome module keeps track of all entities.
With this method we can send the discovery
message for all entities to Home Assistant:
"""
device.discover_all()

### PUBLISH ENTITY VALUES ###
"""
Here we publish the values of the diagnostic entities.
Some of these values are published only once, while others
should be published regularly to keep Home Assistant up to date.
"""
def publishDiagnostics(tmr=None):
    """
    Helper function to publish variable diagnostic values.
    """
    signal_strength.publish(f'{sta.status('rssi'):.0f}')
    reset_cause.publish(f'{machine.reset_cause()}')
    ip_addr.publish(f'{sta.ifconfig()[0]}')


# Inicialización de Timers
tim_30sec.init(period=30000, mode=Timer.PERIODIC, callback=publishDiagnostics)





while True:
    
    device.loop() # Handle all device specific tasks (mandatory).
    mqttc.check_msg()
    
    if led.value():
        led.off()
    else:
        led.on()
    
    if (t_count==0):
        sensor.measure()
        temp = sensor.temperature()
        hum = sensor.humidity()
        
        # PUBLISH TEMPERATURE AND HUMIDITY -> MQTT
        temperature.publish(f'{temp:.1f}')
        humidity.publish(f'{hum:.0f}')
        time_on.publish(f'{t_on:.0f}')
        #temperature_setpoint.publish(f'{temp_sp:.1f}')    

        
        print('Temperature: %3.1f C' %temp)
        print('Humidity: %3.1f %%' %hum)
        print('t_on: %i' %t_on)
        print('t_count: %i' %t_count)
        
    if (t_count==0 and temp>temp_sp+1):
        relay.off()
    elif(t_count==0 and temp<=temp_sp+1):
        relay.on()    
     
    
    if (t_count==0 and (temp<temp_sp) and (t_on<t_on_MAX)):
        t_on = t_on+5
    
    if (t_count==0 and (temp>temp_sp) and (t_on>t_on_MIN)):
        t_on = t_on-5
    

    if (t_count>t_on):
        relay.off()


    time.sleep_ms(1000)
    t_count = t_count+1
    if (t_count>t_cycle):
        t_count=0
    
    if(temp_sp_old != temp_sp):
        mqttc.publish(PUBLISH_TOPIC, str(temp_sp))
        temp_sp_old = temp_sp

   
    print('Temperature setpoint: %3.1f C' %temp_sp)
#    print('Humidity: %3.1f %%' %hum)
#    print('t_on: %i' %t_on)
#    print('t_count: %i' %t_count)
#    if(relay()): print('Relay: ON')
#    else: print('Relay: OFF')
