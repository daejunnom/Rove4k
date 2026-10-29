"""Execute the actual final E19 evaluator/setter and inline ordering consumer.

The engine main, TT and worker pool are never started here. The unchanged
ordering loop is extracted from its real h caller and executed with the real
generated move pool, learner values and a TT-move priority. This is model
consumer evidence, not whole-engine/search/resource qualification.
"""
from __future__ import annotations

import argparse
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from typing import Sequence

ROOT = Path(__file__).resolve().parents[3]
sys.dont_write_bytecode = True
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from engines.model.e19 import Model, mailbox_from_fen

INLINE_SOURCE = ROOT / "engines/compact/tiny-entry-e/shipping_order_inline.py"
CONSUMER_ABI = "e19-physical21-inline-h-v1"
Q_REGION = b"static L Q(L q){J 7-(abs(q%8*2-7)+abs(q/8-7))/2;}"
S_REGION = b"static L S(const E*p){L s=p->v+p->a+qi[15]*p->a*abs(p->a)/128+p->s*qi[14];J s>20000?20000:s< -20000?-20000:s;}"
SETTER_REGION = b"static void b(E*p,L q,L v){for(L n=-1,a=p->b[q];;n=1,a=v){if(a){L k=abs(a),s=a>0?n:-n;p->v+=s*qi[k];p->a+=s*(qi[k+6]*Q(q)+(k==1?qi[13]*((a<0?7-(q>>4):q>>4)-1):0));p->h^=e((W)(q+(a+6)*128));}if(n>0)break;p->b[q]=v;}if(abs(v)==6)p->k[v<0]=q;}"
H_PREFIX = b"static L h(ai*w,const E*p,L C,L G,L a,L d,L f,Y*g){"
FIXED_FENS = (
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "4k3/8/8/8/3Pp3/8/8/4K3 b - d3 0 1",
    "k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "4k3/8/8/8/3Pp3/8/8/K3R3 b - d3 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "r3k2r/8/8/8/8/8/8/R3K2R b KQkq - 0 1",
    "1r5k/P7/8/8/8/8/8/7K w - - 0 1",
    "7k/8/8/8/8/8/p7/1R5K b - - 0 1",
)


def _pin(value: bytes) -> dict:
    return {"bytes": len(value), "sha256": sha256(value).hexdigest()}


def _function(source: bytes, prefix: bytes) -> bytes:
    if source.count(prefix) != 1:
        raise ValueError("current E19 consumer ABI differs: " + prefix.decode())
    begin = source.index(prefix)
    level = 1
    for position in range(begin + len(prefix), len(source)):
        if source[position] == ord("{"):
            level += 1
        elif source[position] == ord("}"):
            level -= 1
            if not level:
                return source[begin:position + 1]
    raise ValueError("unterminated E19 consumer function")


def inspect_consumer(source: bytes, model: Model) -> tuple[bytes, dict]:
    """Admit the protected current model ABI; the owning producer admits its closure."""
    if b"\r" in source or source.count(b"#define J return") != 1 or source.count(b"#define L int") != 1:
        raise ValueError("current E19 source lexical ABI differs")
    table = model.validate_physical_table(source, name="qi")
    regions = {"center": Q_REGION, "evaluator": S_REGION, "incremental_setter": SETTER_REGION}
    for role, region in regions.items():
        if source.count(region) != 1:
            raise ValueError("protected E19 semantic region differs: " + role)
    raw_inline = INLINE_SOURCE.read_bytes().replace(b"\r\n", b"\n")
    module = ast.parse(raw_inline)
    assignments = [node for node in module.body if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == "EDITS" for target in node.targets)]
    if len(assignments) != 1:
        raise ValueError("canonical inline-order producer definition differs")
    edits = ast.literal_eval(assignments[0].value)
    if len(edits) != 2 or len(edits[1]) != 4 or not isinstance(edits[1][3], bytes):
        raise ValueError("canonical inline-order region differs")
    loop = edits[1][3]
    actual_h = _function(source, H_PREFIX)
    if source.count(loop) != 1 or actual_h.count(loop) != 1:
        raise ValueError("actual h no longer consumes the protected inline ordering loop")
    regions["actual_h_inline_ordering_loop"] = loop
    return loop, {"consumer_abi": CONSUMER_ABI, "source": _pin(source),
                  "physical_table": table, "model_id": model.model_id,
                  "coefficient_sha256": model.coefficient_sha256(),
                  "canonical_model_sha256": sha256(model.canonical_bytes()).hexdigest(),
                  "regions": {name: _pin(region) for name, region in regions.items()},
                  "inline_producer": {"path": str(INLINE_SOURCE), **_pin(raw_inline)},
                  "h_function": _pin(actual_h), "integer_bounds": model.bounds()}


