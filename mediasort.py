#!/usr/bin/env python3
"""
Sort media files from one or more source directories by type and date.

Scans each input directory recursively, detects whether each file is an image,
video, or audio file, extracts the capture date (from EXIF data or filename
patterns), and copies files into a structured output tree:

    sorted/
        images/  <year>/<month>/<day>/  pics_[prefix_]YYYYMMDD_HHMMSS.<ext>
        videos/  <year>/<month>/<day>/  vid_[prefix_]YYYYMMDD_HHMMSS.<ext>
        audio/   <year>/<month>/<day>/  audio_[prefix_]YYYYMMDD_HHMMSS.<ext>
    unsorted/                           files whose type or date could not be determined

HEIC files are converted to JPEG and opus audio files are converted to MP3
before sorting. Filename date patterns recognised include IMG_, VID_, PXL_,
IMG-, VID-, PTT-, and Burst_Cover_GIF_Action_. When no date can be determined
the file modification timestamp is used as a fallback.

Usage
-----
Single directory:
    uv run mediasort.py -i /path/to/photos -o /path/to/output

Multiple directories:
    uv run mediasort.py -i /path/to/dir1 -i /path/to/dir2 -o /path/to/output

With a custom filename prefix:
    uv run mediasort.py -i /path/to/photos -o /path/to/output --prefix holiday
"""

import concurrent.futures
import mimetypes
import re
import shutil
import subprocess
from datetime import datetime
from enum import Enum, auto, unique
from pathlib import Path

import click
import exifread
import pillow_heif
from PIL import Image
from tqdm import tqdm

VIDEOTYPES = {"mp4"}
IMGTYPES = {"jpg", "png", "jpeg", "heic"}
AUDIOTYPES: set[str] = set()


def convert_opus_audio(target_dir: Path) -> None:
    print("\n############ Converting opus audio files to mp3 ...")
    for opus_file in target_dir.rglob("*"):
        if not (opus_file.is_file() and opus_file.suffix.lower() == ".opus"):
            continue
        print(f"converting {opus_file}")
        wav_file = opus_file.with_suffix(".wav")
        mp3_file = opus_file.with_suffix(".mp3")
        subprocess.run(
            ["opusdec", str(opus_file), str(wav_file)], check=True, capture_output=True
        )
        subprocess.run(
            ["lame", str(wav_file), str(mp3_file)], check=True, capture_output=True
        )
        wav_file.unlink()
        opus_file.unlink()


def convert_heic_to_jpeg(input_path: Path, output_path: Path) -> None:
    try:
        heif_file = pillow_heif.read_heif(input_path)
        image = Image.frombytes(heif_file.mode, heif_file.size, heif_file.data, "raw")
        image.save(output_path, "JPEG")
    except Exception as e:
        print(f"Error converting {input_path}: {e}")


def batch_convert_heic_to_jpeg(source_dir: Path) -> None:
    heic_files = [
        (p, p.with_suffix(".jpg"))
        for p in source_dir.rglob("*")
        if p.is_file()
        and p.suffix.lower() == ".heic"
        and not p.with_suffix(".jpg").exists()
    ]

    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_file = {
            executor.submit(convert_heic_to_jpeg, heic, jpeg): (heic, jpeg)
            for heic, jpeg in heic_files
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_file),
            total=len(heic_files),
            desc="Converting HEIC to JPEG",
        ):
            heic, jpeg = future_to_file[future]
            try:
                future.result()
                tqdm.write(f"Successfully converted: {heic} -> {jpeg}")
            except Exception as e:
                tqdm.write(f"Error converting {heic} -> {jpeg}: {e}")


# ------------------------------------------------------------------------------------------------


