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

    print("    Detailed check:")
    print("    ---------------------")
    i = 0
    for object in answer["predictions"]:
        print(f'    {object["label"]} ({object["confidence"]})')
        cropped = crop(image, object, 0)
        cropped.save("out/1image{}_{}.jpg".format(i,object["label"]))
        i += 1
    print("    ---------------------")
   

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



#==== Code    ===============================================================
#============================================================================

a = "153"

b = "fotos/special/falseDog.jpg"
#"fotos/IMG_20210121_081" + a + ".jpg"
image_data = open(b,"rb").read()
image = Image.open(b).convert("RGB")

width = image.width
height = image.height

response = requests.post("http://localhost:81/v1/vision/detection",files={"image":image_data},data={"min_confidence":0.20}).json()

print("Inital Predictions:")
print('=========================')
for object in response["predictions"]:
    print(f'{object["label"]} ({object["confidence"]})')
print('=========================\n')


setIndex = []
for object in response["predictions"]:
    setIndex.append(0)

index = 1
for i in range(len(setIndex)):
    if setIndex[i] == 0:
        findBunch(setIndex, i, response["predictions"], index, 200)
        index += 1

print("Groups:")
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

#print(objects)

print("\nGroup Checks:")
i = 0
for object in objects:
    label = object["label"]
    print(f'{i+1}) {label}')
    cropped = crop(image, object, 0.5)
    cropped.save("out/0image{}_{}.jpg".format(i,label))
    if not(object["loner"]):
        recheck(crop(image, object, 0.5))
    i += 1