# importing libraries
import PySimpleGUI as sg
import cv2
import numpy as np 
import math
import data
import utils
import threading
from multiprocessing.pool import ThreadPool

pool = ThreadPool(processes=1)

# viewport for projector
# vpv = utils.ViewPort('video')

# # viewport for camera
vpc = utils.ViewPort()

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


def centroid(count):
    M = cv2.moments(count)
    cx = round(M['m10'] / M['m00'], 2)
    cy = round(M['m01'] / M['m00'], 2)  
    return cx, cy
    

def new_corner(corner, num, x, y):
    corner.append(x)
    corner.append(y)
    num = num + 1
    return num 


def manage_agent(frame, hsv):
    for color in utils.agent.keys():   
        is_agent = generate_mask(frame, hsv, color) 


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
        if area > 100:
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
                    
            elif len(approx) == 4 and color !='black':
                flag = 0
                n = approx.ravel()
                i = 0
                for j in n :
                    if(i % 2 == 0):
                        x = n[i]
                        y = n[i + 1] 
                        # this verifies that every vertex is in the region of the viewport 
                        if (vpc.u_max > x > vpc.u_min) and (vpc.v_min > y > vpc.v_max):
                            flag = flag + 1  
                            # coordenadas de cada vertice
                            # string = str(x) + " " + str(y) 
                            # cv2.putText(frame, string, (x, y), 3, 0.5, rgb_white) 
                    i = i + 1
                if flag == 4 :  
                    cv2.drawContours(frame, [approx], 0, (0), 2)
                    # computes the centroid   
                    cx, cy = centroid(count)
                    # convert position (cx cy) and (vx, vy) to world coordinates         
                    cx2, cy2 = utils.vp2w(cx, cy, vpc)
                    print(cx2, cy2)
                    # display info on frame 
                    info = str(cx2)+' | '+ str(cy2)
                    new_agent = utils.Agent(color)
                    new_agent.set_values(cx2, cy2, 0, 0)
                    
                    # create agent in the world
                    global agent  
                    utils.agent[color] = new_agent  
                        
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
            #process image from camera
            imgbytes = cv2.imencode('.png', frame)[1].tobytes() 
            window['image'].update(data=imgbytes)
                

if __name__=='__main__':
    t1 = threading.Thread(target=main)
    t1.start()