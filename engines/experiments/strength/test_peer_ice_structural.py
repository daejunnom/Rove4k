import copy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

try:
    from . import peer_ice_structural as ice
    from . import peers
except ImportError:
    import peer_ice_structural as ice
    import peers


class StructuralTest(unittest.TestCase):
    def synthetic_sources(self, variant):
        return {path: b"prefix\n" + b"\n".join(edit[1] for edit in edits) + b"\nsuffix\n"
                for path, edits in ice.edit_specs(variant).items()}

    def pin(self, sources):
        return mock.patch.dict(peers.SOURCE_BLOBS["ice4"],
                               {path: peers.git_blob(data) for path, data in sources.items()})

    def test_all_variants_recover_full_input_and_reject_tampering(self):
        for variant in ice.VARIANTS:
            sources = self.synthetic_sources(variant)
            with self.subTest(variant=variant), self.pin(sources):
                changed, receipt = ice.transform(variant, sources)
                self.assertEqual(sources, ice.restore(changed, receipt))
                path = next(path for path, edits in ice.edit_specs(variant).items() if edits)
                altered = dict(changed)
                altered[path] += b"tampered"
                with self.assertRaises(ValueError):
                    ice.restore(altered, receipt)
                altered_receipt = copy.deepcopy(receipt)
                altered_receipt["revision"] = "wrong"
                with self.assertRaises(ValueError):
                    ice.restore(changed, altered_receipt)
                with self.assertRaises(ValueError):
                    ice.transform(variant, {**sources, path: sources[path] + b"tampered"})

    def test_duplicate_marker_and_missing_context_rejected(self):
        sources = self.synthetic_sources("castle-v1")
        sources["src/board.cpp"] += ice._CASTLE_BEFORE
        with self.pin(sources), self.assertRaises(ValueError):
            ice.transform("castle-v1", sources)
        with self.assertRaises(ValueError):
            ice.transform("castle-v1", {"src/board.cpp": sources["src/board.cpp"]})
        with self.assertRaises(ValueError):
            ice.edit_specs("unrecognized")

    def test_small_cpp_semantics(self):
        compiler = shutil.which("c++") or shutil.which("g++")
        if compiler is None:
            self.skipTest("C++ compiler unavailable")
        source = r'''
#include <cstdint>
#include <cstdio>
#include <cstring>
int main() {
  for (int from=0; from<256; ++from) for(int to=0; to<128; ++to)
    for(int rights=0; rights<256; ++rights) {
      int a=rights,b=rights;
      if(from==21||to==21)a|=2; if(from==28||to==28)a|=1;
      if(from==91||to==91)a|=8; if(from==98||to==98)a|=4;
      for(int i=0;i<4;i++){int s=21+7*(i&1)+70*(i>>1);
        if(from==s||to==s){b|=(2>>(i&1))<<(2*(i>>1));}}
      if(a!=b)return 1;
    }
  uint64_t a[25][120]={}, b[25][120]={};
  if((void*)&a!=(void*)a || sizeof(a)!=sizeof a)return 2;
  FILE *f=tmpfile(); if(!f)return 3;
  for(unsigned i=0;i<25*120;++i)if(fputc(i%251,f)==EOF)return 4;
  rewind(f); if(fread(&a,sizeof(a),1,f)!=1)return 5;
  rewind(f); if(fread(b,sizeof b,1,f)!=1)return 6;
  if(memcmp(a,b,sizeof a))return 7;
  return fclose(f)!=0;
}
'''
        # Populate the whole byte array, not just its element count.
        source = source.replace('25*120;++i', 'sizeof(a);++i')
        with tempfile.TemporaryDirectory(prefix="ice-structural-") as directory:
            path = Path(directory)
            (path / "fixture.cpp").write_text(source)
            exe = path / "fixture.exe"
            subprocess.run([compiler, "-O2", str(path / "fixture.cpp"), "-o", str(exe)],
                           check=True, timeout=60, capture_output=True)
            subprocess.run([str(exe)], check=True, timeout=30, capture_output=True)


if __name__ == "__main__":
    unittest.main()
