# name:          main.py
# Last Updated:  01 Sept 2022
# author         Colin D Ashley
# Desc:          Display latest APRS record for Callsign
#                Maidenhead Conversion based on code by Walter Underwood K6WRU

from machine import Pin, SPI
import time
import framebuf
import network
import socket
from picozero import pico_led
from time import sleep

# SPI setup
DC = 8
RST = 12
MOSI = 11
SCK = 10
CS = 9

#APRS Data
callsign = '' #Callsign to be requested

#Maidenhead Arrays
upper = 'ABCDEFGHIJKLMNOPQRSTUVWX'
lower = 'abcdefghijklmnopqrstuvwx'

#Wifi connection details
ssid = ''
password = ''

#Hardware assignments
wlan = network.WLAN(network.STA_IF)
pled = machine.Pin("LED", machine.Pin.OUT)

#from OLED SPI file
class OLED_1inch3(framebuf.FrameBuffer):
    def __init__(self):
        self.width = 128
        self.height = 64
        
        self.cs = Pin(CS,Pin.OUT)
        self.rst = Pin(RST,Pin.OUT)
        
        self.cs(1)
        self.spi = SPI(1)
        self.spi = SPI(1,2000_000)
        self.spi = SPI(1,20000_000,polarity=0, phase=0,sck=Pin(SCK),mosi=Pin(MOSI),miso=None)
        self.dc = Pin(DC,Pin.OUT)
        self.dc(1)
        self.buffer = bytearray(self.height * self.width // 8)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_HMSB)
        self.init_display()
        
        self.white =   0xffff
        self.balck =   0x0000
        
    def write_cmd(self, cmd):
        self.cs(1)
        self.dc(0)
        self.cs(0)
        self.spi.write(bytearray([cmd]))
        self.cs(1)

    def write_data(self, buf):
        self.cs(1)
        self.dc(1)
        self.cs(0)
        self.spi.write(bytearray([buf]))
        self.cs(1)

    def init_display(self):
        """Initialize display"""  
        self.rst(1)
        time.sleep(0.001)
        self.rst(0)
        time.sleep(0.01)
        self.rst(1)
        
        self.write_cmd(0xAE)   #turn off OLED display
        self.write_cmd(0x00)   #set lower column address
        self.write_cmd(0x10)   #set higher column address 
        self.write_cmd(0xB0)   #set page address 
        self.write_cmd(0xdc)   #set display start line 
        self.write_cmd(0x00) 
        self.write_cmd(0x81)   #contract control 
        self.write_cmd(0x6f)   #128
        self.write_cmd(0x21)   # Set Memory addressing mode (0x20/0x21) #
        self.write_cmd(0xa0)   #set segment remap 
        self.write_cmd(0xc0)   #Com scan direction
        self.write_cmd(0xa4)   #Disable Entire Display On (0xA4/0xA5) 
        self.write_cmd(0xa6)   #normal / reverse
        self.write_cmd(0xa8)   #multiplex ratio 
        self.write_cmd(0x3f)   #duty = 1/64
        self.write_cmd(0xd3)   #set display offset 
        self.write_cmd(0x60)
        self.write_cmd(0xd5)   #set osc division 
        self.write_cmd(0x41)
        self.write_cmd(0xd9)   #set pre-charge period
        self.write_cmd(0x22)   
        self.write_cmd(0xdb)   #set vcomh 
        self.write_cmd(0x35)  
        self.write_cmd(0xad)   #set charge pump enable 
        self.write_cmd(0x8a)   #Set DC-DC enable (a=0:disable; a=1:enable)
        self.write_cmd(0XAF)
    def show(self):
        self.write_cmd(0xb0)
        for page in range(0,64):
            self.column = 63 - page              
            self.write_cmd(0x00 + (self.column & 0x0f))
            self.write_cmd(0x10 + (self.column >> 4))
            for num in range(0,16):
                self.write_data(self.buffer[page*16+num])
#end of OLED SPI

#functions
#maidenhead calculation
def to_grid(dec_lat, dec_lon):
    if not (-180<=dec_lon<180):
        sys.stderr.write('longitude must be -180<=lon<180, given %f\n'%dec_lon)
        sys.exit(32)
    if not (-90<=dec_lat<90):
        sys.stderr.write('latitude must be -90<=lat<90, given %f\n'%dec_lat)
        sys.exit(33) # can't handle north pole, sorry, [A-R]

    adj_lat = dec_lat + 90.0
    adj_lon = dec_lon + 180.0

    grid_lat_sq = upper[int(adj_lat/10)];
    grid_lon_sq = upper[int(adj_lon/20)];

    grid_lat_field = str(int(adj_lat%10))
    grid_lon_field = str(int((adj_lon/2)%10))

    adj_lat_remainder = (adj_lat - int(adj_lat)) * 60
    adj_lon_remainder = ((adj_lon) - int(adj_lon/2)*2) * 60

    grid_lat_subsq = lower[int(adj_lat_remainder/2.5)]
    grid_lon_subsq = lower[int(adj_lon_remainder/5)]

    return( grid_lon_sq + grid_lat_sq + grid_lon_field + grid_lat_field + grid_lon_subsq + grid_lat_subsq )

#connect to network
def connect():
    pled.off()
    wlan.active(True)
    wlan.connect(ssid, password)
    print("Connecting to LAN")
    while wlan.isconnected() == False:
        #debug print('Waiting for connection...')
        sleep(1)
    ip = wlan.ifconfig()[0]
    print(f'Connected on {ip}')
    pled.on()

#disconnect from network
def disconnect():
    wlan.active(False)
    pled.off()
    print("Disconnected from WAN")
    print("---------------------")

#post APRS urequest and display the JSON result
def getInfo():
    import urequests 
    import json
    import time

    connect()
    OLED = OLED_1inch3()
    OLED.fill(0x0000) 
    OLED.show()
    l1="Fetching " + callsign
    l2="   APRS Data"
    OLED.text(l1,1,22,OLED.white)
    OLED.text(l2,1,32,OLED.white)
    OLED.show()
    #get request results
    print("Sending APRS Request")
    r = urequests.get("https://api.aprs.fi/api/get?name="+callsign+"&what=loc&apikey=<APRS API KEY>&format=json")
    #read as JSON
    jr = r.json()
    ltm = time.localtime(int(jr["entries"][0]["lasttime"]))
    l1=str(ltm[2]) + "/" + f'{(int(ltm[1])):02}' + " @ " +str(ltm[3]) + ":" + f'{(int(ltm[4])):02}'
    l2="lat " + jr["entries"][0]["lat"]
    l3="lng " + jr["entries"][0]["lng"] 
    l4="alt " + str(jr["entries"][0]["altitude"]) + " Mts"
    l5="bearing " + str(jr["entries"][0]["course"]) + " Deg"
    l6="Locator: " + str(to_grid(float(jr["entries"][0]["lat"]),float(jr["entries"][0]["lng"])))
    
    
    r.close()
    #display the results
    OLED.fill(0x0000) 
    OLED.text(str(l1),1,02,OLED.white)
    OLED.text(str(l2),1,12,OLED.white)
    OLED.text(str(l3),1,22,OLED.white)
    OLED.text(str(l4),1,32,OLED.white)
    OLED.text(str(l5),1,42,OLED.white)  
    OLED.text(str(l6),1,52,OLED.white)  
    OLED.show()
    print("Results displayed")
    disconnect()
    #Refresh with reconnect
    keyA = Pin(15,Pin.IN,Pin.PULL_UP)
    keyB = Pin(17,Pin.IN,Pin.PULL_UP)
    print("Waiting on Key0 press")
    while(1):
        if keyA.value() == 0:
            OLED.fill(0x0000) 
            OLED.text("  Refreshing",1,22,OLED.white)
            OLED.show()
            print("Button 0 Pressed")
            return

    
#main code - endless loop
#give Pi Pico W time to settle down
time.sleep(2)
while(1):
    getInfo() #wait for Refresh Button to be pressed

