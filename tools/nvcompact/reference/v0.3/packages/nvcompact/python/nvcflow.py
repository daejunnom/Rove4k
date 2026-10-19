#!/usr/bin/env python3
"""Generate audited, type-checked C expression portfolios with an optional Clang.

This is a deliberately bounded set of local C rewrites, not a general theorem
prover.  Identity is always retained.  A run manifest can compare every candidate
after compilation, whole-file packing, and the user's execution verifier.
"""
from __future__ import annotations

import argparse
import bisect
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from nvnotation import MAX_SOURCE, _lex
import nvnotation


class FlowError(Exception):
    pass


RULES = ("if-return", "return-tail", "if-assignment", "if-effect", "guard",
         "boolean", "zero-test", "truth", "negation", "compound", "increment",
         "leaf-braces", "forever")
STANDARDS = ("c11", "c17", "gnu11", "gnu17")
INTEGER_TYPES = frozenset(("_Bool", "char", "signed char", "unsigned char",
    "short", "unsigned short", "int", "unsigned int", "long", "unsigned long",
    "long long", "unsigned long long", "__int128", "unsigned __int128"))
PROTECTED_KINDS = frozenset(("CompoundLiteralExpr", "StmtExpr", "GenericSelectionExpr",
    "ChooseExpr", "UnaryExprOrTypeTraitExpr", "VAArgExpr", "AtomicExpr",
    "GCCAsmStmt", "MSAsmStmt", "AddrLabelExpr", "IndirectGotoStmt"))
OBSERVING_CALLS = frozenset(("setjmp", "_setjmp", "sigsetjmp", "__builtin_setjmp",
    "__builtin_constant_p", "__builtin_object_size", "__builtin_dynamic_object_size",
    "__builtin_frame_address", "__builtin_return_address"))
EXPR_KINDS = frozenset(("DeclRefExpr", "IntegerLiteral", "FloatingLiteral", "CharacterLiteral",
    "StringLiteral", "ParenExpr", "ImplicitCastExpr", "CStyleCastExpr", "UnaryOperator",
    "BinaryOperator", "CompoundAssignOperator", "ConditionalOperator", "CallExpr",
    "ArraySubscriptExpr", "MemberExpr", "PredefinedExpr"))
PREC = {",": 1, "=": 2, "+=": 2, "-=": 2, "*=": 2, "/=": 2, "%=": 2,
    "&=": 2, "|=": 2, "^=": 2, "<<=": 2, ">>=": 2, "||": 4, "&&": 5,
    "|": 6, "^": 7, "&": 8, "==": 9, "!=": 9, "<": 10, ">": 10,
    "<=": 10, ">=": 10, "<<": 11, ">>": 11, "+": 12, "-": 12,
    "*": 13, "/": 13, "%": 13}
C_PUNCT = frozenset(("[", "]", "(", ")", "{", "}", ".", "->", "++", "--",
    "&", "*", "+", "-", "~", "!", "/", "%", "<<", ">>", "<", ">", "<=", ">=",
    "==", "!=", "^", "|", "&&", "||", "?", ":", ";", "...", "=", "*=", "/=",
    "%=", "+=", "-=", "<<=", ">>=", "&=", "^=", "|=", ",", "#", "##",
    "<:", ":>", "<%", "%>", "%:", "%:%:"))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def children(node):
    return [x for x in node.get("inner", []) if isinstance(x, dict) and x.get("kind")]


def walk(node):
    stack = [node]
    while stack:
        current = stack.pop()
        yield current
        stack.extend(reversed(children(current)))


def type_name(node):
    typ = node.get("type", {})
    return typ.get("desugaredQualType", typ.get("qualType", ""))


def unwrap(node):
    """Reach the expression spelled in source, before contextual conversions."""
    while node.get("kind") in ("ImplicitCastExpr", "ParenExpr") and len(children(node)) == 1:
        node = children(node)[0]
    return node


def value_type(node):
    # ReturnStmt/assignment ASTs contain conversions introduced by their context.
    # Keep the conversions intrinsic to using a source value, not IntegralCast
    # from the enclosing return. Pointee qualifiers must never be erased here.
    while len(children(node)) == 1:
        if node.get("kind") == "ParenExpr":
            node = children(node)[0]
        elif node.get("kind") == "ImplicitCastExpr":
            if node.get("castKind") in ("LValueToRValue", "ArrayToPointerDecay", "FunctionToPointerDecay"):
                return type_name(node)
            node = children(node)[0]
        else:
            break
    return type_name(node)


def integer(typ):
    return typ in INTEGER_TYPES


def pointer(typ):
    return "*" in typ and not any(s in typ for s in ("volatile", "_Atomic", "__attribute__"))


def ordinary(typ):
    return integer(typ) or pointer(typ)


def same_values(a, b, *, void=False):
    left, right = value_type(a), value_type(b)
    return left == right and (ordinary(left) or (void and left == "void"))


def literal(node, value, *, int_only=False):
    node = unwrap(node)
    return node.get("kind") == "IntegerLiteral" and node.get("value") == str(value) and (
        not int_only or type_name(node) == "int")


