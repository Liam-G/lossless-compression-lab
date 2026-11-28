"""Check every relative link and #anchor in the repository's Markdown files (GitHub slug rules, approximately).

    python3 report/check_links.py
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r"\]\(([^)\s]+)\)|(?:src|srcset)=\"([^\"]+)\"")


def slugs(path):
    out, seen = set(), {}
    text = path.read_text(errors="replace")
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if not m:
            continue
        h = re.sub(r"<[^>]+>", "", m.group(2))
        h = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", h)
        s = re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-")
        n = seen.get(s, 0)
        seen[s] = n + 1
        out.add(s if n == 0 else f"{s}-{n}")
    for a in re.findall(r'<a (?:name|id)="([^"]+)"', text):
        out.add(a)
    return out


def main():
    bad = 0
    cache = {}
    files = [p for p in ROOT.rglob("*.md") if "runs" not in p.parts and ".git" not in p.parts]
    for md in files:
        text = re.sub(r"```.*?```", "", md.read_text(errors="replace"), flags=re.S)
        for m in LINK.finditer(text):
            url = m.group(1) or m.group(2)
            if re.match(r"^[a-z]+:", url) or url.startswith("mailto"):
                continue
            path, _, anchor = url.partition("#")
            target = (md.parent / path).resolve() if path else md
            if not target.exists():
                print(f"{md.relative_to(ROOT)}: missing {url}")
                bad += 1
                continue
            if anchor and target.suffix == ".md":
                if target not in cache:
                    cache[target] = slugs(target)
                if anchor.lower() not in cache[target]:
                    print(f"{md.relative_to(ROOT)}: missing anchor {url}")
                    bad += 1
    print(f"{len(files)} files checked, {bad} broken links")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
