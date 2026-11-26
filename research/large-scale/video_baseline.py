"""FFV1 or lossless H.264 in Matroska on exactly the benchmark grayscale frames."""

import argparse
from pathlib import Path
import subprocess

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("ffv1", "h264lossless", "decode"))
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-n"]
    if a.mode == "decode":
        cmd += [
            "-threads",
            "2",
            "-i",
            a.input,
            "-map",
            "0:v:0",
            "-pix_fmt",
            "gray",
            "-threads",
            "1",
            "-f",
            "rawvideo",
            a.output,
        ]
    else:
        cmd += [
            "-f",
            "rawvideo",
            "-pixel_format",
            "gray",
            "-video_size",
            "640x360",
            "-framerate",
            "25",
            "-i",
            a.input,
            "-map",
            "0:v:0",
            "-threads",
            "2",
        ]
        if a.mode == "ffv1":
            cmd += ["-c:v", "ffv1", "-level", "3", "-coder", "1", "-context", "1"]
        else:
            cmd += [
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-qp",
                "0",
                "-color_range",
                "pc",
            ]
        cmd += [
            "-fflags",
            "+bitexact",
            "-flags:v",
            "+bitexact",
            "-f",
            "matroska",
            a.output,
        ]
    subprocess.run(cmd, check=True)
