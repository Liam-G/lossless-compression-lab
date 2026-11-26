"""Run one subprocess and record Linux's maximum resident set size in KiB."""

import resource
import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    result = subprocess.run(sys.argv[2:])
    if result.returncode == 0:
        Path(sys.argv[1]).write_text(
            str(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
        )
    raise SystemExit(result.returncode)
