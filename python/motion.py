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
import sys
import pdb

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

def take_first(elem):
    return elem[0]

def weight(x, y):
    if "placeholder" in x or "placeholder" in y:
        return 0
    x1 = x["center"][0]-y["center"][0] - y["direction"][0]
    x2 = x["center"][1]-y["center"][1] - y["direction"][1]
    dist = math.sqrt((x1)**2 + (x2)**2)
    dist *= 5.3*(dist**0.1)
    x_shape = [x["x_max"]-x["x_min"], x["y_max"]-x["y_min"]]
    y_shape = [y["x_max"]-y["x_min"], y["y_max"]-y["y_min"]]
    x_area = x_shape[0]*x_shape[1]
    y_area = y_shape[0]*y_shape[1]
    area = abs(x_area-y_area)/50
    x_ratio = x_shape[0]/x_shape[1]
    y_ratio = y_shape[0]/y_shape[1]
    ratio = abs(x_ratio-y_ratio)*300
    # print(f"Area weight: {area}, ratio weight: {ratio}")
    dist += area + ratio
    if x["label"] == y["label"]:
        if abs(x["confidence"] - y["confidence"]) < 0.30:
            dist *= 0.6
        else:
            dist *= 0.9
    else:
        dist *= 1.25
    return dist

def different(choices):
    arr = sorted(choices)
    prev = None
    for key in arr:
        if key == -1:
            continue
        if key == prev:
            return key
        prev = key
    return None

def can_move(mover, victim):
    move_distance = 200
    diff = victim - mover
    move_distance += diff
    if move_distance < 0:
        return 0
    return move_distance


def calculate_min_comb(existing_objects, new_objects):
    # if photo_index == 69:
    #     pdb.set_trace()
    pointer = []
    if len(existing_objects) == 0:
        return [-1 for i in range(len(new_objects))]
    if len(new_objects) == 0:
        return []
    for i, new_obj in enumerate(new_objects):
        pointer.append([])
        for j, old_obj in enumerate(existing_objects):
            pointer[i].append((weight(new_obj, old_obj), j))
        pointer[i].sort(key=take_first)
    choices = [o[0][1] for o in pointer]
    # for index,w in enumerate(pointer):
    #     print("weight: ", end="")
    #     for i in w:
    #         if "label" in new_objects[index]:
    #             string = new_objects[index]["label"]
    #         else:
    #             string = "unknown"
    #         print(f"Distance from {i[1]} is {i[0]} and my label is {string}")
            # if i[0] != 0:
            #     print(i[0])
            #     print("Old id: ", end="")
            #     print(i[1])
            #     break
    flag = different(choices)

    while flag != None:
        # min_index = [0,0]
        # min_cost = 10000000
        # for i,c in enumerate(choices):
        #     if flag == c:
        #         index = [x[1] for x in pointer[i]].index(flag)
        #         if index < len(pointer[i])-1:
        #             if pointer[i][index + 1][0] - pointer[i][index][0] < min_cost:
        #                 min_cost = pointer[i][index + 1][0] - pointer[i][index][0]
        #                 min_index[0] = i
        #                 min_index[1] = index + 1
        # if min_cost == 10000000:
        #     raise Exception("No possible choice for different previous id's")
        # choices[min_index[0]] = pointer[min_index[0]][min_index[1]][1]
        best = None
        second_best = None
        for index,choice in enumerate(choices):
            if flag == choice:
                choice_index = [row[1] for row in pointer[index]].index(choice)
                if best == None:
                    best = pointer[index][choice_index][0]
                    second_best = pointer[index][choice_index][0]
                elif best > pointer[index][choice_index][0]:
                    second_best = best
                    best = pointer[index][choice_index][0]
                elif second_best > pointer[index][choice_index][0]:
                    second_best = pointer[index][choice_index][0]
        min_cost = None
        min_position = None
        for index,choice in enumerate(choices):
            if flag == choice:
                choice_index = [row[1] for row in pointer[index]].index(choice)
                if choice_index < len(pointer[index]) - 1:
                    if best != pointer[index][choice_index][0]:
                        if can_move(best, pointer[index][choice_index][0]) > pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]:
                            if min_cost == None or min_cost > pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]:
                                min_cost = pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]
                                min_position = [index, choice_index + 1]
                    else:
                        if can_move(second_best, best) > pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]:
                            if min_cost == None or min_cost > pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]:
                                min_cost = pointer[index][choice_index + 1][0] - pointer[index][choice_index][0]
                                min_position = [index, choice_index + 1]
        if min_cost == None:
            for index,choice in enumerate(choices):
                if flag == choice:
                    choice_index = [row[1] for row in pointer[index]].index(choice)
                    if best != pointer[index][choice_index][0]:
                        choices[index] = -1
        else:
            if min_cost > 8000:
                choices[min_position[0]] = -1
            else:
                choices[min_position[0]] = pointer[min_position[0]][min_position[1]][1]

        flag = different(choices)
    
    for index,choice in enumerate(choices):
        if choice == -1:
            continue
        choice_index = [row[1] for row in pointer[index]].index(choice)
        if pointer[index][choice_index][0] > 8000:
            choices[index] = -1

    # for loop in range(int(len(choices)/2)):
    #     for first, id in enumerate(choices):
    #         for second in range(first+1,len(choices)):
    #             index = [x[1] for x in pointer[first]].index(id)
    #             index_2 = [x[1] for x in pointer[second]].index(choices[second])
    #             current_weight = pointer[first][index][0] + pointer[second][index_2][0]
    #             index = [x[1] for x in pointer[first]].index(choices[second])
    #             index_2 = [x[1] for x in pointer[second]].index(id)
    #             swopped_weight = pointer[first][index][0] + pointer[second][index_2][0]
    #             if current_weight > swopped_weight:
    #                 # print("Array is: ", end="")
    #                 # print(choices)
    #                 # print(f"Swopping {first} with {second}")
    #                 temp = choices[first]
    #                 choices[first] = choices[second]
    #                 choices[second] = temp
    #                 print("Array is: ", end="")
    #                 print(choices)
    # print("==================")
    return choices