def boolean_result(node):
    node = unwrap(node)
    return type_name(node) == "int" and (
        node.get("kind") == "UnaryOperator" and node.get("opcode") == "!" or
        node.get("kind") == "BinaryOperator" and node.get("opcode") in (
            "==", "!=", "<", ">", "<=", ">=", "&&", "||"))


def binding(node):
    node = unwrap(node)
    return node.get("referencedDecl", {}).get("id") if node.get("kind") == "DeclRefExpr" else None


def precedence(node):
    while node.get("kind") == "ImplicitCastExpr" and len(children(node)) == 1:
        node = children(node)[0]
    kind = node.get("kind")
    if kind in ("BinaryOperator", "CompoundAssignOperator"):
        return PREC.get(node.get("opcode"), 0)
    if kind == "ConditionalOperator":
        return 3
    if kind in ("UnaryOperator", "CStyleCastExpr"):
        return 15 if node.get("isPostfix") else 14
    return 16


def validate_args(values):
    """Only frontend/ABI inputs, never plugins, response files or output actions."""
    if not isinstance(values, (tuple, list)) or not all(isinstance(v, str) and "\0" not in v for v in values):
        raise FlowError("compiler_args must be an argv list of strings")
    result, i = [], 0
    paired = ("-I", "-isystem", "-iquote", "-D", "-U", "--target", "-target", "--sysroot", "-isysroot")
    fixed = ("-m32", "-m64", "-funsigned-char", "-fsigned-char", "-fshort-enums",
             "-ffreestanding", "-fno-builtin", "-pthread")
    prefixes = ("-I", "-D", "-U", "--target=", "--sysroot=", "-march=", "-mcpu=", "-mtune=")
    while i < len(values):
        value = values[i]
        if value in paired:
            if i + 1 == len(values) or not values[i + 1] or values[i + 1].startswith("-"):
                raise FlowError(f"{value} requires one literal operand")
            result.extend(values[i:i + 2])
            i += 2
        elif value in fixed or any(value.startswith(p) and len(value) > len(p) for p in prefixes):
            result.append(value)
            i += 1
        else:
            raise FlowError(f"unsupported frontend argument: {value!r}; use a declared preprocessed input or extend the frontend contract")
    return tuple(result)


class Frontend:
    def __init__(self, clang, standard, compiler_args, source_path, seconds, memory_bytes, ast_bytes):
        found = shutil.which(os.fspath(clang))
        if not found:
            raise FlowError(f"Clang frontend unavailable: {clang!r}; provide --clang PATH")
        self.executable = str(Path(found).absolute())
        self.standard, self.args = standard, validate_args(compiler_args)
        self.cwd = Path(source_path).resolve().parent if source_path else Path.cwd()
        self.seconds, self.memory_bytes, self.ast_bytes = seconds, memory_bytes, ast_bytes
        self.directory = tempfile.TemporaryDirectory(prefix="nvcompact-cflow-")
        self.root = Path(self.directory.name)
        self.env = {"PATH": os.pathsep.join((str(Path(self.executable).parent), "/usr/bin", "/bin")),
                    "LANG": "C", "LC_ALL": "C", "TZ": "UTC", "SOURCE_DATE_EPOCH": "0"}
        try:
            version = self.run([self.executable, "--version"], "version", 65536).decode("utf-8", "replace").strip()
            if "clang version" not in version.lower():
                raise FlowError("--clang did not identify itself as Clang")
            self.info = {"executable": self.executable, "executable_sha256": digest(Path(self.executable).read_bytes()),
                         "version": version, "standard": standard, "compiler_args": list(self.args),
                         "source_include_directory": str(self.cwd), "seconds_per_parse": seconds,
                         "address_space_bytes": memory_bytes, "ast_output_bytes": ast_bytes}
        except BaseException:
            self.close()
            raise

    def close(self):
        self.directory.cleanup()

    def run(self, argv, label, limit):
        # A fresh Python child applies limits before exec. No preexec_fn is used:
        # callers may be multi-threaded. This is a bound, not a code sandbox.
        limiter = ("import os,resource,sys; "
            "resource.setrlimit(resource.RLIMIT_AS,(int(sys.argv[1]),)*2); "
            "resource.setrlimit(resource.RLIMIT_CPU,(int(sys.argv[2]),)*2); "
            "resource.setrlimit(resource.RLIMIT_FSIZE,(int(sys.argv[3]),)*2); "
            "os.execv(sys.argv[4],sys.argv[4:])")
        command = [sys.executable, "-c", limiter, str(self.memory_bytes), str(math.ceil(self.seconds) + 1), str(limit), *argv]
        out_path, err_path = self.root / (label + ".out"), self.root / (label + ".err")
        reason, process = None, None
        with out_path.open("wb") as out, err_path.open("wb") as err:
            try:
                process = subprocess.Popen(command, cwd=self.cwd, env=self.env, stdin=subprocess.DEVNULL,
                    stdout=out, stderr=err, start_new_session=True)
                deadline = time.monotonic() + self.seconds
                while process.poll() is None:
                    if time.monotonic() >= deadline:
                        reason = "frontend timeout"
                        break
                    if out_path.stat().st_size + err_path.stat().st_size > limit:
                        reason = "frontend output limit"
                        break
                    time.sleep(.01)
            finally:
                if process is not None:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
        if reason or process.returncode or out_path.stat().st_size + err_path.stat().st_size > limit:
            tail = err_path.read_bytes()[-4096:].decode("utf-8", "replace")
            raise FlowError(f"{reason or 'frontend failure'} ({process.returncode}): {tail}")
        return out_path.read_bytes()

    def parse(self, source):
        path = self.root / "translation.c"
        path.write_bytes(source)
        prefix = [self.executable, "-x", "c", f"-std={self.standard}", *self.args,
                  "-iquote", str(self.cwd)]
        argv = [*prefix, "-fsyntax-only", "-Xclang", "-ast-dump=json", str(path)]
        try:
            tree = json.loads(self.run(argv, "ast", self.ast_bytes))
        except (ValueError, RecursionError) as exc:
            raise FlowError("Clang AST JSON is invalid or exceeds the supported nesting depth") from exc
        if not isinstance(tree, dict) or tree.get("kind") != "TranslationUnitDecl":
            raise FlowError("unsupported Clang JSON AST shape")
        # A generated keyword can itself be a macro, including one supplied by
        # an included header. Retain the union of *all* encountered definitions
        # (also those later undefined), rather than only the final -dM state.
        # This is conservative across conditional inclusion and source ranges.
        definitions = self.run([*prefix, "-E", "-dD", str(path)], "macros", self.ast_bytes)
        macros = set(re.findall(br"(?m)^\s*#\s*define\s+([A-Za-z_]\w*)", definitions))
        return Analysis(source.decode("latin-1"), tree, str(path),
                        {name.decode("ascii") for name in macros})


