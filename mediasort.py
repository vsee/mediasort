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

def getDateTaken(mfile):
    if(mfile.mediaType == MediaType.VIDEO):
        pass
    elif(mfile.mediaType == MediaType.AUDIO):
        pass
    elif(mfile.mediaType == MediaType.IMAGE):
        pass


def addToCollection(coll, mfile):
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
