#!/opt/anaconda3/bin/python

import sys
import time
import os

from enum import Enum, unique, auto
import mimetypes

from glob import glob
import exifread

import argparse
import pprint

CAMERADIR="/sdcard/DCIM/Camera"
WHATSAPPDIR="/sdcard/WhatsApp/Media/WhatsApp\ Voice\ Notes"

def pullMedia(targetDir, srcDir):
    print("Pulling media files from directory: " + srcDir)
    os.system("adb pull " + srcDir + " " + targetDir)

def convertOpusAudio(targetDir):
    print("Converting opus audio files to mp3 ...")

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

    def __init__(self, src):
        self.srcFile = src
        self.mediaType = MediaType.mime_to_mediaType(src)

def getVideoDateTaken(src):
    # EXPECTED: VI_2015110_174731.mp4
    dateStr = os.path.splitext(os.path.basename(src))[0]
    return time.strptime(dateStr, "VID_%Y%m%d_%H%M%S")

def getAudioDateTaken(src):
    # EXPECTED: PTT-20140724-WA0001.mp3
    dateStr = os.path.splitext(os.path.basename(src))[0]
    dateStr = dateStr.split("-")
    return time.strptime(dateStr[1], "%Y%m%d")

def getImageDateTaken(src):
    with open(src, 'rb') as imgFile:
        imgTags = exifread.process_file(imgFile, details=False)

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
        elif(mfile.mediaType == MediaType.AUDIO):
            date = getAudioDateTaken(mfile.srcFile)
        elif(mfile.mediaType == MediaType.IMAGE):
            date = getImageDateTaken(mfile.srcFile)
    except ValueError:
        date = None
    
    if(date == None):
        print("WARNING: date not extracted for " + mfile.srcFile)
    else:
        mfile.dateTaken = date

def addToCollection(coll, mfile):
    # TODO add mfile to collection
    # mediaType -> year -> month -> day -> mediaFile
    pass

def classifyMediaFiles(srcDir):
    print("Classifying Media Files ...")

    # mediaType -> year -> month -> day -> mediaFile
    result = dict()
    for (dirpath, dirnames, filenames) in os.walk(srcDir):
        for fname in filenames:
            currFile = MediaFile(os.path.join(dirpath, fname))
            
            if(currFile.mediaType != MediaType.UNKNOWN):
                getDateTaken(currFile)

            addToCollection(result, currFile)

    return result

# ------------------------------------------------------------------------------------------------

def copyFiles(outDir, mfiles):
    pass

# ------------------------------------------------------------------------------------------------

def mkOutDir(outputDir, dname):
    d = os.path.join(outputDir, dname)
    if not os.path.exists(d):
        os.makedirs(d)
    return d

# ------------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description=
        "Extract media files from adb connected" 
        "device and sort it by content type and data.")

parser.add_argument("-o", "--outputDir",type=str, help="Path to output directory.", required=True)

args = parser.parse_args()

if(not os.path.isdir(args.outputDir)):
    raise RuntimeError("Output directory invalid: " + args.outputDir)

sortmeDir = mkOutDir(args.outputDir, "sortme")

#pullMedia(sortmeDir, CAMERADIR)
#pullMedia(sortmeDir, WHATSAPPDIR)

#convertOpusAudio(sortmeDir)

# mediaType -> year -> month -> day -> mediaFile
mediaFiles = classifyMediaFiles(sortmeDir)
copyFiles(args.outputDir, mediaFiles)