@dataclass(frozen=True)
class Edit:
    start: int
    end: int
    text: str
    rule: str
    proof: str
    function: str


class Analysis:
    def __init__(self, source, tree, main_path, macros=()):
        self.source, self.tree, self.main_path = source, tree, main_path
        self.macros = frozenset(macros)
        self.tokens = [t for t in _lex(source, "c") if t.kind not in ("space", "comment")]
        self.starts = [t.start for t in self.tokens]
        self.parents = {}
        self.declarations = {}
        for node in walk(tree):
            if node.get("id") and node.get("kind", "").endswith("Decl"):
                self.declarations[node["id"]] = node
            for child in children(node):
                self.parents[id(child)] = node
        self.functions, self.notes = [], []
        for node in children(tree):
            if node.get("kind") != "FunctionDecl":
                continue
            body = next((c for c in children(node) if c.get("kind") == "CompoundStmt"), None)
            loc = node.get("loc", {})
            if not body or "includedFrom" in loc or loc.get("file", main_path) != main_path or not self.span(body):
                continue
            reason = self.protection(body)
            if reason:
                self.notes.append(f"function {node.get('name', '?')} left unchanged: {reason}")
            else:
                self.functions.append((node, body))

    def span(self, node):
        ran = node.get("range", {})
        begin, end = ran.get("begin", {}), ran.get("end", {})
        if any("spellingLoc" in p or "expansionLoc" in p or "includedFrom" in p for p in (begin, end)):
            return None
        if any(p.get("file", self.main_path) != self.main_path for p in (begin, end)):
            return None
        a, b, length = begin.get("offset"), end.get("offset"), end.get("tokLen")
        if not all(type(x) is int for x in (a, b, length)) or not 0 <= a <= b < b + length <= len(self.source):
            return None
        return a, b + length

    def text(self, node):
        span = self.span(node)
        if not span:
            raise FlowError("an eligible AST node has no supported source range")
        return self.source[span[0]:span[1]]

    def expression(self, node, minimum=1):
        text = self.text(node)
        return f"({text})" if precedence(node) < minimum else text

    def next_token(self, offset):
        index = bisect.bisect_left(self.starts, offset)
        return self.tokens[index] if index < len(self.tokens) else None

    def statement_span(self, node):
        span = self.span(node)
        if not span:
            return None
        if node.get("kind") == "CompoundStmt":
            return span
        if node.get("kind") == "IfStmt":
            final = self.statement_span(children(node)[-1])
            return (span[0], final[1]) if final else None
        if node.get("kind") in EXPR_KINDS | {"ReturnStmt", "BreakStmt", "ContinueStmt", "NullStmt"}:
            if self.source[span[1] - 1:span[1]] == ";":
                return span
            token = self.next_token(span[1])
            return (span[0], token.end) if token and token.text == ";" else None
        return None

    def protection(self, node):
        span = self.span(node)
        if span:
            for token in self.tokens[bisect.bisect_left(self.starts, span[0]):bisect.bisect_left(self.starts, span[1])]:
                if token.kind == "identifier" and (token.text in self.macros or token.text in ("_Pragma", "__pragma")):
                    # Macros can expand to nothing or only a preprocessing
                    # effect, leaving no AST location to reject afterwards.
                    return "macro or pragma operator in source tokens (including AST-invisible preprocessing effects)"
                if token.kind == "directive":
                    return "preprocessing directive in function body"
        for sub in walk(node):
            kind, typ = sub.get("kind", ""), type_name(sub)
            if not self.span(sub) and sub.get("range"):
                return "macro expansion or non-main-file source location"
            if kind in PROTECTED_KINDS or kind.endswith("Attr"):
                return f"context/lifetime-sensitive AST construct: {kind}"
            if "volatile" in typ or "_Atomic" in typ:
                return "volatile or atomic access/type"
            if kind == "CallExpr":
                call = children(sub)
                callee = unwrap(call[0]) if call else {}
                if callee.get("kind") != "DeclRefExpr" or callee.get("referencedDecl", {}).get("kind") != "FunctionDecl":
                    return "indirect call: target context/returns-twice attributes are not established"
            if kind == "CallExpr" and not (ordinary(typ) or typ in ("void", "float", "double", "long double")):
                return "aggregate or unsupported call result lifetime"
            if kind == "DeclRefExpr":
                ref = sub.get("referencedDecl", {})
                declaration = self.declarations.get(ref.get("id"), {})
                if ref.get("name") in OBSERVING_CALLS or any(c.get("kind") == "ReturnsTwiceAttr" for c in children(declaration)):
                    return "source/context observation or returns-twice call"
            if kind.endswith("Expr") and kind not in EXPR_KINDS:
                return f"unsupported expression kind: {kind}"
        return None

    def leaf(self, node):
        if node.get("kind") == "CompoundStmt":
            inner = children(node)
            return inner[0] if len(inner) == 1 and inner[0].get("kind") in EXPR_KINDS | {"ReturnStmt", "BreakStmt", "ContinueStmt"} else None
        return node

    def safe_rhs(self, node):
        return all(n.get("kind") not in ("CallExpr", "CompoundAssignOperator") and
            not (n.get("kind") == "BinaryOperator" and n.get("opcode") == "=") and
            not (n.get("kind") == "UnaryOperator" and n.get("opcode") in ("++", "--"))
            for n in walk(node))

    def fit_parent(self, node, text, prec):
        parent = self.parents.get(id(node))
        while parent and parent.get("kind") == "ImplicitCastExpr":
            node, parent = parent, self.parents.get(id(parent))
        if not parent or parent.get("kind") in ("ParenExpr", "ReturnStmt", "IfStmt", "WhileStmt", "DoStmt", "ForStmt", "CompoundStmt"):
            return text
        kind = parent.get("kind")
        if kind in ("BinaryOperator", "CompoundAssignOperator", "ConditionalOperator", "UnaryOperator", "CStyleCastExpr"):
            return f"({text})" if prec <= precedence(parent) else text
        if kind in ("CallExpr", "ArraySubscriptExpr", "InitListExpr", "VarDecl"):
            return f"({text})" if prec < 2 else text
        # Member access and unknown consumers need a primary expression.
        return f"({text})" if prec < 16 else text

    def separate_tokens(self, start, end, text):
        """Prevent a splice from creating e.g. elsebreak, ++ or a comment."""
        generated = [t for t in _lex(text, "c") if t.kind not in ("space", "comment")]
        if not generated:
            return text
        def merges(left, right):
            joined = [(t.kind, t.text) for t in _lex(left.text + right.text, "c")]
            return joined != [(left.kind, left.text), (right.kind, right.text)]
        before = bisect.bisect_left(self.starts, start) - 1
        after = bisect.bisect_left(self.starts, end)
        if before >= 0 and self.tokens[before].end == start and generated[0].start == 0 and merges(self.tokens[before], generated[0]):
            text = " " + text
        if after < len(self.tokens) and self.tokens[after].start == end and generated[-1].end == len(text.lstrip(" ")) and merges(generated[-1], self.tokens[after]):
            text += " "
        return text

    def find(self, enabled):
        edits = []
        function = ""
        def add(node, text, rule, proof, *, span=None, prec=None):
            if rule not in enabled:
                return
            ran = span or self.span(node)
            if not ran:
                return
            if prec is not None:
                text = self.fit_parent(node, text, prec)
            text = self.separate_tokens(ran[0], ran[1], text)
            if any(t.kind == "directive" for t in self.tokens[bisect.bisect_left(self.starts, ran[0]):bisect.bisect_left(self.starts, ran[1])]):
                return
            if len(text) < ran[1] - ran[0]:
                edits.append(Edit(*ran, text, rule, proof, function))

        def ternary(condition, left, right):
            return self.expression(condition, 4) + "?" + self.expression(left) + ":" + self.expression(right, 3)

        def returns(condition, left, right, owner, span=None, rule="if-return"):
            if left and right and left.get("kind") == right.get("kind") == "ReturnStmt":
                a, b = children(left), children(right)
                if len(a) == len(b) == 1 and same_values(a[0], b[0]):
                    add(owner, "return " + ternary(condition, a[0], b[0]) + ";", rule,
                        "same source value type before return conversion; condition once, selected operand once", span=span)

        for declaration, body in self.functions:
            function = declaration.get("name", "?")
            for node in walk(body):
                kind, inner = node.get("kind"), children(node)
                if kind == "IfStmt" and len(inner) in (2, 3):
                    condition, then = inner[:2]
                    left = self.leaf(then)
                    if len(inner) == 3 and node.get("hasElse"):
                        right = self.leaf(inner[2])
                        returns(condition, left, right, node, self.statement_span(node))
                        if left and right and left.get("kind") == right.get("kind") == "BinaryOperator" and left.get("opcode") == right.get("opcode") == "=":
                            la, ra = children(left), children(right)
                            if len(la) == len(ra) == 2 and binding(la[0]) and binding(la[0]) == binding(ra[0]) and ordinary(type_name(unwrap(la[0]))) and same_values(la[1], ra[1]):
                                add(node, self.text(la[0]) + "=" + ternary(condition, la[1], ra[1]) + ";", "if-assignment",
                                    "same plain non-atomic/non-volatile binding; matching pre-assignment RHS types; selected store once", span=self.statement_span(node))
                        if left and right and left.get("kind") in EXPR_KINDS and right.get("kind") in EXPR_KINDS and same_values(left, right, void=True):
                            add(node, ternary(condition, left, right) + ";", "if-effect",
                                "discarded same-type (or void) branch expressions; short-circuit order unchanged", span=self.statement_span(node))
                    elif len(inner) == 2 and left and left.get("kind") in EXPR_KINDS and ordinary(value_type(left)):
                        add(node, self.expression(condition, 5) + "&&" + self.expression(left, 6) + ";", "guard",
                            "discarded integer/pointer result; condition then selected effect once", span=self.statement_span(node))
                if kind == "CompoundStmt":
                    for first, second in zip(inner, inner[1:]):
                        ci = children(first)
                        if first.get("kind") == "IfStmt" and len(ci) == 2 and not first.get("hasElse") and second.get("kind") == "ReturnStmt":
                            span = self.statement_span(second)
                            start = self.span(first)
                            if span and start:
                                returns(ci[0], self.leaf(ci[1]), second, first, (start[0], span[1]), "return-tail")
                if kind == "ConditionalOperator" and len(inner) == 3 and type_name(node) == "int":
                    cond, left, right = inner
                    if literal(left, 1, int_only=True) and literal(right, 0, int_only=True):
                        if boolean_result(cond):
                            add(node, self.text(cond), "boolean", "condition already has the exact C int 0/1 result", prec=precedence(cond))
                        else:
                            add(node, "!!" + self.expression(cond, 14), "boolean", "int 0/1 result and one scalar truth evaluation", prec=14)
                    elif literal(left, 0, int_only=True) and literal(right, 1, int_only=True):
                        add(node, "!" + self.expression(cond, 14), "boolean", "int 0/1 result and one scalar truth evaluation", prec=14)
                if kind == "BinaryOperator" and len(inner) == 2:
                    op, left, right = node.get("opcode"), inner[0], inner[1]
                    if op in ("==", "!="):
                        value = left if literal(right, 0) else right if literal(left, 0) else None
                        if value:
                            add(node, ("!" if op == "==" else "!!") + self.expression(value, 14), "zero-test",
                                "C logical-not/equality-to-zero correspondence; one scalar read; int result", prec=14)
                    if op == "=" and binding(left) and ordinary(type_name(unwrap(left))):
                        rhs = unwrap(right)
                        ri = children(rhs)
                        if rhs.get("kind") == "BinaryOperator" and rhs.get("opcode") in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>") and len(ri) == 2 and binding(ri[0]) == binding(left) and self.safe_rhs(ri[1]):
                            add(node, self.text(left) + rhs["opcode"] + "=" + self.expression(ri[1], 2), "compound",
                                "same ordinary plain binding; C compound-assignment conversion; no RHS call or mutation", prec=2)
                if kind == "CompoundAssignOperator" and len(inner) == 2 and node.get("opcode") in ("+=", "-="):
                    left, right = inner
                    if binding(left) and ordinary(type_name(unwrap(left))) and literal(right, 1, int_only=True):
                        add(node, ("++" if node["opcode"] == "+=" else "--") + self.expression(left, 14), "increment",
                            "plain ordinary binding; exact source int literal 1; prefix returns the stored new value", prec=14)
                if kind == "UnaryOperator" and node.get("opcode") == "!" and len(inner) == 1:
                    operand = unwrap(inner[0])
                    oi = children(operand)
                    if operand.get("kind") == "UnaryOperator" and operand.get("opcode") == "!" and len(oi) == 1 and boolean_result(oi[0]):
                        add(node, self.text(oi[0]), "boolean", "double negation of an existing int 0/1 result", prec=precedence(oi[0]))
                    if operand.get("kind") == "BinaryOperator" and len(oi) == 2:
                        op = operand.get("opcode")
                        if op in ("&&", "||"):
                            replacement = "||" if op == "&&" else "&&"
                            add(node, "!" + self.expression(oi[0], 14) + replacement + "!" + self.expression(oi[1], 14), "negation",
                                "De Morgan over C truth values; same left-before-right short-circuit decision and int 0/1 result", prec=PREC[replacement])
                        inv = {"==": "!=", "!=": "==", "<": ">=", ">": "<=", "<=": ">", ">=": "<"}
                        if op in inv and (op in ("==", "!=") or all(ordinary(value_type(x)) for x in oi)):
                            np = PREC[inv[op]]
                            add(node, self.expression(oi[0], np + 1) + inv[op] + self.expression(oi[1], np + 1), "negation",
                                "complementary comparison; relational inversion excludes floating-point NaNs", prec=np)
                if kind in ("IfStmt", "WhileStmt", "DoStmt", "ConditionalOperator", "ForStmt") or (kind == "BinaryOperator" and node.get("opcode") in ("&&", "||")):
                    truth_nodes = []
                    if kind in ("IfStmt", "WhileStmt", "ConditionalOperator") and inner:
                        truth_nodes = [inner[0]]
                    elif kind == "DoStmt" and inner:
                        truth_nodes = [inner[-1]]
                    elif kind == "ForStmt":
                        # Clang has empty inner slots for absent init/condition.
                        slots = node.get("inner", [])
                        if len(slots) == 5 and slots[2].get("kind"):
                            truth_nodes = [slots[2]]
                    elif kind == "BinaryOperator":
                        truth_nodes = inner
                    for value in truth_nodes:
                        plain = unwrap(value)
                        vi = children(plain)
                        replacement = None
                        if plain.get("kind") == "BinaryOperator" and plain.get("opcode") == "!=" and len(vi) == 2:
                            replacement = vi[0] if literal(vi[1], 0) else vi[1] if literal(vi[0], 0) else None
                        elif plain.get("kind") == "UnaryOperator" and plain.get("opcode") == "!" and len(vi) == 1:
                            nested = unwrap(vi[0])
                            if nested.get("kind") == "UnaryOperator" and nested.get("opcode") == "!" and len(children(nested)) == 1:
                                replacement = children(nested)[0]
                        if replacement:
                            add(value, self.text(replacement), "truth", "only a scalar controlling/short-circuit context consumes this value", prec=precedence(replacement))
                if kind == "CompoundStmt" and node is not body:
                    parent = self.parents.get(id(node), {})
                    leaf = self.leaf(node)
                    if parent.get("kind") in ("IfStmt", "WhileStmt", "ForStmt", "DoStmt") and leaf:
                        span = self.statement_span(leaf)
                        if span:
                            add(node, self.source[span[0]:span[1]], "leaf-braces",
                                "single non-declaration leaf; no label, nested if or compound-literal lifetime; function scope retained")
                if kind == "WhileStmt" and "for" not in self.macros and len(inner) == 2 and unwrap(inner[0]).get("kind") == "IntegerLiteral" and int(unwrap(inner[0]).get("value", "0")) != 0:
                    ns, bs = self.span(node), self.span(inner[1])
                    if ns and bs:
                        add(node, "for(;;)", "forever", "nonzero integer-literal control; identical loop body and continue/break targets", span=(ns[0], bs[0]))
        return edits


