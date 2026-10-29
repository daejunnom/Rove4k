"""Synthetic ELF DATA checks; no compiler, loader, native or engine execution."""
import importlib.util
from pathlib import Path
import struct
import sys
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("elf_dependency_test_owner", HERE / "elf_dependencies.py")
deps = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = deps
SPEC.loader.exec_module(deps)


def fixture(*, needed=("libc.so.6",), interpreter="/lib64/ld-linux-x86-64.so.2",
            kind=2, dynamic=True, tls=False, rpath=None, runpath=None, extra=()):
    """Construct actual little-endian tables, not a mocked inspector result."""
    base, dyn_at, str_at, interp_at = 0x400000, 0x280, 0x400, 0x200
    strings = bytearray(b"\0")

    def name(value):
        at = len(strings)
        strings.extend(value.encode("ascii") + b"\0")
        return at

    rows = [(deps.DT_NEEDED, name(value)) for value in needed]
    if rpath is not None:
        rows.append((deps.DT_RPATH, name(rpath)))
    if runpath is not None:
        rows.append((deps.DT_RUNPATH, name(runpath)))
    rows += list(extra)
    rows += [(deps.DT_STRTAB, base + str_at), (deps.DT_STRSZ, len(strings)), (deps.DT_NULL, 0)]
    dyn = b"".join(struct.pack("<qQ", *row) for row in rows)
    data = bytearray(max(0x500, str_at + len(strings)))
    data[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    struct.pack_into("<HHIQQQIHHHHHH", data, 16, kind, 62, 1, base + 0x180,
                     64, 0, 0, 64, 56, 0, 0, 0, 0)
    phdrs = [(deps.PT_LOAD, 5, 0, base, base, len(data), len(data) + 0x3000, 0x1000)]
    if interpreter is not None:
        raw = interpreter.encode("ascii") + b"\0"
        data[interp_at:interp_at + len(raw)] = raw
        phdrs.append((deps.PT_INTERP, 4, interp_at, base + interp_at, base + interp_at, len(raw), len(raw), 1))
    if dynamic:
        data[dyn_at:dyn_at + len(dyn)] = dyn
        data[str_at:str_at + len(strings)] = strings
        phdrs.append((deps.PT_DYNAMIC, 6, dyn_at, base + dyn_at, base + dyn_at, len(dyn), len(dyn), 8))
    if tls:
        phdrs.append((deps.PT_TLS, 4, 0x480, base + 0x480, base + 0x480, 8, 16, 8))
    struct.pack_into("<H", data, 56, len(phdrs))
    for index, row in enumerate(phdrs):
        struct.pack_into("<IIQQQQQQ", data, 64 + index * 56, *row)
    return bytes(data)


class ELFDependencies(unittest.TestCase):
    def test_exec_dyn_tls_and_documented_system_libraries(self):
        for kind in (2, 3):
            raw = fixture(kind=kind, tls=True, needed=("libc.so.6", "libpthread.so.0", "libm.so.6", "libstdc++.so.6"))
            actual = deps.inspect_dependencies(raw)
            self.assertEqual(actual["elf_type"], "ET_EXEC" if kind == 2 else "ET_DYN")
            self.assertTrue(actual["has_tls"])
            self.assertEqual(actual["needed"], ["libc.so.6", "libpthread.so.0", "libm.so.6", "libstdc++.so.6"])
            policy = deps.check_tcec_policy(actual)
            self.assertTrue(policy["allowed"])
            self.assertFalse(policy["runtime_qualified"])
            self.assertFalse(policy["runtime_resolution_checked"])

    def test_static_large_bss_is_metadata_without_allocation(self):
        raw = bytearray(fixture(dynamic=False, needed=(), interpreter=None))
        struct.pack_into("<Q", raw, 64 + 40, 1 << 38)
        actual = deps.inspect_dependencies(bytes(raw))
        self.assertFalse(actual["has_dynamic"])
        self.assertIsNone(actual["interpreter"])
        self.assertEqual(actual["needed"], [])
        self.assertLess(actual["input"]["bytes"], 4096)
        self.assertTrue(deps.check_tcec_policy(actual)["allowed"])

    def test_library_and_interpreter_paths_are_role_specific(self):
        allowed = ("libdl.so.2", "libgcc_s.so.1", "/lib/x86_64-linux-gnu/libc.so.6",
                   "/usr/lib/x86_64-linux-gnu/libstdc++.so.6")
        self.assertTrue(deps.check_tcec_policy(deps.inspect_dependencies(fixture(needed=allowed)))["allowed"])
        for name in ("libatomic.so.1", "/tmp/libc.so.6", "../libc.so.6",
                     "/lib/x86_64-linux-gnu/../libc.so.6", "libc.so$ORIGIN", "/lib64/libc.so.6"):
            with self.subTest(name=name):
                self.assertFalse(deps.check_tcec_policy(deps.inspect_dependencies(fixture(needed=(name,))))["allowed"])
        for path in ("/tmp/ld-linux-x86-64.so.2", "/lib/x86_64-linux-gnu/libc.so.6"):
            self.assertFalse(deps.check_tcec_policy(deps.inspect_dependencies(fixture(interpreter=path)))["allowed"])

    def test_search_paths_loader_extensions_and_unknown_tags_are_not_silently_allowed(self):
        for keyword in ("rpath", "runpath"):
            for value in ("/tmp", ""):
                self.assertFalse(deps.check_tcec_policy(deps.inspect_dependencies(fixture(**{keyword: value})))["allowed"])
        for tag, name in deps.LOADER_FEATURES.items():
            actual = deps.inspect_dependencies(fixture(extra=((tag, 1),)))
            self.assertEqual(actual["loader_features"], [{"tag": name, "value": 1}])
            self.assertFalse(deps.check_tcec_policy(actual)["allowed"])
        actual = deps.inspect_dependencies(fixture(extra=((0x60000001, 0),)))
        self.assertEqual(actual["unrecognized_dynamic_tags"], [0x60000001])
        self.assertFalse(deps.check_tcec_policy(actual)["allowed"])

    def test_malformed_dynamic_strings_segments_and_ambiguous_maps_are_rejected(self):
        originals = fixture()
        changes = []
        raw = bytearray(originals)
        struct.pack_into("<Q", raw, 0x280 + 8, 0xFFFFFF)
        changes.append(raw)  # NEEDED offset outside actual STRTAB.
        raw = bytearray(originals)
        raw[0x400 + 1 + len("libc.so.6")] = ord("x")
        changes.append(raw)  # Last library terminator is gone.
        raw = bytearray(originals)
        struct.pack_into("<Q", raw, 0x280 + 16 + 8, 0x400000 + 0x2000)
        changes.append(raw)  # STRTAB in BSS, not in file-backed load.
        raw = bytearray(originals)
        struct.pack_into("<Q", raw, 0x280 + 32 + 8, deps.MAX_STRTAB + 1)
        changes.append(raw)
        raw = bytearray(originals)
        struct.pack_into("<qQ", raw, 0x280 + 32, deps.DT_STRTAB, 0x400400)
        changes.append(raw)  # Repeated STRTAB cannot choose a hidden interpretation.
        raw = bytearray(originals)
        struct.pack_into("<qQ", raw, 0x280 + 32, 30, 0)
        changes.append(raw)  # STRTAB without STRSZ is incomplete.
        raw = bytearray(originals)
        struct.pack_into("<qQ", raw, 0x280 + 48, deps.DT_NEEDED, 1)
        changes.append(raw)  # No DT_NULL within the declared segment.
        raw = bytearray(originals)
        struct.pack_into("<Q", raw, 64 + 2 * 56 + 8, 0x281)
        changes.append(raw)  # Dynamic file and virtual mappings disagree.
        for index, raw in enumerate(changes):
            with self.subTest(case=index), self.assertRaises(ValueError):
                deps.inspect_dependencies(bytes(raw))

    def test_partial_page_and_bss_load_aliases_reach_geometry_rejection(self):
        # All extra LOADs satisfy file extents and page/segment congruence.
        # A containing-LOAD-only lookup misses these partial or page aliases.
        def alias(address, offset, filesz, memsz, *, move_strings=False):
            raw = bytearray(fixture())
            old_size = len(raw)
            raw.extend(b"\0" * (0x3000 - len(raw)))
            if move_strings:
                strings = raw[0x400:0x40B]
                raw[0x1400:0x140B] = strings
                struct.pack_into("<Q", raw, 0x280 + 16 + 8, 0x401400)
                struct.pack_into("<Q", raw, 64 + 32, 0x2000)
                struct.pack_into("<Q", raw, 64 + 40, 0x2000)
            else:
                self.assertLess(old_size, 0x1000)
                struct.pack_into("<Q", raw, 64 + 40, old_size)
            struct.pack_into("<H", raw, 56, 4)
            struct.pack_into("<IIQQQQQQ", raw, 64 + 3 * 56, deps.PT_LOAD, 6,
                             offset, address, address, filesz, memsz, 0x1000)
            return bytes(raw)

        cases = (
            alias(0x401405, 0x2405, 6, 6, move_strings=True),  # STRTAB suffix alias.
            alias(0x400281, 0x1281, 1, 1),  # PT_DYNAMIC partial alias.
            alias(0x400800, 0x1800, 1, 1),  # No byte overlap; same mapped page.
            alias(0x400400, 0x1400, 0, 11),  # BSS replaces a file metadata page.
        )
        for index, raw in enumerate(cases):
            with self.subTest(case=index), self.assertRaisesRegex(ValueError, "page-rounded LOAD"):
                deps.inspect_dependencies(raw)

    def test_typed_extent_and_metadata_requirements(self):
        for raw in (None, bytearray(fixture()), b"not ELF"):
            with self.assertRaises(ValueError):
                deps.inspect_dependencies(raw)
        raw = bytearray(fixture())
        struct.pack_into("<H", raw, 56, deps.MAX_PHDRS + 1)
        with self.assertRaises(ValueError):
            deps.inspect_dependencies(bytes(raw))
        for metadata in ({}, {"format": deps.FORMAT}, []):
            with self.assertRaises(ValueError):
                deps.check_tcec_policy(metadata)
        actual = deps.inspect_dependencies(fixture())
        for name in ("interpreter", "rpath", "runpath", "soname"):
            incomplete = dict(actual)
            del incomplete[name]
            with self.subTest(missing=name), self.assertRaisesRegex(ValueError, "metadata keys"):
                deps.check_tcec_policy(incomplete)
        for page in (True, 8192):
            wrong_page = dict(actual)
            wrong_page["load_page_bytes"] = page
            with self.subTest(page=page), self.assertRaises(ValueError):
                deps.check_tcec_policy(wrong_page)


if __name__ == "__main__":
    unittest.main()
