# Media Sort

Extracts media files from Android mobile devices
and sorts them by date and media type.

## Features:

* handles video, image and audio files and sorts accordingly
* converts opus to mp3
* considers DCIM/Camera and WhatsApp Voice Notes, WhatsApp Video, WhatsApp Image folders
* ignores Sent folders from WhatsApp directories

## Requirements

* python3
* [exifread](https://pypi.org/project/ExifRead/)  
```$ pip3 install exifread```
* Android Platform-Tools, i.e. adb
* opus-tools, lame  
```$ sudo apt install opus-tools lame```

## Target Devices

Tested for Nexus 6p
