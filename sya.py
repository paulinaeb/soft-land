# importing libraries 
import PySimpleGUI as sg
from io import BytesIO
from PIL import Image
import cv2
import numpy as np 
import math
import data
import utils
import com
import threading 
from multiprocessing.pool import ThreadPool
from screeninfo import get_monitors 
import time
import serial 

pool = ThreadPool(processes=1)

# global variables
# connects to gateway by serial
ser_port = None
found = None
msg = None
num_agents = 0

# obj for serial communication
obj_resp = com.Resp()
obj_req = com.Resp()

# viewport for projector
vpv = utils.ViewPort('video')

# viewport for camera
vpc = utils.ViewPort('camera')

# for drawing in init agent
vpv_mid_x = None
vpv_mid_y = None

# handler
event = None

# rgb colors for opencv
rgb_black = (0, 0, 0)
rgb_white = (255, 255, 255)

# colors of agent triangles
agent = { 'blue': None,
          'green': None,
        #   'yellow': None
        }  

obj_masks = ['blue', 'yellow']

# init agents with id and no attributes
for col in agent.keys():
    agent[col] = utils.Agent(col)  
    
# for timer
int_sec = None
# total of secs to count
count_secs = 10

def image_to_data(im): 
    with BytesIO() as output:
        im.save(output, format="PNG")
        data = output.getvalue()
    return data
    
# layout for first monitor
def main_layout():
    # define the window layout
    layout = [[sg.Text('Entorno Virtual', size=(40, 1), justification='center', font='Helvetica 20')],
              [sg.Image(filename='', key='image')],
              [sg.Button('Iniciar', size=(8, 1), font='Helvetica 12', key='Iniciar'),
               sg.pin(sg.Button('Inicializar objetos', size=(15, 1),  font='Helvetica 12', key='_obj_', visible=False)),
               sg.pin(sg.Button('Inicializar agentes', size=(15, 1),  font='Helvetica 12', key='_agents_', visible=False)),
               sg.Button('Finalizar', size=(8, 1),  font='Helvetica 12')
               ]] 
    return layout

# layout for second monitor
def second_layout():
    # define the window layout to project drawings
    layout = [[sg.Graph((vpv.u_max + 5, vpv.v_max + 5), (0, 0), (vpv.u_max + 5, vpv.v_max + 5), enable_events=True, key='-GRAPH-', pad=(0,0))]]
    return layout

# draw marks and define rectangle as background
def draw_marks():
    draw.draw_rectangle((5, 5), ((vpv.u_max, vpv.v_max)), fill_color='black', line_color='gray')
    draw.draw_circle((5, 5), 5, fill_color='yellow') 
    draw.draw_circle((vpv.u_max, vpv.v_max), 5, fill_color='yellow')
    # x, y = utils.w2vp(52, 10, vpv)
    # draw.draw_circle((x, y), 1, fill_color='white')
    return

# clear projection in second monitor
def clear_screen():
    draw.erase()
    draw_marks()
    return

# centroid of rectangle
def centroid(count):
    M = cv2.moments(count)
    cx = round(M['m10'] / M['m00'], 2)
    cy = round(M['m01'] / M['m00'], 2)  
    return cx, cy

# centroid of triangle
def center(vx, vy):
    cx = round((vx[0] + vx[1] + vx[2]) / 3, 2)
    cy = round((vy[0] + vy[1] + vy[2]) / 3, 2)
    return cx, cy
    
# function to define region of interest
def new_corner(corner, num, x, y):
    corner.append(x)
    corner.append(y)
    num = num + 1
    return num 


def line_length(x1, y1, x2, y2):
    x_dif = x1 - x2
    y_dif = y1 - y2
    return x_dif * x_dif + y_dif * y_dif