@unique
class MediaType(Enum):
    VIDEO = auto()
    IMAGE = auto()
    AUDIO = auto()
    UNKNOWN = auto()

    @classmethod
    def from_file(cls, path: Path) -> "MediaType":
        mime, _ = mimetypes.guess_type(path)
        if mime is not None:
            if mime.startswith("video"):
                return cls.VIDEO
            if mime.startswith("image"):
                return cls.IMAGE
            if mime.startswith("audio"):
                return cls.AUDIO
            print(f"WARNING unhandled media type [{mime}] for file {path}")
            return cls.UNKNOWN

        ext = path.suffix.lstrip(".").lower()
        if ext in VIDEOTYPES:
            return cls.VIDEO
        if ext in IMGTYPES:
            return cls.IMAGE
        if ext in AUDIOTYPES:
            return cls.AUDIO
        print(f"WARNING unhandled media extension [{ext}] for file {path}")
        return cls.UNKNOWN

    @property
    def prefix(self) -> str:
        return {
            MediaType.VIDEO: "vid",
            MediaType.IMAGE: "pics",
            MediaType.AUDIO: "audio",
        }.get(self, "unknown")

    @property
    def subdir(self) -> str:
        return {
            MediaType.VIDEO: "videos",
            MediaType.IMAGE: "images",
            MediaType.AUDIO: "audio",
        }.get(self, "unsorted")


class MediaFile:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.media_type = MediaType.from_file(path)
        self.date_taken: datetime | None = None

    def __repr__(self) -> str:
        date_str = self.date_taken.strftime("%Y-%m-%d") if self.date_taken else "NONE"
        return f"{self.media_type.name} {self.path} {date_str}"


# ------------------------------------------------------------------------------------------------


def _get_video_date(path: Path) -> datetime | None:
    stem = path.stem
    if stem.startswith("VID_"):
        # EXPECTED: VID_20151101_174731.mp4
        return datetime.strptime(stem, "VID_%Y%m%d_%H%M%S")
    if stem.startswith("VID-"):
        # EXPECTED: VID-20190906-WA0011.mp4
        parts = stem.split("-")
        return datetime.strptime(parts[1], "%Y%m%d") if len(parts) == 3 else None
    if stem.startswith("PXL_"):
        # EXPECTED: PXL_20210121_175800715.mp4
        return datetime.strptime(stem, "PXL_%Y%m%d_%H%M%S%f")
    return None


def _get_audio_date(path: Path) -> datetime | None:
    stem = path.stem
    if stem.startswith("PTT-"):
        # EXPECTED: PTT-20140724-WA0001.mp3
        parts = stem.split("-")
        return datetime.strptime(parts[1], "%Y%m%d")
    return None


def _get_image_date(path: Path) -> datetime | None:
    with path.open("rb") as f:
        tags = exifread.process_file(f, details=False, stop_tag="EXIF DateTimeOriginal")
        if "EXIF DateTimeOriginal" in tags:
            return datetime.strptime(
                str(tags["EXIF DateTimeOriginal"]), "%Y:%m:%d %H:%M:%S"
            )

        stem = path.stem
        if stem.startswith("IMG_"):
            # EXPECTED: IMG_20141225_105859.jpg
            return datetime.strptime(stem, "IMG_%Y%m%d_%H%M%S")
        if stem.startswith("Burst_Cover_GIF_Action_"):
            # EXPECTED: Burst_Cover_GIF_Action_20170621113951.gif
            return datetime.strptime(stem, "Burst_Cover_GIF_Action_%Y%m%d%H%M%S")
        if stem.startswith("IMG-"):
            # EXPECTED: IMG-20190906-WA0004.jpg
            parts = stem.split("-")
            return datetime.strptime(parts[1], "%Y%m%d") if len(parts) == 3 else None

    # Fallback: companion .heic file with date in filename
    # EXPECTED: 2024-08-17 08.35.05.heic
    heic = path.with_suffix(".heic")
    if heic.exists():
        match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}\.\d{2}\.\d{2})", heic.name)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y-%m-%d %H.%M.%S")
            except ValueError:
                print(f"WARNING: failed to parse date string from {heic}")

    return None


def _resolve_date(mfile: MediaFile) -> None:
    date: datetime | None = None
    try:
        if mfile.media_type == MediaType.VIDEO:
            date = _get_video_date(mfile.path)
        elif mfile.media_type == MediaType.AUDIO:
            date = _get_audio_date(mfile.path)
        elif mfile.media_type == MediaType.IMAGE:
            date = _get_image_date(mfile.path)
    except ValueError:
        print(f"WARNING: expected date format invalid for: {mfile.path}")

    if date is None:
        print(
            f"WARNING: date not extracted for {mfile.path}. Using modification timestamp."
        )
        date = datetime.fromtimestamp(mfile.path.stat().st_mtime)

    mfile.date_taken = date


