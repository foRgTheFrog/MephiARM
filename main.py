from machine import Pin, PWM
import ubluetooth
import time
import uasyncio as asyncio
import tcs34725
import neopixel
from ntag_reader import NTAGReader

#=-=-=-=--=-=-=-=-=-=-=-= Какие то цифорки для ble =-=-=-=-=--=-=-=-=-=-=-=
UART_SERVICE_UUID = ubluetooth.UUID("6E400001-B5A3-F393-E0A9-E50E24DCCA9E")
RX_CHAR_UUID = ubluetooth.UUID("6E400002-B5A3-F393-E0A9-E50E24DCCA9E")
TX_CHAR_UUID = ubluetooth.UUID("6E400003-B5A3-F393-E0A9-E50E24DCCA9E")
#=-=-=-=--=-=-=-=-=-=-=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=--=-=-=-=-=-=-=-=-=-=-=--=-=-=-=-=-=-=-

'''BUTTON DATA YO:
button 1: нажал !B11:, отжал !B10;
button 2: нажал !B219, отжал !B20
button 3: нажал !B318, отжал !B309
button 4: нажал !B417, отжал !B408
'''

#=-=-=-=--=-=-=-=-=-=-=-= ПИНЫ Драйвера Мотора =-=-=-=-=--=-=-=-=-=-=-=
PWMA = PWM(Pin(27), freq=1900)  # Левый
PWMB = PWM(Pin(25), freq=1900)  # Правый

AIN1 = Pin(32, Pin.OUT)         # Левый
AIN2 = Pin(33, Pin.OUT)

BIN1 = Pin(12, Pin.OUT)         # Правый
BIN2 = Pin(14, Pin.OUT)

STBY = Pin(26, Pin.OUT)
STBY.value(1)

#=-=-=-=-=-=-=-=-=-=-= СЕРВОПРИВОД =-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=-=
SERVO_VV = Pin(22, Pin.OUT)
SERVO_VV_PWM = PWM(Pin(SERVO_VV), freq=50)
SERVO_VV_PWM.duty(0)
VV_angle = 0


SERVO_SZ = Pin(13, Pin.OUT)
SERVO_SZ_PWM = PWM(Pin(SERVO_SZ), freq=50)
SERVO_SZ_PWM.duty(0)
SZ_angle = 0

kastil = True
def set_servo_vv(angle):
    global VV_angle
    global kastil
    global d_angle
    #if kastil == True:
    VV_angle = angle   
    VV_angle = max(0, min(180, VV_angle))
    duty = int((26 + (VV_angle / 180) * 102))
    print("duty =" + str(duty))
    SERVO_VV_PWM.duty(duty)
    #else:
    
def set_servo_sz(angle):
    global SZ_angle
    global kastil
    if kastil == True:
        SZ_angle = max(0, min(180, angle))
        duty = int((26 + (SZ_angle / 180) * 102))
        SERVO_SZ_PWM.duty(duty)
   # else:
        #SERVO_SZ_PWM.duty(26)
    
    
    

stopper = False
d_angle = 5
async def servo_vv(): 
    global stopper, d_angle, VV_angle
    while True:
        if stopper == True:
            VV_angle += d_angle
            VV_angle = max(0, min(180, VV_angle))
            set_servo_vv(VV_angle)
            print(VV_angle)
            await asyncio.sleep_ms(100)
        else:
            await asyncio.sleep_ms(10)
        #SERVO_VV_PWM.duty(0)
    
    
sz_running = False
SJATIE = -1
async def servo_sz():
    global SJATIE, sz_running
    if sz_running:
        return
    sz_running = True

    STOP_DUTY = 77
    FWD_DUTY = 100
    REV_DUTY = 50       
    ROTATION_MS = 750  

    if SJATIE == 1:
        SERVO_SZ_PWM.duty(FWD_DUTY)
    else:
        SERVO_SZ_PWM.duty(REV_DUTY)

    await asyncio.sleep_ms(ROTATION_MS)
    SERVO_SZ_PWM.duty(STOP_DUTY)
    sz_running = False


