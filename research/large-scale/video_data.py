"""Extract a reproducible 128-frame luma volume from each locally installed clip."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

CLIPS = {
    "luma-kath": "sddm-astronaut-theme/Backgrounds/hyprland_kath.mp4",
    "luma-jake": "sddm-astronaut-theme/Backgrounds/jake_the_dog.mp4",
    "luma-rei": "silent/backgrounds/rei.mp4",
}


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("themes", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    a.output.mkdir(exist_ok=True, parents=True)
    result = {}
    for name, rel in CLIPS.items():
        source = a.themes / rel
        target = a.output / name
        with target.open("xb") as out:
            subprocess.run(
                [
                    "ffmpeg",
                    "-loglevel",
                    "error",
                    "-threads",
                    "2",
                    "-i",
                    source,
                    "-map",
                    "0:v:0",
                    "-frames:v",
                    "128",
                    "-vf",
                    "scale=640:360:flags=area,format=gray",
                    "-filter_threads",
                    "1",
                    "-threads",
                    "1",
                    "-f",
                    "rawvideo",
                    "pipe:1",
                ],
                stdout=out,
                check=True,
            )
        if target.stat().st_size != 640 * 360 * 128:
            raise ValueError("Missing frames")
        result[name] = dict(
            bytes=target.stat().st_size,
            sha256=digest(target),
            source=rel,
            source_sha256=digest(source),
            width=640,
            height=360,
            frames=128,
        )
    (a.output / "videos.json").write_text(json.dumps(result, indent=2) + "\n")
