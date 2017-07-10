#!/opt/anaconda3/bin/python

import sys
import time
import os

from enum import Enum, unique, auto
import mimetypes

from glob import glob
import exifread
import shutil

import argparse
import pprint

CAMERADIR="/sdcard/DCIM/Camera"
WHATSAPPDIR="/sdcard/WhatsApp/Media/WhatsApp\ Voice\ Notes"

# TODO check if device is connected and readble
def pullMedia(targetDir, srcDir):
    print("\n############ Pulling media files from directory: " + srcDir)
    os.system("adb pull " + srcDir + " " + targetDir)

def convertOpusAudio(targetDir):
    print("\n############ Converting opus audio files to mp3 ...")

    for subdirContent in os.walk(targetDir):
        for opusFile in glob(os.path.join(subdirContent[0], '*.opus')):
            print("converting " + opusFile)
            fileNoExt = opusFile.rsplit('.',1)[0]
            wavFile = fileNoExt + ".wav"
            mp3File = fileNoExt + ".mp3"
            os.system("opusdec " + opusFile + " " + wavFile + ">/dev/null 2>&1")
            os.system("lame " + wavFile + " " + mp3File + ">/dev/null 2>&1")
            if(os.path.exists(wavFile) and os.path.exists(mp3File)):
                os.system("rm " + wavFile + " " + opusFile)
            else:
                raise RuntimeError("Converting opus file failed: " + opusFile)

# ------------------------------------------------------------------------------------------------

@unique
class MediaType(Enum):
    VIDEO = auto()
    IMAGE = auto()
    AUDIO = auto()
    UNKNOWN = auto()

    @classmethod
    def mime_to_mediaType(cls, filename):
        mime = mimetypes.guess_type(filename)[0] 
        if(mime == None):
            return cls.UNKNOWN
        elif(mime.startswith("video")):
            return cls.VIDEO
        elif(mime.startswith("image")):
            return cls.IMAGE
        elif(mime.startswith("audio")):
            return cls.AUDIO
        else:
            print("WARNING unhandled media type [" + mime + "] for file " + filename)
            return cls.UNKNOWN


class MediaFile:
    dateTaken = None
    mediaType = None
    srcFile = None
    prefix = None

    def __init__(self, src):
        self.srcFile = src
        self.mediaType = MediaType.mime_to_mediaType(src)
    
    def __repr__(self):
        dateStr = time.strftime("%Y-%m-%d",self.dateTaken) if self.dateTaken != None else "NONE"
        return self.mediaType.name + " " + self.srcFile + " " + dateStr


def getVideoDateTaken(src):
    if(os.path.basename(src).startswith("VID_")):
        # EXPECTED: VID_2015110_174731.mp4
        dateStr = os.path.splitext(os.path.basename(src))[0]
        return time.strptime(dateStr, "VID_%Y%m%d_%H%M%S")
    else:
        return None

def getAudioDateTaken(src):
    if(os.path.basename(src).startswith("PTT-")):
        # EXPECTED: PTT-20140724-WA0001.mp3
        dateStr = os.path.splitext(os.path.basename(src))[0]
        dateStr = dateStr.split("-")
        return time.strptime(dateStr[1], "%Y%m%d")
    else:
        return None

def getImageDateTaken(src):
    with open(src, 'rb') as imgFile:
        imgTags = exifread.process_file(imgFile, details=False, stop_tag='EXIF DateTimeOriginal')

        if("EXIF DateTimeOriginal" in imgTags):
            dateStr = str(imgTags["EXIF DateTimeOriginal"])
            return time.strptime(dateStr, "%Y:%m:%d %H:%M:%S")
        elif(os.path.basename(src).startswith("IMG_")):
            #EXPECTED IMG_20141225_105859
            dateStr = os.path.splitext(os.path.basename(src))[0]
            return time.strptime(dateStr, "IMG_%Y%m%d_%H%M%S")
        elif(os.path.basename(src).startswith("Burst_Cover_GIF_Action_")):
            #EXPECTED Burst_Cover_GIF_Action_20170621113951.gif
            dateStr = os.path.splitext(os.path.basename(src))[0]
            return time.strptime(dateStr, "Burst_Cover_GIF_Action_%Y%m%d%H%M%S")
    
    return None

def getDateTaken(mfile):
    date = None
    
    try:
        if(mfile.mediaType == MediaType.VIDEO):
            date = getVideoDateTaken(mfile.srcFile)
            mfile.prefix = "vid"
        elif(mfile.mediaType == MediaType.AUDIO):
            date = getAudioDateTaken(mfile.srcFile)
            mfile.prefix = "audio"
        elif(mfile.mediaType == MediaType.IMAGE):
            date = getImageDateTaken(mfile.srcFile)
            mfile.prefix = "pics"
    except ValueError:
        date = None
    
    if(date == None):
        print("WARNING: date not extracted for " + mfile.srcFile)
    else:
        mfile.dateTaken = date