# ========== Кольцо адресных светодиодов ==========
ring = neopixel.NeoPixel(Pin(21), 12) 
ring.fill((0, 0, 0))
ring.write()

NUM_LEDS = 12
PIN_NUM = 21

np = neopixel.NeoPixel(Pin(PIN_NUM), NUM_LEDS)

def test_ring():
    np.fill((0, 0, 0))
    np.write()
    time.sleep(1)

    for i in range(NUM_LEDS):
        np[i] = (30, 0, 0)
        np.write()
        print(f"Зажжён светодиод {i}")
        time.sleep(0.2)

    np.fill((0, 0, 0))
    np.write()
    time.sleep(1)

    colors = [(30, 0, 0), (0, 30, 0), (0, 0, 30), (30, 30, 0), (30, 0, 30), (0, 30, 30)]
    for col in colors:
        np.fill(col)
        np.write()
        print(f"Цвет: {col}")
        time.sleep(0.5)

    np.fill((0, 0, 0))
    np.write()
    print("Тест кольца завершён")

#test_ring()


'''
servo = PWM(Pin(22), freq=50)
servo.duty(77)   # нейтраль – должен остановиться
time.sleep(2)
servo.duty(100)  # должен крутиться в одну сторону
time.sleep(2)
servo.duty(50)   # должен крутиться в другую
time.sleep(2)
servo.duty(77)   # стоп
'''






# ========== СЛОВАРЬ ЦВЕТОВ ==========
# Значения RGB подобраны для кольца WS2812B (0-255, но для яркости используем 30)
COLOR_MAP = {
    "WHITE":  (30, 30, 30),
    "BLACK":  (0, 0, 0), 
    "RED":    (30, 0, 0),
    "YELLOW": (30, 30, 0),
    "BLUE":   (0, 0, 30),
    "GREEN":  (0, 30, 0),
    "ORANGE": (30, 15, 0),
    "PINK":   (30, 20, 20),
    "PURPLE": (30, 0, 30),
    "BROWN":  (20, 10, 0),
    "GREY":   (15, 15, 15),
}

# =-=-=-=---=-=-=-= RFID метки =-=-=-=-=-=-[-=-=-=-=-=-












rfid = NTAGReader(sck=18, mosi=15, miso=17, cs=19, rst=16)
#sda = cs

uid_str = None
data = None
success = False

Chtenie = -1
async def tag_reading():
    global Chtenie, uid_str, data, success, COLOR_MAP, np
    np.fill(COLOR_MAP["WHITE"])
    np.write()
    await asyncio.sleep(1)
    while (Chtenie == 1):
        print(",")
        success, uid_str, data = rfid.auto_read()
        if (success != None):
            if data != None:
                print("DEBUG: data =", data)
                print("DEBUG: type(data) =", type(data))
                print("DEBUG: data keys =", data.keys() if isinstance(data, dict) else "not dict")
                color = data.get("raw_text", "").strip().upper()
                if color and color in COLOR_MAP:
                    print(color)
                    np.fill(COLOR_MAP[color])
                    np.write()
                else:
                    print("Цвет не распознан (raw_text пуст или не найден)")
            Chtenie = -1
            return
        await asyncio.sleep(3)
    np.fill(COLOR_MAP["BLACK"])
    np.write()
    return