# get all angles of given 3 points of triangle and returns the min angle vertex found
def get_vertex(x1, y1, x2, y2, x3, y3):
    # bc
    a2 = line_length(x2, y2, x3, y3)
    # ac
    b2 = line_length(x1, y1, x3, y3)
    # ab
    c2 = line_length(x1, y1, x2, y2)
    
    a = math.sqrt(a2)
    b = math.sqrt(b2)
    c = math.sqrt(c2)
    
    alpha = math.acos((b2 + c2 - a2) / (2 * b * c))
    beta = math.acos((a2 + c2 -b2) / (2 * a * c))
    gamma = math.acos((a2 + b2 - c2) / (2 * a * b))
    # Converting to degree
    alpha = round(alpha * 180 / math.pi, 2);
    beta = round(beta * 180 / math.pi, 2);
    gamma = round(gamma * 180 / math.pi, 2);
    
    # return lower angle and its coordinates
    if gamma > alpha < beta: 
        return x1 , y1
    elif gamma > beta < alpha: 
        return x2, y2
    elif beta > gamma < alpha: 
        return x3, y3 
    
# get direction of the triangle using min angle triangle vertices and centroid
def direction_angle(cx, cy, vx, vy):
    diff_x = vx - cx
    # cy and vy are inverted because camera orientation in Y is inverted
    diff_y = cy - vy
    # hypotenuse of the rectangle triangle formed with X and the line between C and min angle V
    h = math.sqrt((diff_x * diff_x) + (diff_y * diff_y))
    angle = math.acos (diff_x / h)
    # transform result to degrees
    angle = radians2degrees(angle)
    if vy > cy:
        angle = 360 - angle 
    return round(angle, 2)

# distance between 2 points  
def get_distance(x1, x2, y1, y2):
    d = round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 2)
    return d

# conversion of angle units below
def degrees2radians(angle):
    radians = angle / 180 * math.pi
    return round(radians, 2) 


def radians2degrees(angle):
    degrees = angle * 180 / math.pi
    return round(degrees, 2)

# clears the draws associated to the color received in the projection
def remove_figures(color):
    if agent[color] is not None: 
        if agent[color].cx: 
            for figure in agent[color].draws:  
                draw.delete_figure(figure)  
        return True
    return


def manage_masks(frame, hsv):
    # generate masks for every agent to detect the color required
    if init_objs == False:
        for color in agent.keys():   
            agnt = generate_mask(frame, hsv, color) 

            # if there is not agent detected, clears its draws if existed
            if not agnt:  
                if remove_figures(color): 
                    # clears the object
                    agent[color].set_out()  
                
            # if an agent is detected, clears previous draws if existed
            elif agnt:
                # start of init agent management validating time
                if int_sec:
                    if count_secs >= int_sec >= 0 and agent[color].found == False and init_objs == False: 
                        # send by serial
                        agent[color].found = True
                        # serialize message to send, from sand to all (command = Info ID) with one parameter
                        send_msg('0', 'F', 'II', [str(agent[color].id)])
                        str_found = 'Se encontró agente: '+color+' ID: '+str(agent[color].id)
                        print(str_found)
                        global msg
                        msg = draw.draw_text(str_found, location=(vpv_mid_x, vpv_mid_y+80), color = 'white', font='Helvetica 20')
                        global found 
                        found = True 
                        
                if remove_figures(color):
                    # drops draws from object
                    agent[color].draws = []
                
                # draws a circle verifying that there is nothing in its radius
                if detect_agents(agnt): 
                    circle_color = 'red'
                else: 
                    circle_color = 'green'  
                # shows the draws corresponding to the agent in the projection
                show_draws(frame, agnt, circle_color) 
                transform_points(frame, agnt)
                if num_agents > 0:
                    detect_objects(agnt, d_small, small_obj, False, True, False)
                    detect_objects(agnt, d_big, big_obj, False, False, True)
                    detect_objects(agnt, d_home, home, True, False, False)
                
    else:
        for color in obj_masks:
            generate_mask(frame, hsv, color) 
    return

d_small = 8
d_big = 12
d_home = 15
d_obs = 10

