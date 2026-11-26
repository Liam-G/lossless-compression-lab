"""Scan Q for exact products of small primes and cross-base repdigit quotients."""
from argparse import ArgumentParser
from collections import Counter
from hashlib import file_digest
import json
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import codec

PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53)
STRIDE = 1 + len(PRIMES)
WIDTH = 255
ZERO_ID = -1
MAGIC = b"QFT1"
MATCH = struct.Struct("<BIBI")
CAPS = (16, 32, 64, 128, WIDTH)


class Wires:
    def __init__(self, leaves):
        self.leaves = leaves

    def __getitem__(self, idx):
        if idx == ZERO_ID:
            return codec.ZERO
        leaf, factor = divmod(idx, STRIDE)
        wire = self.leaves[leaf]
        return bytes([0x80 + factor - 1]) + wire if factor else wire

    def family(self, idx):
        if idx == ZERO_ID:
            return 'zeros'
        leaf, factor = divmod(idx, STRIDE)
        kind = 'quotient' if self.leaves[leaf][0] >> 6 else 'direct'
        return 'product-' + kind if factor else kind


def decode(archive, output):
    with archive.open('rb') as f, output.open('xb') as out:
        magic, size, count = codec.HEADER.unpack(f.read(codec.HEADER.size))
        if magic != MAGIC or count > size // 8:
            raise ValueError('invalid product archive')
        patches = []
        end = 0
        for _ in range(count):
            start, width, length = codec.PATCH.unpack(f.read(codec.PATCH.size))
            if not (end <= start < start + width <= size and 1 <= length <= 5):
                raise ValueError('invalid interval')
            end = start + width
            wire = f.read(length)
            if len(wire) != length:
                raise ValueError('incomplete record')
            if wire == codec.ZERO:
                value = 0
            else:
                prime = 1
                if 128 <= wire[0] < 128 + len(PRIMES):
                    prime, wire = PRIMES[wire[0] - 128], wire[1:]
                if not wire or len(wire) > 4 or wire[0] >> 6 > 1:
                    raise ValueError('invalid repdigit leaf')
                value = prime * codec.reconstruct(wire)
            patches.append((start, value.to_bytes(width, 'big')))
        end = 0
        for start, value in patches:
            codec.copy(f, out, start - end)
            out.write(value)
            end = start + len(value)
        codec.copy(f, out, size - end)
        if f.read(1):
            raise ValueError('trailing data')


def plant(path):
    rng = Random(7283)
    with path.open('xb') as f:
        for i in range(256):
            # The repunit denominators are 7 (111 base 2) and 13 (111 base 3).
            if i % 2:
                r = 6 * rng.randint(15, 166)
                leaf, rem = divmod((3 ** r - 1) // 2, 7)
            else:
                r = 12 * rng.randint(7, 80)
                leaf, rem = divmod(2 ** r - 1, 13)
            assert rem == 0
            n = rng.choice(PRIMES[7:]) * leaf
            f.write(rng.randbytes(rng.randrange(9, 30)))
            f.write(n.to_bytes((n.bit_length() + 7) // 8 + rng.randrange(3), 'big'))
        f.write(((1 << 2039) - 1).to_bytes(255, 'big'))


def digest(path):
    with path.open('rb') as f:
        return file_digest(f, 'sha256').hexdigest()


def score(source, matches, wires, work, output, name):
    size = source.stat().st_size
    matches.extend(codec.zeroes(source, size, ZERO_ID, WIDTH))
    base = {'direct', 'quotient', 'zeros'}
    arms = {'leaf': base, 'factor_direct': base | {'product-direct'},
            'factor_both': base | {'product-direct', 'product-quotient'}}
    rows = []
    verified = {}
    winner = None
    for cap in CAPS:
        for arm, families in arms.items():
            choices = [m for m in matches if m[1] <= cap and wires.family(m[2]) in families]
            selected, gain = codec.select(choices, wires)
            signature = tuple(selected)
            archive_size = size + codec.HEADER.size - gain
            if signature not in verified:
                archive = work / f'{name}.{len(verified)}.qft'
                restored = work / 'restored'
                codec.encode(source, archive, selected, wires, magic=MAGIC)
                assert archive.stat().st_size == archive_size
                subprocess.run([sys.executable, '-I', '-B', __file__, 'decode', archive, restored], check=True)
                subprocess.run(['cmp', source, restored], check=True)
                restored.unlink()
                verified[signature] = archive
            rows.append(dict(cap=cap, arm=arm, archive_bytes=archive_size,
                             selected=dict(Counter(wires.family(i) for _, _, i in selected)),
                             widths=dict(sorted(Counter(w for _, w, _ in selected).items()))))
            if cap == WIDTH and arm == 'factor_both':
                winner = verified[signature]
    report = dict(dataset=name, bytes=size, sha256=digest(source), variants=rows,
                  distinct_streams_verified=len(verified), archive_sha256=digest(winner))
    if name == 'Q':
        winner.replace(output / 'Q.qft')
    for archive in verified.values():
        archive.unlink(missing_ok=True)
    return report


def bench(args):
    args.output.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=args.output) as tmp:
        work = Path(tmp)
        bank = work / 'leaves'
        wires, _, _, meta = codec.bank_file(bank, max_width=WIDTH)
        print(json.dumps(meta), flush=True)
        wires = Wires(wires)
        planted = work / 'planted'
        plant(planted)
        random_file = work / 'uniform'
        rng = Random(972165)
        with random_file.open('wb') as f:
            remaining = args.q.stat().st_size
            while remaining:
                chunk = min(1 << 20, remaining)
                f.write(rng.randbytes(chunk))
                remaining -= chunk
        datasets = [('planted', planted), ('Q', args.q), ('uniform', random_file)]
        raw = subprocess.check_output([args.scanner, bank, *[p for _, p in datasets]])
        matches = [[] for _ in datasets]
        for file, start, width, recipe in MATCH.iter_unpack(raw):
            matches[file].append((start, width, recipe))
        with (args.output / 'quotient-results.json').open('w') as log:
            reports = []
            for (name, path), found in zip(datasets, matches):
                report = score(path, found, wires, work, args.output, name)
                reports.append(report)
                print(name, len(found), [r['archive_bytes'] for r in report['variants'][-3:]], flush=True)
            json.dump(dict(bank=meta, datasets=reports), log, indent=2)
            log.write('\n')


if __name__ == '__main__':
    parser = ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    dec = sub.add_parser('decode')
    dec.add_argument('archive', type=Path)
    dec.add_argument('output', type=Path)
    run = sub.add_parser('bench')
    run.add_argument('q', type=Path)
    run.add_argument('scanner', type=Path)
    run.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.mode == 'bench':
        bench(args)
    else:
        decode(args.archive, args.output)