def apply_pass(analysis, enabled):
    edits = analysis.find(enabled)
    selected = []
    # Choose greatest local savings; ties have stable rule/range order. This is
    # one portfolio candidate, never a claim about the compression optimum.
    for edit in sorted(edits, key=lambda e: (-(e.end - e.start - len(e.text)), e.start, e.end, e.rule)):
        if not any(edit.start < old.end and old.start < edit.end for old in selected):
            selected.append(edit)
    source, audit = analysis.source, []
    for edit in sorted(selected, key=lambda e: e.start, reverse=True):
        audit.append({"start": edit.start, "end": edit.end, "before": source[edit.start:edit.end],
            "after": edit.text, "rule": edit.rule, "proof": edit.proof, "function": edit.function,
            "source_bytes_saved": edit.end - edit.start - len(edit.text)})
        source = source[:edit.start] + edit.text + source[edit.end:]
    return source.encode("latin-1"), list(reversed(audit))


def generate_variants(source: bytes, *, token_contract="opaque", clang="clang", standard="c11",
                      compiler_args=(), source_path=None, max_variants=16, max_passes=2,
                      frontend_seconds=30, frontend_memory_bytes=1 << 30, ast_bytes=32 << 20):
    """Return raw, combined and per-rule variants; never execute the C program.

    Equal-byte recipes retain their identities and provenance. Each changed
    pass is parsed again by the same fixed frontend. The caller must compare
    compile/link/packed candidates and verify the program's real contract.
    """
    if not isinstance(source, bytes) or len(source) > MAX_SOURCE:
        raise FlowError(f"source must be bytes of at most {MAX_SOURCE}")
    if token_contract not in ("opaque", "no-token-observation", "preprocessed"):
        raise FlowError("unknown source/token contract")
    if standard not in STANDARDS:
        raise FlowError(f"supported C standards: {STANDARDS}")
    if type(max_variants) is not int or not 1 <= max_variants <= 32 or type(max_passes) is not int or not 1 <= max_passes <= 8:
        raise FlowError("max_variants must be 1..32 and max_passes 1..8")
    if not isinstance(frontend_seconds, (float, int)) or not math.isfinite(frontend_seconds) or not 0 < frontend_seconds <= 300:
        raise FlowError("frontend_seconds must be finite, positive and at most 300")
    if type(frontend_memory_bytes) is not int or frontend_memory_bytes < 64 << 20 or type(ast_bytes) is not int or not 65536 <= ast_bytes <= 128 << 20:
        raise FlowError("frontend memory must be at least 64 MiB; AST limit must be 64 KiB..128 MiB")
    args = validate_args(compiler_args)
    contract = {"language": "c", "token_contract": token_contract, "standard": standard,
        "source_sha256": digest(source), "compiler_args": list(args),
        "generator_sha256": {"nvcflow.py": digest(Path(__file__).read_bytes()),
                             "nvnotation.py": digest(Path(nvnotation.__file__).read_bytes())},
        "required_acceptance": "fixed compatible frontend/ABI, compilation and application verification; whole-file size selection",
        "proof_scope": "guarded local C rules, not whole-program equivalence proof"}
    def make(identifier, data, audit, notes):
        return {"id": identifier, "data": data, "source_bytes": len(source), "bytes": len(data),
            "sha256": digest(data), "audit": audit, "notes": notes, "contract": contract,
            "size_claim": "source bytes only, not final compressed-file optimum"}
    result = [make("raw", source, [], [])]
    if token_contract == "opaque":
        result[0]["notes"].append("identity only: source/token/location non-observation has not been declared")
        return result
    if b"\\\n" in source or b"\\\r\n" in source or b"??" in source or b"\0" in source:
        result[0]["notes"].append("identity only: line splicing, trigraph-like input or NUL is outside the byte-range frontend contract")
        return result
    try:
        tokens = _lex(source.decode("latin-1"), "c")
    except nvnotation.NotationError as exc:
        raise FlowError(f"unsupported source tokenization: {exc}") from exc
    if any(t.kind == "punct" and t.text not in C_PUNCT or
           t.kind not in ("quoted", "comment", "space", "directive") and any(ord(c) >= 128 for c in t.text)
           for t in tokens):
        # The shared byte lexer deliberately leaves unknown tokens opaque. C
        # universal character names, UTF-8 identifier bytes and implementation-
        # specific identifier characters (e.g. '$') cannot therefore participate
        # in safe splices. Quoted text, comments and directives stay untouched.
        result[0]["notes"].append("identity only: unsupported preprocessing token/identifier spelling; ASCII identifier splice boundaries are required")
        return result
    frontend = Frontend(clang, standard, args, source_path, frontend_seconds, frontend_memory_bytes, ast_bytes)
    try:
        contract["frontend"] = frontend.info
        original = frontend.parse(source)
        recipes = [("c-all", set(RULES)), *(("c-" + rule, {rule}) for rule in RULES)]
        for identifier, enabled in recipes[:max_variants - 1]:
            data, analysis, audits = source, original, []
            notes = list(original.notes)
            for pass_index in range(max_passes):
                changed, records = apply_pass(analysis, enabled)
                if not records:
                    break
                checked = frontend.parse(changed)
                affected = {r["function"] for r in records}
                eligible = {decl.get("name") for decl, _ in checked.functions}
                if affected - eligible:
                    # A generated keyword might itself be a macro supplied by a
                    # header/flag. The changed regions must still be macro-free.
                    notes.append("pass inapplicable after frontend protection: newly context-sensitive or macro-expanded function")
                    break
                for record in records:
                    record["pass"] = pass_index + 1
                audits.extend(records)
                data, analysis = changed, checked
            if not audits:
                notes.append("no applicable shorter rewrite for this recipe")
            result.append(make(identifier, data, audits, notes))
        return result
    finally:
        frontend.close()