def addToCollection(mediafiles, mfile):
    # mediaType -> year -> month -> day -> mediaFile
    if not mfile.mediaType in mediafiles:
        if mfile.mediaType == MediaType.UNKNOWN:
            mediafiles[mfile.mediaType] = list()
        else:
            mediafiles[mfile.mediaType] = dict()

    if mfile.mediaType == MediaType.UNKNOWN:
        mediafiles[mfile.mediaType].append(mfile)
        return

    years = mediafiles[mfile.mediaType]
    year = str(mfile.dateTaken.tm_year)
    if not year in years:
        years[year] = dict()

    months = years[year]
    month = time.strftime("%m_%B", mfile.dateTaken)
    if not month in months:
        months[month] = dict()
	
    days = months[month]
    day = time.strftime("%d_%a", mfile.dateTaken)
    if not day in days:
        days[day] = list()

    days[day].append(mfile)


def classifyMediaFiles(srcDir):
    print("\n############ Classifying Media Files ...")

    # mediaType -> year -> month -> day -> mediaFile
    mediafiles = dict()
    for (dirpath, dirnames, filenames) in os.walk(srcDir):
        for fname in filenames:
            currFile = MediaFile(os.path.join(dirpath, fname))
            
            #print(currFile) 
            if(currFile.mediaType != MediaType.UNKNOWN):
                getDateTaken(currFile)
                if(currFile.dateTaken == None):
                    currFile.mediaType = MediaType.UNKNOWN

            addToCollection(mediafiles, currFile)

    return mediafiles

# ------------------------------------------------------------------------------------------------

def mkOutDir(outputDir, dname):
    d = os.path.join(outputDir, dname)
    if not os.path.exists(d):
        os.makedirs(d)
    return d

def copyFile(src, tdir, tname, text):
    if not os.path.exists(tdir): 
        os.makedirs(tdir)
    
    target = os.path.join(tdir,tname + text)
    counter = 1
    while(os.path.isfile(target) and counter < 100):
        target = os.path.join(tdir, tname + "_" + str(counter).zfill(2) + text)
        counter += 1

    if(counter == 100):
        print("WARNING: target file name duplicate. Gave up renaming: " + target)
        return False

    try:
        shutil.copy2(src, target)
        print(src + " --> " + target)
    except shutil.SameFileError:
        print("ERROR: Source " + src + " and destination " + target + " are the same.")
        return False
    except IOError:
        print("ERROR: copy source " + src + " to destination " + target + " failed.")
        return False

    return True

def sortFiles(outDir, mediafiles):
    print("\n############# Copying files ...")
    
    for mtype, years in mediafiles.items():
        if mtype == MediaType.UNKNOWN: continue
        elif mtype == MediaType.VIDEO: sortedDir = os.path.join(outDir, "sorted", "videos")
        elif mtype == MediaType.AUDIO: sortedDir = os.path.join(outDir, "sorted", "audio")
        elif mtype == MediaType.IMAGE: sortedDir = os.path.join(outDir, "sorted", "images")
        else: raise RuntimeError("Unhandled media type: " + mtype)

        for year, months in years.items():
            for month, days in months.items():
                for day, files in days.items():
                    for mf in files:
                        tbase = (mf.prefix + "_" +
                                time.strftime("%Y%m%d_%H%M%S", mf.dateTaken))
                        text = os.path.splitext(mf.srcFile)[1]
                        tdir = os.path.join(sortedDir,year,month,day)
                        if(not copyFile(mf.srcFile, tdir, tbase, text)):
                            mediafiles[MediaType.UNKNOWN].append(mf)

    print("\n############# Copying unsorted files ...")
    unsortedDir = mkOutDir(outDir, "unsorted")
    for mf in mediafiles[MediaType.UNKNOWN]:
        tbase = os.path.splitext(os.path.basename(mf.srcFile))[0]
        text = os.path.splitext(mf.srcFile)[1]
        if(not copyFile(mf.srcFile, unsortedDir, tbase, text)):
            print("WARNING: copying unsorted file " + mf.srcFile + " failed.")

# ------------------------------------------------------------------------------------------------

def removeMedia(destDir):
    answer = None
    while answer == None:
        answer = input("Do you want to remove media files from " + destDir + "? [yes/no]: ")
        if answer != "yes" and answer != "no":
            print("please answer yes or no")
            answer = None
        else:
            answer = True if answer == "yes" else False
    
    if answer:
        os.system("adb shell rm -r \"" + destDir + "/*\"")

# ------------------------------------------------------------------------------------------------


parser = argparse.ArgumentParser(description=
        "Extract media files from adb connected" 
        "device and sort it by content type and data.")

parser.add_argument("-o", "--outputDir",type=str, help="Path to output directory.", required=True)
parser.add_argument("-s", "--srcDir", type=str, help="Source directory of files to be sorted. If not specified, files will retrived from connected mobile using adb.")

args = parser.parse_args()

if(not os.path.isdir(args.outputDir)):
    raise RuntimeError("Output directory invalid: " + args.outputDir)

sortmeDir = None
if(args.srcDir != None):
    sortmeDir = args.srcDir
    if(not os.path.isdir(args.srcDir)):
        raise RuntimeError("Source directory invalid " + args.srcDir)

else:
    sortmeDir = mkOutDir(args.outputDir, "sortme")
    pullMedia(sortmeDir, CAMERADIR)
    pullMedia(sortmeDir, WHATSAPPDIR)

convertOpusAudio(sortmeDir)

# mediaType -> year -> month -> day -> list(mediaFile)
mediafiles = classifyMediaFiles(sortmeDir)
sortFiles(args.outputDir, mediafiles)

if(args.srcDir == None):
    removeMedia(CAMERADIR)
    removeMedia(WHATSAPPDIR)
