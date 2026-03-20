# Media Sort

Sorts media files from one or more source directories by type and capture date.

## Features

- Sorts images, videos, and audio files into a structured output tree by year/month/day
- Extracts capture date from EXIF metadata or recognised filename patterns (IMG_, VID_, PXL_, PTT-, …)
- Falls back to file modification timestamp when no date can be determined
- Converts HEIC images to JPEG before sorting; reads EXIF from companion HEIC files for JPGs that lack embedded metadata
- Converts opus audio files to MP3 before sorting
- Accepts multiple source directories in a single run

## Output structure

```
<output_dir>/
    sorted/
        images/  <year>/<MM_Month>/<DD_Weekday>/  pics_[prefix_]YYYYMMDD_HHMMSS.<ext>
        videos/  <year>/<MM_Month>/<DD_Weekday>/  vid_[prefix_]YYYYMMDD_HHMMSS.<ext>
        audio/   <year>/<MM_Month>/<DD_Weekday>/  audio_[prefix_]YYYYMMDD_HHMMSS.<ext>
    unsorted/                                      files whose type or date could not be determined
```

## Requirements

- [uv](https://docs.astral.sh/uv/)
- opus-tools, lame (for opus → MP3 conversion) — `sudo apt install opus-tools lame`

## Setup

```bash
make env
```

Installs dependencies and sets up pre-commit hooks.

## Usage

```bash
uv run mediasort.py -i <source_dir> -o <output_dir>
```

Multiple source directories:

```bash
uv run mediasort.py -i /path/to/dir1 -i /path/to/dir2 -o <output_dir>
```

| Flag | Description |
|------|-------------|
| `-i` / `--input-dir` | Source directory to sort (required, repeatable) |
| `-o` / `--output-dir` | Output directory (required, must already exist) |
| `--prefix` | Optional string prepended to every sorted filename |

## Development

```bash
make lint   # run pre-commit checks on all files
```