# avoid distance for agents
def detect_objects(this, d2detect, ob_list, is_home, is_small, is_big):
    if len(ob_list) > 0:
        if is_home:
            r_ob = ob_list[2]
        else:
            r_ob = ob_list[0][3]
        d2ignore = get_distance(this.cx, this.vx, this.cy, this.vy) + r_ob
        d_final = d2detect + d2ignore
        if is_home:
            d = get_distance(this.cx, ob_list[0], this.cy, ob_list[1])
            print(d)
            if d <= d_final:
                print('home detected')
                # sends position
                send_msg('0', str(this.id), 'HO', [str(round(ob_list[0], 1)), str(round(ob_list[1], 1))])
        else:
            for ob in ob_list:
                d = get_distance(this.cx, ob[0], this.cy, ob[1])
                print(d)
                if d <= d_final:
                    if is_small:
                        print('small object detected')
                        c = 'SO'
                    if is_big:
                        print('big object detected')
                        c = 'BO'                       # x                  # y                 #id_obj
                    send_msg('0', str(this.id), c, [str(round(ob[0], 1)), str(round(ob[1], 1)), str(ob[2])])

# detect agents around another (this)
def detect_agents(this):
    # verifies distance between agents
    flag = 0
    # check every object in agent dict
    for a in agent.values():
        if a is not None: 
            # checks every agent different to itself and that currently exists in the world
            if a.id is not this.id: 
                if a.cx is not None:  
                    # gets distance between 2 centroids
                    d = get_distance(a.cx, this.cx, this.cy, a.cy)  
                    r_sum = a.radius + this.radius
                    # print('this ', this.id,'b ', a.id, 'dis ', d, 'r sum ', r_sum) 
                    # if the distance is lower than the radius sum, returns true
                    if d < r_sum: 
                        flag += 1   
                        if num_agents > 0:                      # dir   # dis
                            send_msg('0', str(this.id), 'CR', [str('0'), str(round(this.radius, 2))])
                            send_msg('0', str(a.id), 'CR', [str('1'), str(round(this.radius, 2))])
    limit_col = 2.5
    if this.cx < data.NEW_MIN_X + limit_col + this.radius or this.cx > data.NEW_MAX_X - limit_col - this.radius:
        if num_agents > 0:
            try:
                send_msg('0', str(this.id), 'CL', [])
            except serial.SerialException:
                pass
        return True
    if this.cy < data.NEW_MIN_Y + limit_col + this.radius -1 or this.cy > data.NEW_MAX_Y - limit_col - this.radius:
        if num_agents > 0:
            try:
                send_msg('0', str(this.id), 'CL', [])
            except serial.SerialException:
                pass    
        return True
    if flag > 0:
        return True
    return False         
        
        
def show_draws(frame, agnt, color):
    #camera vp
    rc, _ = utils.w2vp(agnt.radius, 0, vpc) 
    cxc, cyc = utils.w2vp(agnt.cx, agnt.cy, vpc)
    #vb vp
    rv, _ = utils.w2vp(agnt.radius, 0, vpv)
    cxv, cyv = utils.w2vp(agnt.cx, agnt.cy, vpv)
    #draws
    if color == 'green':
        cv2.circle(frame, (int(cxc), int(cyc)), int(rc - (rc * 0.28)), (0, 255, 0), 2)
    else:
        #red
        cv2.circle(frame, (int(cxc), int(cyc)), int(rc - (rc * 0.28)), (0, 0, 255), 2)
       
    agnt.add_draws(draw.draw_circle((cxv, cyv), rv, line_color=color)) 
    agnt.add_draws(draw.draw_text(text = 'X', location = (cxv, cyv), color = 'gray', font='Helvetica 15'))
    
    vx, vy = utils.w2vp(agnt.vx, agnt.vy, vpv)
    if vy > cyv:
        vx, vy = utils.w2vp(agnt.vx + 5, agnt.vy + 5, vpv)
    else:
        vx, vy = utils.w2vp(agnt.vx - 5, agnt.vy - 5, vpv)
    agnt.add_draws(draw.draw_text(text = agnt.info, location = (vx, vy), color = 'gray', font='Helvetica 15')) 
    
    return