def fixture_source(source: bytes, model: Model, *, additional_fens: Sequence[str] = ()) -> tuple[bytes, dict]:
    if len(additional_fens) > 256:
        raise ValueError("at most 256 real-data FENs per consumer fixture")
    for fen in additional_fens:
        mailbox_from_fen(fen)
        if not fen.isascii() or any(char in fen for char in '\r\n\x00"\\'):
            raise ValueError("plain standard FEN fixture required")
    loop, proof = inspect_consumer(source, model)
    values = ",".join(map(str, model.coefficients))
    fens = ",\n".join(json.dumps(fen) for fen in (*FIXED_FENS, *additional_fens))
    activity_bound = model.bounds()["activity_abs_upper"]
    # Initial production E19 needs 3,457 activity values. Larger revised domains
    # remain bounded while keeping both endpoints and exact integer arithmetic.
    stride = max(1, (2 * activity_bound + 1) // 65536)
    wrapper = _C_FIXTURE.replace("@WEIGHTS@", values).replace("@FENS@", fens)
    wrapper = wrapper.replace("@ACTIVITY@", str(activity_bound)).replace("@STRIDE@", str(stride))
    wrapper = wrapper.replace("@MATERIAL@", str(model.bounds()["material_abs_upper"]))
    wrapper = wrapper.replace("@EXTRA@", str(len(additional_fens))).replace("@LOOP@", loop.decode())
    result = b"#define main e19_unused_engine_main\n" + source + b"\n#undef main\n" + wrapper.encode()
    proof.update(additional_data_fens=len(additional_fens), additional_fens=list(additional_fens),
                 additional_fens_sha256=sha256(json.dumps(list(additional_fens), separators=(",", ":")).encode()).hexdigest(),
                 fixed_fens=len(FIXED_FENS),
                 fixture=_pin(result), exhaustive_activity_interval=stride == 1,
                 activity_stride=stride, actual_engine_main_executed=False,
                 actual_search_executed=False, actual_model_evaluator_executed=True,
                 actual_incremental_setter_executed=True, actual_generated_move_pool_executed=True,
                 exact_inline_loop_extracted_from_h=True,
                 full_engine_or_resource_qualification=False)
    return result, proof


def _group_exists(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def _signal_group(pgid: int, value: int):
    try:
        os.killpg(pgid, value)
    except ProcessLookupError:
        pass


def _run(command: list[str], out: Path, label: str, *, timeout: float) -> dict:
    import resource

    def limits():
        resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
        resource.setrlimit(resource.RLIMIT_CPU, (25, 30))
        resource.setrlimit(resource.RLIMIT_FSIZE, (4 << 20, 4 << 20))

    started = time.monotonic()
    process = subprocess.Popen(command, cwd=out, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               start_new_session=True, preexec_fn=limits)
    timed_out = False
    forced = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = forced = True
        _signal_group(process.pid, signal.SIGTERM)
        try:
            stdout, stderr = process.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            _signal_group(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate(timeout=2)
    for _ in range(50):
        if not _group_exists(process.pid):
            break
        time.sleep(0.02)
    if _group_exists(process.pid):
        forced = True
        _signal_group(process.pid, signal.SIGKILL)
        for _ in range(50):
            if not _group_exists(process.pid):
                break
            time.sleep(0.02)
    (out / (label + ".stdout")).write_bytes(stdout)
    (out / (label + ".stderr")).write_bytes(stderr)
    result = {"argv": command, "leader_pid": process.pid, "returncode": process.returncode,
              "wall_seconds": time.monotonic() - started, "timed_out": timed_out,
              "forced_cleanup": forced, "group_absent": not _group_exists(process.pid),
              "stdout": _pin(stdout), "stderr": _pin(stderr)}
    (out / (label + ".json")).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if len(stdout) + len(stderr) > 2 << 20:
        raise RuntimeError("consumer command output budget exceeded")
    return result


def check_actual_consumer(source_path: Path | str, out: Path | str, *, model: Model | None = None,
                          cc: str = "cc", additional_fens: Sequence[str] = ()) -> dict:
    if sys.platform != "linux":
        raise ValueError("actual E19 C consumer checking requires Linux")
    model = model or Model.load()
    path = Path(source_path).resolve()
    source = path.read_bytes()
    fixture, admission = fixture_source(source, model, additional_fens=additional_fens)
    requested = Path(out)
    output = requested.resolve()
    if not requested.is_absolute() or output.exists() or any((ancestor / ".git").exists() for ancestor in (output, *output.parents)):
        raise ValueError("new absolute consumer output outside Git required")
    output.mkdir(parents=True)
    (output / "shipping-input.c").write_bytes(source)
    (output / "consumer-fixture.c").write_bytes(fixture)
    report = {"format": 1, "kind": "e19-actual-consumer-check", "complete": False,
              "source_path": str(path), **admission,
              "checker": _pin(Path(__file__).read_bytes().replace(b"\r\n", b"\n")),
              "affinity": sorted(os.sched_getaffinity(0)), "performance_claimed": False,
              "commands": [], "model_consumer_semantics_checked": False}

    def save():
        (output / "consumer.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    save()
    try:
        command = [cc, "-std=c11", "-O1", "-pthread", "-fsanitize=undefined", "-fno-sanitize-recover=all",
                   "-Werror=shift-count-overflow", "consumer-fixture.c", "-o", "consumer-fixture"]
        compile_receipt = _run(command, output, "compile", timeout=35)
        report["commands"].append(compile_receipt)
        save()
        if compile_receipt["returncode"] != 0 or compile_receipt["forced_cleanup"] or not compile_receipt["group_absent"]:
            raise RuntimeError("actual consumer fixture compilation failed; stderr preserved")
        report["fixture_native"] = _pin((output / "consumer-fixture").read_bytes())
        execution = _run([str(output / "consumer-fixture")], output, "execute", timeout=25)
        report["commands"].append(execution)
        save()
        if execution["returncode"] != 0 or execution["forced_cleanup"] or not execution["group_absent"]:
            raise RuntimeError("actual consumer oracle failed; stdout/stderr preserved")
        rows = [json.loads(line) for line in (output / "execute.stdout").read_text().splitlines() if line.strip()]
        if len(rows) != 1 or rows[0].get("pass") is not True:
            raise RuntimeError("consumer did not return one successful summary")
        report.update(observations=rows[0], complete=True, model_consumer_semantics_checked=True)
        save()
        return report
    except Exception as error:
        report["error"] = {"type": type(error).__name__, "message": str(error)}
        save()
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--cc", default="cc")
    parser.add_argument("--additional-fens", type=Path, help="JSON list of actual retained dataset FENs")
    args = parser.parse_args()
    extra = json.loads(args.additional_fens.read_text()) if args.additional_fens else []
    report = check_actual_consumer(args.source, args.out, model=Model.load(args.model) if args.model else None,
                                   cc=args.cc, additional_fens=extra)
    print(json.dumps({"complete": report["complete"], "source": report["source"], "observations": report["observations"]}))
    return 0


_C_FIXTURE = r'''
#include <ctype.h>
#include <inttypes.h>
static const int64_t e19_expected_weights[19]={@WEIGHTS@};
static uint64_t e19_positions,e19_orders,e19_legal,e19_accumulators,e19_setters;
static unsigned e19_ep,e19_castle,e19_capture,e19_promotion[2],e19_promocapture[2];
static void e19_need(int good,const char *why){if(!good){fprintf(stderr,"E19 FAIL %s\n",why);exit(1);}}
static int e19_min(int x,int y){return x<y?x:y;}
static int e19_center(int q){return e19_min(q%16,7-q%16)+e19_min(q/16,7-q/16);}
static int e19_material(int piece){int k=abs(piece);return k&&k<6?(int)e19_expected_weights[k-1]:0;}
static int e19_reference(const E *p){
 int64_t material=0,activity=0;int populations[2]={0};
 for(int q=0;q<128;q++){
  int v=p->b[q];e19_need(!(q&0x88)||!v,"mailbox padding");if((q&0x88)||!v)continue;
  int sign=v>0?1:-1,k=abs(v);e19_need(k<=6,"piece kind");populations[v<0]++;
  material+=sign*e19_material(v);
  activity+=sign*(e19_expected_weights[k+4]*e19_center(q)+(k==1?e19_expected_weights[11]*((v>0?q/16:7-q/16)-1):0));
 }
 e19_need(populations[0]<=16&&populations[1]<=16,"piece population");
 e19_need(material==p->v&&activity==p->a,"actual incremental state versus independent scan");
 int64_t raw=material+activity+e19_expected_weights[13]*activity*llabs(activity)/128+p->s*e19_expected_weights[12];
 e19_positions++;return raw>20000?20000:raw< -20000?-20000:(int)raw;
}
static int e19_order_reference(const E *p,Y m){
 int from=FROM(m),to=TO(m),piece=p->b[from],kind=abs(piece),victim=abs(p->b[to]),promotion=PROMO(m);
 if(kind==1&&to==p->e&&!victim)victim=1;
 int64_t result=e19_expected_weights[17]*(e19_center(to)-e19_center(from));
 if(victim)result+=e19_expected_weights[14]*e19_material(victim)+e19_expected_weights[15]*e19_material(kind);
 if(promotion)result+=e19_expected_weights[16]*(e19_material(promotion)-e19_material(1));
 if(kind==1)result+=e19_expected_weights[18]*(to/16-from/16)*(piece>0?1:-1);
 e19_need(result>=INT32_MIN&&result<=INT32_MAX,"ordering int32");return(int)result;
}
static void e19_check_score(const E *p){e19_need(S(p)==e19_reference(p),"actual shipping S versus int64 scan");}
static void e19_check_loop(const E *p,Y *B,int z){
 ai e19_worker={0};ai *w=&e19_worker;int f=6;Y j=z?B[z/2]:0;int y[512];w->id=3;
 for(int a=0;a<128;a++)for(int t=0;t<128;t++)w->zC[a][t]=(a*17+t*3)%23-11;
 for(int a=0;a<13;a++)for(int t=0;t<13;t++)w->an[a][t]=(a*3+t*11)%19-9;
 @LOOP@
 for(int e19_i=0;e19_i<z;e19_i++){
  Y m=B[e19_i];int from=FROM(m),to=TO(m),previous_piece=p->b[from]+6,promotion=PROMO(m);
  int base=m==j?1000000:m&8?500000:w->zC[from][to]+w->an[f][previous_piece]+(int)((m*37u+w->id*19u)%17);
  if(promotion)base+=400000+promotion*1000;
  e19_need(y[e19_i]==base+e19_order_reference(p,m),"actual h inline ordering and learner/TT/promotion priorities");e19_orders++;
 }
}
static void e19_children(const E *p,int recurse){
 E saved=*p;Y moves[512];int n=T(p,moves);e19_need(n>=0&&n<=512,"move pool capacity");e19_check_score(p);e19_check_loop(p,moves,n);
 for(int i=0;i<n;i++){
  E child;if(!v(p,moves[i],&child))continue;e19_legal++;e19_check_score(&child);
  e19_need(!memcmp(&saved,p,sizeof saved),"parent immutable");
  int from=FROM(moves[i]),to=TO(moves[i]),color=p->s<0,capture=p->b[to]!=0;
  if(capture)e19_capture|=1u<<color;
  if(abs(p->b[from])==1&&to==p->e&&!capture)e19_ep|=1u<<color;
  if(abs(p->b[from])==6&&abs(to-from)==2)e19_castle|=1u<<(2*color+(to<from));
  if(PROMO(moves[i])){e19_promotion[color]|=1u<<PROMO(moves[i]);if(capture)e19_promocapture[color]|=1u<<PROMO(moves[i]);}
  if(recurse)e19_children(&child,0);
 }
}
static void e19_load(E *p,const char *fen){
 char cells[96],side,rights[8],ep[3];int half,full;
 static const char e19_letters[]=" PNBRQK",e19_rights[]="KQkq";
 e19_need(sscanf(fen,"%95s %c %7s %2s %d %d",cells,&side,rights,ep,&half,&full)==6,"fixture FEN");
 E t={0};t.s=side=='w'?1:-1;t.e=-1;t.aI=half;int rank=7,file=0;
 for(const char *c=cells;*c;c++){
  if(*c=='/'){rank--;file=0;}else if(isdigit((unsigned char)*c))file+=*c-'0';else{
   const char *k=strchr(e19_letters,toupper((unsigned char)*c));e19_need(k&&rank>=0&&file<8,"fixture piece");
   b(&t,rank*16+file++,(int)(k-e19_letters)*(isupper((unsigned char)*c)?1:-1));
  }
 }
 for(const char *c=rights;*c&&*c!='-';c++){const char *k=strchr(e19_rights,*c);e19_need(k!=0,"fixture rights");t.c|=1<<(k-e19_rights);}
 if(ep[0]!='-')t.e=(ep[1]-'1')*16+ep[0]-'a';D(&t);t.h^=l(&t);t.r=t.h;*p=t;e19_check_score(p);
}
int main(void){
 for(int q=0;q<128;q++)if(!(q&0x88)){
  e19_need(Q(q)==e19_center(q),"actual compressed center versus independent coordinates");
  for(int piece=-6;piece<=6;piece++)for(int side=-1;side<=1;side+=2){
   E p={0};p.s=side;p.e=-1;b(&p,q,piece);e19_check_score(&p);b(&p,q,-piece);e19_check_score(&p);b(&p,q,0);e19_check_score(&p);e19_setters+=3;
  }
 }
 const int e19_activity_bound=@ACTIVITY@,e19_stride=@STRIDE@;
 for(int a=-e19_activity_bound;a<=e19_activity_bound;a+=e19_stride)for(int side=-1;side<=1;side+=2)for(int sign=-1;sign<=1;sign+=2){
  E p={0};p.v=sign*@MATERIAL@;p.a=a;p.s=side;
  int64_t raw=(int64_t)p.v+a+e19_expected_weights[13]*(int64_t)a*llabs(a)/128+side*e19_expected_weights[12];
  int expected=raw>20000?20000:raw< -20000?-20000:(int)raw;e19_need(S(&p)==expected,"actual C predivision/division/clamp versus int64");e19_accumulators++;
 }
 const char *fens[]={@FENS@};
 for(unsigned i=0;i<sizeof fens/sizeof*fens;i++){E p;e19_load(&p,fens[i]);e19_children(&p,i<2);}
 e19_need(e19_capture==3&&e19_ep==3&&e19_castle==15,"both-color capture EP castling coverage");
 e19_need(e19_promotion[0]==60&&e19_promotion[1]==60&&e19_promocapture[0]==60&&e19_promocapture[1]==60,"both-color NBRQ generation and promotion capture");
 printf("{\"pass\":true,\"positions\":%"PRIu64",\"orders\":%"PRIu64",\"legal_transitions\":%"PRIu64",\"setter_observations\":%"PRIu64",\"accumulator_cases\":%"PRIu64",\"capture_mask\":%u,\"ep_mask\":%u,\"castle_mask\":%u,\"promotion_masks\":[%u,%u],\"promotion_capture_masks\":[%u,%u],\"additional_data_fens\":@EXTRA@}\n",e19_positions,e19_orders,e19_legal,e19_setters,e19_accumulators,e19_capture,e19_ep,e19_castle,e19_promotion[0],e19_promotion[1],e19_promocapture[0],e19_promocapture[1]);return 0;
}
'''


if __name__ == "__main__":
    raise SystemExit(main())