class ESP32_BLE:
    def __init__(self, name):
        self.name = name
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        
        self.connected = False
        
        self.ble.irq(self.ble_irq)
        
        self.register_services()
        self.advertise()
    
    def ble_irq(self, event, data):
        if event == 1:
            self.connected = True
            
        elif event == 2:
            self.connected = False
            stop()
            self.advertise()
        elif event == 3:
            #print("Данные доходят")
            dataFromWho, dataType = data  # esp32 получает данные
            #print(dataType)
            #print(self.rx_handle)
            if dataType == self.tx_handle: # если данные нужно читать а не отправлять, то
                #print("YO")
                data = self.ble.gatts_read(self.tx_handle) # акшуали читаем данные
                print("сигнал ", data.decode('utf-8').strip())
                self.controls(data.decode('utf-8').strip()) # отправляем инпут в управление
    def register_services(self):
        self.rx = (RX_CHAR_UUID, ubluetooth.FLAG_WRITE | ubluetooth.FLAG_WRITE_NO_RESPONSE)
        self.tx = (TX_CHAR_UUID, ubluetooth.FLAG_NOTIFY | ubluetooth.FLAG_READ)
        
        self.services = (UART_SERVICE_UUID, (self.rx, self.tx),)
        
        # Регистрация сервисов
        ((self.tx_handle, self.rx_handle),) = self.ble.gatts_register_services((self.services,))
        #print(f"tx_handle={self.tx_handle}, rx_handle={self.rx_handle}")
        
        # Установка начальных значений
        self.ble.gatts_write(self.tx_handle, b'\x00')
    
    def advertise(self):
        self.ble.gap_advertise(100, b'\x02\x01\x06' +  b'\x03\x03\xAA\xFE' + bytes([len(self.name)+1, 0x09]) + self.name.encode())
    
    def controls(self, controlInput):
        global stopper, d_angle, SJATIE, VV_angle, Chtenie, SERVO_VV_PWM, sz_running
        if controlInput == "!B516":
            # КНОПКА ВВЕРХ
            turn_left()
            print("Вперёд")
        elif controlInput == "!B615":
            # КНОПКА ВНИЗ
            turn_right()
            print("Назад")
        elif controlInput == "!B714":
            # КНОПКА ВЛЕВО
            backwards()
            print("Влево")
        elif controlInput == "!B813":
            # КНОПКА ВПРАВО
            print("Вправо")
            forward()
        elif controlInput == "!B11:":
            #Поворот клешни ВВЕРХ
            
            #SERVO_VV_PWM.duty(70)
            print("ВВЕРХ!")
            
            stopper = True
            d_angle = 1
            #asyncio.create_task(servo_vv(VV_angle))
            
        elif controlInput == "!B10;":
            stopper = False
            #VV_angle = 0
            #SERVO_VV_PWM.duty(77)
            #SERVO_SZ_PWM.duty(0)
        elif controlInput == "!B20:":
            #d_angle = 0
            #SERVO_VV_PWM.duty(77)
            #VV_angle = 26
            stopper = False
            #asyncio.create_task(servo_vv())
        elif controlInput == "!B219":
            
            
            #SERVO_VV_PWM.duty(90) 
            # Поворот КЛЕШНИ вниз
            
            stopper = True
            #kastil = True
            
            d_angle = -1
            #VV_angle = 120
            #asyncio.create_task(servo_vv())
            
        elif controlInput == "!B318":
            SJATIE *= -1
            asyncio.create_task(servo_sz())
            
            
        elif controlInput == "!B417":
            Chtenie *= -1
            asyncio.create_task(tag_reading())

        elif controlInput not in ["!B516", "!B615", "!B714", "!B813", "!B11:", "!B10;", "!B219", "!B20:", "!B318","!B417"]:
            print("Стоп!")
            stop()
                
    

def forward():
    AIN1.value(1)
    AIN2.value(0)
    BIN1.value(1)
    BIN2.value(0)
    print("YO")
    
    PWMA.duty(1000)
    PWMB.duty(1000)
def stop():
    AIN1.value(0)
    AIN2.value(0)
    BIN1.value(0)
    BIN2.value(0)
    
    PWMA.duty(0)
    PWMB.duty(0)
def turn_left():
    AIN1.value(0)
    AIN2.value(1)
    BIN1.value(1)
    BIN2.value(0)
    
    PWMA.duty(800)
    PWMB.duty(800)
def turn_right():
    AIN1.value(1)
    AIN2.value(0)
    BIN1.value(0)
    BIN2.value(1)
    
    PWMA.duty(800)
    PWMB.duty(800)

def backwards():
    AIN1.value(0)
    AIN2.value(1)
    BIN1.value(0)
    BIN2.value(1)
    
    PWMA.duty(1000)
    PWMB.duty(1000)

stop()

async def main():
    asyncio.create_task(servo_vv())
    #asyncio.create_task(tag_reading())
    while True:
        await asyncio.sleep(0.1)

ble = ESP32_BLE("MEPHIARM")
led = Pin(2, Pin.OUT)
led(0)
asyncio.run(main())



