# import serial
# f = source
# d = destiny
# c = command 
# p = list of params or variable with one param
def serialize(f, d, c, p):
    # num of params passed
    n_param = len(p) 
    # header of message
    msg = f + d + c 
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

class Resp:
    def __init__(self):
        self.d = self.f = self.c = None
        self.p = []
    def set_header(self, d, f, c):
        self.d = d 
        self.f = f 
        self.c = c
    def add_p(self, param):
        self.p.append(param)
    
        
obj_req = Resp()

msg = '01GP6.70/0ana/01/0';

def deserialize_msg(msg): 
    obj_req.set_header(msg[0], msg[1], msg[2] + msg[3])
    str_p = msg[4:]
    limit = str_p.count('/')
    if limit > 0:
        #  insert params into array
        index = 0
        aux = 0
        for i in range(limit):
            if i == 0: 
                index = str_p.find('/') 
                obj_req.add_p(str_p[:index])
            else:
                index = str_p.find('/', index + 1)
                obj_req.add_p(str_p[aux + 1:index])
            aux = index
            flag = 0 
            for char in range (len(obj_req.p[i])):
                # checks if num or str for every char 
                if not (((obj_req.p[i][char] >= '0') and (obj_req.p[i][char] <= '9')) or (obj_req.p[i][char] =='.')):
                    flag += 1
            # if the param is a str - remove 0
            if flag > 0:
                obj_req.p[i] = obj_req.p[i].replace('0',''); 
        print(obj_req.p)
    return 

deserialize_msg(msg)
# ser_msg = serialize('0', 'F', 'II', ['1'])
# print(ser_msg)
# ser_port = serial.Serial(port='COM3', baudrate=115200, timeout=1)  
# ser_port.write((ser_msg+',').encode())