def show_line(frame, agnt, p1, p2, p3, p4):
    x1c, y1c = utils.w2vp(p1, p2, vpc)
    x2c, y2c = utils.w2vp(p3, p4, vpc)
    cv2.line(frame, (int(x1c), int(y1c)), (int(x2c), int(y2c)), (255, 0, 0), 2)
    x1c, y1c = utils.w2vp(p1, p2, vpv)
    x2c, y2c = utils.w2vp(p3, p4, vpv) 
    agnt.add_draws(draw.draw_line((x1c, y1c), (x2c, y2c), color='blue')) 
    return


def transform_points(frame, agnt): 
    # distance between centroid and vertex
    d = get_distance(agnt.cx, agnt.vx, agnt.cy, agnt.vy)  
    # angle to radians conversion
    angle = degrees2radians(agnt.direction) 
    # calculate points of lines to draw 
    p1x, p1y = agnt.vx, agnt.vy
    p2x, p2y = (d + 2) * math.cos(angle) + agnt.cx, (d+2) * math.sin(angle) + agnt.cy
    p3x, p3y = 2 * agnt.cx - agnt.vx, 2 * agnt.cy - agnt.vy
    p4x, p4y = 2 * agnt.cx - p2x, 2 * agnt.cy - p2y
    # show lines
    show_line(frame, agnt, p1x, p1y, p2x, p2y)
    show_line(frame, agnt, p3x, p3y, p4x, p4y)
    return


# a is the agent that follows and b which is followed 
def transform_center2get_angle(frame, a, b):
    if agent[a] and agent[b]:
        if agent[a].cx and agent[b].cx:
            # point where I wish to go
            d = get_distance(agent[a].cx,  agent[b].cx,  agent[a].cy,  agent[b].cy)
            
            # transform points
            angle = -1 * degrees2radians(agent[a].direction)
            xt = ((agent[b].cx - agent[a].cx) * math.cos(angle)) - ((agent[b].cy - agent[a].cy) * math.sin(angle))
            yt = ((agent[b].cx - agent[a].cx) * math.sin(angle)) + ((agent[b].cy - agent[a].cy) * math.cos(angle)) 
            yt = round(yt, 2)

            dir_angle = math.asin(yt / d)
            dir_angle = radians2degrees(dir_angle) 
            
            if xt < 0 :
                dir_angle = 180 - dir_angle  
            else:
                if yt < 0:
                    dir_angle = 360 + dir_angle   
                    
            # shows distance
            cx, cy = utils.w2vp(agent[a].cx, agent[a].cy, vpc)
            cv2.putText(frame, 'd:'+str(d), (int(cx), int(cy)), 3, 0.5, rgb_white)
            # shows angle
            cx, cy = utils.w2vp(agent[b].cx, agent[b].cy, vpc)
            cv2.putText(frame, 'angle: '+str(dir_angle), (int(cx), int(cy)), 3, 0.5, rgb_white)
            
            print('follows:',agent[a].cx,' ', agent[a].cy, ' followed:',agent[b].cx, ' ', agent[b].cy)
            print('distance:', d,' ', 'angle:',dir_angle)
    return

obstacles = []
big_obj = []
small_obj = []
home = []

def set_obj(arr, cx, cy, is_movable):
    exists = False
    if len(arr) == 0:
        if is_movable:
            # x - y - id draw - radius
            arr.append([cx, cy, 0, 0])
        else:
            arr.append([cx, cy])
    else:
        for obj in arr:
            if obj[0] in (cx - 1, cx, cx + 1) and obj[1] in (cy - 1, cy, cy + 1):
                exists = True
        if exists == False:
            if is_movable:
                arr.append([cx, cy, 0, 0])
            else:
                arr.append([cx, cy])
    return arr

