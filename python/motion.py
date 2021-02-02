import numpy as np
import cv2
from imutils import contours
from skimage import measure
import argparse
import imutils
import os
import itertools
import math
import copy
import yaml
import requests
from PIL import Image, ImageDraw, ImageFont
import io
import time

with open("config/detection.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile)

def same(person, other):
    for dog in other:
        deviation = 0
        deviation += abs((dog["x_min"]-person["x_min"]) + (dog["x_max"]-person["x_max"]))
        deviation += abs((dog["y_min"]-person["y_min"]) + (dog["y_max"]-person["y_max"]))
        if deviation < 30:
            return True
    return False

def cropObj(object, sf):
    c = calculateCrop(object, sf)
    return {"x_min":c[0], "x_max":c[2], "y_min":c[1], "y_max":c[3]}

def center(object):
    x = (int(object["x_max"]) - int(object["x_min"]))/2
    y = (int(object["y_max"]) - int(object["y_min"]))/2
    return tuple((x, y))

def calculateCrop(object, sf):
    y_max = int(object["y_max"]) + sf
    if y_max > height:
        y_max = height
    y_min = int(object["y_min"]) - sf
    if y_min < 0:
        y_min = 0
    x_max = int(object["x_max"]) + sf
    if x_max > width:
        x_max = width
    x_min = int(object["x_min"]) - sf
    if x_min < 0:
        x_min = 0
    return [x_min,y_min,x_max,y_max]

def crop(image, object, sf):
    values = calculateCrop(object, sf)
    return image.crop((values[0],values[1],values[2],values[3]))

def take_id(elem):
    return elem["id"]

def take_second(elem):
    return elem[1]

def distance(x, y):
    if "placeholder" in x or "placeholder" in y:
        return 0
    dist = math.sqrt((x["center"][0]-y["center"][0])**2 + (x["center"][1]-y["center"][1])**2)
    if dist > 300:
        return 1000
    return dist

def different(choices):
    arr = sorted(choices)
    prev = -1
    for key in arr:
        if key == prev:
            return key
        prev = key
    return -1

def calculate_min_comb(existing_objects, new_objects):
    pointer = []
    for i, new_obj in enumerate(new_objects):
        pointer.append([])
        for j, old_obj in enumerate(existing_objects):
            pointer[i].append((distance(new_obj, old_obj), j))
        pointer[i].sort(key=take_second)
    choices = [o[0][1] for o in pointer]
    flag = different(choices)
    while flag != -1:
        min_index = [0,0]
        min_cost = 10000000
        for i,c in enumerate(choices):
            if flag == c:
                index = [ x[1] for x in pointer[i] ].index(flag)
                if index < len(pointer[i])-1:
                    if pointer[i][index + 1][0] - pointer[i][index][0] < min_cost:
                        min_cost = pointer[i][index + 1][0] - pointer[i][index][0]
                        min_index[0] = i
                        min_index[1] = index + 1
        if min_cost == 10000000:
            raise Exception("No possible choice for different previous id's")
        choices[min_index[0]] = pointer[min_index[0]][min_index[1]][1]
        flag = different(choices)
    return choices

def calculatePos(object, size):
    x_min = size["x_min"] + object["x_min"]
    y_min = size["y_min"] + object["y_min"]
    x_max = size["x_min"] + object["x_max"]
    y_max = size["y_min"] + object["y_max"]
    return int(x_min), int(y_min), int(x_max), int(y_max)

def RGB(colour):
    return colour[::-1]

class Tracker:
    objects = []

    def label(self, image):
        for o in self.objects:
            image = cv2.putText(image, str(o["id"]), o["center"], cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2, cv2.LINE_AA) 

    def replace(self, object, index):
        new_id = 0
        temp = sorted(self.objects, key=take_id)
        for o in temp:
            if o["id"] < 0:
                continue
            if new_id != o["id"]:
                break
            new_id += 1
        object["id"] = new_id
        self.objects[index] = object

    def track(self, objs):
        if len(self.objects) > 0:
            self.objects.sort(key=take_id)
        if len(self.objects) > len(objs):
            for i in range(len(self.objects) - len(objs)):
                objs.append({"placeholder":True, "id":-(i+1)})
        elif len(self.objects) < len(objs):
            for i in range(len(objs) - len(self.objects)):
                self.objects.append({"placeholder":True, "id":-(i+1)})
        comb = calculate_min_comb(self.objects, objs)
        for index, key in enumerate(comb):
            if "placeholder" in objs[index]:
                self.objects.remove(self.objects[key])
            elif "placeholder" in self.objects[key]:
                self.replace(objs[index], key)
            else:
                objs[index]["id"] = self.objects[key]["id"]
                self.objects[key] = objs[index]
    
    def get_max(self):
        x_min = 10000
        y_min = 10000
        x_max = 0
        y_max = 0
        for o in self.objects:
            if x_min > o["x_min"]:
                x_min = o["x_min"]
            if y_min > o["y_min"]:
                y_min = o["y_min"]
            if x_max < o["x_max"]:
                x_max = o["x_max"]
            if y_max < o["y_max"]:
                y_max = o["y_max"]
        return {"x_min":x_min, "x_max":x_max, "y_min":y_min, "y_max":y_max,}

        

file_name = input("File In Videos To Read From: ")

try: 
    if not os.path.exists(f'media/out/{file_name}'): 
        os.makedirs(f'media/out/{file_name}') 
except OSError: 
    print ('Error: Creating directory for out')

cap = cv2.VideoCapture(f'media/videos/{file_name}.mp4')

fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

tracker = Tracker()

index = 0
photo_index = 0
while(1):
    ret, frame = cap.read()
    # cv2.imwrite(f'media/out/1_3/clean{index}.jpg',frame)

    if ret == False:
        break

    if index % 3 == 0:
        fgmask = fgbg.apply(frame)
        

    #print(type(fgmask))

    if index % 15 == 0:
        image = copy.deepcopy(frame)
        width = image.shape[1]
        height = image.shape[0]
        print(".")
        ret1,fgmask = cv2.threshold(fgmask,240,255,cv2.THRESH_BINARY)
        fgmask = cv2.erode(fgmask, None, iterations=2)
        #blur = cv2.GaussianBlur(fgmask,(5,5),0)
        #blur = cv2.blur(fgmask,(10,10))
        #ret2,mask = cv2.threshold(blur,255,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
        # fgmask = cv2.dilate(fgmask, None, iterations=1)

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
        masked_data = cv2.bitwise_and(frame, frame, mask=mask)
        #cv2.imwrite(f'media/out/1_3/masked{photo_index}.jpg',masked_data)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        if len(cnts) == 0:
            index += 1
            continue
        cnts = contours.sort_contours(cnts)[0]

        objects = []
        for i, c in enumerate(cnts):
            M = cv2.moments(c)
            cX = int(M["m10"] / M["m00"])
            cY = int(M["m01"] / M["m00"])
            (x, y, w, h) = cv2.boundingRect(c)
            objects.append({"center":(cX,cY), "x_min":x, "y_min":y, "x_max":x+w, "y_max":y+h})
            mask = cv2.rectangle(mask, (x,y), (x+w,y+h), (255,255,255), 3)
            masked_data = cv2.rectangle(masked_data, (x,y), (x+w,y+h), (255,255,255), 3)
        tracker.track(copy.deepcopy(objects))
        #tracker.label(masked_data)

        size = tracker.get_max()

        tracker.label(image)
        crop_arr = calculateCrop(size, cfg["crop"]["size"])
        crop_obj = cropObj(size, cfg["crop"]["size"])
        image = cv2.rectangle(image, (int(crop_arr[0]),int(crop_arr[1])), (int(crop_arr[2]),int(crop_arr[3])), RGB((51,73,255)), 2)


        image = Image.fromarray(image)
        
        img_crop = crop(image, size, cfg["crop"]["size"])

        img_byte_arr = io.BytesIO()
        img_crop.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        tic = time.perf_counter()
        answer = requests.post(cfg["ai_api"]["path"],files={"image":img_byte_arr},data={"min_confidence":cfg["ai_api"]["confidence"]}).json()
        toc = time.perf_counter()
        print(f"Api call for {photo_index} was done in {toc - tic:0.4f} seconds")

        image = np.array(image)
        other = [o for o in answer["predictions"] if o["label"] != "person"]
        for object in answer["predictions"]:
            if object["label"] == "person":
                if same(object, other):
                    continue
                x_min, y_min, x_max, y_max = calculatePos(object, crop_obj)
                if object["confidence"] < 0.55:
                    colour = (18,217,0)
                elif object["confidence"] < 0.75:
                    colour = (255,247,0)
                elif object["confidence"] < cfg["trigger"]["single_frame"]:
                    colour = (252,181,0)
                else:
                    colour = (255,0,0)
                image = cv2.rectangle(image, (x_min,y_min), (x_max,y_max), RGB(colour), 2)
            elif object["label"] == "dog":
                x_min, y_min, x_max, y_max = calculatePos(object, crop_obj)
                image = cv2.rectangle(image, (x_min,y_min), (x_max,y_max), RGB((255,51,252)), 2)

        cv2.imwrite(f'media/out/{file_name}/labeled{photo_index}.jpg',image)
        #cv2.imwrite(f'media/out/1_3/masked{photo_index}.jpg',masked_data)
        #cv2.imwrite(f'media/out/1_3/{photo_index}.jpg',mask)
        photo_index += 1
    index += 1
    # k = cv2.waitKey(30) & 0xff
    # if k == 27:
    #     break

cap.release()
