# Media Sort

Extracts media files from Android mobile devices
and sorts them by date and media type.

## Features

* handles video, image and audio files and sorts accordingly
* converts opus to mp3
* considers DCIM/Camera and WhatsApp Voice Notes, WhatsApp Video, WhatsApp Image folders
* ignores Sent folders from WhatsApp directories

## Requirements

* [uv](https://docs.astral.sh/uv/)
* Android Platform-Tools (adb)
* opus-tools, lame — `sudo apt install opus-tools lame`

## Setup

```bash
make env
```

This installs dependencies and sets up pre-commit hooks.

## Usage

```bash
uv run mediasort.py -o <output_dir> [-s <source_dir>] [--prefix <prefix>] [--pullOnly]
```

| Flag | Description |
|------|-------------|
| `-o` / `--outputDir` | Output directory (required) |
| `-s` / `--srcDir` | Source directory. If omitted, files are pulled from a connected Android device via adb |
| `--prefix` | Optional prefix added to every sorted file |
| `--pullOnly` | Pull files from device without sorting |

## Development

```bash
make lint   # run pre-commit checks on all files
```

## Target Devices

Tested for Nexus 6p
