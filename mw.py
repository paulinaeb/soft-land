from sya import agent 

aux = agent 
 
# drops unused values  
for key, val in aux.items():
    delattr(val, 'draws')
    delattr(val, 'radius') 
    delattr(val, 'info')
    delattr(val, 'vx')
    delattr(val, 'vy')
    aux[key] = val.__dict__ 
     
print(aux)      
#writes the dictionary on a text file to be used in agents 
file = open('file.txt', 'w')
file.write(str(aux))
file.close() 