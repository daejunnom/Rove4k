"""Guarded Rust A shipping-source specialization for loose and fixed root.

The accepted input descends from canonical de5676d with reviewed PALS feedback. This optional
producer removes inactive source before packing; it does not call a C backend,
change the canonical files, add crates, or claim 4 KiB eligibility. The pure API
accepts and returns byte dictionaries. Templates are loaded once at module import.
Unknown source/profile shapes fail closed rather than guessing Rust semantics.
"""
import hashlib
import importlib.util
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("rove_rust_syntax", _HERE / "syntax.py")
_syntax = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_syntax)
tokenize, render, matching = _syntax.tokenize, _syntax.render, _syntax.matching
_TEMPLATES = {name: (_HERE / (name + ".in")).read_text(encoding="utf-8") for name in ("main", "parallel")}
_SOURCE_BINDINGS = {'rust/board.rs': '1e48a2780dac8d401045528e6e942bb616a68c330ae283b24ab789234e4df59d', 'rust/eval.rs': 'd68e4f7c74792282436a1916b6c4d2ec9ccdcce2324a909b178b8bf79c36e1de', 'rust/main.rs': '8755390bf5444064614c31206393af9027adfed4983035b5cbbbb707650e1719', 'rust/parallel.rs': 'f7d7b2fec50f000a6b65884fa0a1da2392cb612226cd43059b479dd74b4fce54', 'rust/pool.rs': '0b2584e9953cb14ff3b9a658af5b674351791ca05518dc047b9361a38a877c84', 'rust/search.rs': '5107c61b93cd827e2e3f11efab89def94244b8da138474838ea9d52d83ce5e4b'}
_UNKNOWN = object()


def _groups(tokens):
    """Yield top-level token positions, treating delimiter groups as opaque."""
    i = 0
    while i < len(tokens):
        yield i
        i = matching(tokens, i) + 1 if tokens[i] in ("(", "[", "{") else i + 1


def _clean(tokens):
    return [t for t in tokens if not t.startswith(("///", "//!", "/**", "/*!", "#!"))]


def _value(tokens, constants):
    while len(tokens) >= 2 and tokens[0] == "(" and matching(tokens, 0) == len(tokens) - 1:
        tokens = tokens[1:-1]
    if not tokens:
        return _UNKNOWN, False
    # A block in the condition is ambiguous with the if body without a full
    # Rust expression parser. Keep that whole expression rather than treating
    # the block as the body and exposing the actual body unconditionally.
    if tokens[-1] in ("&&", "||", "!", "unsafe", "const", "async", "move", "try", ":"):
        return _UNKNOWN, False
    key = "".join(tokens)
    if key in constants:
        return constants[key], True
    if tokens == ["true"]: return True, True
    if tokens == ["false"]: return False, True
    if len(tokens) == 1:
        t = tokens[0]
        if t.isdecimal(): return int(t), True
        if t.startswith("b'") and len(t) == 4: return ord(t[2]), True
    # Boolean operators are evaluated in Rust short-circuit order. A known
    # RHS cannot erase an effectful unknown LHS (effect() && false).
    positions = list(_groups(tokens))
    for operator in ("||", "&&"):
        for i in positions:
            if tokens[i] != operator: continue
            left, lp = _value(tokens[:i], constants)
            right, rp = _value(tokens[i+1:], constants)
            if operator == "&&":
                if left is False: return False, lp
                if left is True: return right, lp and rp
                if right is False and lp: return False, lp
            else:
                if left is True: return True, lp
                if left is False: return right, lp and rp
                if right is True and lp: return True, lp
            return _UNKNOWN, lp and rp
    for i in positions:
        if tokens[i] in ("==", "!=", "<", ">", "<=", ">="):
            left, lp = _value(tokens[:i], constants)
            right, rp = _value(tokens[i+1:], constants)
            if left is not _UNKNOWN and right is not _UNKNOWN:
                op = tokens[i]
                return {"==": lambda: left == right, "!=": lambda: left != right,
                        "<": lambda: left < right, ">": lambda: left > right,
                        "<=": lambda: left <= right, ">=": lambda: left >= right}[op](), lp and rp
            return _UNKNOWN, lp and rp
    if tokens[0] == "!":
        value, pure = _value(tokens[1:], constants)
        return (not value if isinstance(value, bool) else _UNKNOWN), pure
    # Reading a local/field is pure. Calls, indexing, macros, closures and
    # if-let bindings remain unknown and potentially effectful.
    # Unknown field reads can invoke an overloaded Deref, and Rust control
    # keywords are not harmless local identifiers. Only a bare local is pure.
    keywords = {"return", "break", "continue", "yield", "await", "unsafe", "const", "async", "move", "loop", "match", "let", "if", "while", "for", "try"}
    pure = len(tokens) == 1 and tokens[0].isidentifier() and tokens[0] not in keywords
    return _UNKNOWN, pure


