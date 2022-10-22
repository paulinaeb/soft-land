import data

# utils for classes and conversion functions  

# colors of agent triangles
agent = {'blue': None,
         'green': None,
         'yellow': None}  

#classes definition
class ViewPort:
    def __init__(self, name):
        self.name = name
        self.u_min = self.u_max = self.v_min = self.v_max = self.du = self.dv =  None 
    def set_values(self,  u_min, v_min, u_max, v_max):
        self.u_min = u_min
        self.u_max = u_max     
        self.v_min = v_min
        self.v_max = v_max
        self.du = u_max - u_min
        if self.name == 'camera':
            self.dv = v_min - v_max
        else:
            self.dv = v_max - v_min

    
class Agent:
    def __init__(self, color): 
        self.id = get_id(color) 
        self.draws = []
        self.found = False
        self.home = False
        self.collision = False
        self.searching = False
        self.busy = False
        self.cx = self.cy = self.direction = self.radius = self.info = self.vx = self.vy = self.name = None 
    def set_values(self, cx, cy, vx, vy, r, direction, info): 
        self.cx = cx
        self.cy = cy 
        self.vx = vx
        self.vy = vy
        self.radius = r 
        self.direction = direction
        self.info = info 
    def add_draws(self, obj):
        self.draws.append(obj)  
    def set_out(self):
        self.draws = []
        self.cx = self.cy = self.direction = self.radius = self.info = self.vx = self.vy = None    


# utils functions
def get_id(color):
    agent_id = 0
    for col in agent.keys():
        agent_id = agent_id + 1 
        if col == color:  
            return agent_id    
        
# viewport to window function
def vp2w(x, y, VP):
    if VP.du > 0 and VP.dv > 0:
        value_x = round(((x - VP.u_min) * (data.NEW_MAX_X - data.NEW_MIN_X) / VP.du) + data.NEW_MIN_X, 2)
        
        if VP.name == 'camera':
            diff_y = VP.v_min - y
        else:
            diff_y = y - VP.v_min
            
        value_y = round((diff_y * (data.NEW_MAX_Y - data.NEW_MIN_Y) / VP.dv) + data.NEW_MIN_Y, 2)
        return value_x, value_y 
    else:
        return None

# window to viewport function
def w2vp(x, y, VP):
    div_x = data.NEW_MAX_X - data.NEW_MIN_X
    div_y = data.NEW_MAX_Y - data.NEW_MIN_Y
    if div_x > 0 and div_y > 0:
        value_x = round(((x - data.NEW_MIN_X) * VP.du / div_x) + VP.u_min, 2)  
        
        if VP.name == 'camera':
            diff_y = data.NEW_MIN_Y - y
        else:
            diff_y = y - data.NEW_MIN_Y
            
        value_y = round((diff_y * VP.dv / div_y) + VP.v_min, 2)
        return value_x, value_y     
    else:
        return None