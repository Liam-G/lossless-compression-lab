"""Fast regression checks for original archive compatibility and the new codecs."""

from hashlib import sha256
from pathlib import Path
import random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
FIXTURES = ROOT / "hierarchical-gf2/fixtures"


def run(*args):
    return subprocess.check_output(args)


class ResearchCodecs(unittest.TestCase):
    def roundtrip(self, engine, data, encode="encode", decode="decode", options=()):
        with TemporaryDirectory() as directory:
            source, archive, restored = (
                Path(directory) / name for name in ("source", "archive", "restored")
            )
            source.write_bytes(data)
            run(*engine, encode, source, archive, *options)
            run(*engine, decode, archive, restored)
            self.assertEqual(restored.read_bytes(), data)
            return archive.read_bytes()

    def test_quartic_original_width(self):
        for data in (b"", bytes(12), b"\x00\x00\x01", b"\x00" + bytes(range(128))):
            self.roundtrip([sys.executable, ROOT / "quartic-trees/codec.py"], data)

    def test_seeded_tree_with_zero_prefixed_children(self):
        with TemporaryDirectory() as directory:
            base = Path(directory)
            data = (bytes(15) + b"\x03") * 19 + b"\xff"
            (base / "input").write_bytes(data)
            run(
                BUILD / "factor-tree",
                "split-seeded",
                base / "input",
                base / "tree",
                base / "levels",
                "16",
                "9,11",
                "2",
            )
            run(BUILD / "factor-tree", "join", base / "tree", base / "out")
            self.assertEqual((base / "out").read_bytes(), data)

    def test_original_whiteboard_record(self):
        with TemporaryDirectory() as directory:
            dest = Path(directory) / "decoded"
            run(
                sys.executable,
                ROOT / "whiteboard-trees/tree.py",
                "decode",
                ROOT / "whiteboard-trees/original-control.qbt",
                dest,
            )
            self.assertEqual(dest.stat().st_size, 1572864)
            self.assertEqual(
                sha256(dest.read_bytes()).hexdigest(),
                "bad606ca440dbf05adf65b2ee810664b824b2cc4d633cf9da8e67062caca9075",
            )

    def test_nested_factor_placement(self):
        sys.path.insert(0, str(ROOT / "whiteboard-trees"))
        import factor_forest
        from benchmark_forest import cases

        _, data = next(cases(Path(".")))
        data = data[:4096] + b"tail"
        best = factor_forest.encode(data, "nested")
        decoded, stats = factor_forest.decode(best)
        self.assertEqual(decoded, data)
        self.assertGreater(stats["formula_below_factor"], 0)
        self.assertGreater(stats["split_below_factor"], 0)
        self.assertLess(len(best), len(factor_forest.encode(data, "leaf-factor")))

    def test_hierarchical_compatibility(self):
        engine = [sys.executable, ROOT / "hierarchical-gf2/codec.py"]
        data = (FIXTURES / "rank-4-evolved.bin").read_bytes()
        self.assertEqual(
            self.roundtrip(engine, data, "pack", "unpack"),
            (FIXTURES / "rank-4-evolved.gfh").read_bytes(),
        )

    def test_3d_reversibility_and_panel_ranks(self):
        sys.path.insert(0, str(ROOT / "tensor-orbits"))
        import codec as tensor

        rng = random.Random(1367)
        for depth in (1, 3, 64):
            data = rng.randbytes(128 * depth)
            for rule in (0, 1):
                state = bytearray(data)
                for _ in range(4):
                    tensor.advance(state, rule, False)
                for _ in range(4):
                    tensor.advance(state, rule, True)
                self.assertEqual(state, data)
        rows = tensor.panels(bytes(128)).copy()
        rows[1] = [0, 11] * 8
        rows[2] = [0, 11, 19, 11 ^ 19] * 4
        rows[3] = list(range(16))
        mixed = tensor.restore_panels(rows)
        self.assertEqual(tensor.unfactor(tensor.factor(mixed), len(mixed)), mixed)
        self.roundtrip(
            [sys.executable, ROOT / "tensor-orbits/codec.py"], mixed * 64 + b"tail"
        )

    def test_fax_reference_archive(self):
        reference = ROOT / "shape-context/results/ptt5.scx"
        with TemporaryDirectory() as directory:
            restored = Path(directory) / "fax"
            rebuilt = Path(directory) / "archive"
            run(BUILD / "shape", "decode", reference, restored)
            self.assertEqual(restored.stat().st_size, 513216)
            self.assertEqual(
                sha256(restored.read_bytes()).hexdigest(),
                "0ec3a75089bb52342813496b17e51377bc9eba3cb519a444d67025354841d650",
            )
            run(BUILD / "shape", "encode", restored, rebuilt)
            self.assertEqual(rebuilt.read_bytes(), reference.read_bytes())

    def test_shape_fallback_and_coded_streams(self):
        for data in (b"", b"\x00", bytes(range(255)), bytes(8192)):
            archive = self.roundtrip([BUILD / "shape"], data)
            if not data:
                self.assertEqual(archive[14], 255)
            elif len(data) == 8192:
                self.assertLess(archive[14], 3)
                self.assertLess(len(archive), 100)


if __name__ == "__main__":
    unittest.main(verbosity=2)
