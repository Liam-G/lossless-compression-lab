"""Strict lower triangles of distances derived from corpus coordinates or seeded points."""

import argparse
import hashlib
import json
import mmap
from pathlib import Path
import re

import numpy as np

COUNT = 4600
COORD = re.compile(
    rb"\{\{coor(?:dinates)?[ _]+(?:dms|dm|d)\s*\|([^}\r\n]{4,160})", re.I
)


def coordinates(path):
    result = {}
    with (
        path.open("rb") as src,
        mmap.mmap(src.fileno(), 0, access=mmap.ACCESS_READ) as data,
    ):
        for match in COORD.finditer(data):
            fields = [x.strip().upper() for x in match[1].split(b"|")]
            try:
                ns = next(i for i, v in enumerate(fields) if v in (b"N", b"S"))
                ew = next(i for i, v in enumerate(fields) if v in (b"E", b"W"))

                def angle(pieces):
                    if not 1 <= len(pieces) <= 3:
                        raise ValueError()
                    values = [float(v) for v in pieces]
                    if any(x < 0 or not np.isfinite(x) for x in values) or any(
                        x >= 60 for x in values[1:]
                    ):
                        raise ValueError()
                    return sum(x / 60**j for j, x in enumerate(values))

                lat = angle(fields[:ns]) * (-1 if fields[ns] == b"S" else 1)
                lon = angle(fields[ns + 1 : ew]) * (-1 if fields[ew] == b"W" else 1)
                if abs(lat) <= 90 and abs(lon) <= 180:
                    result[round(lat, 8), round(lon, 8)] = None
            except (StopIteration, ValueError):
                continue
            if len(result) == COUNT:
                break
        # Some articles give the coordinates as individually named infobox fields.
        for m in re.finditer(rb"(?i)\blatd\s*=\s*([0-9.]+)", data):
            fields = dict(
                re.findall(
                    rb"(?i)\b(latd|latm|lats|latns|longd|longm|longs|longew)\s*=\s*([a-z0-9.]+)",
                    data[m.start() : m.start() + 215].lower(),
                )
            )
            try:

                def named(prefix, sign):
                    degrees = float(fields[prefix + b"d"])
                    minutes = float(fields.get(prefix + b"m", b"0"))
                    seconds = float(fields.get(prefix + b"s", b"0"))
                    if minutes >= 60 or seconds >= 60:
                        raise ValueError()
                    return (degrees + minutes / 60 + seconds / 3600) * sign

                if fields[b"latns"] not in (b"n", b"s") or fields[b"longew"] not in (
                    b"e",
                    b"w",
                ):
                    continue
                lat = named(b"lat", -1 if fields[b"latns"] == b"s" else 1)
                lon = named(b"long", -1 if fields[b"longew"] == b"w" else 1)
                if abs(lat) <= 90 and abs(lon) <= 180:
                    result[round(lat, 8), round(lon, 8)] = None
            except (KeyError, ValueError):
                continue
            if len(result) == COUNT:
                break
    if len(result) < COUNT:
        raise ValueError(f"Found {len(result)} distinct coordinate pairs")
    phi, lam = np.radians(list(result)).T
    return np.stack(
        (np.cos(phi) * np.cos(lam), np.cos(phi) * np.sin(lam), np.sin(phi)), axis=1
    )


def write_distances(path, points, scale, angular=False):
    with path.open("xb") as f:
        for i in range(1, len(points)):
            dist = np.sqrt(np.square(points[:i] - points[i]).sum(axis=1))
            if angular:
                dist = 2 * np.arcsin(np.clip(dist / 2, 0, 1))
            f.write(np.rint(dist * scale).clip(0, 65535).astype("<u2").tobytes())
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("enwik9", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument(
        "--only",
        nargs="+",
        choices=(
            "place-distances",
            "walk-distances",
            "arc-distances",
            "random-triangle",
        ),
    )
    a = p.parse_args()
    a.out.mkdir(exist_ok=True, parents=True)
    places = coordinates(a.enwik9)
    rng = np.random.default_rng(777)
    walk = np.cumsum(rng.normal(0, 1, (COUNT, 2)), axis=0)
    scale = 65535 / np.linalg.norm(np.ptp(walk, axis=0))
    manifest_path = a.out / "distances.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name, points, units in (
        ("place-distances", places, 65535 / 2),
        ("walk-distances", walk, scale),
        ("arc-distances", places, 65535 / np.pi),
    ):
        if a.only and name not in a.only:
            continue
        path = a.out / name
        manifest[name] = dict(
            sha256=write_distances(path, points, units, name == "arc-distances"),
            bytes=path.stat().st_size,
            vertices=len(points),
            dimensions=points.shape[1],
            scale=units,
        )
    if not a.only or "random-triangle" in a.only:
        from random import Random

        path = a.out / "random-triangle"
        random_bytes = Random(77091).randbytes(COUNT * (COUNT - 1))
        with path.open("xb") as stream:
            stream.write(random_bytes)
        manifest[path.name] = dict(
            sha256=hashlib.sha256(random_bytes).hexdigest(),
            bytes=len(random_bytes),
            vertices=COUNT,
            seed=77091,
        )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