def calculatePos(object, size):
    x_min = size["x_min"] + object["x_min"]
    y_min = size["y_min"] + object["y_min"]
    x_max = size["x_min"] + object["x_max"]
    y_max = size["y_min"] + object["y_max"]
    return int(x_min), int(y_min), int(x_max), int(y_max)

def check_match(existing, new, comb):
    # flag = -1
    # og_weight = 0
    # # print("Old: ", end="")
    # # print(existing)
    # # print("New: ", end="")
    # # print(new)
    # for index,key in enumerate(comb):
    #     og_weight += weight(new[index],existing[key])
    # # print("og_weight: ", end="")
    # # print(og_weight)
    # temp = existing
    # difference = 0
    # best_comb = comb
    # for index,obj in enumerate(existing):
    #     temp[index] = {"placeholder":True, "id":-1}
    #     combination = calculate_min_comb(existing, new)
    #     new_weight = 0
    #     for index,key in enumerate(combination):
    #         new_weight += weight(new[index],existing[key])
    #     # print("New weight: ", end="")
    #     # print(new_weight)
    #     print("Difference: ", end="")
    #     print(difference)
    #     if og_weight - new_weight > difference:
    #         difference = og_weight - new_weight
    #         if difference > 3000:
    #             print("Difference is big!!")
    #             best_comb = combination
    #             flag = index
    #     temp[index] = obj
    return flag, best_comb
    





def RGB(colour):
    return colour[::-1]

