from sya import agent
import json  

aux = agent 
 
for key, val in aux.items():
    delattr(val, 'draws')
    delattr(val, 'radius') 
    delattr(val, 'info')
    delattr(val, 'vx')
    delattr(val, 'vy')
    aux[key] = val.__dict__ 
     
# obtains json str     
obj_json = json.dumps(aux) 
print(obj_json)

file = open('test.py', 'w')
file.write("a = '"+ obj_json+"'")
file.close()
  
# deserialize info (dictionary)
# dict_info = json.loads(obj_json)
# print(dict_info) 