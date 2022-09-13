from microbit import *   
import radio

radio.config(group=23)
radio.on()
  
while True: 
    color = radio.receive()  
    # read info file and convert to dictionary
    with open('file.txt') as f:
        info_dict = eval(f.read())
    # validate that color exists
    for col_key in info_dict.keys():
        if color == col_key:
            # get request and validate it
            request = radio.receive()
            if request == 'get_pos':
                # get value from dictionary
                dir_angle = info_dict[color]['direction']
                if dir_angle:
                    # if exists, sends value
                    radio.send(str(dir_angle))  