def generate_mask(frame, hsv, color):
    mask = cv2.inRange(hsv, np.array(data.HSV_COLORS[color][0]), np.array(data.HSV_COLORS[color][1]))
    contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    #variables to define the rectangle of viewport
    num_corner = 0
    corner1 = []
    corner2 = []
    for count in contours:
        # using functions to get the contour of shapes
        epsilon = 0.01 * cv2.arcLength(count, True)
        approx = cv2.approxPolyDP(count, epsilon, True)
        # get area to work with only visible objects
        area = cv2.contourArea(count)
        if area > 600:
            # recognize rectangles 
            if len(approx) == 4 and color == 'black':
                    cx, cy = centroid(count)
                    cv2.circle(frame, (int(cx),int(cy)), 2, rgb_white, 2)
                    # rectangles - marks 
                    if num_corner == 0: 
                        num_corner = new_corner(corner1, num_corner, cx, cy)
                    elif num_corner == 1: 
                        num_corner = new_corner(corner2, num_corner, cx, cy)
                        # draws the region of interest as a rectangle
                        cv2.rectangle(frame, (int(corner1[0]), int(corner1[1])), (int(corner2[0]), int(corner2[1])), rgb_white, 2)
                        return corner1, corner2
                    elif num_corner == 2:
                        # reset values
                        corner1 = []
                        corner2 = []
                        num_corner = 0
            elif (color in ('blue', 'yellow')) and init_objs == True and (len(approx) == 4 or len(approx) > 13):
                cx, cy = centroid(count)
                cx, cy = utils.vp2w(cx, cy, vpc)
                cx, cy =(math.floor(cx), math.floor(cy))
                cv2.drawContours(frame, [approx], 0, (0), 2)
                if len(approx) == 4 and color == 'blue':
                    global obstacles
                    obstacles = set_obj(obstacles, cx, cy, False)
                elif len(approx) > 13 and color == 'blue':
                    global big_obj
                    big_obj = set_obj(big_obj, cx, cy, True)
                elif len(approx) == 4 and color == 'yellow':
                    global home
                    # x, y, radius
                    home = [cx, cy, 3]
                elif len(approx) > 13 and color == 'yellow' and area < 700:
                    global small_obj
                    small_obj = set_obj(small_obj, cx, cy, True)
            # recognize triangles        
            elif len(approx) == 3 and color !='black':
                flag = 0
                # vertex of triangles 
                vx_coord = []
                vy_coord = []
                n = approx.ravel()
                i = 0
                for j in n :
                    if(i % 2 == 0):
                        x = n[i]
                        y = n[i + 1] 
                        # this verifies that every vertex is in the region of the viewport 
                        if (vpc.u_max > x > vpc.u_min) and (vpc.v_min > y > vpc.v_max):
                            flag = flag + 1  
                        # string = str(x) + " " + str(y) 
                        # cv2.putText(frame, string, (x, y), 3, 0.5, rgb_white) 
                        vx_coord.append(x)
                        vy_coord.append(y)
                    i = i + 1
                if flag == 3 :  
                    cv2.drawContours(frame, [approx], 0, (0), 2)
                    # computes the centroid of triangle   
                    cx, cy = center(vx_coord, vy_coord)  
                    # get min angle coordinates 
                    vx, vy = get_vertex(vx_coord[0], vy_coord[0], vx_coord[1], vy_coord[1], vx_coord[2], vy_coord[2])
                     
                    #get angle of vertex (direction of agent)
                    direction = direction_angle(cx, cy, vx, vy)
                    
                    # convert position (cx cy) and (vx, vy) to world coordinates         
                    cx2, cy2 = utils.vp2w(cx, cy, vpc)
                    vx2, vy2 = utils.vp2w(vx, vy, vpc) 
                    
                    #distance between centroid and min angle vertex in world coordinates to get radius
                    r = get_distance(cx2, vx2, cy2, vy2)  + 1.2
                    # display info on frame 
                    info = 'x: '+str(cx2)+'\ny:'+ str(cy2)+'\nt:'+str(direction)
                    info2 = 'x: '+str(cx2)+' y:'+ str(cy2)+' t:'+str(direction)
                    cv2.putText(frame, info2, (vx, vy), 3, 0.5, (0, 0, 0))
                    # create object agent and assign values in the world  
                    agent[color].set_values(cx2, cy2, vx2, vy2, r, direction, info)   
                    return agent[color]
                else:
                    return False
    return                 