def _if_parts(tokens, at):
    i = at + 1
    while i < len(tokens) and tokens[i] != "{":
        if tokens[i] in ("(", "["): i = matching(tokens, i) + 1
        else: i += 1
    if i == len(tokens): raise ValueError("if without body")
    close = matching(tokens, i)
    end, alternative = close + 1, None
    if end < len(tokens) and tokens[end] == "else":
        other = end + 1
        if tokens[other] == "if":
            _, _, end, _ = _if_parts(tokens, other)
        elif tokens[other] == "{": end = matching(tokens, other) + 1
        else: raise ValueError("unsupported else body")
        alternative = tokens[other:end]
    return i, close, end, alternative


def _is_match_guard(tokens, at):
    i = at+1
    while i < len(tokens):
        if tokens[i] == "=>": return True
        if tokens[i] == "{": return False
        if tokens[i] in ("(", "["): i = matching(tokens, i)+1
        else: i += 1
    return True


def fold_tokens(tokens, constants):
    """Fold only provable pure conditions; preserve scopes and unknown effects.

    constants names are an explicit caller promise that those names are
    unshadowed. The production caller additionally binds every source hash.
    """
    out, i = [], 0
    while i < len(tokens):
        if tokens[i] == "if" and not _is_match_guard(tokens, i):
            opening, closing, end, alternative = _if_parts(tokens, i)
            value, pure = _value(tokens[i+1:opening], constants)
            if isinstance(value, bool) and pure:
                if value: chosen = tokens[opening+1:closing]
                elif alternative is None: chosen = []
                elif alternative[0] == "{": chosen = alternative[1:-1]
                else: chosen = alternative
                out += ["{"] + fold_tokens(chosen, constants) + ["}"]
                i = end
                continue
        if tokens[i] in ("(", "[", "{"):
            close = matching(tokens, i)
            out += [tokens[i]] + fold_tokens(tokens[i+1:close], constants) + [tokens[close]]
            i = close + 1
        else:
            out.append(tokens[i]); i += 1
    return out


def specialize_text(source, constants):
    return render(fold_tokens(tokenize(source), constants))


def _cfg_value(tokens):
    key = "".join(tokens)
    if key in ("test", "rove_f_single"): return False
    if key in ('target_arch="x86_64"',): return True
    if len(tokens) >= 3 and tokens[1] == "(" and matching(tokens, 1) == len(tokens)-1:
        name, inside = tokens[0], tokens[2:-1]
        if name == "not": return not _cfg_value(inside)
        parts, begin = [], 0
        for i in _groups(inside):
            if inside[i] == ",": parts.append(inside[begin:i]); begin = i+1
        if begin < len(inside): parts.append(inside[begin:])
        values = [_cfg_value(p) for p in parts]
        if name == "all": return all(values)
        if name == "any": return any(values)
    raise ValueError("unsupported cfg: " + key)


def _following_end(tokens, at):
    """End of a cfg-controlled field, initializer, statement or item."""
    i = at
    while tokens[i:i+2] == ["#", "["]:
        i = matching(tokens, i+1)+1
    if i < len(tokens) and tokens[i] == "{": return matching(tokens, i)+1
    # Functions, structs and impls end at their body; uses/constants/let/fields
    # end at ; or , while nested calls/tuples are opaque.
    header, j = [], i
    while j < len(tokens):
        t = tokens[j]
        if t in (";", ","): return j+1
        if t == "{":
            close = matching(tokens, j)
            if any(x in header for x in ("fn", "struct", "impl", "enum", "trait")): return close+1
            j = close+1; continue
        if t in ("(", "["): j = matching(tokens, j)+1; continue
        header.append(t); j += 1
    if j == len(tokens):
        # Last field of a struct/initializer may omit its trailing comma.
        if at+1 < len(tokens) and tokens[at+1] == ":": return len(tokens)
    raise ValueError("cfg target has no terminator: " + render(tokens[at:]))


