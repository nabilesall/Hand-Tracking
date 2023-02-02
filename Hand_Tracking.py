import cv2
import math 
import time
import numpy as np
import collections.abc
from datetime import datetime
from sense_emu import SenseHat #replace sense_emu by sense_hat

start_time = 0
curr_time = 0
end_time = 0
delay = 800 #time to wait (in ms) before cancelling a swipe
cooldown = 700 #time to wait inside area after a swipe before considering it to be a new swipe attempt
check_swiping = False #if we're currently waiting to complete a swipe
has_swiped = False #if we just swiped and are still in a swipe area

pos_rect_left = (0, 0, 0.3, 1)
pos_rect_right = (0.7, 0, 1, 1)

display_area = (0.3, 0.4, 0.7, 0.6)
menu = (1, 2, 3, 4)
selected_option = 1
display_string = ""

#Color to consider as finger
lower_red = np.array([200, 0, 0])
upper_red = np.array([255, 100, 100])

width = 680
height = 480

#RaspberryPi
sense = SenseHat()
sense.clear()

gyro_calib = (0,0,0)

################################################################

def gyro_calibration():
    calibration_time = 3
    end_calibration = time.time() + calibration_time

    while time.time() < end_calibration:
        o = sense.get_orientation()
        x = o['pitch']
        y = o['roll']
        z = o['yaw']

    calib = (-x, -y, -z)
    return calib

def get_gyro_value():
    o = sense.get_orientation()
    x = o['pitch'] + gyro_calib[0]
    y = o['roll'] + gyro_calib[1]
    z = o['yaw'] + gyro_calib[2]

    x=round(x, 1)
    y=round(y, 1)
    z=round(z, 1)

    return "pitch={0}, roll={1}, yaw={2}".format(x, y, z)

def get_humidity():
    humidity = sense.get_humidity()
    return "Humidity : " + str(humidity) + " %"

def get_pressure():
    pressure = sense.get_pressure()
    return "Pressure :" + str(pressure) + " hPa"

def get_temperature():
    temp = sense.get_temperature_from_pressure()
    return "Temperature : " + str(temp) + "C"


def get_index_pos(imgRGB):
    #assume finger is at the center of the screen if nothing detected
    mask = cv2.inRange(imgRGB, lower_red, upper_red)
    index_pos = (width//2, height//2)
    points = cv2.findNonZero(mask)
    if (type(points) == np.ndarray):
        avg = np.mean(points, axis=0)
        index_pos = (avg[0][0], avg[0][1])      
    return index_pos

#return 1 if in left rectangle, 2 if in right rectangle, else 0
def check_pos(pos_finger):
    if pos_finger[0] < math.floor(pos_rect_left[2]*width):
        pos = 1
    elif pos_finger[0] > math.floor(pos_rect_right[0]*width):
        pos = 2
    else:
        pos = 0
    return pos

#return direction of swipe based on start and end position
def check_swipe(index_pos, start_pos):
    end_pos = check_pos(index_pos)
    swipe=""

    #if not in an area or same area as start one
    if end_pos == 0 or end_pos == start_pos:
        return swipe
    if end_pos > start_pos:
        swipe = "right"
    else:
        swipe = "left"
    return swipe

#what to do with the swipe direction (move menu)
def handle_swipe(swipe, selected_option):
    if swipe == "left":
        selected_option -= 1
        if selected_option < 1:
            selected_option = menu[len(menu)-1]
    else:
        selected_option += 1
        if selected_option > 4:
            selected_option = menu[0]
    return selected_option


################################################################

#calibrate gyroscope
gyro_calib = gyro_calibration()

# initialize the camera and grab a reference to the raw camera capture
camera = cv2.VideoCapture(0)

# allow the camera to warmup
time.sleep(0.1)

# capture frames from the camera
while (1):
    start, img = camera.read()
    
    if start:
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # current position of index
        index_pos = get_index_pos(imgRGB)

        # datetime object containing current date and time
        now = datetime.now()

        # dd/mm/YY H:M:S
        dt_string = now.strftime("%d/%m/%Y %H:%M")

        #math.floor because we need integers
        cv2.putText(img,dt_string, (math.floor(width * 0.01),math.floor(height * 0.05)), cv2.FONT_HERSHEY_PLAIN, 1.5, (0,0,0), 1)
        cv2.rectangle(img, (math.floor(width * pos_rect_left[0]), math.floor(height * pos_rect_left[1])), (math.floor(width * pos_rect_left[2]), math.floor(height * pos_rect_left[3])), (255,0,0), 2)
        cv2.rectangle(img, (math.floor(width * pos_rect_right[0]),math.floor(height * pos_rect_right[1])), (math.floor(width * pos_rect_right[2]), math.floor(height * pos_rect_right[3])), (255,0,0), 2)

        cv2.rectangle(img, (math.floor(width * display_area[0]),math.floor(height * display_area[1])), (math.floor(width * display_area[2]), math.floor(height * display_area[3])), (0,255,0), 2)

        # chose what sensor to display
        if selected_option == 1:
            display_string = get_gyro_value()
        elif selected_option == 2:
            display_string = get_temperature()
        elif selected_option == 3:
            display_string = get_pressure()
        else:
            display_string = get_humidity()

        cv2.putText(img,display_string, (math.floor(width * display_area[0]),math.floor(height * 0.5)), cv2.FONT_HERSHEY_PLAIN, 1.5, (0,255,0), 1)


        #always get current position ans only assign it IF we're in an area
        curr_pos = check_pos(index_pos)
        if curr_pos > 0:
            if check_swiping:
                #if delay has expired : reset position
                if curr_time > start_time + delay:
                    check_swiping = False
                    start_pos = 0
                else:
                    #get direction of swipe
                    swipe = check_swipe(index_pos, start_pos)
                    if swipe != "":
                        check_swiping = False
                        print(swipe)
                        selected_option = handle_swipe(swipe, selected_option)
                        swipe = ""
                        start_pos = 0
                        has_swiped = True
                        end_time = time.time() * 1000
            #check cooldown before new swipe attempt
            elif has_swiped:
                if curr_time > end_time + cooldown:
                    has_swiped = False
            #change the start_pos if no current swipe attempt
            else:
                start_pos = curr_pos
                #start time in ms
                start_time = time.time() * 1000
                check_swiping = True
        else:
            has_swiped = False

        curr_time = time.time() * 1000
        cv2.imshow("Frame", img)
    key = cv2.waitKey(1) & 0xFF
