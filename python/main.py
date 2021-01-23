import reread as rr
import os

folder = input("Folder In data To Read From: ")

try: 
    if not os.path.exists(f'out/{folder}'): 
        os.makedirs(f'out/{folder}') 
except OSError: 
    print ('Error: Creating directory for out')

fileName = 0
while rr.analyzeFrame("data/" + folder + "/", str(fileName) + ".jpg", "out/" + folder + "/"):
    fileName += 1