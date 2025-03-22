#!/usr/bin/env python3

import time
import os
import concurrent.futures

from enum import Enum, unique, auto
import mimetypes

from glob import glob
import exifread
import shutil

import argparse

import os.path

import datetime
import pathlib

from PIL import Image
import pillow_heif
from tqdm import tqdm

import re

CAMERADIR="/sdcard/DCIM/Camera"
WHATSAPPROOT = "/sdcard/Android/media/com.whatsapp/WhatsApp/Media"
# WHATSAPPROOT = "/sdcard/WhatsApp/Media"
WHATSAPPVOICEDIR= WHATSAPPROOT + "/WhatsApp\ Voice\ Notes"
WHATSAPPVIDEODIR= WHATSAPPROOT + "/WhatsApp\ Video"
WHATSAPPIMGDIR= WHATSAPPROOT + "/WhatsApp\ Images"

VIDEOTYPES = ["mp4"]
IMGTYPES = ["jpg","png","jpeg","HEIC"]
AUDIOTYPES = []

# TODO check if device is connected and readble
def pullMedia(targetDir, srcDir, removeSent=False):
    print("\n############ Pulling media files from directory: " + srcDir)
    os.system("adb pull " + srcDir + " " + targetDir)

    if removeSent:
        target = targetDir + "/" + srcDir.split("/")[-1] + "/Sent"
        print("Removing Sent directory: " + target)
        os.system("rm -r " + target)

def convertOpusAudio(targetDir):
    print("\n############ Converting opus audio files to mp3 ...")

    for subdirContent in os.walk(targetDir):
        for opusFile in glob(os.path.join(subdirContent[0], '*.opus')):
            print("converting " + opusFile)
            fileNoExt = opusFile.rsplit('.',1)[0]
            wavFile = fileNoExt + ".wav"
            mp3File = fileNoExt + ".mp3"
            os.system("opusdec \"" + opusFile + "\" \"" + wavFile + "\" >/dev/null 2>&1")
            os.system("lame \"" + wavFile + "\" \"" + mp3File + "\" >/dev/null 2>&1")
            if(os.path.exists(wavFile) and os.path.exists(mp3File)):
                os.system("rm \"" + wavFile + "\" \"" + opusFile + "\"")
            else:
                raise RuntimeError("Converting opus file failed: " + opusFile)


def convert_heic_to_jpeg(input_path, output_path):

    try:
        heif_file = pillow_heif.read_heif(input_path)
        image = Image.frombytes(
            heif_file.mode,
            heif_file.size,
            heif_file.data,
            "raw"
        )
        image.save(output_path, "JPEG")

    except Exception as e:
        print(f"Error converting {input_path}: {e}")

def batch_convert_heic_to_jpeg(source_dir):
    heic_files = []
    # Collect all HEIC files and their output paths
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.lower().endswith(".heic"):
                heic_path = os.path.join(root, file)
                jpeg_path = os.path.splitext(heic_path)[0] + ".jpg"
                if not os.path.exists(jpeg_path):
                    heic_files.append((heic_path, jpeg_path))

    # Parallelize the conversion using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit tasks to the executor for each file
        future_to_file = {executor.submit(convert_heic_to_jpeg, heic_path, jpeg_path): (heic_path, jpeg_path) for heic_path, jpeg_path in heic_files}

        # Wait for all futures to complete and handle results
        for future in tqdm(concurrent.futures.as_completed(future_to_file), total=len(heic_files), desc="Converting HEIC to JPEG"):
            heic_path, jpeg_path = future_to_file[future]
            try:
                future.result()  # If any exception was raised during conversion, it will be re-raised here
                tqdm.write(f"Successfully converted: {heic_path} -> {jpeg_path}")
            except Exception as e:
                tqdm.write(f"Error converting {heic_path} -> {jpeg_path}: {e}")


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

    @classmethod
    def filename_to_mediaType(cls, filename):
        extension = os.path.splitext(filename)[1][1:]

        if(extension in VIDEOTYPES):
            return cls.VIDEO
        elif(extension in IMGTYPES):
            return cls.IMAGE
        elif(extension in AUDIOTYPES):
            return cls.AUDIO
        else:
            print("WARNING unhandled media extension [" + 
                    extension + "] for file " + filename)
            return cls.UNKNOWN

class MediaFile:
    dateTaken = None
    mediaType = None
    srcFile = None
    prefix = None

    def __init__(self, src):
        self.srcFile = src
        
        # try to get media type from mime type
        self.mediaType = MediaType.mime_to_mediaType(src)

        # try to get media type from file extension
        if self.mediaType == MediaType.UNKNOWN:
            self.mediaType = MediaType.filename_to_mediaType(src)
    
    def __repr__(self):
        dateStr = time.strftime("%Y-%m-%d",self.dateTaken) if self.dateTaken != None else "NONE"
        return self.mediaType.name + " " + self.srcFile + " " + dateStr


