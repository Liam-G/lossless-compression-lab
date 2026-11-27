"""Regression checks for exact transforms, independent decoding and benchmark accounting."""

from contextlib import contextmanager
from importlib.util import module_from_spec, spec_from_file_location
from io import BytesIO
import json
import os
from pathlib import Path
from random import Random
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
RESEARCH = HERE.parent
ROOT = RESEARCH.parent


@contextmanager
def engine(folder, filename="codec"):
    directory = RESEARCH / folder
    key = "test_" + folder.replace("-", "_") + filename
    spec = spec_from_file_location(key, directory / (filename + ".py"))
    module = module_from_spec(spec)
    before = list(sys.path)
    previous = sys.modules.pop("codec", None)
    try:
        sys.path.insert(0, str(directory))
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path[:] = before
        sys.modules.pop("codec", None)
        if previous is not None:
            sys.modules["codec"] = previous


class ReversibleModels(unittest.TestCase):
    def test_ragged_rows_and_field_lanes(self):
        with engine("lattice-prediction", "ragged") as r:

            def roundtrip(raw, modes):
                for mode in modes:
                    with self.subTest(mode=mode, length=len(raw)):
                        prepared, restored = BytesIO(), BytesIO()
                        r.encode(BytesIO(raw), prepared, mode)
                        prepared.seek(0)
                        r.decode(prepared, restored)
                        self.assertEqual(restored.getvalue(), raw)

            raw = b'\x00\n\n"X,Y",,,,a,b,c,d,e,f,g,h,i,j\r\n'
            raw += b"\n".join(bytes([n % 256]) * n for n in (254, 255, 256))
            for data in (b"", b"\n", raw, bytes(range(256)) * 3):
                roundtrip(data, r.PROFILES)
            roundtrip(b"a" * (r.BLOCK - 4) + b",abcde\nabcdef", r.PROFILES)
            token = b"k" * 65539
            roundtrip(token + b",0\n" + token + b",1", ("prefix", "field-prefix"))
            stream = r.field_stream(b"aa,10\nb,2", 9, "fields")
            self.assertEqual(stream[:32], bytes.fromhex("0000000500000004") + bytes(24))
            self.assertEqual(stream[32:], b"aa,b,10\n2")
            with self.assertRaises(ValueError):
                r.field_stream(bytes(32) + stream[32:], 9, "fields", True)
            with self.assertRaises(ValueError):
                r.front_stream(b"\x00\x00\x00\x01\x01", 1, "prefix", True)
            prepared = BytesIO()
            r.encode(BytesIO(raw), prepared, "joint")
            for bad in (prepared.getvalue()[:-1], prepared.getvalue() + b"x"):
                with self.assertRaises(ValueError):
                    r.decode(BytesIO(bad), BytesIO())

    def test_row_shuffle_and_match_probe(self):
        with engine("lattice-prediction", "row_inputs") as inputs:
            raw = b"mississippi\n\nabba dabba\nabc" * 50

            def shuffled():
                return inputs.permute_rows(raw, np.random.default_rng(34))

            result = shuffled()
            self.assertEqual(shuffled(), result)
            self.assertNotEqual(raw, result)
            self.assertEqual(
                [sorted(r) for r in raw.split(b"\n")],
                [sorted(r) for r in result.split(b"\n")],
            )
        with engine("lattice-prediction", "match_probe") as probe:
            raw = b"abcdxxabcdyyabcdxxabcdbb" * 6
            lengths = []
            for i in range(0, len(raw) - 16 + 1, 3):
                prior = next(
                    (
                        j
                        for j in range(i - 1, max(-1, i - 21), -1)
                        if raw[j : j + 4] == raw[i : i + 4]
                    ),
                    None,
                )
                length = 0
                while (
                    prior is not None
                    and length < 16
                    and raw[prior + length] == raw[i + length]
                ):
                    length += 1
                lengths.append(length)
            row = probe.measure(raw, stride=3, window=20, limit=16)
            self.assertEqual(row["matched_bytes"], sum(lengths))
            self.assertEqual(row["at_cap"], lengths.count(16))
            repeated = probe.measure(b"abcd" * 32810)
            self.assertEqual(repeated["at_cap"], repeated["samples"] - 1)

    def test_carry_and_sparse_scales(self):
        rng = Random(73)
        with engine("carry-trees") as c:
            for length in (0, 1, 2, 17, 129):
                sample = b"\0" + rng.randbytes(length) if length else b""
                for factor in c.FACTORS:
                    for direction in (True, False):
                        self.assertEqual(
                            c.transform(
                                c.transform(sample, factor, direction),
                                factor,
                                not direction,
                            ),
                            sample,
                        )
            archive = BytesIO()
            c.pack(BytesIO(b"\0x" * 65539), archive, "joint")
            with self.assertRaises(ValueError):
                c.unpack(BytesIO(archive.getvalue()[:-1]), BytesIO())
        with engine("carry-trees", "sparse_scale") as s:
            for n in (0, 1, 5, 128, 153):
                raw = rng.randbytes(n)
                self.assertEqual(s.nibble_lanes(s.nibble_lanes(raw), True), raw)
            raw = b"a" * 17001 + rng.randbytes(11000)
            packed, _ = s.encode(raw, "regions")
            self.assertEqual(s.decode(packed), raw)

    def test_formula_leaf_references_and_escapes(self):
        with engine("shared-factor-forest") as c:
            n = 16
            p = 7
            basis = c.forest.book()
            a, b = [v for v in basis if 10 < v < 2**40][:2]
            bits = (((1 << 128) // p).bit_length()) // 2
            raw = (
                b"".join(
                    (p * ((x << bits) + y) + offset).to_bytes(n, "big")
                    for x, y, offset in ((a, b, 0), (b, a, -1), (a, a, 1), (b, b, 2))
                )
                + b"tail"
            )
            for mode in (c.INLINE, c.SHARED):
                coded = c.transformed(raw, n, p, mode, basis)
                self.assertEqual(c.inverse(coded, len(raw), n, p, mode), raw)
                with self.assertRaises(ValueError):
                    c.inverse(coded[:-1], len(raw), n, p, mode)

    def test_four_axes_and_equivalent_factors(self):
        rng = np.random.default_rng(4451)
        with engine("four-dimensional-factors") as c:
            for shape in ((1, 1, 1, 1), (2, 2, 3, 1), (3, 5, 7, 3)):
                actual = rng.integers(0, 256, shape, dtype=np.uint8)
                for rule in (0, 1):
                    field = actual.copy()
                    c.evolve(field, rule, False)
                    c.evolve(field, rule, True)
                    np.testing.assert_array_equal(field, actual)
            raw = rng.bytes(16 * 89)
            for equivalent in (False, True):
                self.assertEqual(c.matrix(c.matrix(raw, equivalent), inverse=True), raw)
            with self.assertRaises(ValueError):
                c.matrix(b"bad")

    def test_bitmap_tree_wire_format_and_tails(self):
        with engine("checkerboard-orbits", "bitmap") as b:
            # The first 8x8 tile contains exactly one pixel. The first quadrant
            # at each of three levels is occupied, and row zero of the leaf is 0x80.
            grid = np.zeros((32, b.ROW), np.uint8)
            grid[0, 0] = 128
            tree = b.layout(grid, "tree")
            root = bytes([128]) + bytes(6)
            self.assertEqual(tree, root + b"\x80\x80\x80" + bytes(7))
            for bad in (tree[:-1], tree + b"?", root + bytes(2)):
                with self.assertRaises(ValueError):
                    b.unlayout(bad, 32, "tree")
            rng = np.random.default_rng(13)
            for raw in (b"", b"\0", bytes(7936), rng.bytes(17), rng.bytes(b.BLOCK + 3)):
                for mode in b.PROFILES:
                    with self.subTest(size=len(raw), mode=mode):
                        prepared, decoded = BytesIO(), BytesIO()
                        b.encode(BytesIO(raw), prepared, mode)
                        prepared.seek(0)
                        b.decode(prepared, decoded)
                        self.assertEqual(decoded.getvalue(), raw)
            mixed = rng.integers(0, 256, (32, b.ROW), dtype=np.uint8)
            mixed[:, 10:40] = mixed[:, :1]
            for mode in ("book", "planes", "hot", "hotplanes"):
                body = b.layout(mixed, mode)
                np.testing.assert_array_equal(b.unlayout(body, 32, mode), mixed)
                with self.assertRaises(ValueError):
                    b.unlayout(body[:-1], 32, mode)

    def test_bitmap_checker_zero_boundaries(self):
        with engine("checkerboard-orbits", "bitmap") as b:
            raw = np.array([[0x81, 0x81], [0x24, 0x18], [0xFF, 0x01]], np.uint8)
            for rotated in (False, True):
                expected = np.unpackbits(raw, axis=1)
                for parity in (0, 1):
                    previous = np.pad(expected, 1)
                    for y, x in np.ndindex(expected.shape):
                        if (x + y) % 2 == parity:
                            left, right = previous[y + 1, x], previous[y + 1, x + 2]
                            above, below = previous[y, x + 1], previous[y + 2, x + 1]
                            if rotated:
                                left, right, above, below = above, below, left, right
                            expected[y, x] ^= (left & right) ^ (above | below)
                result = b.checker(raw, forward=True, rotated=rotated)
                np.testing.assert_array_equal(result, np.packbits(expected, axis=1))
                np.testing.assert_array_equal(
                    b.checker(result, forward=False, rotated=rotated), raw
                )

    def test_checkerboard_matches_cell_update(self):
        def phase(word, even):
            dst = word

            def bit(x, y):
                return (word >> (8 * (y % 8) + (x % 8))) & 1

            for y in range(8):
                for x in range(8):
                    if ((x + y) % 2 == 0) == even:
                        flip = (bit(x - 1, y) & bit(x + 1, y)) ^ (
                            bit(x, y - 1) | bit(x, y + 1)
                        )
                        dst ^= flip << (8 * y + x)
            return dst

        with engine("checkerboard-orbits") as c:
            source = np.array([3, 0, 0xC41E1100345527A3], dtype="<u8")
            dst = source.copy()
            c.evolve(dst, 1)
            self.assertEqual(
                dst.tolist(), [phase(phase(int(w), False), True) for w in source]
            )
            dst = source.copy()
            times = np.array([0, 1, 1000], dtype="<u2")
            c.evolve(dst, times=times)
            c.evolve(dst, times=times, inverse=True)
            np.testing.assert_array_equal(dst, source)

    def test_text_empty_elements_and_full_alphabet(self):
        with engine("text-views") as c:
            for raw in (
                b"banana",
                b"\0",
                bytes(range(256)) * 3,
                b'<page><text xml:space="preserve"></text></page>' * 35,
            ):
                self.assertEqual(c.sort_context(c.sort_context(raw), True), raw)
                self.assertEqual(c.mtf(c.mtf(raw), True), raw)
                for pieces in c.TEXT[1:]:
                    try:
                        view = c.textfront.encode(raw, pieces)
                    except ValueError:
                        continue
                    self.assertEqual(c.textfront.decode(view), raw)
                archive = BytesIO()
                c.encode(BytesIO(raw), archive, "joint")
                out = BytesIO()
                c.decode(BytesIO(archive.getvalue()), out)
                self.assertEqual(out.getvalue(), raw)

    def test_wavelet_boundaries(self):
        rng = np.random.default_rng(53)
        with engine("reversible-wavelets") as c:
            for h, w in ((1, 1), (7, 1), (8, 9), (3, 257)):
                image = rng.integers(0, 256, (h, w, 3), dtype=np.uint8)
                for depth in (0, 1, 3):
                    for chromatic in (False, True):
                        state = image.astype(np.int32)
                        if chromatic:
                            state = c.color(state)
                        c.lift(state, depth, False)
                        restored = c.restore(
                            c.coefficients(state, depth), image.shape, depth, chromatic
                        )
                        np.testing.assert_array_equal(image, restored)

    def test_distance_triangle_and_modular_errors(self):
        with engine("distance-geometry") as c:
            self.assertIsNone(c.dimension(37))
            points = np.random.default_rng(999).integers(-2000, 2000, (64, 3))
            words = np.concatenate(
                [
                    np.rint(np.linalg.norm(points[:i] - points[i], axis=1)).astype(
                        "<u2"
                    )
                    for i in range(1, len(points))
                ]
            )
            for spherical in (False, True):
                verts, _ = c.landmarks(
                    c.sphere_tables()[0][words] if spherical else words, 64, 3
                )
                noisy = words.copy()
                a, b = [i for i in range(64) if i not in verts][:2]
                noisy[b * (b - 1) // 2 + a] = 65535
                cols = [c.column(noisy, 64, v) for v in verts]
                delta = c.transform(noisy, 64, verts, cols, spherical=spherical)
                np.testing.assert_array_equal(
                    c.transform(delta, 64, verts, cols, True, spherical), noisy
                )
            self.assertEqual(c.decode(c.encode(b"odd", "all")[0]), b"odd")

    def test_glyph_alignment_and_exact_fuzzy_correction(self):
        with engine("glyph-residuals") as c:
            stamp = np.eye(12, dtype=np.uint8) | np.fliplr(np.eye(12, dtype=np.uint8))
            stamp[5:7, :] = 1
            key = (12, 12, np.packbits(stamp).tobytes())
            diff = stamp.copy()
            diff[5, 3] ^= 1
            variant = (12, 12, np.packbits(diff).tobytes())
            entries = [(key, 3, 4), (key, 24, 4), (key, 1, 19), (variant, 20, 22)]
            bank = c.dictionary(entries)
            self.assertEqual(bank, [key])
            events = c.classify(entries, bank, True)
            self.assertEqual(len(events), 4)
            for align in (0, 1):
                body = bytes([1, 12, 12]) + key[2] + c.event_bytes(events, bank, align)
                decoded, book = c.read_metadata(body)
                self.assertEqual(sorted(decoded), sorted(events))
                self.assertEqual(book, bank)
            bitmap = np.zeros((64, 64), np.uint8)
            for k, x, y in entries:
                bitmap[y : y + 12, x : x + 12] |= c.texture(k)
            packed = np.packbits(bitmap, axis=1)
            residual = c.apply(packed, events, bank)
            self.assertEqual(sum(v.bit_count() for v in residual), 1)
            self.assertEqual(
                c.apply(np.frombuffer(residual, np.uint8).reshape(-1, 8), events, bank),
                packed.tobytes(),
            )

    def test_motion_edges(self):
        with engine("motion-residuals") as c:
            frame = np.random.default_rng(168).integers(
                0, 256, (39, 47), dtype=np.uint8
            )
            vectors = np.zeros(c.vector_size(*frame.shape), np.int8)
            vectors[0] = -127
            with self.assertRaises(ValueError):
                c.warp(frame, vectors)
            data = (
                frame.tobytes() + np.roll(frame, 2, axis=1).tobytes() + frame.tobytes()
            )
            archive = BytesIO()
            c.pack(BytesIO(data), archive, "joint", 47, 39)
            out = BytesIO()
            c.unpack(BytesIO(archive.getvalue()), out)
            self.assertEqual(out.getvalue(), data)

    def test_collection_native_equivalence(self):
        import collection

        rng = Random(137)
        reference = collection.module_for(7)
        with engine("hierarchical-gf2") as native:
            for placement in ("pre", "post"):
                for depth in (1, 3):
                    for rows in (
                        (0,) * 16,
                        tuple(rng.randrange(65536) for _ in range(16)),
                    ):
                        self.assertEqual(
                            reference.encode_block(rows, placement, 4, depth, 2),
                            native.encode_block(
                                rows,
                                "full" if placement == "pre" else placement,
                                4,
                                depth,
                                2,
                            ),
                        )
        raw = (b"a" * 33000) + b"fin"
        first = BytesIO()
        second = BytesIO()
        collection.encode(BytesIO(raw), first, 7, "pre-1", workers=1, native=False)
        collection.encode(BytesIO(raw), second, 7, "pre-1", workers=2, native=True)
        self.assertEqual(first.getvalue(), second.getvalue())
        out = BytesIO()
        collection.decode(BytesIO(second.getvalue()), out)
        self.assertEqual(out.getvalue(), raw)

    def test_learned_cellular_rule_and_basis(self):
        with engine("learned-cellular-rules") as c:
            rng = np.random.default_rng(208)
            for shape in ((1, 1, 1), (2, 3, 5), (7, 9, 13)):
                grid = rng.integers(0, 256, shape, dtype=np.uint8)
                np.testing.assert_array_equal(c.planes(c.planes(grid), True), grid)
                for second in (False, True):
                    rules = c.fit(grid, second)
                    residual = c.transform(grid, rules, second)
                    np.testing.assert_array_equal(
                        c.transform(residual, rules, second, True), grid
                    )
                    learned, basis = c.coupled_fit(grid, second)
                    residual = c.transform(grid, learned, second)
                    values = c.change_basis(residual, basis)
                    np.testing.assert_array_equal(
                        c.change_basis(values, basis, True), residual
                    )
            with self.assertRaises(ValueError):
                c.change_basis(grid, bytes(8))

    def test_text_templates_page_order_and_eager_dictionary(self):
        with engine("wiki-structures") as c:
            lines = [
                b"    <title>Shared target</title>",
                b"Paragraph [[Shared target|a]] and [[Other destination]].",
            ]
            raw = b"\n".join(lines * 20) + b"\n[[Other destination#section]]"
            self.assertEqual(c.unlink(c.link_view(raw)), raw)
            for arithmetic in (False, True):
                view, _ = c.wiki_templates.encode(raw, arithmetic)
                self.assertEqual(c.wiki_templates.decode(view), raw)
            page = b"  <page>\n    <title>%s</title>\n    <id>%d</id>\n      <text>%s</text>\n  </page>\n"
            source = (
                b"prefix\n"
                + page % (b"Z", 1, b"[[A]]")
                + page % (b"A", 19, b"group")
                + b"partial"
            )
            for ordering in ("title", "similar"):
                view, stats = c.wiki_order.encode(source, ordering)
                self.assertEqual(stats["pages"], 2)
                self.assertEqual(c.wiki_order.decode(view), source)
            with self.assertRaises(ValueError):
                c.wiki_order.encode(
                    page % (b"A", 5, b"x") + page % (b"A", 5, b"x"), "title"
                )

    def test_learned_glyph_positions(self):
        with engine("glyph-residuals") as c:
            bank = [(8, 8, b"\xff" * 8), (5, 6, b"\x8f" * 4)]
            events = [
                (i * 12 + j % 2, 10 * j + (i % 2) * 2, i % 2)
                for j in range(50)
                for i in range(15)
            ]
            body = c.placement.encode(events, bank)
            decoded, book = c.placement.decode(body)
            self.assertEqual(book, bank)
            self.assertEqual(sorted(decoded), sorted(events))

    def test_reference_pin_and_direct_mode(self):
        with engine("arithmetic-references") as c, TemporaryDirectory() as td:
            f = Path(td)
            source = f / "source"
            base = f / "base"
            raw = Random(519).randbytes(1600)
            base.write_bytes(raw)
            source.write_bytes(raw)
            for mode in ("direct", "exact"):
                archive = f / (mode + ".arf")
                output = f / (mode + ".restored")
                result = c.encode(source, base, archive, mode)
                self.assertEqual(result["reference_used"], mode == "exact")
                c.decode(archive, base if mode == "exact" else None, output)
                self.assertEqual(output.read_bytes(), raw)
                if mode == "exact":
                    other = f / "wrong"
                    other.write_bytes(raw[:-1])
                    with self.assertRaises(ValueError):
                        c.decode(archive, other, f / "invalid")

    def test_prime_modes_and_decimal_zero_padding(self):
        with TemporaryDirectory() as td:
            work = Path(td)
            raw = work / "raw"
            raw.write_bytes(b"\x00" * 4 + bytes(range(231)))
            for mode in ("fixed", "tree", "explore", "sums"):
                archive = work / (mode + ".qpi")
                out = work / (mode + ".raw")
                subprocess.run(
                    [RESEARCH / "build/prime-indices", mode, raw, archive],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [RESEARCH / "build/prime-indices", "decode", archive, out],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(raw.read_bytes(), out.read_bytes())
            for end in (b"", b"\n"):
                digits = work / ("decimal" + str(len(end)))
                digits.write_bytes(b"000000012300456001" + end)
                arc = digits.with_suffix(".qbf")
                out = digits.with_suffix(".txt")
                subprocess.run(
                    [
                        RESEARCH / "build/decimal-blocks",
                        "split",
                        digits,
                        arc,
                        work / "report",
                        "5",
                    ],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [RESEARCH / "build/decimal-blocks", "join", arc, out],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(digits.read_bytes(), out.read_bytes())

    def test_integer_leading_zeros(self):
        python = os.environ.get("GMP_PYTHON", sys.executable)
        if subprocess.run(
            [python, "-c", "import gmpy2"], capture_output=True
        ).returncode:
            self.skipTest("gmpy2 is optional")
        with TemporaryDirectory() as td:
            folder = Path(td)
            source = folder / "number"
            source.write_bytes(b"\x00\x00" + Random(228).randbytes(1535) + b"\x19")
            for mode in ("floor", "nearest", "mixed", "modular", "composite"):
                archive = folder / (mode + ".arc")
                restored = folder / (mode + ".out")
                command = [python, RESEARCH / "integer-formulas/run.py"]
                subprocess.run(
                    [*command, mode, source, archive], check=True, capture_output=True
                )
                subprocess.run(
                    [*command, "decode", archive, restored],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(source.read_bytes(), restored.read_bytes())
            for i, raw in enumerate((b"", b"\0", b"\0\x07", b"\xff", b"\0abc")):
                source.write_bytes(raw)
                arc = folder / f"adjust-{i}"
                dst = folder / f"out-{i}"
                subprocess.run(
                    [*command, "composite-adjusted", source, arc],
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    [*command, "decode", arc, dst], check=True, capture_output=True
                )
                self.assertEqual(raw, dst.read_bytes())

    def test_integer_grid_planes_and_lags(self):
        with engine("lattice-prediction") as c:
            rng = np.random.default_rng(45)
            for width in (1, 2, 4):
                raw = rng.bytes(width * 117)
                a = np.frombuffer(raw, dtype=f"<u{width}")
                for kind in range(3):
                    np.testing.assert_array_equal(
                        c.unlayout(c.layout(a, kind), width, kind), a
                    )
                for method in range(5):
                    for lag in (1, 16, 155):
                        np.testing.assert_array_equal(
                            c.recover(c.predict(a, method, lag), method, lag), a
                        )

    def test_sparse_census_events(self):
        with engine("whiteboard-census", "changes") as model:
            samples = [b"", bytes(122), bytes([3]) * 577, bytes(range(256))]
            sparse = bytearray(44443)
            sparse[0], sparse[441], sparse[-1] = 2, 15, 2
            for sample in [*samples, bytes(sparse)]:
                coded = model.pack_changes(sample)
                self.assertEqual(model.unpack_changes(coded, len(sample)), sample)
                with self.assertRaises(ValueError):
                    model.unpack_changes(coded + b"x", len(sample))
                with self.assertRaises(ValueError):
                    model.unpack_changes(coded[:-1], len(sample))
            duplicated = model.pack_changes(b"\x01")
            with self.assertRaises(ValueError):
                model.unpack_changes(bytes([2]) + duplicated[1:] + duplicated[1:], 1)

    def test_witness_regeneration_and_receiver_build(self):
        with (
            engine("whiteboard-census", "regenerate") as model,
            TemporaryDirectory() as tmp,
        ):
            directory = Path(tmp)
            data = model.predict(12, 11, 0, False, directory)
            self.assertEqual(model.infer(data), (12, 11, 0))
            archive, stats = model.encode(data, "generic", directory)
            self.assertEqual(stats["mode"], 2)
            self.assertEqual(model.decode(archive, directory), data)
            bad = bytearray(archive)
            bad[-1] ^= 32
            with self.assertRaisesRegex(ValueError, "different witness"):
                model.decode(bytes(bad), directory)
            changed = bytearray(data)
            changed[20] ^= 8
            archive, stats = model.encode(bytes(changed), "generic", directory)
            self.assertIn(stats["mode"], (3, 4))
            self.assertEqual(model.decode(archive, directory), changed)
            raw = Random(73).randbytes(99)
            archive, _ = model.encode(raw, "generic", directory)
            self.assertEqual(model.decode(archive, directory), raw)

    def test_delivered_witness_decoder(self):
        with (
            engine("whiteboard-census", "witness_app") as model,
            TemporaryDirectory() as tmp,
        ):
            directory = Path(tmp)
            raw = model.predict(18, 17, 0, True, directory)
            source = directory / "raw"
            source.write_bytes(raw)
            app = directory / "witness.pyz"
            stats = model.package(source, app, "source")
            self.assertEqual(stats["mode"], 1)
            output = directory / "out"
            subprocess.run([sys.executable, "-I", "-S", app, output], check=True)
            self.assertEqual(output.read_bytes(), raw)

    def test_byte_checkerboard_and_kronecker_factors(self):
        with engine("modular-kronecker") as model, TemporaryDirectory() as tmp:
            rng = np.random.default_rng(17039)
            a = rng.integers(0, 256, (15, 16), dtype=np.uint8)
            b = rng.integers(0, 256, (15, 16), dtype=np.uint8)
            a[:, 0] &= 254
            a[:, -1] |= 1
            b[:, -1] |= 1
            original = model.factors_to_grid(a, b)
            self.assertFalse(any(model.split(original, True)[len(a) * 32 :]))
            for flexible in (False, True):
                packed = model.split(original, flexible)
                np.testing.assert_array_equal(model.join(packed, len(a)), original)
            for shift in range(1, 9):
                shifted = original << np.uint8(shift)
                packed = model.split(shifted, valuation=True)
                self.assertFalse(any(packed[len(a) * 32 :]))
                np.testing.assert_array_equal(model.join(packed, len(a)), shifted)
            evolved = original.copy()
            for _ in range(4):
                model.step(evolved)
            for _ in range(4):
                model.step(evolved, True)
            np.testing.assert_array_equal(evolved, original)
            t = Path(tmp)
            raw = t / "source"
            for length in (0, 17, 256, 3853):
                data = (original.tobytes() + bytes(31))[:length]
                raw.write_bytes(data)
                archive, back = t / f"arc-{length}", t / f"back-{length}"
                model.encode(raw, archive, "adaptive-joint")
                model.decode(archive, back)
                self.assertEqual(data, back.read_bytes())

    def test_census_against_independent_brute_force(self):
        with (
            TemporaryDirectory() as directory,
            engine("whiteboard-census", "costs") as c,
        ):
            t = Path(directory)
            prefix = t / "census"
            subprocess.run([c.EXE, "10", "9", prefix], check=True, capture_output=True)
            t3 = prefix.with_suffix(".f3.u8")
            t6 = prefix.with_suffix(".f6.u8")
            report = t / "brute.json"
            subprocess.run(
                [
                    sys.executable,
                    RESEARCH / "whiteboard-census/brute_check.py",
                    "10",
                    "9",
                    t6,
                    t3,
                    report,
                    "full",
                ],
                check=True,
                capture_output=True,
            )
            counts = json.loads(report.read_text())
            self.assertEqual((counts["F3_mismatches"], counts["F6_mismatches"]), (0, 0))
            raw = t3.read_bytes() + t6.read_bytes()
            archive, stats = c.encode(raw, "exact", t)
            self.assertEqual(stats["residual_bytes"], 0)
            self.assertEqual(c.decode(archive, t), raw)
            damaged = bytearray(raw)
            damaged[121] ^= 197
            self.assertEqual(
                c.decode(c.encode(bytes(damaged), "exact", t)[0], t), damaged
            )

    def test_witness_formula_and_exact_corrections(self):
        with engine("whiteboard-census", "witnesses") as c:
            params = np.array(
                [[1, 2, 12, 1, 2, 3], [1, 2, 9, 1, 2, 3], [2, 3, 1, 1, 2, 1]],
                dtype="<u4",
            )
            self.assertEqual(c.inferred(params)[:, 0].tolist(), [585, 73, 2])
            np.testing.assert_array_equal(
                c.adjust_params(c.adjust_params(params, False), True), params
            )
            nums = c.inferred(params)
            table = np.column_stack((nums[:, :2], params, nums[:, 2]))
            repeated = np.tile(table, (311, 1))
            repeated[101, 0] ^= 123
            data = c.WITNESS.pack(b"WIT1", 0, len(repeated)) + repeated.tobytes()
            for profile in ("columns", "arithmetic", "joint"):
                self.assertEqual(c.decode(c.encode(data, profile)[0]), data)
            with self.assertRaises(ValueError):
                c.repdigit(7, 7, 3)

    def test_archived_torus_packet(self):
        # Run the script entry point independently, including the original recorded lab vector.
        with TemporaryDirectory() as directory:
            out = Path(directory) / "torus"
            cli = RESEARCH / "checkerboard-orbits/explore.py"
            result = subprocess.run(
                [sys.executable, cli, "--recorded", "--steps", "255", "--save", out],
                check=True,
                capture_output=True,
            )
            self.assertIn(b"step 183", result.stdout)
            self.assertEqual(out.read_bytes().hex(), "0808232c4e4ee5a1d5325d")
            decoded = subprocess.run(
                [sys.executable, cli, "--open", out], check=True, capture_output=True
            )
            self.assertEqual(len(decoded.stdout.decode().splitlines()), 8)

    def test_study_chunks_and_joint_selection_shortcut(self):
        import collection
        import wire

        rng = Random(874)
        for number, profile in (
            (17, "combined"),
            (18, "orbit-enumerative"),
            (19, "mixed"),
        ):
            data = rng.randbytes(79) + b"\0" * 47
            base = rng.randbytes(126)
            archive = BytesIO()
            restored = BytesIO()
            collection.encode(BytesIO(data), archive, number, profile, BytesIO(base))
            collection.decode(BytesIO(archive.getvalue()), restored, BytesIO(base))
            self.assertEqual(data, restored.getvalue())
        module = collection.module_for(16)
        raw = b"\0" * 32768
        encoded, _ = wire.encode(module, raw, "intervals-regions")
        decoded, _ = wire.decode(module, encoded)
        self.assertEqual(decoded, raw)
        self.assertEqual(
            module.pack(raw, "intervals-regions", b"", {})[:2],
            module.pack(raw, "single", b"", {})[:2],
        )

    def test_portable_sparse_decoder_in_isolation(self):
        with (
            engine("portable-arithmetic", "pack") as c,
            TemporaryDirectory() as directory,
        ):
            data = b"\0" * 9200 + Random(21).randbytes(9389) + b"\x85" * 9217
            source = Path(directory) / "file"
            source.write_bytes(data)
            payload, _ = c.sparse_scale.encode(data, "joint")
            archive = Path(directory) / "program.pyz"
            archive.write_bytes(c.application(payload, b"SCL1"))
            restored = Path(directory) / "back"
            subprocess.run([sys.executable, "-I", "-S", archive, restored], check=True)
            self.assertEqual(restored.read_bytes(), data)

    def test_public_benchmark_entry_points(self):
        commands = (
            [ROOT / "suite.py", "benchmark", "--project", "shared"],
            [ROOT / "lab.py", "7", "benchmark"],
            [ROOT / "experiments/01-repdigit-segmentation/benchmark.py"],
            [ROOT / "studies/run.py", "formula-factor-grammar", "unused"],
        )
        with TemporaryDirectory() as t:
            for cmd in commands:
                result = subprocess.run(
                    [sys.executable, *cmd, "--list"],
                    cwd=t,
                    check=True,
                    capture_output=True,
                )
                self.assertGreaterEqual(int(result.stdout.split()[-1]), 20 << 20)
            small = Path(t) / "short"
            small.write_bytes(b"x" * 128)
            dest = Path(t) / "dest"
            check = subprocess.run(
                [
                    sys.executable,
                    ROOT / "lab.py",
                    "7",
                    "benchmark",
                    dest,
                    "--input",
                    small,
                ],
                capture_output=True,
            )
            self.assertNotEqual(check.returncode, 0)
            self.assertFalse(dest.exists())

    def test_empirical_byte_entropy_and_chunk_boundary(self):
        from entropy_bench import describe
        from math import log2
        from collections import Counter

        self.assertEqual(describe(b"")["h0"], 0)
        self.assertEqual(describe(b"x")["h1"], 0)
        cyclic = describe(bytes(range(256)) * 8)
        self.assertEqual(cyclic["h0"], 8)
        self.assertEqual(cyclic["h1"], 0)
        data = b"a" * (1 << 20) + b"ba"
        observed = Counter(zip(data, data[1:]))
        previous = Counter(data[:-1])
        expected = -sum(n * log2(n / previous[a]) for (a, _), n in observed.items()) / (
            len(data) - 1
        )
        self.assertAlmostEqual(describe(data)["h1"], expected, places=12)

    def test_prepared_stream_contains_side_information(self):
        from preprocess import transcode
        import struct
        import zstandard as zstd

        header = struct.Struct(">4sIIQ")
        record = struct.Struct(">BBI")
        side = bytes(range(40))
        body = bytes(range(64))
        coded = zstd.ZstdCompressor(level=6).compress(body)
        native = (
            header.pack(b"LCA1", 8, 8, 1)
            + record.pack(2, 2, len(side + coded))
            + side
            + coded
        )
        plain, _ = transcode(native)
        self.assertEqual(
            plain,
            header.pack(b"LCAP", 8, 8, 1)
            + record.pack(2, 2, len(side + body))
            + side
            + body,
        )
        self.assertEqual(transcode(plain, restore=True)[0], native)
        with self.assertRaises(ValueError):
            transcode(plain)
        with self.assertRaises(ValueError):
            transcode(native[:-1])
        with self.assertRaises(ValueError):
            transcode(b"unknown")

    def test_receipts_and_minimum(self):
        import report

        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "row"
            trial = dict(
                dataset="fixture",
                codec="relative-exact",
                input_bytes=20 << 20,
                input_sha256="1" * 64,
                archive_bytes=50,
                archive_sha256="2" * 64,
                knobs=dict(
                    reference="external", reference_sha256="3" * 64, reference_bytes=123
                ),
                verified=True,
            )
            path.write_text(json.dumps(trial))
            self.assertEqual(
                report.read_trials([path])[0]["archive_plus_reference_bytes"], 173
            )
            trial["selections"] = {"reference_used": False}
            path.write_text(json.dumps(trial))
            self.assertEqual(
                report.read_trials([path])[0]["archive_plus_reference_bytes"], 50
            )
            trial["input_bytes"] -= 1
            path.write_text(json.dumps(trial))
            with self.assertRaises(ValueError):
                report.read_trials([path])
            log = Path(tmp) / "receipt"
            attempt = subprocess.run(
                [sys.executable, HERE / "bench.py", path, log, "zstd3"],
                capture_output=True,
            )
            self.assertNotEqual(attempt.returncode, 0)
            self.assertIn(b"20 MiB", attempt.stderr)
            self.assertFalse(log.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