def _strip_cfg(tokens):
    out, i = [], 0
    while i < len(tokens):
        if tokens[i:i+2] == ["#", "["]:
            end = matching(tokens, i+1)
            attr = tokens[i+2:end]
            if attr[:2] == ["cfg", "("]:
                keep = _cfg_value(attr[2:-1])
                if not keep: i = _following_end(tokens, end+1); continue
                i = end+1; continue
        if tokens[i] in ("(", "[", "{"):
            close = matching(tokens, i)
            out += [tokens[i]] + _strip_cfg(tokens[i+1:close]) + [tokens[close]]
            i = close+1
        else: out.append(tokens[i]); i += 1
    return out


def _function(tokens, name):
    found = [i for i in range(len(tokens)-1) if tokens[i:i+2] == ["fn", name]]
    if len(found) != 1: raise ValueError("expected one function: " + name)
    at = found[0]; start = at-1 if at and tokens[at-1] == "pub" else at
    i = at+2
    while tokens[i] != "{":
        i = matching(tokens, i)+1 if tokens[i] in ("(", "[") else i+1
    return start, matching(tokens, i)+1


def _drop_functions(tokens, names):
    for name in names:
        start, end = _function(tokens, name)
        # Function attributes are not meaningful without their item.
        while start >= 2 and tokens[start-1] == "]":
            opening = matching(tokens, start-1)
            if opening == 0 or tokens[opening-1] != "#": break
            start = opening-1
        tokens = tokens[:start] + tokens[end:]
    return tokens


def _replace(tokens, old, new, *, count=1):
    needle, replacement = tokenize(old), tokenize(new)
    positions = [i for i in range(len(tokens)-len(needle)+1) if tokens[i:i+len(needle)] == needle]
    if len(positions) != count: raise ValueError("source anchor mismatch: " + old[:70])
    for i in reversed(positions): tokens[i:i+len(needle)] = replacement
    return tokens


