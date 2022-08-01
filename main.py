# importing libraries
from ctypes import util
import PySimpleGUI as sg
import cv2
import numpy as np 
import math
import data
import utils
import threading
from multiprocessing.pool import ThreadPool
from screeninfo import get_monitors 

pool = ThreadPool(processes=1)

# viewport for projector
vpv = utils.ViewPort('video')

# viewport for camera
vpc = utils.ViewPort('camera')

# rgb colors for opencv
rgb_black = (0, 0, 0)
rgb_white = (255, 255, 255)

def main_layout():
    # define the window layout
    layout = [[sg.Text('Virtual Environment', size=(40, 1), justification='center', font='Helvetica 20')],
              [sg.Image(filename='', key='image')],
              [sg.Button('Start', size=(10, 1), font='Helvetica 14'), 
               sg.Button('Exit', size=(10, 1),  font='Helvetica 14')]] 
    return layout


def second_layout():
    # define the window layout to project drawings
    layout = [[sg.Graph((vpv.u_max + 5, vpv.v_max + 5), (0, 0), (vpv.u_max + 5, vpv.v_max + 5), enable_events=True, key='-GRAPH-', pad=(0,0))]]
    return layout

# draw marks and define rectangle as background
def draw_marks():
    draw.draw_rectangle((5, 5), ((vpv.u_max, vpv.v_max)), fill_color='black', line_color='gray')
    draw.draw_circle((5, 5), 5, fill_color='yellow')
    draw.draw_circle((vpv.u_max, vpv.v_max), 5, fill_color='yellow')
    
    return


def centroid(count):
    M = cv2.moments(count)
    cx = round(M['m10'] / M['m00'], 2)
    cy = round(M['m01'] / M['m00'], 2)  
    return cx, cy


def center(vx, vy):
    cx = round((vx[0] + vx[1] + vx[2]) / 3, 2)
    cy = round((vy[0] + vy[1] + vy[2]) / 3, 2)
    return cx, cy
    

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
    direction_angle = math.acos (diff_x / h)
    # transform result to degrees
    direction_angle = direction_angle * 180 / math.pi
    if vy > cy:
        direction_angle = 360 - direction_angle 
    return round(direction_angle, 2)


# distance between 2 points  
def get_distance(x1, x2, y1, y2):
    d = round(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2), 2)
    return d


def manage_agent(frame, hsv):
    for color in utils.agent.keys():   
        is_agent = generate_mask(frame, hsv, color) 
        

def detect_agents(this):
    # verifies distance between agents
    flag = 0
    # check every object in agent dict
    for a in utils.agent.values():
        if a is not None: 
            # checks every agent different to itself and that currently exists in the world
            if a.id is not this.id: 
                if a.cx is not None:  
                    # gets distance between 2 centroids
                    d = get_distance(a.cx, this.cx, this.cy, a.cy)  
                    r_sum = a.radius + this.radius
                    print('this ', this.id,'b ', a.id, 'dis ', d, 'r sum ', r_sum) 
                    # if the distance is lower than the radius sum, returns true
                    if d < r_sum: 
                        flag = flag + 1   
    if flag > 0:
        return True
    else:
        return False         
        
        
def show_circle(frame, cx, cy, r, color):
    #camera vp
    rc, _ = utils.w2vp(r, 0, vpc)
    cxc, cyc = utils.w2vp(cx, cy, vpc)
    #vb vp
    rv, _ = utils.w2vp(r, 0, vpv)
    cxv, cyv = utils.w2vp(cx, cy, vpv)
    #draws
    if color == 'green':
        cv2.circle(frame, (int(cxc), int(cyc)), int(rc), (0, 255, 0), 2)
    else:
        #red
        cv2.circle(frame, (int(cxc), int(cyc)), int(rc), (0, 0, 255), 2)    
    draw.draw_circle((cxv, cyv), rv, line_color=color)  
    return