def write_portfolio(directory, variants):
    directory.mkdir(parents=True, exist_ok=False)
    for item in variants:
        (directory / (item["id"] + ".c")).write_bytes(item["data"])
    metadata = [{k: v for k, v in item.items() if k != "data"} for item in variants]
    (directory / "audit.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_run_manifest(directory, variants, *, verifier, target, contract, codecs, max_bytes=None):
    """Standalone C only: retain every candidate and snapshot a Python oracle.

    A verifier accepts the candidate's absolute path as its only argument and
    exits zero on success. It must be self-contained. Project headers/auxiliary
    objects require adapting an explicit normal NVCompact manifest instead.
    """
    if not target or not contract.strip():
        raise FlowError("run manifest requires a target and an application contract")
    frontend = variants[0]["contract"].get("frontend")
    if not frontend:
        raise FlowError("run manifest requires the explicit Clang frontend contract")
    # Build snapshots must not silently depend on original mutable directories.
    args = frontend["compiler_args"]
    if any(v in ("-I", "-iquote", "-isystem", "-isysroot", "--sysroot") or v.startswith(("-I", "--sysroot=")) for v in args):
        raise FlowError("standalone run manifests cannot capture external include/sysroot paths; use an explicit project manifest")
    for variant in variants:
        for token in _lex(variant["data"].decode("latin-1"), "c"):
            directive = re.match(r"\s*(?:#|%:)\s*([A-Za-z_]\w*)\b(.*)", token.text, re.S) if token.kind == "directive" else None
            if directive and (directive[1] in ("include_next", "import") or
                              directive[1] == "include" and not directive[2].lstrip().startswith("<")):
                raise FlowError("standalone run manifests support system <...> includes only; snapshot local headers in a project manifest")
    if not codecs or not all(isinstance(x, str) and x for x in codecs):
        raise FlowError("run manifest requires explicit nonempty codec IDs")
    oracle = Path(verifier).read_bytes()
    with (directory / "verify.py").open("xb") as stream:
        stream.write(oracle)
    std = "-std=" + frontend["standard"]
    compile_command = ["{cc}", std, *args, "-Os", "-frandom-seed=nvcompact-cflow", "-ffile-prefix-map={root}=.",
        "-fdebug-prefix-map={root}=.", "-c", "{source}", "-o", "{object}"]
    unit_variants = [{"id": v["id"], "language": "c", "sources": [v["id"] + ".c"],
                      "commands": [compile_command]} for v in variants]
    manifest = {"format": 1, "project_root": ".", "target": target,
        "contract": contract + "; same Clang frontend/standard/ABI arguments as rewrite generation; source/token/location non-observation; no self-file/path observation for packing",
        "inputs": [v["id"] + ".c" for v in variants] + ["audit.json", "verify.py"],
        "tools": {"cc": {"executable": frontend["executable"], "requires_tools": ["ld"]},
                  "ld": {"executable": "ld"}, "python": {"executable": "python3"}},
        "components": [{"id": "program", "contract": contract, "variants": unit_variants}],
        "build_profiles": [{"id": "size", "variables": {}}],
        "link_profiles": [{"id": "hosted", "allow_section_header_removal": False,
            "argv": ["{cc}", *args, "{objects}", "-Wl,--build-id=none,-s", "-o", "{binary}"]}],
        "baseline": {"build": "size", "link": "hosted", "order": ["program"], "variants": {"program": "raw"}},
        "verify": ["{python}", "{root}/verify.py", "{binary}"], "codecs": codecs,
        "max_native_bytes": 16 << 20}
    if max_bytes is not None:
        manifest["max_bytes"] = max_bytes
    with (directory / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return directory / "manifest.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--standard", choices=STANDARDS, default="c11")
    parser.add_argument("--compiler-arg", action="append", default=[])
    parser.add_argument("--token-contract", choices=("opaque", "no-token-observation", "preprocessed"), default="opaque")
    parser.add_argument("--max-variants", type=int, default=16)
    parser.add_argument("--max-passes", type=int, default=2)
    parser.add_argument("--frontend-seconds", type=float, default=30)
    parser.add_argument("--frontend-memory-mib", type=int, default=1024)
    parser.add_argument("--ast-mib", type=int, default=32)
    parser.add_argument("--variant", help="explicit candidate ID; defaults to c-all when available, otherwise raw")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--audit", type=Path)
    parser.add_argument("--portfolio", type=Path)
    parser.add_argument("--list-variants", action="store_true")
    parser.add_argument("--run-manifest", action="store_true", help="write a standalone C run manifest inside --portfolio; generation does not execute it")
    parser.add_argument("--verifier", type=Path, help="self-contained Python checker accepting one candidate binary path")
    parser.add_argument("--run-target", help="explicit target triple for native packing")
    parser.add_argument("--run-contract", help="application domain/observable contract and packing non-observation assertion")
    parser.add_argument("--codec", action="append", help="manifest codec ID; defaults to gzip-9 and xz-6")
    parser.add_argument("--max-bytes", type=int)
    args = parser.parse_args(argv)
    try:
        if not (args.output or args.portfolio or args.list_variants):
            raise FlowError("choose --output, --portfolio or --list-variants")
        if args.run_manifest and not all((args.portfolio, args.verifier, args.run_target, args.run_contract)):
            raise FlowError("--run-manifest requires --portfolio, --verifier, --run-target and --run-contract")
        if args.max_bytes is not None and args.max_bytes <= 0:
            raise FlowError("--max-bytes must be positive")
        variants = generate_variants(args.input.read_bytes(), token_contract=args.token_contract, clang=args.clang,
            standard=args.standard, compiler_args=args.compiler_arg, source_path=args.input,
            max_variants=args.max_variants, max_passes=args.max_passes, frontend_seconds=args.frontend_seconds,
            frontend_memory_bytes=args.frontend_memory_mib << 20, ast_bytes=args.ast_mib << 20)
        if args.list_variants:
            print(json.dumps([{k: v for k, v in item.items() if k != "data"} for item in variants], ensure_ascii=False, indent=2))
        if args.portfolio:
            write_portfolio(args.portfolio, variants)
            if args.run_manifest:
                path = write_run_manifest(args.portfolio, variants, verifier=args.verifier, target=args.run_target,
                    contract=args.run_contract, codecs=args.codec or ["gzip-9", "xz-6"], max_bytes=args.max_bytes)
                print(f"Run manifest: {path}; generation only, no target execution")
        if args.output:
            wanted = args.variant or ("c-all" if any(v["id"] == "c-all" for v in variants) else "raw")
            selected = next((v for v in variants if v["id"] == wanted), None)
            if selected is None:
                raise FlowError(f"variant {wanted!r} unavailable; available: {[v['id'] for v in variants]}")
            if args.output.resolve() == args.input.resolve():
                raise FlowError("output must not overwrite source")
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("xb") as stream:
                stream.write(selected["data"])
            if args.audit:
                with args.audit.open("x", encoding="utf-8") as stream:
                    json.dump({k: v for k, v in selected.items() if k != "data"}, stream, ensure_ascii=False, indent=2)
                    stream.write("\n")
    except (FlowError, OSError, ValueError) as exc:
        print(f"nvcflow: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if globals().get("_NVCOMPACT_MANAGED"):
        raise SystemExit(main())
    import nvlaunch
    raise SystemExit(nvlaunch.main(["rewrite-c", *sys.argv[1:]]))
