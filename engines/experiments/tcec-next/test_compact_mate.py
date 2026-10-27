"""Pure mate-source boundaries and opt-in actual-fragment C fixture emission.

Default unittest execution does not compile or run C. Positive source checks
take the caller's actual pinned bytes; no generated engine fixture is embedded
and no production input policy is patched. The hosted caller may compile the
emitted C with fatal UBSan. Its old and new bodies are slices of those actual
source buffers, not two copies of a Python arithmetic implementation.
"""
import copy
import importlib.util
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mate = load("compact_mate_test_owner", HERE / "compact_mate.py")
projection = load("compact_mate_test_projection", HERE / "spelling_compound.py")


def require(value, message):
    if not value:
        raise ValueError(message)


def check_actual_source(source, *, family, profile_id, variant):
    """Exercise real positive inverse/tamper checks without changing policy."""
    candidate, proof = mate.transform_source(source, family=family,
        profile_id=profile_id, variant=variant, projection=projection)
    require(mate.restore_source(candidate, proof, projection=projection) == source,
            "actual complete source inverse differs")
    replay, repeated = mate.transform_source(source, family=family,
        profile_id=profile_id, variant=variant, projection=projection)
    require(replay == candidate and repeated == proof, "actual replay differs")
    previous_in = previous_out = 0
    for row, gap in zip(proof["edits"], proof["protected_gaps"]):
        old, new = row["before"].encode("ascii"), row["after"].encode("ascii")
        before = source[previous_in:row["input_begin"]]
        after = candidate[previous_out:row["output_begin"]]
        require(before == after and mate.pin(before) ==
                {key: gap[key] for key in ("bytes", "sha256")},
                "actual protected complement differs")
        require(source[row["input_begin"]:row["input_begin"] + len(old)] == old
                and candidate[row["output_begin"]:row["output_begin"] + len(new)] == new,
                "actual edit body differs")
        previous_in = row["input_begin"] + len(old)
        previous_out = row["output_begin"] + len(new)
    require(source[previous_in:] == candidate[previous_out:]
            and mate.pin(source[previous_in:]) ==
            {key: proof["protected_gaps"][-1][key] for key in ("bytes", "sha256")},
            "actual final complement differs")
    changes = []
    for key, value in (("family", "F"), ("profile_id", "tcec-provisional"),
                       ("variant", "unknown"), ("full_inverse", 1),
                       ("resources_changed", True), ("native_identity_claimed", True)):
        changed = copy.deepcopy(proof)
        changed[key] = value
        changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["domain"]["TT_score_min"] = -32767
    changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["edits"][0]["input_begin"] += 1
    changes.append(changed)
    changed = copy.deepcopy(proof)
    changed["protected_gaps"][-1]["sha256"] = "0" * 64
    changes.append(changed)
    for changed in changes:
        try:
            mate.restore_source(candidate, changed, projection=projection)
        except ValueError:
            pass
        else:
            raise ValueError("modified actual proof was accepted")
    try:
        mate.restore_source(candidate + b" ", proof, projection=projection)
    except ValueError:
        pass
    else:
        raise ValueError("modified candidate was accepted")
    return dict(family=family, profile_id=profile_id, variant=variant,
        input=mate.pin(source), output=mate.pin(candidate), raw_delta=len(candidate)-len(source),
        inverse=True, protected_gaps=len(proof["protected_gaps"]),
        tampered_proofs_rejected=len(changes), modified_candidate_rejected=True,
        actual_C_semantics_executed=False, native_identity_claimed=False)


def _fragment(buffer, row, *, candidate):
    text = row["after" if candidate else "before"].encode("ascii")
    begin = row["output_begin" if candidate else "input_begin"]
    actual = buffer[begin:begin + len(text)]
    require(actual == text, "fixture must use the actual recorded source span")
    return begin, actual


