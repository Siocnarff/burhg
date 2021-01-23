import requests
from PIL import Image, ImageDraw
import io
import math

def center(object):
    x = (int(object["x_max"]) - int(object["x_min"]))/2
    y = (int(object["y_max"]) - int(object["y_min"]))/2
    return tuple((x, y))

def centerabs(object):
    c = center(object)
    return tuple((c[0] + object["x_min"], c[1] + object["y_min"]))

def calculateCrop(object, sf):
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
    return [x_min,y_min,x_max,y_max]

def crop(image, object, sf):
    values = calculateCrop(object, sf)
    return image.crop((values[0],values[1],values[2],values[3]))

def cropObj(object, sf):
    c = calculateCrop(object, sf)
    return {"x_min":c[0], "x_max":c[2], "y_min":c[1], "y_max":c[3]}

def distance(one, two):
    return math.sqrt((one[0]-two[0])**2 + (one[1]-two[1])**2)

def recheck(image, size, labeledImage, out):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    answer = requests.post("http://localhost:81/v1/vision/detection",files={"image":img_byte_arr},data={"min_confidence":0.50}).json()

    print("    Detailed check:")
    print("    ---------------------")
    i = 0
    for object in answer["predictions"]:
        mark(labeledImage, object, size)
        print(f'    {object["label"]} ({object["confidence"]})')
        cropped = crop(image, object, 0)
        #cropped.save("{}1image{}_{}.jpg".format(out,i,object["label"]))
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
    if new["label"] == "person":
        current["label"] = new["label"]

def mark(labeledImage, object, size):
    x_min = size["x_min"] + object["x_min"]
    y_min = size["y_min"] + object["y_min"]
    x_max = size["x_min"] + object["x_max"]
    y_max = size["y_min"] + object["y_max"]
    shape = [(x_min, y_min), (x_max, y_max)]
    img1 = ImageDraw.Draw(labeledImage)   
    img1.rectangle(shape, fill =None, outline ="#ffff33", width =5) 
    return labeledImage



#==== Code    ===============================================================
#============================================================================

#imagePath = "fotos/special/"
#imageName = "falseDog.jpg"


def analyzeFrame(imagePath, imageName, out):

    #"fotos/IMG_20210121_081" + a + ".jpg"
    image_data = open(imagePath + imageName,"rb").read()
    image = Image.open(imagePath + imageName).convert("RGB")

    global width
    global height

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
                update(objects[i-1], response["predictions"][pos])
                bunch = True

    #print(objects)

    labeledImage = image

    print("\nGroup Checks:")
    i = 0
    for object in objects:
        label = object["label"]
        print(f'{i+1}) {label}')
        cropped = crop(image, object, 0.5)
        #cropped.save("{}0image{}_{}.jpg".format(out,i,label))

        if not(object["loner"]) and object["label"] == "person":
            recheck(cropped, cropObj(object, 0.5), labeledImage, out)
        else:
            mark(labeledImage, object, {"x_min":0, "x_max":labeledImage.width, "y_min":0, "y_max":labeledImage.height})
        i += 1

    labeledImage.save("{}labaledImage_{}".format(out,imageName))