# import serial

# d = destiny
# f = source
# c = command 
# p = list of params or variable with one param
def serialize(d, f, c, p):
    # num of params passed
    n_param = len(p) 
    # header of message
    msg = d + f + c 
    # size of params str with delimiter (/)
    size = n_param
    if (size > 0):
        # adds the size of each param
        for obj in p:
            size += len(obj)
        # define the number of spaces to be filled with '0'
        num_fill = 14 - size 
        # number of spaces that every param will have added to (if>0)
        n_each = num_fill / n_param 
        if num_fill >= 0: 
            if n_param >= 1: 
                for obj in p:
                    msg += obj + '/'
                    for i in range(int(n_each)):
                        msg += '0' 
            # if num to add is odd or there are less spaces to be filled than params 
            if ((n_each != int(n_each)) or (num_fill < n_param)):
                ex = 18 - len(msg)
                for i in range(ex):
                    msg += '0'
        else:
            print('El tamaño de los parámetros ingresados sobrepasa el limite permitido. Verifique e intente nuevamente.')
    # else:
    #     # no params needed 
    return msg

# ser_msg = serialize('0', 'F', 'II', ['1'])
# print(ser_msg)
# ser_port = serial.Serial(port='COM3', baudrate=115200, timeout=1)  
# ser_port.write((ser_msg+',').encode())