import random
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import benchmark
import codec


class RepdigitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.direct = codec.catalog(False)
        cls.extended = codec.catalog(True)

    def test_catalog(self):
        for number, wire in self.extended.items():
            self.assertEqual(codec.reconstruct(wire), number)
        for number, wire in self.direct.items():
            self.assertLessEqual(len(self.extended[number]), len(wire))

    def test_edges_and_accounting(self):
        for data in (b"", b"\0", bytes(33), random.Random(42).randbytes(321)):
            for profile in codec.PROFILES:
                table = self.extended if profile.endswith("ratios") else self.direct
                archive, stats = codec.encode(data, profile, table)
                self.assertEqual(codec.decode(archive), data)
                self.assertEqual(stats["metadata_bytes"] + stats["literal_bytes"], len(archive))

    def test_off_grid_quotient(self):
        data = b"abc" + (((1 << 192) - 1) // 13).to_bytes(25, "big") + b"xyz"
        sizes = []
        for profile in codec.PROFILES:
            table = self.extended if profile.endswith("ratios") else self.direct
            archive, _ = codec.encode(data, profile, table)
            self.assertEqual(codec.decode(archive), data)
            sizes.append(len(archive))
        self.assertLess(sizes[-1], min(sizes[:-1]))

    def test_original_lab_archive(self):
        # Produced by the original repdigit_split encoder with its C++ scanner.
        archived = bytes.fromhex(
            "525053310000004e00000003000000031903602fab0000001f1803202fa0"
            "0000003a1401c06162636d6964656e64"
        )
        quotient = (((1 << 192) - 1) // 13).to_bytes(25, "big")
        expected = b"abc" + quotient + b"mid" + bytes([255]) * 24 + b"end" + bytes(20)
        self.assertEqual(codec.decode(archived), expected)

    def test_interval_choice(self):
        data = bytes(range(1, 26))
        # The longest prefix saves 10 bytes. Two adjacent matches save 11.
        table = {int.from_bytes(part, "big"): b"x" for part in (data[:17], data[:12], data[12:])}
        archive, stats = codec.encode(data, "adaptive-direct", table)
        self.assertEqual(stats["records"], 2)
        self.assertEqual(len(archive), codec.HEADER.size + len(data) - 11)

    def test_cli_and_delivered_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            source = folder / "input"
            source.write_bytes(benchmark.planted(24, 75)[0])
            script = Path(codec.__file__)
            archive, restored = folder / "encoded", folder / "restored"
            for args in (("encode", source, archive), ("decode", archive, restored)):
                subprocess.run([sys.executable, script, *args], check=True, cwd=folder)
            self.assertEqual(restored.read_bytes(), source.read_bytes())
            bundle = folder / "delivery.pyz"
            bundle.write_bytes(benchmark.package(archive.read_bytes()))
            output = subprocess.check_output([sys.executable, "-I", bundle], cwd=folder)
            self.assertEqual(output, source.read_bytes())


if __name__ == "__main__":
    unittest.main()