def _add_to_collection(mediafiles: dict, mfile: MediaFile) -> None:
    if mfile.media_type == MediaType.UNKNOWN:
        mediafiles.setdefault(MediaType.UNKNOWN, []).append(mfile)
        return

    date = mfile.date_taken
    (
        mediafiles.setdefault(mfile.media_type, {})
        .setdefault(str(date.year), {})
        .setdefault(date.strftime("%m_%B"), {})
        .setdefault(date.strftime("%d_%a"), [])
        .append(mfile)
    )


def _classify_media_files(src_dirs: tuple[Path, ...]) -> dict:
    print("\n############ Classifying Media Files ...")
    mediafiles: dict = {}
    for src_dir in src_dirs:
        for path in src_dir.rglob("*"):
            if not path.is_file():
                continue
            mfile = MediaFile(path)
            if mfile.media_type != MediaType.UNKNOWN:
                _resolve_date(mfile)
            _add_to_collection(mediafiles, mfile)
    return mediafiles


def _copy_file(src: Path, target_dir: Path, stem: str, suffix: str) -> bool:
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / (stem + suffix)
    if target.exists():
        for i in range(1, 1000):
            candidate = target_dir / f"{stem}_{str(i).zfill(3)}{suffix}"
            if not candidate.exists():
                target = candidate
                break
        else:
            print(f"WARNING: target file name duplicate. Gave up renaming: {target}")
            return False

    try:
        shutil.copy2(src, target)
        print(f"{src} --> {target}")
    except shutil.SameFileError:
        print(f"ERROR: source and destination are the same: {src}")
        return False
    except OSError:
        print(f"ERROR: copy failed: {src} -> {target}")
        return False
    return True


def _sort_files(out_dir: Path, mediafiles: dict, custom_prefix: str | None) -> None:
    print("\n############# Copying files ...")

    for mtype, years in mediafiles.items():
        if mtype == MediaType.UNKNOWN:
            continue
        sorted_dir = out_dir / "sorted" / mtype.subdir
        for year, months in years.items():
            for month, days in months.items():
                for day, files in days.items():
                    for mf in files:
                        stem = mf.media_type.prefix + "_"
                        if custom_prefix:
                            stem += custom_prefix + "_"
                        stem += mf.date_taken.strftime("%Y%m%d_%H%M%S")
                        target_dir = sorted_dir / year / month / day
                        if not _copy_file(mf.path, target_dir, stem, mf.path.suffix):
                            mediafiles.setdefault(MediaType.UNKNOWN, []).append(mf)

    if MediaType.UNKNOWN not in mediafiles:
        return

    print("\n############# Copying unsorted files ...")
    unsorted_dir = out_dir / "unsorted"
    for mf in mediafiles[MediaType.UNKNOWN]:
        if not _copy_file(mf.path, unsorted_dir, mf.path.stem, mf.path.suffix):
            print(f"WARNING: copying unsorted file {mf.path} failed.")


# ------------------------------------------------------------------------------------------------


@click.command()
@click.option(
    "--input-dir",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    multiple=True,
    help="Source directory of files to be sorted. Can be specified multiple times.",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Path to output directory.",
)
@click.option(
    "--prefix",
    type=str,
    default=None,
    help="Add this prefix to every media file.",
)
def main(input_dir: tuple[Path, ...], output_dir: Path, prefix: str | None) -> None:
    if not output_dir.is_dir():
        raise click.BadParameter(
            f"Output directory does not exist: {output_dir}", param_hint="'-o'"
        )

    for src in input_dir:
        convert_opus_audio(src)
        batch_convert_heic_to_jpeg(src)

    mediafiles = _classify_media_files(input_dir)
    _sort_files(output_dir, mediafiles, prefix)


if __name__ == "__main__":
    main()