def semantic_fixture(source, *, family, profile_id, variant):
    """Emit exhaustive fragment comparisons; compilation/execution is external.

    Both decode and store cover all 65,536 signed16 values and all 128 plies.
    This widens the actual +/-30000 store domain and includes every poisoned
    signed16 TT value. It does not test arbitrary int values or a whole engine.
    """
    candidate, proof = mate.transform_source(source, family=family,
        profile_id=profile_id, variant=variant, projection=projection)
    require(mate.restore_source(candidate, proof, projection=projection) == source,
            "fixture source inverse differs")
    context = mate.CONTEXT[family]
    score, best, ply = (context[key] for key in ("score", "best", "ply"))
    rows = {row["role"]: row for row in proof["edits"]}
    load_row, store_row = rows["mate-load-" + variant], rows["mate-store-" + variant]
    _, old_load = _fragment(source, load_row, candidate=False)
    _, new_load = _fragment(candidate, load_row, candidate=True)
    old_at, old_store = _fragment(source, store_row, candidate=False)
    new_at, new_store = _fragment(candidate, store_row, candidate=True)
    assignment = (score + "=" + best + ";").encode("ascii")
    if variant == "folded":
        require(source[old_at-len(assignment):old_at] == assignment
                and candidate[new_at-len(assignment):new_at] == assignment,
                "actual unchanged score assignment differs")
        old_store = source[old_at-len(assignment):old_at] + old_store
        new_store = candidate[new_at-len(assignment):new_at] + new_store
    else:
        require(old_store.startswith(assignment), "actual store assignment is absent")
    actual_helper = b""
    if variant == "shared":
        helper_row = rows["mate-shared-owner"]
        _, old_owner = _fragment(source, helper_row, candidate=False)
        _, new_owner = _fragment(candidate, helper_row, candidate=True)
        require(new_owner.endswith(old_owner), "actual helper insertion differs")
        actual_helper = new_owner[:-len(old_owner)]
        require(actual_helper and mate.HELPER_NAME.encode("ascii") in actual_helper,
                "actual shared helper is absent")
    aliases = {context["integer"]: "int", context["returned"]: "return",
               context["static"]: "static", context["conditional"]: "if"}
    definitions = "".join("#define " + old + " " + new + "\n"
                          for old, new in aliases.items() if old != new)

    def function(name, role, body):
        first = score if role == "load" else best
        local = "" if role == "load" else "int " + score + ";"
        return ("static int " + name + "(int " + first + ",int " + ply + "){" + local +
                body.decode("ascii") + "return " + score + ";}\n")

    header = ("#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n"
              "#include <limits.h>\n#include <inttypes.h>\n"
              "_Static_assert(INT_MAX>=2147483647 && INT_MIN<=-2147483647,\"int domain\");\n"
              "_Static_assert(INT16_MIN==-32768 && INT16_MAX==32767,\"int16 domain\");\n"
              "#define MATE 30000\n#define PLY 128\n")
    functions = (function("rv_old_load", "load", old_load) +
                 function("rv_new_load", "load", new_load) +
                 function("rv_old_store", "store", old_store) +
                 function("rv_new_store", "store", new_store))
    main = r'''
int main(void){
 uint64_t checksum=UINT64_C(1469598103934665603),loads=0,stores=0;
 for(unsigned bits=0;bits<65536;bits++){
  int score=(int)bits-32768;
  for(int ply=0;ply<128;ply++){
   int a=rv_old_load(score,ply),b=rv_new_load(score,ply);
   if(a!=b){fprintf(stderr,"load score=%d ply=%d old=%d new=%d\n",score,ply,a,b);return 1;}
   int c=rv_old_store(score,ply),d=rv_new_store(score,ply);
   if(c!=d){fprintf(stderr,"store score=%d ply=%d old=%d new=%d\n",score,ply,c,d);return 2;}
   checksum=(checksum^(uint64_t)(int64_t)a)*UINT64_C(1099511628211);
   checksum=(checksum^(uint64_t)(int64_t)c)*UINT64_C(1099511628211);
   loads++;stores++;
  }
 }
 printf("{\"complete\":true,\"family\":\"@FAMILY@\",\"profile\":\"@PROFILE@\",\"variant\":\"@VARIANT@\",\"decode_cases\":%" PRIu64 ",\"store_cases\":%" PRIu64 ",\"TT_values\":65536,\"plies\":128,\"checksum\":%" PRIu64 "}\n",loads,stores,checksum);
 return loads!=UINT64_C(8388608)||stores!=UINT64_C(8388608);
}
'''
    main = main.replace("@FAMILY@", family).replace("@PROFILE@", profile_id).replace("@VARIANT@", variant)
    fixture = (header + definitions + actual_helper.decode("ascii") + "\n" + functions + main).encode("ascii")
    return fixture, dict(family=family, profile_id=profile_id, variant=variant,
        source=mate.pin(source), candidate=mate.pin(candidate), fixture=mate.pin(fixture),
        actual_source_fragments=True, decode_values=65536, decode_plies=128,
        store_values=65536, store_plies=128, actual_store_domain_included=True,
        arbitrary_int_equivalence_claimed=False, engine_executed=False)


class MateBoundaries(unittest.TestCase):
    def test_unrequested_families_and_profiles_are_rejected(self):
        for family, profile, variant in (("D", "test-p4", "folded"),
                ("F", "test-p4", "folded"), ("F8", "test-p4", "shared"),
                ("A", "tcec-provisional", "folded"), ("C", "test-p4", "control"),
                (True, "test-p4", "folded"), ("E", True, "shared")):
            with self.assertRaisesRegex(ValueError, "finite A/B/C/E"):
                mate.transform_source(b"unadmitted", family=family, profile_id=profile,
                    variant=variant, projection=projection)

    def test_unpinned_source_and_wrong_source_types_are_rejected(self):
        for family, profile in mate.INPUTS:
            for source in (b"unadmitted", bytearray(b"unadmitted"), "unadmitted", None):
                with self.assertRaisesRegex(ValueError, "exact selected"):
                    mate.transform_source(source, family=family, profile_id=profile,
                        variant="folded", projection=projection)

    def test_restore_rejects_unbound_output_before_inverse(self):
        for candidate, proof in ((b"x", {}), (bytearray(b"x"), {}),
                (b"x", dict(schema=mate.SCHEMA, edits=[], output=mate.pin(b"y")))):
            with self.assertRaisesRegex(ValueError, "candidate and complete proof"):
                mate.restore_source(candidate, proof, projection=projection)

    def test_arithmetic_domain_defines_abs_and_excludes_opposite_band_crossover(self):
        low, high, threshold = -32768, 32767, 29872
        for score in (low, -threshold-1, -threshold, -threshold+1, -1,
                      0, 1, threshold-1, threshold, threshold+1, high):
            for ply in (0, 1, 126, 127):
                self.assertGreater(score, -(1 << 31))
                if score > threshold:
                    self.assertGreater(score-ply, -threshold)
                if score < -threshold:
                    self.assertLess(score+ply, threshold)
                self.assertGreaterEqual(score-ply, -(1 << 31))
                self.assertLessEqual(score+ply, (1 << 31)-1)


if __name__ == "__main__":
    unittest.main()