def _root_parallel(tokens):
    """Prune the bound production scheduler for fixed A/root; never a template.

    The journal is inverted before returning. Only exact, pinned token spans
    are edited; work publication, queue consumption and drain stay canonical.
    """
    original = list(tokens)
    journal = []

    def change(start, end, replacement, role):
        old = tokens[start:end]
        journal.append((start, old, list(replacement), role))
        tokens[start:end] = replacement

    def rewrite(old, new, role):
        needle = tokenize(old)
        positions = [i for i in range(len(tokens)-len(needle)+1) if tokens[i:i+len(needle)] == needle]
        if len(positions) != 1: raise ValueError("root source anchor mismatch: " + role)
        change(positions[0], positions[0]+len(needle), tokenize(new), role)

    def drop_function(name):
        start, end = _function(tokens, name)
        while start >= 2 and tokens[start-1] == "]":
            opening = matching(tokens, start-1)
            if opening == 0 or tokens[opening-1] != "#": break
            start = opening-1
        change(start, end, [], "unreachable function " + name)

    needle = tokenize("#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Bound")
    starts = [i for i in range(len(tokens)-len(needle)+1) if tokens[i:i+len(needle)] == needle]
    if len(starts) != 1: raise ValueError("root PALS item boundary mismatch")
    change(starts[0], _function(tokens, "report")[0], [], "unreachable PALS types and producer")
    for name in ("report", "policy", "group_count", "loose_depth"):
        drop_function(name)
    rewrite("if let Some(r)=result{report(r);}", "", "shipping terminal report")
    rewrite("report(r);", "", "shipping completed-depth report")
    rewrite("use std::time::{Duration,Instant};", "", "unreachable policy timing import")
    rewrite("enum Kind{Reset,Loose,Split}", "enum Kind{Reset,Split}", "fixed task kinds")
    rewrite("depth:u8,guess:i32,", "depth:u8,", "unused loose guess field")
    rewrite("epoch:u64,workers:usize,groups:usize,first_job:usize,", "epoch:u64,first_job:usize,", "single shared-table task context")
    rewrite("let loose={{false}};if loose{completed(searcher.iteration_frozen(&self.board,self.depth,self.guess))}else{self.work(searcher,worker*self.groups/self.workers,self.first_job+worker);None}", "self.work(searcher,0,self.first_job+worker);None", "canonical root task callback")
    rewrite("workers:usize,mode:u8,effective:u8,groups:usize,counters:Arc<Counters>,", "workers:usize,counters:Arc<Counters>,", "inactive engine policy fields")
    rewrite("let effective=if variant==b'F'{0}else{mode};let groups=group_count(variant,effective,workers,tt_bits);let group_shift=if groups==1{0}else{usize::BITS as usize-(groups-1).leading_zeros()as usize};let tables:Vec<_> =(0..groups).map(|_|Arc::new(Table::new(tt_bits.saturating_sub(group_shift)))).collect();", "let tables=vec![Arc::new(Table::new(tt_bits))];", "one table with the original total TT budget")
    rewrite("tables[i*groups/workers].clone()", "tables[0].clone()", "helpers share the original single group")
    rewrite("depth:0,guess:0,", "depth:0,", "unused loose guess initializer")
    rewrite("epoch:0,workers,groups,first_job:0,", "epoch:0,first_job:0,", "single group task initializer")
    rewrite("workers,mode,effective,groups,counters", "workers,counters", "inactive engine policy initializer")
    rewrite("previous:Option<SearchResult>,pals:bool", "previous:Option<SearchResult>", "fixed root split signature")
    rewrite("let pals={crate::PARALLEL==3};", "", "fixed root excludes PALS selection")
    positions = [i for i in range(len(tokens)-3) if tokens[i:i+4] == ["if", "pals", "&&", "depth"]]
    if len(positions) != 1: raise ValueError("root PALS statement boundary mismatch")
    _, _, end, _ = _if_parts(tokens, positions[0])
    change(positions[0], end, [], "PALS-only proposal/Repair cache producer")
    rewrite("let mut proposal=", "let proposal=", "immutable exact first proposal")
    rewrite("let mut cache=None;", "let cache=None;", "mode1 cache remains None")
    rewrite("let(mut best,mut older,mut last_cost,mut last_policy)=(None,None,Duration::ZERO,255);let mut parity_guess=[0;2];", "let mut best=None;", "only completed root depth state")
    rewrite("let selected={policy(crate::PARALLEL,best,older,last_cost,&self.control)};if last_policy!=255&&selected!=last_policy{self.counters.switches.fetch_add(1,Ordering::Relaxed);}self.counters.policies.fetch_or(1<<selected,Ordering::Relaxed);last_policy=selected;let start=Instant::now();let previous=best.map_or(0,|r:SearchResult|r.score);let guess={previous};{}", "", "inactive hybrid/F selection and timing")
    rewrite("let r=if selected==0{self.loose_depth(board,depth,guess)}else{self.split_depth(board,depth,best,selected==3)};last_cost=start.elapsed();", "let r=self.split_depth(board,depth,best);", "canonical fixed-root invocation")
    rewrite("parity_guess[(depth&1)as usize]=r.score;older=best;", "", "inactive hybrid/F history")
    rewrite("let counters=&self.counters;{}", "", "inactive DEV counter display")
    restored = list(tokens)
    for start, old, new, role in reversed(journal):
        if restored[start:start+len(new)] != new: raise ValueError("root inverse mismatch: " + role)
        restored[start:start+len(new)] = old
    if restored != original: raise ValueError("root inverse did not restore bound scheduler")
    digest = lambda ts: hashlib.sha256(render(ts).encode()).hexdigest()
    proof = {"input_token_sha256": digest(original), "output_token_sha256": digest(tokens),
             "inverse_exact": True, "edits": [{"role": role, "old_token_sha256": digest(old), "new_token_sha256": digest(new)} for _,old,new,role in journal]}
    return tokens, proof