def show_line(frame, p1, p2, p3, p4):
    x1c, y1c = utils.w2vp(p1, p2, vpc)
    x2c, y2c = utils.w2vp(p3, p4, vpc)
    cv2.line(frame, (int(x1c), int(y1c)), (int(x2c), int(y2c)), (255, 0, 0), 2)
    x1c, y1c = utils.w2vp(p1, p2, vpv)
    x2c, y2c = utils.w2vp(p3, p4, vpv)
    draw.draw_line((x1c, y1c), (x2c, y2c), color='blue')


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
        if area > 10:
            # recognize triangles or rectangles 
            if len(approx) == 4 and color == 'black': 
                # computes the centroid of shapes 
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
                    corner1 = corner2 = []
                    num_corner = 0
                    
            elif len(approx) == 3 and color !='black':
                flag = 0
                # triangles 
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
                    # print(cx, cy, vx, vy, direction)
                    
                    # convert position (cx cy) and (vx, vy) to world coordinates         
                    cx2, cy2 = utils.vp2w(cx, cy, vpc)
                    vx2, vy2 = utils.vp2w(vx, vy, vpc) 
                    
                    #distance between centroid and min angle vertex in world coordinates 
                    d = get_distance(cx2, vx2, cy2, vy2) 
                    #d, _ = utils.vp2w(d, 0, vpc)
                    
                    r = d + 1
                    print('dis', d)
                    #radius of agent circle
                    print(cx2, cy2, vx2, vy2, d, r)
                    
                    
                    angle = direction / 180 * math.pi
                    p1x, p1y = vx2, vy2
                    p2x, p2y = (((d + 2) * math.cos(angle)) + cx2), (((d+2) *math.sin(angle)) + cy2)
                    p3x, p3y = (2*cx2 - vx2), (2*cy2 - vy2)
                    p4x, p4y = (2*cx2 - p2x), (2*cy2 - p2y)
                    # print('puntos', p1x, p1y, p2x, p2y, p3x, p3y, p4x, p4y)
                    show_line(frame, p1x, p1y, p2x, p2y)
                    show_line(frame, p3x, p3y, p4x, p4y)
                    
                    # display info on frame 
                    info = str(direction)+' | '+str(cx2)+' | '+ str(cy2)
                    cv2.putText(frame, info, (vx, vy), 3, 0.5, (0, 0, 0))  
                    
                    new_agent = utils.Agent(color)
                    new_agent.set_values(cx2, cy2, r, direction)
                    
                    # create agent in the world
                    global agent  
                    utils.agent[color] = new_agent  
                    
                    if detect_agents(new_agent): 
                        circle_color = 'red'
                    else: 
                        circle_color = 'green'
                        
                    show_circle(frame, cx2, cy2, r, circle_color) 
                     
                    vx, vy = utils.w2vp(vx2, vy2, vpv)
                    
                    text = [draw.draw_text(text = info, location = (vx, vy), color = 'gray')]
                    
                    return new_agent
                else:
                    return False
                    
    return                 


def main():
    sg.theme('Black')
    # create the window and show it without the plot
    window = sg.Window('Virtual Environment', main_layout(), element_justification='c', location=(350, 100))
    #indicates which camera use
    cap = cv2.VideoCapture(1)
    recording = False
    # Event loop that reads and displays frames 
    while True:
        event, _ = window.read(timeout=20) 
        
        if event == 'Exit' or event == sg.WIN_CLOSED:
            if recording:
                cap.release()
            return
        
        elif event == 'Start': 
            recording = True 
            for m in get_monitors():  
                x_init = m.x 
                 # set viewport values for projection 
                vpv.set_values(5, 5, m.width - 5, m.height - 5) 
            print(vpv.u_min, vpv.v_min, vpv.u_max, vpv.v_max)
            # calls to layout to define window
            virtual_world = sg.Window('Virtual world', second_layout(), no_titlebar=True, finalize=True, location=(x_init,0), size=(vpv.u_max + 5, vpv.v_max + 5), margins=(0,0)).Finalize()
            virtual_world.Maximize() 
            global draw
            draw = virtual_world['-GRAPH-']  
            draw_marks()  
            
        if recording: 
            cap.set(cv2.CAP_PROP_AUTOFOCUS, 0) # turn the camera autofocus off
            _, frame = cap.read() 
            # converting image obtained to hsv, if exists
            if frame is None:
                print('Something went wrong trying to connect to your camera. Please verify.')
                return
            else:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV) 
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
                    manage_agent(frame, hsv)
            else:
                draw.delete_figure('all')
                draw_marks()          
                    
            #process image from camera
            imgbytes = cv2.imencode('.png', frame)[1].tobytes() 
            window['image'].update(data=imgbytes)
                

if __name__=='__main__':
    t1 = threading.Thread(target=main)
    t1.start()