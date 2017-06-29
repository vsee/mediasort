#!/opt/anaconda3/bin/python

import sys
import time
import os

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

def getMetaData(mfile):
    pass

def sortMediaByDate(targetDir, srcDir):
    print("Sorting media files by date ...")

    unsorted = list()
    for (dirpath, dirnames, filenames) in os.walk(srcDir):
        for fname in filenames:
            mediaFile = os.path.join(dirpath, fname)

            dataTaken, prefix = getMetaData(mediaFile)
            if(dateTaken = None): 
                unsorted.append(mediaFile)
                continue

            targetFile = getTragetName(targetDir, mediaFile, dataTaken, prefix)
            if(targetFile == None):
                unsorted.append(mediaFile)
                continue

            copyTargetFile(targetFile)

            if(len(unsorted) > 0):
                copyUnsortedFiles(targetDir, unsorted)


def sortMediaByType(targetDir, srcDir):
    pass

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

sortedDateDir = mkOutDir(args.outputDir, "sortedDate")
sortMediaByDate(sortedDateDir, sortmeDir)

sortedMediaDir = mkOutDir(args.outputDir, "sortedMedia")
sortMediaByType(sortedMediaDir, sortedDateDir)
