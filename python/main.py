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
    index = 0

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

def draw(image, objects):
    for index, object in enumerate(objects):
        colour = Switch({
            range(20, 55): "#12d900",
            range(55, 75): "#fff700",
            range(75, 90): "#fcb500",
            range(90, 101): "#ff0000"
        })
        confidence = int(object["confidence"]*100)
        shape = [(object["x_min"], object["y_min"]), (object["x_max"], object["y_max"])]
        textBack = [(object["x_min"], object["y_min"] - 20),(object["x_min"] + len(str(object["confidence"]))*11, object["y_min"] - 2)]
        confidenceBack = [(object["x_min"], object["y_min"] - 40),(object["x_min"] + len(str(object["confidence"]))*11, object["y_min"] - 20)]
        img1 = ImageDraw.Draw(image)   
        font = ImageFont.truetype("arial.ttf", 22)
        font2 = ImageFont.truetype("arial.ttf", 20)
        img1.rectangle(textBack, fill="#000000", outline="#000000", width=5)
        img1.rectangle(confidenceBack, fill="#000000", outline="#000000", width=5)
        img1.text((object["x_min"], object["y_min"] - 25), "person", (255,255,255), font=font)
        img1.text((object["x_min"], object["y_min"] - 42), str(object["confidence"]), (255,255,255), font=font2)
        img1.rectangle(shape, fill =None, outline =colour[confidence], width =5) 

    

folder = input("Folder In data To Read From: ")

try: 
    if not os.path.exists(f'media/out/{folder}'): 
        os.makedirs(f'media/out/{folder}') 
except OSError: 
    print ('Error: Creating directory for out')


frameManager = FrameManager()
fileName = 0
frame = []
while rr.analyzeFrame("media/data/" + folder + "/", str(fileName) + ".jpg", "media/out/" + folder + "/", frame):
    image = Image.open("media/data/" + folder + "/" + str(fileName) + ".jpg").convert("RGB")
    frameManager.add(frame)
    draw(image, frame)
    image.save("{}labaledImage_{}".format("media/out/" + folder + "/",str(fileName) + ".jpg"))
    fileName += 1
    frame.clear()