class Tracker:
    objects = []
    inside = 0

    def label(self, image):
        # if photo_index == 334 or photo_index == 147 or photo_index == 148:
        # print("Objects in tracker: ")
        # for o in self.objects:
        #     print(o)
        # print("-------------")
        string = "In: " + str(self.inside)
        image = cv2.putText(image, string, (10,30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2, cv2.LINE_AA) 
        for o in self.objects:
            c_x = o["center"][0]
            c_y = o["center"][1]
            if o["history"] == 0:
                colour = (255,0,0)
            else:
                colour = (255,255,255)
            image = cv2.putText(image, str(o["id"]), (c_x-10,c_y), cv2.FONT_HERSHEY_SIMPLEX, 1, colour, 2, cv2.LINE_AA) 
        for object in self.objects:
            if object["label"] == "person":
                if object["confidence"] < 0.55:
                    colour = (18,217,0)
                elif object["confidence"] < 0.75:
                    colour = (255,247,0)
                elif object["confidence"] < cfg["trigger"]["single_frame"]:
                    colour = (252,181,0)
                else:
                    colour = (255,0,0)
                image = cv2.rectangle(image, (object["x_min"], object["y_min"]), (object["x_max"], object["y_max"]), RGB(colour), 2)
            elif object["label"] == "dog":
                image = cv2.rectangle(image, (object["x_min"], object["y_min"]), (object["x_max"], object["y_max"]), RGB((255,51,252)), 2)

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
    
    def add(self, object):
        new_id = 0
        temp = sorted(self.objects, key=take_id)
        for o in temp:
            if o["id"] < 0:
                continue
            if new_id != o["id"]:
                break
            new_id += 1
        object["id"] = new_id
        object["direction"] = [0,0]
        self.objects.append(object)

    def track(self, objs):
        if len(self.objects) > 0:
            self.objects.sort(key=take_id)
        comb = calculate_min_comb(self.objects, objs)
        print("comb: ", end="")
        print(comb)
        # flag = False
        # for o in self.objects:
        #     if "placeholder" in o:
        #         flag = True
        # for o in objs:
        #     if "placeholder" in o:
        #         flag = True
        # if not flag:
        #     ret,combination = check_match(copy.deepcopy(self.objects), copy.deepcopy(objs), comb)
        #     # print("Current comb: ", end="")
        #     # print(comb)
        #     # print("New combination: ", end="")
        #     # print(combination)
        #     if ret != -1:
        #         self.objects[ret] = {"placeholder":True, "id":-1}
        #         comb = combination
        to_remove = []
        # flag = False
        # for choice in comb:
        #     if choice == -1:
        #         flag = True
        #         break
        # if photo_index == 55:
        #     pdb.set_trace()
        history_indices = [index for index,obj in enumerate(self.objects) if index not in comb]
        for index,key in enumerate(history_indices):
            if self.objects[key]["history"] == 1:
                to_remove.append(self.objects[key]["id"])
            else:
                self.objects[key]["history"] += 1
                self.objects[key]["center"][0] += self.objects[key]["direction"][0]
                self.objects[key]["center"][1] += self.objects[key]["direction"][1]
        for index, key in enumerate(comb):
            if key == -1:
                self.add(objs[index])
            else:
                objs[index]["id"] = self.objects[key]["id"]
                delta_x = objs[index]["center"][0] - self.objects[key]["center"][0]
                delta_y = objs[index]["center"][1] - self.objects[key]["center"][1]
                objs[index]["direction"] = [delta_x, delta_y]
                area = (objs[index]["x_max"] - objs[index]["x_min"]) * (objs[index]["y_max"] - objs[index]["y_min"])
                if cv2.pointPolygonTest(contour, tuple(objs[index]["center"]), False) == -1 and objs[index]["label"] == "person" and area > 20000:
                    if cv2.pointPolygonTest(contour, tuple(self.objects[key]["center"]), False) == 1 and self.objects[key]["history"] == 0:
                        c = (self.objects[key]["center"][0], self.objects[key]["center"][1])
                    else:
                        if not "out" in self.objects[key]:
                            c = (self.objects[key]["center"][0]-delta_x*0.4, self.objects[key]["center"][1]-delta_y*0.4)
                        else:
                            c = (self.objects[key]["center"][0], self.objects[key]["center"][1])
                            del self.objects[key]["out"]
                    if cv2.pointPolygonTest(contour, c, False) == 1:
                        objs[index]["out"] = True
                        self.inside -= 1
                if "in" in self.objects[key]:
                    objs[index]["in"] = self.objects[key]["in"]
                if self.objects[key]["label"] == objs[index]["label"]:
                    print("This is true!!")
                    print("Original confidence: ", end="")
                    print(self.objects[index]["confidence"])
                    objs[index]["confidence"] = min(1, objs[index]["confidence"] + self.objects[key]["confidence"])
                self.objects[key] = objs[index]
                self.objects[key]["history"] = 0

        for obj in self.objects:
            area = (obj["x_max"] - obj["x_min"]) * (obj["y_max"] - obj["y_min"])
            if obj["history"] == 1:
                if cv2.pointPolygonTest(contour, tuple(obj["center"]), False) == 1 and obj["direction"][0] < 0 and area > 20000 and (not "in" in obj):
                    self.inside += 1
                if "in" in obj:
                    del obj["in"]
                to_remove.append(obj["id"])
            else:
                if cv2.pointPolygonTest(contour, tuple(obj["center"]), False) == 1 and obj["direction"][0] < 0 and area > 20000 and (not "in" in obj):
                    id = obj["id"]
                    print(f"Obj is inside and left and big and in is not in obj, inside is {self.inside} and object has id {id}")
                    obj["in"] = True
                    self.inside += 1

            # if not "placeholder" in self.objects[key]:
            #     if self.objects[key]["history"] == 1:
            #         c = (self.objects[key]["center"][0] - self.objects[key]["direction"][0], self.objects[key]["center"][1])
            #         print("Center of point is: ", end="")
            #         print(c)
            #         print("Inside? ", end="")
            #         print(cv2.pointPolygonTest(contour, c, False) == 1)
            #         if cv2.pointPolygonTest(contour, c, False) == 1 and self.objects[key]["direction"][0] < 0  and self.objects[key]["label"] == "person":
            #             self.inside += 1
            # elif "placeholder" in objs[index]:
            #     if self.objects[key]["history"] == 1:
            #         to_remove.append(self.objects[key])
            #     self.objects[key]["history"] += 1
            #     self.objects[key]["center"][0] += self.objects[key]["direction"][0]
            #     self.objects[key]["center"][1] += self.objects[key]["direction"][1]
            # elif "placeholder" in self.objects[key]:
            #     objs[index]["direction"] = [0,0]
            #     self.replace(objs[index], key)
            # else:
            #     objs[index]["id"] = self.objects[key]["id"]
            #     delta_x = objs[index]["center"][0] - self.objects[key]["center"][0]
            #     delta_y = objs[index]["center"][1] - self.objects[key]["center"][1]
            #     objs[index]["direction"] = [delta_x, delta_y]
            #     if cv2.pointPolygonTest(contour, tuple(objs[index]["center"]), False) == -1 and objs[index]["label"] == "person":
            #         if cv2.pointPolygonTest(contour, tuple(self.objects[key]["center"]), False) == 1:
            #             c = (self.objects[key]["center"][0], self.objects[key]["center"][1])
            #         else:
            #             c = (self.objects[key]["center"][0]-delta_x*0.3, self.objects[key]["center"][1]-delta_y*0.3)
            #         if cv2.pointPolygonTest(contour, c, False) == 1:
            #             self.inside -= 1
            #     self.objects[key] = objs[index]
            #     self.objects[key]["history"] = 0
        objects_to_remove = [obj for obj in self.objects if obj["id"] in to_remove]
        for obj in objects_to_remove:
            self.objects.remove(obj)
    
    def get_max(self, extra_obj):
        x_min = width
        y_min = height
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
        for o in extra_obj:
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

cap = cv2.VideoCapture(f'media/videos/{file_name}.avi')
print("Cap is opened? ", end="")
print(cap.isOpened())

fgbg = cv2.createBackgroundSubtractorMOG2(detectShadows=True)

tracker = Tracker()
tracker.inside = int(input("How many people are in the house? "))

background_mask = cv2.imread(f'media/videos/{file_name}mask.jpg', cv2.IMREAD_GRAYSCALE)
entrance = cv2.imread(f'media/videos/{file_name}door.jpg', cv2.IMREAD_GRAYSCALE)

entrance_labels = measure.label(entrance, background=0)
entrance_mask = np.zeros(entrance.shape, dtype="uint8")
for entrance_label in np.unique(entrance_labels):
    if entrance_label == 0:
        continue
    label_mask = np.zeros(entrance.shape, dtype="uint8")
    label_mask[entrance_labels == entrance_label] = 255
    numPixels = cv2.countNonZero(label_mask)
    if numPixels > 500:
        entrance_mask = cv2.add(entrance_mask, label_mask)
    
contour = cv2.findContours(entrance_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
contour = imutils.grab_contours(contour)
contour = contours.sort_contours(contour)[0]
contour = contour[0]
#print(cv2.pointPolygonTest(contour, (100,500), False))


index = 0
photo_index = 0
while(1):
    ret, frame = cap.read()
    #print(f"Video was read correctly? {ret}")
    #cv2.imwrite(f'media/out/{file_name}/clean{index}.jpg',frame)

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
        fgmask = cv2.bitwise_and(fgmask, background_mask)
        #cv2.imwrite(f'media/out/{file_name}/masked{photo_index}.jpg',fgmask)
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
        #cv2.imwrite(f'media/out/{file_name}/masked{photo_index}.jpg',masked_data)
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
        # tracker.track(copy.deepcopy(objects))
        # tracker.label(masked_data)

        size = tracker.get_max(objects)

        
        crop_arr = calculateCrop(size, cfg["crop"]["size"])
        crop_obj = cropObj(size, cfg["crop"]["size"])
        image = cv2.rectangle(image, (int(crop_arr[0]),int(crop_arr[1])), (int(crop_arr[2]),int(crop_arr[3])), RGB((51,73,255)), 2)


        image = Image.fromarray(image)
        
        img_crop = crop(image, size, cfg["crop"]["size"])

        img_byte_arr = io.BytesIO()
        img_crop.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()


        try:
            tic = time.perf_counter()
            answer = requests.post(cfg["ai_api"]["path"],files={"image":img_byte_arr},data={"min_confidence":cfg["ai_api"]["confidence"]}).json()
            toc = time.perf_counter()
            print(f"Api call for {photo_index} was done in {toc - tic:0.4f} seconds")
        except:
            sys.exit("Restart Api")

        image = np.array(image)
        other = [o for o in answer["predictions"] if o["label"] != "person"]
        persons = [o for o in answer["predictions"] if o["label"] == "person"]
        ai_obs = []
        for object in answer["predictions"]:
            if object["label"] == "person":
                if object["confidence"] < 0.5 and same(object, other):
                    continue
                x_min, y_min, x_max, y_max = calculatePos(object, crop_obj)
                c_x = int(x_min + (x_max-x_min)/2)
                c_y = int(y_min + (y_max-y_min)/2)
                ai_obs.append({"center":[c_x,c_y], "x_min":x_min, "y_min":y_min, "x_max":x_max, "y_max":y_max, "label":object["label"], "confidence":object["confidence"], "history":0})
                if object["confidence"] < 0.55:
                    colour = (18,217,0)
                elif object["confidence"] < 0.75:
                    colour = (255,247,0)
                elif object["confidence"] < cfg["trigger"]["single_frame"]:
                    colour = (252,181,0)
                else:
                    colour = (255,0,0)
                # image = cv2.rectangle(image, (x_min,y_min), (x_max,y_max), RGB(colour), 2)
            elif object["label"] == "dog":
                if same(object, persons):
                    continue
                x_min, y_min, x_max, y_max = calculatePos(object, crop_obj)
                c_x = int(x_min + (x_max-x_min)/2)
                c_y = int(y_min + (y_max-y_min)/2)
                ai_obs.append({"center":[c_x,c_y], "x_min":x_min, "y_min":y_min, "x_max":x_max, "y_max":y_max, "label":"dog", "confidence":object["confidence"], "history":0})
                # image = cv2.rectangle(image, (x_min,y_min), (x_max,y_max), RGB((255,51,252)), 2)
        
        tracker.track(copy.deepcopy(ai_obs))
        tracker.label(image)


        cv2.imwrite(f'media/out/{file_name}/labeled{photo_index}.jpg',image)
        #cv2.imwrite(f'media/out/1_3/masked{photo_index}.jpg',masked_data)
        #cv2.imwrite(f'media/out/1_3/{photo_index}.jpg',mask)
        photo_index += 1
    index += 1
    # k = cv2.waitKey(30) & 0xff
    # if k == 27:
    #     break

cap.release()
