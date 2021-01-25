import reread as rr
import os

class FrameManager:
    

folder = input("Folder In data To Read From: ")

try: 
    if not os.path.exists(f'media/out/{folder}'): 
        os.makedirs(f'media/out/{folder}') 
except OSError: 
    print ('Error: Creating directory for out')

fileName = 0
while rr.analyzeFrame("media/data/" + folder + "/", str(fileName) + ".jpg", "media/out/" + folder + "/"):
    fileName += 1