def time_as_int():
    return int(round(time.time() * 100)) 


def init_obj(obj_type):
    # calculates positions for projection strings 
    top_left = (vpv_mid_x + 40, vpv_mid_y + 22)
    top_right = (vpv_mid_x - 40, vpv_mid_y - 22) 
    # time
    count = count_secs * 100
    # will use global variable
    global int_sec
    # as many times as agents exists
    if obj_type == 1:
        times = len(agent)
    else:
        times = 1
    for i in range(times):
        global found
        found = False
        if obj_type == 1:
            str_title = 'Coloque el agente nº '+str(i + 1)+' en la arena'
        else:
            str_title = 'Coloque sus objetos en la arena'
        time.sleep(.01)
        title = draw.draw_text(str_title, location = (vpv_mid_x, vpv_mid_y+50), color = 'white', font='Helvetica 20')
        # variables to complete timer
        int_sec = 0
        current_time = 0 
        start_time = time_as_int()
        str_time = ''
        aux_str = '' 
        text = None
        rect = None
        i = 0
        # repeats until get to limit number given or until an agent is found
        while current_time < count and found == False:
            i+=1
            # validates main gui
            if event == 'Finalizar' or event == sg.WIN_CLOSED: 
                return
            current_time = time_as_int() - start_time  
            aux_str = str_time
            str_time = '{:02d}'.format((current_time // 100) % 60) 
            int_sec = int(str_time)  
            if i % 10000 == 0:
                print('Init..')
            # manages and draws projection
            if aux_str != str_time:
                if text:
                    draw.delete_figure(text)
                if rect:
                    draw.delete_figure(rect)
                rect = draw.draw_rectangle(top_left, top_right, fill_color='black')
                text = draw.draw_text(text = str_time, location = (vpv_mid_x, vpv_mid_y), color = 'white', font='Helvetica 20')
        time.sleep(.8)
        try:
            draw.delete_figure(text)
        except:
            pass
        draw.draw_rectangle(top_left, top_right, fill_color='black')
        try:
            draw.delete_figure(rect)
        except:
            pass
        try:
            draw.delete_figure(title)
        except: 
            pass
        if msg:
            try:
                draw.delete_figure(msg)
            except:
                pass
        int_sec = None 
    if obj_type == 1:
        # calculates num of agents initialized
        global num_agents
        for ag in agent.values():
            if ag:
                if ag.found:
                    num_agents += 1
    # end of loop and clearing screen
    str_fin = 'Inicializacion terminada'
    fin = draw.draw_text(str_fin, location = (vpv_mid_x, vpv_mid_y + 50), color = 'white', font='Helvetica 20')
    time.sleep(1)
    draw.delete_figure(fin)
    print(str_fin)
    if obj_type == 1:
        print('Number of agents', str(num_agents))
        # send msg to agents: number of agents on sandbox from sand to all (command = AI) with one parameter
        if num_agents > 0:
            send_msg('0', 'F', 'AI', [str(num_agents)])
    else:
        global init_objs
        init_objs = False
        r, _ = utils.w2vp(3, 0, vpv)
        if len(obstacles) > 0:
            for obj in obstacles:
                x, y = utils.w2vp(obj[0], obj[1], vpv)
                draw.draw_rectangle((x - r, y - r), (x + r, y + r), fill_color='brown4')
        if len(big_obj) > 0:
            for obj in big_obj:
                x, y = utils.w2vp(obj[0], obj[1], vpv)
                id_draw = draw.draw_circle((x, y), r, line_color='light pink') 
                obj[2] = id_draw
                obj[3] = 3
        if len(small_obj) > 0:
            r, _ = utils.w2vp(1.5, 0, vpv)
            for obj in small_obj:
                x, y = utils.w2vp(obj[0], obj[1], vpv)
                id_draw = draw.draw_circle((x, y), r, line_color = 'SeaGreen1')
                obj[2] = id_draw
                obj[3] = 1.5
        if len(home) > 0:
            r, _ = utils.w2vp(home[2], 0, vpv)
            a = int(r*2)
            im = Image.open("house.png")
            im = im.resize((a, a))
            x, y = utils.w2vp(home[0], home[1], vpv)
            draw.draw_image(data = image_to_data(im), location=(x - r, y + r))
    return

# sets values to response object, serializes, encodes and sends message by serial
def send_msg(f, d, c, p):
    obj_resp.set_values(f, d, c, p)
    ser_msg = com.serialize(obj_resp)
    ser_port.write((ser_msg+',').encode())
    print('Sent:', ser_msg)
    return


msg_received = []
stop = False


def read_msg():
    while True:
        try:
            read_val = ser_port.readline()
            msg_read = read_val.decode()
            if msg_read:
                print(msg_read)
                if msg_read != 'SS':
                    msg_received.append(msg_read)
                else:
                    global stop
                    stop = True
        except serial.SerialException:
            print('There was found a problem with your serial port connection. Please verify and try again.')
        if event == 'Finalizar' or event == sg.WIN_CLOSED:
            break
    return


def answer(val, d, c):
    global stop
    i = 0
    while True:
        if i % 10000 == 0:
            print(i/10000)
        if val.cx and c == 'GP':
            if val.cx <= 99.44:
                x = str(round(val.cx, 1))
            else:
                x = str(round(val.cx))
            send_msg('0', d, c, [x, str(round(val.cy, 1)), str(round(val.direction))])
            break
        elif event == 'Finalizar' or event == sg.WIN_CLOSED:
            break
        elif stop:
            print('stop searching')
            stop = False
            break
        i += 1
    return

init_objs = False

def main():
    sg.theme('Black')
    # create the window and show it without the plot
    window = sg.Window('Entorno Virtual', main_layout(), element_justification='c', location=(350, 100))
    #indicates which camera use
    cap = cv2.VideoCapture(1)
    recording = False
    for m in get_monitors():  
        x_init = m.x 
        # set viewport values for projection 
        vpv.set_values(5, 5, m.width - 5, m.height - 5) 
    # print(vpv.u_min, vpv.v_min, vpv.u_max, vpv.v_max)
    # calls to layout to define window
    virtual_world = sg.Window('Sand', second_layout(), no_titlebar=True, finalize=True, location=(x_init,0), size=(vpv.u_max + 5, vpv.v_max + 5), margins=(0,0)).Finalize()
    virtual_world.Maximize() 
    global draw
    draw = virtual_world['-GRAPH-']  
    draw_marks()  
    com = False
    # Event loop that reads and displays frames 
    while True:
        global event
        event, _ = window.read(timeout=20) 
        if event == 'Finalizar' or event == sg.WIN_CLOSED:
            if recording:
                cap.release()
            return
        
        elif event == 'Iniciar': 
            window['Iniciar'].Update(visible = False)
            window['_obj_'].Update(visible = True)
            window['_agents_'].Update(visible = True)
            recording = True 
            
        if recording: 
            # turn the camera autofocus off
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0) 
            _, frame = cap.read() 
            # converting image obtained to hsv, if exists
            if frame is None:
                print('Something went wrong trying to connect to your camera. Please verify.')
                return
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) 
            # thread
            region = pool.apply_async(generate_mask, (frame, hsv, 'black'))
            region = region.get()  

            if region: 
                # print(region)
                min_corner, max_corner = region
                # define vpc values
                vpc.set_values(min_corner[0], min_corner[1], max_corner[0], max_corner[1]) 
                # convert limits coordinates to window (main layout)
                vpc_min  = utils.vp2w(min_corner[0], min_corner[1], vpc)  
                vpc_max  = utils.vp2w(max_corner[0], max_corner[1], vpc)  
                if vpc_min and vpc_max:
                    cv2.putText(frame, (str(int(vpc_min[0]))+','+str(int(vpc_min[1]))), (int(vpc.u_min) - 10, int(vpc.v_min) + 15), 3, 0.5, rgb_white)
                    cv2.putText(frame, (str(int(vpc_max[0]))+','+str(int(vpc_max[1]))), (int(vpc.u_max) - 70, int(vpc.v_max) - 5), 3, 0.5, rgb_white)
                    # call to function to detect agents
                    manage_masks(frame, hsv)
                    # transform_center2get_angle(frame, 'blue', 'green')
                    global vpv_mid_x
                    global vpv_mid_y
                    # gets the middle of the projection screen
                    vpv_mid_x = int(vpv.u_max/2)
                    vpv_mid_y = int(vpv.v_max/2) 
                    if event == '_obj_':
                        window['_obj_'].Update(visible = False)
                        global init_objs
                        init_objs = True
                        obj_th = threading.Thread(target = init_obj, args=(2,))
                        obj_th.start()
                    
                    if event == '_agents_' and init_objs == False:  
                        # serial connection variable
                        global ser_port
                        # set global values used multiple times to print in projection gui
                        try:
                            # tries serial connection before start initialization
                            ser_port = serial.Serial(port='COM3', baudrate=115200, timeout=0.01)  
                            window['_agents_'].Update(visible = False)
                            window['_obj_'].Update(visible = False)
                            # start of thread that init timer
                            thre = threading.Thread(target = init_obj, args=(1,))
                            thre.start()
                            # handles exception
                        except serial.SerialException:
                            print('There was found a problem with your serial port connection. Please verify and try again.')
            else:
                # clear_screen()        
                pass
            if num_agents > 0 and com == False:
                com = True
                t2 = threading.Thread(target=read_msg)
                t2.start()
            if len(msg_received) > 0 and processing == False:
                t = threading.Thread(target=process_msg)
                t.start()
            #process and updates image from camera 
            imgbytes = cv2.imencode('.png', frame)[1].tobytes() 
            window['image'].update(data=imgbytes)
            
            
