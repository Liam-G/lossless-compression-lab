"""Reorder Wikipedia pages by shared text, with a byte-exact inverse by page ID."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
import re
import zlib


PAGE_START = re.compile(rb"(?m)^  <page>\n")
PAGE_END = b"\n  </page>\n"
TITLE = re.compile(rb"(?m)^    <title>([^\n]*)</title>\n")
PAGE_ID = re.compile(rb"(?m)^    <id>([0-9]+)</id>\n")
TEXT = re.compile(rb"<text\b[^>]*>")
WORD = re.compile(rb"[a-z]{3,}")
NAMESPACE = {
    b"image",
    b"wikipedia",
    b"category",
    b"template",
    b"talk",
    b"user",
    b"help",
}


@dataclass(frozen=True, slots=True)
class Page:
    page_id: int
    start: int
    stop: int
    title: bytes


def pages_in(data):
    """Keep a partial first or last page and the XML envelope outside the reorder."""
    starts = [match.start() for match in PAGE_START.finditer(data)]
    pages = []
    for index, start in enumerate(starts):
        last = index == len(starts) - 1
        if last:
            footer = data.find(PAGE_END, start)
            if footer < 0:
                break
            stop = footer + len(PAGE_END)
        else:
            stop = starts[index + 1]
            if not data.endswith(PAGE_END, start, stop):
                raise ValueError("Reordering requires contiguous complete page records")
        title = TITLE.search(data, start, stop)
        page_id = PAGE_ID.search(data, start, stop)
        if not title or not page_id:
            raise ValueError("A complete page must have a title and an integer page ID")
        pages.append(Page(int(page_id[1]), start, stop, title[1].lower()))
    return pages


def article_view(data, page):
    tag = TEXT.search(data, page.start, page.stop)
    if tag is None:
        return b""
    return data[tag.end() : min(page.stop, tag.end() + 4096)].lower().lstrip()


def layout_key(title, text):
    if text.startswith(b"#redirect"):
        return b"redirect"
    namespace, _, _ = title.partition(b":")
    if namespace in NAMESPACE:
        return b"namespace-" + namespace
    if b"households out of which" in text:
        return b"census"
    if title.startswith(b"list of "):
        return b"list"
    return b"article"


def features(title, text):
    words = WORD.findall(title) + WORD.findall(text)[:192]
    hashes = {zlib.crc32(word) for word in words}
    hashes.update(zlib.crc32(left + b" " + right) for left, right in pairwise(words))
    return hashes


def nearby_pages(rows, terms):
    """Walk a sparse graph of pages that share uncommon words or word pairs."""
    frequencies = Counter(term for page in rows for term in terms[page])
    limit = max(8, min(64, len(rows) // 8))
    retained = {}
    postings = defaultdict(list)
    for page in rows:
        candidates = (term for term in terms[page] if 2 <= frequencies[term] <= limit)
        retained[page] = sorted(candidates, key=lambda term: (frequencies[term], term))[
            :48
        ]
        for term in retained[page]:
            postings[term].append(page)

    unvisited = set(rows)
    ranks = {page: index for index, page in enumerate(rows)}
    for start in rows:
        page = start
        while page in unvisited:
            unvisited.remove(page)
            yield page
            scores = Counter()
            for term in retained[page]:
                weight = 256 // frequencies[term]
                for other in postings[term]:
                    if other in unvisited:
                        scores[other] += weight
            if not scores:
                break
            page = max(scores, key=lambda other: (scores[other], -ranks[other]))


def rearrange(data, original, order):
    if not original:
        return data
    return b"".join(
        [
            data[: original[0].start],
            *(data[page.start : page.stop] for page in order),
            data[original[-1].stop :],
        ]
    )


def encode(data, method):
    if method not in ("title", "similar"):
        raise ValueError("Unknown article order")
    pages = pages_in(data)
    if any(left.page_id >= right.page_id for left, right in pairwise(pages)):
        raise ValueError(
            "Reordering requires strictly increasing page IDs in the source"
        )
    groups = defaultdict(list)
    terms = {}
    for page in pages:
        text = article_view(data, page)
        groups[layout_key(page.title, text)].append(page)
        if method == "similar":
            terms[page] = features(page.title, text)
    order = []
    for key in sorted(groups):
        rows = sorted(groups[key], key=lambda page: (page.title, page.page_id))
        order.extend(nearby_pages(rows, terms) if method == "similar" else rows)
    moved = sum(left != right for left, right in zip(pages, order))
    return rearrange(data, pages, order), {"pages": len(pages), "moved_pages": moved}


def decode(data):
    pages = pages_in(data)
    if len({page.page_id for page in pages}) != len(pages):
        raise ValueError("Duplicate page ID in reordered data")
    return rearrange(data, pages, sorted(pages, key=lambda page: page.page_id))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("encode", "decode"))
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--method", choices=("title", "similar"), default="similar")
    args = parser.parse_args()
    data = args.source.read_bytes()
    if args.mode == "encode":
        data, stats = encode(data, args.method)
        print(stats)
    else:
        data = decode(data)
    args.destination.write_bytes(data)


if __name__ == "__main__":
    main()
