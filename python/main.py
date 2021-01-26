import reread as rr
import os
import yaml
from PIL import Image, ImageDraw, ImageFont

with open("config/detection.yml", "r") as ymlfile:
    cfg = yaml.load(ymlfile)

class Switch(dict):
    def __getitem__(self, item):
        for key in self.keys():                   # iterate over the intervals
            if item in key:                       # if the argument is part of that interval
                return super().__getitem__(key)   # return its associated value
        raise KeyError(item)                      # if not in any interval, raise KeyError

class FrameManager:
    length = cfg["time_analysis"]["length"]
    size = 0
    frames = []
    index = -1

    def __init__(self):
        for i in range(self.length):
            self.frames.append(None)
    
    def getCurrent(self):
        return self.frames[self.index]

    def add(self, frame):
        self.incrementIndex()
        self.frames[self.index] = frame
        if self.size < self.length:
            self.size += 1

    def incrementIndex(self):
        self.index += 1
        self.index %= self.length

    def checkPast(self, num):
        index = (self.index - num) % self.length
        return self.frames[index] is not None

    def getPast(self, num):
        index = (self.index - num) % self.length
        if self.frames[index] is None:
            raise Exception("No frame at current index")
        return self.frames[index]

    def setCurrent(self, frame):
        self.frames[self.index] = frame

def draw(image, objects):
    if(objects == None):
        return
    for index, object in enumerate(objects):
        colour = Switch({
            range(20, 55): "#12d900",
            range(55, 75): "#fff700",
            range(75, int(100*cfg["trigger"]["single_frame"])): "#fcb500",
            range(int(100*cfg["trigger"]["single_frame"]), 101): "#ff0000"
        })
        confidence = 0
        shape = [(object["x_min"], object["y_min"]), (object["x_max"], object["y_max"])]
        confidenceBack = [(object["x_min"], object["y_min"] - 20),(object["x_min"] + len(str(object["confidence"]))*11, object["y_min"] - 2)]
        img1 = ImageDraw.Draw(image)   
        font = ImageFont.truetype("arial.ttf", 22)
        font2 = ImageFont.truetype("arial.ttf", 20)
        img1.rectangle(confidenceBack, fill="#000000", outline="#000000", width=5)
        img1.text((object["x_min"], object["y_min"] - 22), str(object["confidence"]), (255,255,255), font=font2)
        if cfg["time_analysis"]["algo"] == 0:
            confidence = int(object["confidence"]*100)
            idBack = [(object["center"][0]-10,object["center"][1]-10),(object["center"][0]+10,object["center"][1]+10)]
            img1.rectangle(idBack, fill="#000000", outline="#000000", width=5)
            img1.text((object["center"][0]-8, object["center"][1]-12), str(object["id"]), (255,255,255), font)
        else:
            confidence = int(object["d_confidence"]*100)
            d_confidence_back = [(object["x_min"], object["y_min"] - 40),(object["x_min"] + len(str(object["d_confidence"]))*11, object["y_min"] - 20)]
            is_repeat = [(object["x_min"], object["y_min"] - 60),(object["x_min"] + len(str(object["is_repeat"]))*11, object["y_min"] - 40)]
            img1.rectangle(d_confidence_back, fill="#000000", outline="#000000", width=5)
            img1.rectangle(is_repeat, fill="#000000", outline="#000000", width=5)
            img1.text((object["x_min"], object["y_min"] - 42), str(object["d_confidence"]), (255,255,255), font=font2)
            img1.text((object["x_min"], object["y_min"] - 62), str(object["is_repeat"]), (255,255,255), font=font2)
        img1.rectangle(shape, fill =None, outline =colour[confidence], width =5) 

def takeSecond(elem):
    return elem[1]

def confidence(elem):
    return elem["confidence"]

def differs(a, b):
    m = cfg["algo1"]["min_move_gap"]
    return abs(a["center"][0] - b["center"][0]) > m or abs(a["center"][1] - b["center"][1]) > m

def is_repeat(person, frameManager):
    t = 1
    while(t < frameManager.size - 1):
        for old_person in frameManager.getPast(t):
            if not differs(person, old_person):
                old_person["matched"] = True
                person["is_repeat"] = True
                return True
        t += 1
    return False

def in_frame(person, frame):
    for other_person in frame:
        if not differs(other_person, person):
            return True
    return False

def may_use(old_person):
    return not (old_person["matched"] or old_person["is_old_repeat"])

folder = input("Folder In data To Read From: ")

try: 
    if not os.path.exists(f'media/out/{folder}'): 
        os.makedirs(f'media/out/{folder}') 
except OSError: 
    print ('Error: Creating directory for out')


frameManager = FrameManager()
fileName = 0
frame = []
while rr.analyzeFrame("media/data/" + folder + "/", str(fileName) + ".jpg", frame):
    image = Image.open("media/data/" + folder + "/" + str(fileName) + ".jpg").convert("RGB")
    
    current = sorted(frame, reverse=True, key=confidence)
    frame = []
    frameManager.add(current)

    if cfg["time_analysis"]["algo"] == 0:
        if frameManager.checkPast(1) == True:
            prev = frameManager.getPast(1)
            combination = []
            for id, person in enumerate(current):
                combination.append([])
                for prevId, prevPerson in enumerate(prev):
                    combination[id].append((prevPerson["id"], rr.distance(person["center"], prevPerson["center"])))
                if len(person) > len(prev):
                    for i in range(len(person) - len(prev)):
                        combination[id].append((-1,0))
                combination[id].sort(key=takeSecond)
                print("combination")
                print(combination[id])
        else:
            for id, person in enumerate(current):
                person["id"] = id
            frameManager.setCurrent(current)

    elif cfg["time_analysis"]["algo"] == 1:
        for person in current:
            person["matched"] = person["is_repeat"] = person["is_old_repeat"] = found = False
            person["d_confidence"] = person["confidence"]
            if is_repeat(person, frameManager):
                continue
            t = 1
            while(t < frameManager.size - 1 and not found):
                for old_person in frameManager.getPast(t):
                    if may_use(old_person) and not in_frame(old_person, current):
                        person["d_confidence"] = min(
                                person["d_confidence"] + 
                                (cfg["algo1"]["prev_frame_weight"] * old_person["d_confidence"]), 1
                            )
                        old_person["matched"] = True
                        found = True
                        break
                t += 1
        if frameManager.checkPast(1):
            for old_person in frameManager.getPast(1):
                if old_person["is_repeat"]:
                    old_person["is_old_repeat"] = True

    draw(image, current)
    image.save("{}labaledImage_{}".format("media/out/" + folder + "/",str(fileName) + ".jpg"))
    fileName += 1
