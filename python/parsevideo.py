import cv2
import os

videoname = input("Video To Read From: ")
cam = cv2.VideoCapture(f'videos/{videoname}.mp4')
period = int(input("Period: "))

try: 
    if not os.path.exists(f'data/{videoname}'): 
        os.makedirs(f'data/{videoname}') 
except OSError: 
    print ('Error: Creating directory for data') 

label = 0
count = 0
while(True):
    ret,frame = cam.read()
    if ret:
        if(count%period == 0):
            name = "./data/" + videoname + "/" + str(label) + ".jpg"
            print ('Creating...' + name) 
            cv2.imwrite(name,frame)
            label += 1
    else:
        break
    count += 1

cam.release()
cv2.destroyAllWindows()