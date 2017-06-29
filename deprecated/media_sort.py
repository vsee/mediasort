#!/usr/bin/python

import time
import exifread

import sys

from os import system, walk
from os.path import isfile, join, isdir, splitext, basename

birthDay = time.strptime("2013:07:12", "%Y:%m:%d")

def getMonth(taken):
	year = taken.tm_year - birthDay.tm_year
	month = taken.tm_mon - birthDay.tm_mon
	day = None
	if (taken.tm_mday - birthDay.tm_mday < 0):
		day = 0
	else:
		day = 1

	return str(year * 12 + month + day)

def isImgEnding(name):
	return name.endswith("JPG") or \
	       name.endswith("jpg") or \
	       name.endswith("jpeg") or \
	       name.endswith("JPEG")
	       
def isVidEnding(name):
	return name.endswith("mp4") and basename(name).startswith("VID_")

def isAudioEnding(name):
	return name.endswith("aac") and basename(name).startswith("PTT-")

def getTargetPath_age(taken):
	path = str(dateTaken.tm_year) + "/"
	
	if(taken >= birthDay):
		# month_02_August
		path += "month_" + getMonth(dateTaken).zfill(2) + time.strftime("_%m%B", taken)  + "/"
	else:
		# 12_December
		path += time.strftime("%m_%B", taken) + "/"
	path += time.strftime("%m%d", taken)
	
	if(title != None):
		path += "-" + title + "/"

	return path

def getTargetPath(taken):
	year = str(dateTaken.tm_year)
	month = time.strftime("%m_%B", taken)
	day = time.strftime("%d_%a", taken)
	
	if(title != None):
		day += "-" + title

	return join(year,month,day)

def getImgDateTaken(srcFileName):
	imgFile = open(srcFileName, 'rb')
	imgTags = exifread.process_file(imgFile, details=False)

	if(imgTags.has_key("EXIF DateTimeOriginal")):
		dateStr = str(imgTags["EXIF DateTimeOriginal"])
		return time.strptime(dateStr, "%Y:%m:%d %H:%M:%S")
	elif(basename(srcFileName).startswith("IMG_")):
		#IMG_20141225_105859
		dateStr = splitext(basename(srcFileName))[0]
		return time.strptime(dateStr, "IMG_%Y%m%d_%H%M%S")
	else:
		print("no date specified " + srcFileName)
		return None
	
def getVidDateTaken(srcFileName):
	# sortme150227/nexus5/VID_20150110_174731.mp4
	
	dateStr = splitext(basename(srcFileName))[0]
	return time.strptime(dateStr, "VID_%Y%m%d_%H%M%S")

def getAudioDateTaken(srcFileName):
	# PTT-20140724-WA0001.aac
	
	dateStr = splitext(basename(srcFileName))[0]
	dateStr = dateStr.split("-")
	return time.strptime(dateStr[1], "%Y%m%d")


def print_progress(curr, end):
    progress = "Processing File: [%s]" % (str(curr) + "/" + str(end))
    sys.stdout.write(progress)
    sys.stdout.flush()

    if(curr < end - 1):
        sys.stdout.write("\b" * (len(progress)))
    else:
        sys.stdout.write("\n")

# ------------------------------------------------------------------------------

if(len(sys.argv) < 2):
	raise RuntimeError("Invalid arguments. Expected: ./image_sort.py <src_folder> (<title>)")

imgPath = sys.argv[1]

title = None
if(len(sys.argv) >= 3):
	title = sys.argv[2]

sourceFiles = []

# recursively collect all file names from given folder
for (dirpath, dirnames, filenames) in walk(imgPath):
	sourceFiles.extend(join(dirpath, filename) for filename in filenames)

skipped = 0
unsorted = list()
for srcFileIdx in range(len(sourceFiles)):
	srcFileName = sourceFiles[srcFileIdx]
	print_progress(srcFileIdx, len(sourceFiles))
	
	dateTaken = None
	prefix = None
	
	if(isImgEnding(srcFileName)):
		prefix = "pics"
		dateTaken = getImgDateTaken(srcFileName)
	elif(isVidEnding(srcFileName)):
		prefix = "vid"
		dateTaken = getVidDateTaken(srcFileName)
	elif(isAudioEnding(srcFileName)):
		prefix = "audio"
		dateTaken = getAudioDateTaken(srcFileName)
	else:
		print("unknown file type " + srcFileName)
		
	if(dateTaken == None):
		skipped += 1
		unsorted.append(srcFileName)
		continue
	
	targetName = prefix + "_" + time.strftime("%Y%m%d_%H%M%S", dateTaken)
	targetExt = splitext(srcFileName)[1]
	targetPath = getTargetPath(dateTaken)
	targetFinal = join(targetPath, targetName + targetExt)

	counter = 1
	while(isfile(targetFinal) and counter < 100):
		targetFinal = join(targetPath, 
						   targetName + "_" + str(counter).zfill(2) + targetExt)
		counter += 1

	if(isfile(targetFinal)):
		print("target file name duplicate. gave up after " + str(counter) + " tries: " + srcFileName)
		skipped += 1
		unsorted.append(srcFileName)
		continue

	if(not isdir(targetPath)): system("mkdir -p " + targetPath)
	system("cp -i \"" + srcFileName + "\" " + targetFinal)

if(skipped > 0):
	print("Copying unsorted files...")
	
	if(not isdir("unsorted")): system("mkdir -p unsorted")
	
	for srcFileName in unsorted:   
		system("cp -i \"" + srcFileName + "\" unsorted")

print("DONE -- " + str(len(sourceFiles) - skipped) + " sorted - " + str(skipped) + " skipped") 
