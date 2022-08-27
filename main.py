from microbit import *  
from test import a
import radio

radio.config(group=23)
radio.on()
  
while True: 
    radio.send(str(a[16])) 