import cv2
import os

cam = cv2.VideoCapture(f'videos/{input("Video To Read From: ")}.mp4')
period = int(input("Period: "))

try: 
    if not os.path.exists('data'): 
        os.makedirs('data') 

except OSError: 
    print ('Error: Creating directory for data') 

label = 0

while(True):
    ret,frame = cam.read()

    if ret:
        if(label%period == 0):
            name = "./data/" + str(label) + ".jpg"
            print ('Creating...' + name) 

            cv2.imwrite(name,frame)
    else:
        break
    label += 1

cam.release()
cv2.destroyAllWindows()