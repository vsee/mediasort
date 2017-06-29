#!/usr/bin/python

import sys

import shutil

from os import system, walk, makedirs
from os.path import isfile, join, isdir, splitext, dirname, basename

KNOWN_EXTS={"amr":"a","m4a":"a","aac":"a","3gp":"v","mp4":"v","MOV":"v",
            "png":"i","JPG":"i","gif":"i","jpg":"i","jpeg":"i"}

srcPath = sys.argv[1]
destPath = sys.argv[2]

endings = dict()

videos = list()
audio = list()

for (dirpath, dirnames, filenames) in walk(srcPath):
  for name in filenames:
    ext = splitext(name)[1][1:]
    if(ext in KNOWN_EXTS):
      if(KNOWN_EXTS[ext] == "v"):
        videos.append(join(dirpath,name))
      elif(KNOWN_EXTS[ext] == "a"):
        audio.append(join(dirpath,name))
      elif(KNOWN_EXTS[ext] == "i"):
        pass
    else:
      print("WARNING: unhandled file type: " + ext)

vDest = join(destPath, "videos")
if(not isdir(vDest)): makedirs(vDest)
aDest = join(destPath, "audio")
if(not isdir(aDest)): makedirs(aDest)

def moveFiles(files, destination):

  for srcfile in files:
    dDir = join(destination, dirname(srcfile))
    if(not isdir(dDir)): makedirs(dDir)
    dFile = join(dDir, basename(srcfile))
    print(srcfile + " --> " + dFile)
    if(not isfile(dFile)): shutil.move(srcfile, dFile)
    else: print("ERROR: file already exists: " + dFile)

print("####### Moving videos ...")
moveFiles(videos, vDest)
print("\n\n####### Moving audio ...")
moveFiles(audio, aDest)