def _configuration(configuration):
    cfg = dict(configuration)
    for key in ("ROVE_VARIANT", "ROVE_WORKERS", "ROVE_TT_BITS", "ROVE_DEV", "ROVE_PARALLEL", "ROVE_MODEL", "ROVE_HQ"):
        if key not in cfg or not isinstance(cfg[key], str): raise ValueError("configuration missing: " + key)
    allowed = {"ROVE_VARIANT", "ROVE_WORKERS", "ROVE_TT_BITS", "ROVE_DEV", "ROVE_PARALLEL", "ROVE_MODEL", "ROVE_HQ", "ROVE_F_SINGLE", "ROVE_F_PARITY"}
    for key in cfg:
        if key not in allowed | {"SOURCE_DATE_EPOCH", "LC_ALL", "TZ"}: raise ValueError("unsupported configuration: " + key)
        if not isinstance(cfg[key], str): raise ValueError("configuration values must be strings")
    for key,value in {"SOURCE_DATE_EPOCH":"0", "LC_ALL":"C", "TZ":"UTC"}.items():
        if key in cfg and cfg[key] != value: raise ValueError("unsupported configuration: " + key)
    fixed = {"ROVE_VARIANT": "A", "ROVE_DEV": "0", "ROVE_MODEL": "0", "ROVE_HQ": "0", "ROVE_F_SINGLE": "0", "ROVE_F_PARITY": "0"}
    for key, value in fixed.items():
        if cfg.get(key, "0") != value: raise ValueError("unsupported configuration: " + key)
    for key, lo, hi in (("ROVE_WORKERS", 1, 512), ("ROVE_TT_BITS", 8, 26)):
        text = cfg[key]
        if not text.isascii() or not text.isdecimal() or not lo <= int(text) <= hi: raise ValueError("unsupported configuration: " + key)
        if str(int(text)) != text: raise ValueError("noncanonical configuration: " + key)
    if cfg["ROVE_PARALLEL"] not in ("0", "1"): raise ValueError("unsupported configuration: ROVE_PARALLEL")
    if cfg["ROVE_PARALLEL"] == "1" and (cfg["ROVE_WORKERS"], cfg["ROVE_TT_BITS"]) != ("2", "18"):
        raise ValueError("root structural profile requires workers 2 / TT bits 18")
    return cfg


