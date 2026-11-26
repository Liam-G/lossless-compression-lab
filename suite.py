"""Test every experiment or reproduce the reference measurements in a new directory."""

import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent


def run(*args, cwd=ROOT):
    subprocess.run([sys.executable, *args], cwd=cwd, check=True)


def main():
    if sys.argv[1:2]==["benchmark"]:
        run(ROOT/"research/large-scale/primary.py",*sys.argv[2:],cwd=Path.cwd())
        return
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("test")
    commands.add_parser("benchmark",help="Primary benchmarks of at least 20 MiB")
    commands.add_parser("diagnostics").add_argument("output", type=Path)
    args = parser.parse_args()
    if args.action == "diagnostics":
        args.output = args.output.resolve()
        args.output.mkdir(parents=True)
    for folder in sorted((ROOT / "experiments").iterdir()):
        number = folder.name[:2]
        if args.action == "diagnostics":
            if number == "01":
                run("benchmark.py", "--diagnostics", args.output / folder.name, cwd=folder)
            else:
                run("lab.py", number, "diagnostics", args.output / folder.name)
            continue
        if number == "01":
            run("-m", "unittest", "-v", cwd=folder)
        else:
            run("lab.py", number, "test")
        with tempfile.TemporaryDirectory() as work:
            source = ROOT / "fixtures" / "medical.bin"
            archive = Path(work) / "file.archive"
            restored = Path(work) / "file.out"
            cli = [folder / "codec.py"] if number == "01" else [ROOT / "lab.py", number]
            ref = ["--reference", ROOT / "fixtures" / "fax-mid.bin"] if number == "12" else []
            run(*cli, "encode", source, archive, *ref, cwd=work)
            run(*cli, "decode", archive, restored, *ref, cwd=work)
            if restored.read_bytes() != source.read_bytes():
                raise ValueError(f"CLI round trip failed for {folder.name}")


if __name__ == "__main__":
    main()
