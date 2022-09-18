# from sya import agent 

# aux = agent 
 
# # drops unused values  
# for key, val in aux.items():
#     delattr(val, 'draws')
#     delattr(val, 'radius') 
#     delattr(val, 'info')
#     delattr(val, 'vx')
#     delattr(val, 'vy')
#     aux[key] = val.__dict__ 
     
# print(aux)      
# #writes the dictionary on a text file to be used in agents 
# file = open('file.txt', 'w')
# file.write(str(aux))
# file.close() 

# with open('file.txt') as f:
#     info_dict = eval(f.read())
# if info_dict['yellow'] is not None:
#     dir_angle = info_dict['yellow']['direction']
#     print(dir_angle)
# f.close()

# while True:
#     try:
#         with open('file.txt') as f:
#             info_dict = eval(f.read())
#         if info_dict['yellow'] is not None:
#             dir_angle = info_dict['yellow']['direction']
#             print(dir_angle)
#     except:
#         print('eof')
#     f.close()
    # get agent info
    
    
# aux = agent
# # open text file
# file = open('file.txt', 'w')
# file.write('{')  
# for key, val in aux.items():
#     #writes  dictionary on a text file to be used in agents 
#     file.write("'"+key+"'"+': '+str(val.__dict__)+',')
# file.write('}')
# file.close()       