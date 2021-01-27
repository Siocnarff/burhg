import requests
from PIL import Image, ImageDraw, ImageFont
import io
import math
from termcolor import colored
import yaml

with open("config/detection.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile)

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

def recheck(image, size, frame):
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()

    answer = requests.post(cfg["ai_api"]["path"],files={"image":img_byte_arr},data={"min_confidence":cfg["ai_api"]["recheck_confidence"]}).json()

    print("    Detailed check:")
    print("    ---------------------")
    i = 0
    for object in answer["predictions"]:
        if object["label"] == "person":
            x_min, y_min, x_max, y_max = calculatePos(object, size)
            frame.append({"center":centerabs({"x_min":x_min, "x_max":x_max, "y_min":y_min, "y_max":y_max,}), "x_min":x_min, "x_max":x_max, "y_min":y_min, "y_max":y_max, "confidence":object["confidence"]})
        # if object["label"] == "person" and object["confidence"] > cfg["trigger"]["single_frame"]:
        #     colour = "#ff0000"
        # else:
        #     colour = "#ffff33"
        # mark(labeledImage, object, size, object["label"], colour)
        print(f'    {object["label"]} ({object["confidence"]})')
        i += 1
    print("    ---------------------")
   

def findBunch(arr, current, objects, i, bunch=False):
    dist = cfg["bunch"]["max_gap"]
    arr[current] = i
    index = 0
    for o in objects:
        if arr[index] == 0 \
        and distance(centerabs(o), centerabs(objects[current])) < dist \
        and distance(centerabs(o), centerabs(objects[current])) > cfg["bunch"]["min_gap"]:
            bunch = findBunch(arr, index, objects, i, bunch)
        index += 1
    if objects[current]["confidence"] < 0.60 and objects[current]["label"] == "person":
        bunch = True
    return bunch

def update(current, new):
    if current["x_min"] > new["x_min"]:
        current["x_min"] = new["x_min"]
    if current["y_min"] > new["y_min"]:
        current["y_min"] = new["y_min"]
    if current["x_max"] < new["x_max"]:
        current["x_max"] = new["x_max"]
    if current["y_max"] < new["y_max"]:
        current["y_max"] = new["y_max"]
    if new["label"] == "person" or current["label"] == "":
        current["label"] = new["label"]
        if new["confidence"] < current["confidence"]:
            current["confidence"] = new["confidence"]

def calculatePos(object, size):
    x_min = size["x_min"] + object["x_min"]
    y_min = size["y_min"] + object["y_min"]
    x_max = size["x_min"] + object["x_max"]
    y_max = size["y_min"] + object["y_max"]
    return x_min, y_min, x_max, y_max

# def mark(labeledImage, object, size, label, colour):
#     x_min, y_min, x_max, y_max = calculatePos(object, size)
#     shape = [(x_min, y_min), (x_max, y_max)]
#     textBack = [(x_min, y_min - 20),(x_min + len(label)*11, y_min - 2)]
#     confidenceBack = [(x_min, y_min - 40),(x_min + len(str(object["confidence"]))*11, y_min - 20)]
#     img1 = ImageDraw.Draw(labeledImage)   
#     font = ImageFont.truetype("arial.ttf", 22)
#     font2 = ImageFont.truetype("arial.ttf", 20)
#     img1.rectangle(textBack, fill="#000000", outline="#000000", width=5)
#     img1.rectangle(confidenceBack, fill="#000000", outline="#000000", width=5)
#     img1.text((x_min, y_min - 25), label, (255,255,255), font=font)
#     img1.text((x_min, y_min - 42), str(object["confidence"]), (255,255,255), font=font2)
#     img1.rectangle(shape, fill =None, outline =colour, width =5) 
#     return labeledImage



#==== Code    ===============================================================
#============================================================================

#imagePath = "fotos/special/"
#imageName = "falseDog.jpg"


def analyzeFrame(imagePath, imageName, frame):

    #"fotos/IMG_20210121_081" + a + ".jpg"
    error_to_catch = getattr(__builtins__,'FileNotFoundError', IOError)

    try:
        image_data = open(imagePath + imageName,"rb").read()
    except error_to_catch:
        return False
    
    image = Image.open(imagePath + imageName).convert("RGB")

    global width
    global height

    width = image.width
    height = image.height

    response = requests.post(cfg["ai_api"]["path"],files={"image":image_data},data={"min_confidence":cfg["ai_api"]["confidence"]}).json()

    print(colored(f"{imageName}  Inital Predictions:",'yellow'))
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
            if findBunch(setIndex, i, response["predictions"], index):
                index += 1
            else:
                bunchID = index
                for j in range(len(setIndex)):
                    if setIndex[j] == bunchID:
                        setIndex[j] = index
                        index += 1
                        
    print(colored("Groups:",'blue'))
    print(setIndex)

    objects = []

    for i in range(1, index):
        objects.append({"x_min":1000000, "x_max":0, "y_min":1000000, "y_max":0, "loner":True, "label":"", "confidence":1})
        bunch = False
        for pos, key in enumerate(setIndex):
            if key == i:
                if bunch == True:
                    objects[i-1]["loner"] = False
                update(objects[i-1], response["predictions"][pos])
                bunch = True

    # print(objects)

    # labeledImage = image

    print(colored("\nGroup Checks:",'blue'))
    i = 0
    for object in objects:
        print(f'{i+1}) {object["label"]}')
        cropped = crop(image, object, 0.5)
        #cropped.save("{}0image{}_{}.jpg".format(out,i,label))

        if not(object["loner"]) and object["label"] == "person":
            # mark(labeledImage, object, {"x_min":0, "x_max":labeledImage.width, "y_min":0, "y_max":labeledImage.height}, label, "#43eb34")
            if object["confidence"] < 0.8:
                recheck(cropped, cropObj(object, 0.5), frame)
        else:
            if object["label"] == "person":
                frame.append({"center":centerabs(object), "x_min":object["x_min"], "x_max":object["x_max"], "y_min":object["y_min"], "y_max":object["y_max"], "confidence":object["confidence"]})
            # if label == "person" and object["confidence"] > cfg["trigger"]["single_frame"]:
            #     colour = "#ff0000"
            # else:
            #     colour = "#ffff33"
            # mark(labeledImage, object, {"x_min":0, "x_max":labeledImage.width, "y_min":0, "y_max":labeledImage.height}, label, colour)
        i += 1

    # labeledImage.save("{}labaledImage_{}".format(out,imageName))
    return True