def specialize_rust(files, *, configuration):
    cfg = _configuration(configuration)
    if not isinstance(files, dict) or any(not isinstance(k, str) or not isinstance(v, bytes) for k,v in files.items()): raise ValueError("files must map names to bytes")
    for name, expected in _SOURCE_BINDINGS.items():
        # Rust normalizes CRLF before lexical analysis, including literal
        # contents. Bind that exact normalized text, but retain the actual raw
        # input hashes/lengths in evidence. Lone CR or any content drift fails.
        if name not in files or hashlib.sha256(files[name].replace(b"\r\n",b"\n")).hexdigest() != expected: raise ValueError("source binding mismatch: " + name)
    if any(name not in {*_SOURCE_BINDINGS, "model/frozen.rs"} for name in files): raise ValueError("unexpected production source input")
    root = cfg["ROVE_PARALLEL"] == "1"
    constants = {"DEV": False, "crate::DEV": False, "VARIANT": 65, "crate::VARIANT": 65, "self.variant()": 65, "HQ": False, "eval::CROSS_MODEL": False, "crate::PARALLEL": int(cfg["ROVE_PARALLEL"])}
    tokens = {name: _strip_cfg(_clean(tokenize(data.decode("utf-8")))) for name,data in files.items() if name in _SOURCE_BINDINGS}
    # Profile-conditioned branches are folded before selected unreachable items.
    tokens = {name: fold_tokens(ts, constants) for name,ts in tokens.items()}
    main = tokens["rust/main.rs"]
    extracted = {}
    for name in ("read_command", "set_position", "go_limits"):
        start,end = _function(main,name); extracted[name] = render(main[start:end])
    main_text = _TEMPLATES["main"].replace("@WORKERS@",cfg["ROVE_WORKERS"]).replace("@TT_BITS@",cfg["ROVE_TT_BITS"])
    if root:
        if main_text.count("const PARALLEL:u8=0;") != 1: raise ValueError("root main profile anchor mismatch")
        main_text = main_text.replace("const PARALLEL:u8=0;", "const PARALLEL:u8=1;")
    for name in extracted: main_text = main_text.replace("@"+name.upper()+"@",extracted[name])
    # DEV match guards must be removed as arms, not converted to wildcard arms.
    mt = tokenize(main_text)
    i = 0
    while i < len(mt)-2:
        if mt[i:i+3] == ["if", "DEV", "=>"]:
            start=i-1
            while start and mt[start-1] == "|": start-=2
            at=i+3
            if mt[at] == "{": end=matching(mt,at)+1
            else:
                end=at
                while mt[end] != ",": end+=1
            if end < len(mt) and mt[end] == ",": end+=1
            del mt[start:end];i=start
        else:i+=1
    board = tokens["rust/board.rs"]
    board = _drop_functions(board,("hq_line","hq_attacks","square","from_fen","attackers_hq","perft","see","see_with_abort","exchange","fen") + (() if root else ("extend",)))
    # The profile's false HQ constant is now unused; remove its full const item.
    at=board.index("HQ"); begin=at-1; end=at
    while board[end] != ";":
        if board[end] in ("(","[","{"): end=matching(board,end)+1
        else:end+=1
    del board[begin:end+1]
    search = _drop_functions(tokens["rust/search.rs"], ("search_clause",) if root else ("search_move","search_move_hint","search_clause"))
    # Retain the eager TT publication when the F-only inconsistency abort is
    # removed. Dropping the false conditional wholesale would lose this write.
    search = _replace(search,"if !self.table.put(Entry {key,mv:best_move,depth,lower,upper},ply,&self.control) && self.variant()==b'F' {self.control.stop.store(true,Ordering::Relaxed);return Err(());}","let _=self.table.put(Entry {key,mv:best_move,depth,lower,upper},ply,&self.control);")
    search = _replace(search,"let mut lower_witness=None;","")
    parallel, root_proof = _root_parallel(tokens["rust/parallel.rs"]) if root else (tokenize(_TEMPLATES["parallel"]), None)
    pool = _drop_functions(tokens["rust/pool.rs"], ("control","first_result") if root else ("control","task"))
    output = {
        "rust/main.rs": render(mt).encode(),
        "rust/board.rs": render(board).encode(),
        "rust/eval.rs": b"use crate::board::Board;pub fn evaluate(b:&Board,_variant:u8)->i32{(b.evalwhite()*b.side as i32).clamp(-20000,20000)}",
        "rust/search.rs": render(search).encode(),
        "rust/parallel.rs": render(parallel).encode(),
        "rust/pool.rs": render(pool).encode(),
    }
    changes = ["DEV UCI arms and diagnostics excluded from runtime source", "A incremental HCE retained; inactive B/C/E model/SIMD source excluded", "A scalar sliding attacks retained; inactive HQ/SEE and FEN/perft display excluded", "paired TT writes retained including eager F-abort condition publication", "F MTD/singular/PALS branches excluded only for fixed A loose profile", "loose SMP startup/barriers, frozen correction epoch and first completed worker priority preserved", "test modules excluded before packing"]
    metadata = {"producer":"rust-A-structural-v1", "configuration":dict(cfg),"input_sha256":{n:hashlib.sha256(d).hexdigest() for n,d in sorted(files.items())},"binding_normalized_sha256":{n:hashlib.sha256(files[n].replace(b"\r\n",b"\n")).hexdigest() for n in sorted(_SOURCE_BINDINGS)},"input_crlf_counts":{n:d.count(b"\r\n") for n,d in sorted(files.items())},"output_sha256":{n:hashlib.sha256(d).hexdigest() for n,d in sorted(output.items())},"input_bytes":sum(map(len,files.values())),"output_bytes":sum(map(len,output.values())),"changes":changes,"guards":{"source_binding":"canonical-de5676d+reviewed-PALS-feedback","source_binding_review":"finite proposal/refutation/same-first repair/same-reply followup; hint-node TT cutoff gate and priority; terminal draw boundary in pruned helper methods","binding_normalization":"Rust CRLF to LF; raw input hashes retained","variant":"A","development":False,"parallel":"loose","hq":False,"model":False,"external_crates":False,"canonical_unchanged":True}}
    if root:
        metadata["producer"] = "rust-A-fixed-root-structural-v1"
        metadata["guards"].update(parallel="root", workers=2, tt_bits=18, native_threads=3,
                                  source_only=True, runtime_qualified=False,
                                  source_binding_review="canonical fixed mode1 root queue and completion; PALS/group/hybrid producers unreachable and excluded")
        metadata["root_transform"] = root_proof
        metadata["changes"] = changes[:4] + [
            "canonical Depth/search_move queue and all-required-complete aggregation retained; no parallel.in backend",
            "exact first NORMAL proposal seeds initial best and finished=1; cache=None implies first_job=1 and skips that first task",
            "PALS Some-cache/approved unrestricted Repair producers excluded for mode1; typed cache consumer remains depth-local",
            "canonical Board.play(first), ply1, root history, SearchResult depth/witness and hint-node TT rules retained",
            "original GO control/deadline, immutable root owner, frozen correction epoch, helper drain and physical join retained",
            "group/PALS/hybrid/F-only and DEV/test paths excluded; no new resource UCI options",
            "Rust frozen-correction leaf and epoch/history TT differ from C; no language-only matched claim"]
    return output, metadata
