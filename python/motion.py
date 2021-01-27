import numpy as np
import cv2
from imutils import contours
from skimage import measure
import argparse
import imutils
import os

file_name = input("File In Videos To Read From: ")

try: 
    if not os.path.exists(f'media/out/{file_name}'): 
        os.makedirs(f'media/out/{file_name}') 
except OSError: 
    print ('Error: Creating directory for out')

cap = cv2.VideoCapture(f'media/videos/{file_name}.mp4')

fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=False)

index = 0
photo_index = 0
while(1):
    ret, frame = cap.read()

    if ret == False:
        break

    if index % 3 == 0:
        fgmask = fgbg.apply(frame)
        

    #print(type(fgmask))

    if index % 15 == 0:
        print(".")
        fgmask = cv2.erode(fgmask, None, iterations=2)
        #fgmask = cv2.dilate(fgmask, None, iterations=1)
        labels = measure.label(fgmask, background=0)
        mask = np.zeros(fgmask.shape, dtype="uint8")

        for label in np.unique(labels):
            if label == 0:
                continue
            labelMask = np.zeros(fgmask.shape, dtype="uint8")
            labelMask[labels == label] = 255
            numPixels = cv2.countNonZero(labelMask)

            if numPixels > 300:
                mask = cv2.add(mask, labelMask)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        if len(cnts) == 0:
            index += 1
            continue
        cnts = contours.sort_contours(cnts)[0]

        for i, c in enumerate(cnts):
            (x, y, w, h) = cv2.boundingRect(c)
            mask = cv2.rectangle(mask, (x,y), (x+w,y+h), (255,255,255), 3)
        cv2.imwrite(f'media/out/1_3/{photo_index}.jpg',mask)
        photo_index += 1
    index += 1
    # k = cv2.waitKey(30) & 0xff
    # if k == 27:
    #     break

cap.release()
cv2.destroyAllWindows()