processing = False           
            
def process_msg():
    global processing
    processing = True
    if len(msg_received[0]) >= 4:
        com.deserialize(msg_received[0], obj_req)
        print(obj_req.__dict__)
        if obj_req.d == '0':
            for val in agent.values():
                if val:
                    if (val.found is True) and (str(val.id) == obj_req.f):
                        # type of commands here...
                        # get position
                        if obj_req.c == 'GP':
                            if len(obj_req.p) == 0:
                                answer(val, obj_req.f, obj_req.c)
                            else:
                                for a in agent.values():
                                    if str(a.id) == obj_req.p[0]:
                                        answer(a, obj_req.f, obj_req.c)
                                        break
                        # who are near me
                        elif obj_req.c == 'WN':
                            res = ''
                            flag = 0
                            if num_agents > 1:
                                for a in agent.values():
                                    if a:
                                        if str(a.id) != obj_req.f and a.found == True:
                                            for i in range(45):
                                                if a.cx and val.cx:
                                                    d_max = int(obj_req.p[0]) 
                                                    d = get_distance(a.cx, val.cx, val.cy, a.cy)  
                                                    r_sum = a.radius + val.radius
                                                    d_total = d - r_sum
                                                    if d_total <= d_max:
                                                        print('d', d, 'r sum', r_sum, 'd total', d_total, 'id', a.id)
                                                        res += str(a.id)
                                                        flag += 1
                                                    break
                            print('res', res)
                            if flag > 0:
                                p = [res]
                            else:
                                p = '0'
                            send_msg('0', obj_req.f, obj_req.c, [p])
                             # call agent         # agent arrived      # follow me
                        elif obj_req.c == 'CA' or obj_req.c == 'AR' or obj_req.c == 'FM':
                            send_msg('0', obj_req.p[0], obj_req.c, [obj_req.f])
    else:
        send_msg('0', 'F', 'NF', [])
    msg_received.pop(0)
    processing = False
    return
            

if __name__=='__main__': 
    main()