def getVideoDateTaken(src):
    if(os.path.basename(src).startswith("VID_")):
        # EXPECTED: VID_2015110_174731.mp4
        dateStr = (os.path.basename(src)).split(".")[0]
        return time.strptime(dateStr, "VID_%Y%m%d_%H%M%S")
    elif(os.path.basename(src).startswith("VID-")):
         # EXPECTED: VID-20190906-WA0011.mp4
        dateStr = (os.path.basename(src)).split(".")[0]
        
        parts = dateStr.split("-")
        if len(parts) != 3:
            return None
        else: 
            return time.strptime(parts[1], "%Y%m%d")
    elif(os.path.basename(src).startswith("PXL_")):
        # EXPECTED: PXL_20210121_175800715.mp4
        dateStr = (os.path.basename(src)).split(".")[0]
        return time.strptime(dateStr, "PXL_%Y%m%d_%H%M%S%f")
    else:
        return None

def getAudioDateTaken(src):
    if(os.path.basename(src).startswith("PTT-")):
        # EXPECTED: PTT-20140724-WA0001.mp3
        dateStr = (os.path.basename(src)).split(".")[0]
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
            dateStr = (os.path.basename(src)).split(".")[0]
            return time.strptime(dateStr, "IMG_%Y%m%d_%H%M%S")
        elif(os.path.basename(src).startswith("Burst_Cover_GIF_Action_")):
            #EXPECTED Burst_Cover_GIF_Action_20170621113951.gif
            dateStr = (os.path.basename(src)).split(".")[0]
            return time.strptime(dateStr, "Burst_Cover_GIF_Action_%Y%m%d%H%M%S")
        elif(os.path.basename(src).startswith("IMG-")):
            # EXPECTED: IMG-20190906-WA0004.jpg
           dateStr = (os.path.basename(src)).split(".")[0]
           
           parts = dateStr.split("-")
           if len(parts) != 3:
               return None
           else: 
               return time.strptime(parts[1], "%Y%m%d")

    # If no EXIF data and none of the conditions above matched, check for a .heic file
    folder = os.path.dirname(src)
    base_name = os.path.splitext(os.path.basename(src))[0]
    heic_file = os.path.join(folder, f"{base_name}.heic")

    if os.path.exists(heic_file):
        # Expected format: 2024-08-17 08.35.05.heic or 2025-02-26 06.09.49-1.heic
        base_name = os.path.basename(heic_file)  # Get full file name (no need to split extension here)
        
        # Use regular expression to match the date-time pattern
        match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})", base_name)
        
        if match:
            dateStr = match.group(1)  # Extract the matched date-time string
            try:
                return time.strptime(dateStr, "%Y-%m-%d %H.%M.%S")
            except ValueError:
                print(f"WARNING: failed to parse date string from {heic_file}")
                return None

    return None

def getDateTaken(mfile):
    date = None
    
    try:
        if(mfile.mediaType == MediaType.VIDEO):
            mfile.prefix = "vid"
            date = getVideoDateTaken(mfile.srcFile)
        elif(mfile.mediaType == MediaType.AUDIO):
            mfile.prefix = "audio"
            date = getAudioDateTaken(mfile.srcFile)
        elif(mfile.mediaType == MediaType.IMAGE):
            mfile.prefix = "pics"
            date = getImageDateTaken(mfile.srcFile)
    except ValueError as e:
        print("WARNING: expected date format invalid for: " + mfile.srcFile)
        date = None
    
    if (mfile.prefix == None):
        print("DEBUG: " + mfile.srcFile)

    if(date == None):
        print("WARNING: date not extracted for " + mfile.srcFile + ". Using Creation Timestamp.")
        srcPath = pathlib.Path(mfile.srcFile)
        mtime = datetime.datetime.fromtimestamp(srcPath.stat().st_mtime)
        date = mtime.timetuple()

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
    while(os.path.isfile(target) and counter < 1000):
        target = os.path.join(tdir, tname + "_" + str(counter).zfill(3) + text)
        counter += 1

    if(counter == 1000):
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

def sortFiles(outDir, mediafiles, custom_prefix):
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
                        tbase = mf.prefix + "_"
                        if custom_prefix:
                            tbase += custom_prefix + "_"
                        tbase += time.strftime("%Y%m%d_%H%M%S", mf.dateTaken)
                        text = os.path.splitext(mf.srcFile)[1]
                        tdir = os.path.join(sortedDir,year,month,day)
                        if(not copyFile(mf.srcFile, tdir, tbase, text)):
                            mediafiles[MediaType.UNKNOWN].append(mf)

    # bail out early if all files where successfully sorted
    if not MediaType.UNKNOWN in mediafiles:
        return

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
parser.add_argument('--pullOnly', help='Only pull the data from mobile, do not sort.',  action='store_true')
parser.add_argument("--prefix", type=str, help="Add this prefix to every media file.")

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
    pullMedia(sortmeDir, WHATSAPPVOICEDIR)
    pullMedia(sortmeDir, WHATSAPPVIDEODIR, removeSent=True)
    pullMedia(sortmeDir, WHATSAPPIMGDIR, removeSent=True)

if not args.pullOnly:
    convertOpusAudio(sortmeDir)
    batch_convert_heic_to_jpeg(sortmeDir)

    # mediaType -> year -> month -> day -> list(mediaFile)
    mediafiles = classifyMediaFiles(sortmeDir)
    sortFiles(args.outputDir, mediafiles, args.prefix)

if(args.srcDir == None):
    removeMedia(CAMERADIR)
    removeMedia(WHATSAPPVOICEDIR)
    removeMedia(WHATSAPPVIDEODIR)
    removeMedia(WHATSAPPIMGDIR)
