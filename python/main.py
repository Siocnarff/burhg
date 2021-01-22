# import requests

# image_data = open("images/8.jpg","rb").read()

# response = requests.post("http://localhost:81/v1/vision/detection",files={"image":image_data}).json()

# for object in response["predictions"]:
#     print(object["label"])

# print(response)

import requests
from PIL import Image
import io
import math

def center(object):
    x = (int(object["x_max"]) - int(object["x_min"]))/2
    y = (int(object["y_max"]) - int(object["y_min"]))/2
    return tuple((x, y))

def centerabs(object):
    c = center(object)
    return tuple((c[0] + object["x_min"], c[1] + object["y_min"]))

def crop(image, object, sf):
    c = center(object)
    y_max = int(object["y_max"]) + c[1]*sf
    if y_max > height:
        y_max = height
    y_min = int(object["y_min"]) - c[1]*sf
    if y_min < 0:
        y_min = 0
    x_max = int(object["x_max"]) + c[0]*sf
    if x_max > width:
        x_max = width
    x_min = int(object["x_min"]) - c[0]*sf
    if x_min < 0:
        x_min = 0

    return image.crop((x_min,y_min,x_max,y_max))

def distance(one, two):
    return math.sqrt((one[0]-two[0])**2 + (one[1]-two[1])**2)

def recheck(image):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    answer = requests.post("http://localhost:81/v1/vision/detection",files={"image":img_byte_arr},data={"min_confidence":0.80}).json()

    print("Detailed check:")
    print(answer)
    print("-------------------------")
    i = 0
    for object in answer["predictions"]:
        label = object["label"]
        cropped = crop(image, object, 0)
        cropped.save("1image{}_{}.jpg".format(i,label))
        i += 1


def findBunch(arr, current, objects, i, dist):
    arr[current] = i
    index = 0
    for o in objects:
        if arr[index] == 0 and distance(centerabs(o), centerabs(objects[current])) < dist:
            findBunch(arr, index, objects, i , dist)
        index += 1

def update(current, new):
    if current["x_min"] > new["x_min"]:
        current["x_min"] = new["x_min"]
    if current["y_min"] > new["y_min"]:
        current["y_min"] = new["y_min"]
    if current["x_max"] < new["x_max"]:
        current["x_max"] = new["x_max"]
    if current["y_max"] < new["y_max"]:
        current["y_max"] = new["y_max"]
    current["label"] = new["label"]

a = "153"
#"fotos/IMG_20210121_081" + a + ".jpg"
image_data = open("special/falseDog.jpg","rb").read()
print(type(image_data))
image = Image.open("special/falseDog.jpg").convert("RGB")

width = image.width
height = image.height

response = requests.post("http://localhost:81/v1/vision/detection",files={"image":image_data},data={"min_confidence":0.60}).json()

#loners = response["predictions"]

setIndex = []
for object in response["predictions"]:
    setIndex.append(0)

index = 1
for i in range(len(setIndex)):
    if setIndex[i] == 0:
        findBunch(setIndex, i, response["predictions"], index, 200)
        index += 1

print(setIndex)

objects = []

for i in range(1, index):
    objects.append({"x_min":1000000, "x_max":0, "y_min":1000000, "y_max":0, "loner":True, "label":""})
    bunch = False
    for pos, key in enumerate(setIndex):
        if key == i:
            if bunch == True:
                objects[i-1]["loner"] = False
            update(objects[i-1], response["predictions"][pos]);
            bunch = True

print(objects)

i = 0
for object in objects:
    label = object["label"]
    print(label)
    if label == "person" or not(object["loner"]):
        recheck(crop(image, object, 0.5))
    cropped = crop(image, object, 0.5)
    cropped.save("0image{}_{}.jpg".format(i,label))
    i += 1

#print(response)