"""Full-only result-stream grouping change after the fixed clock stage.

The shipping callback has one complete bestmove printf and a following fflush.
Its worker aggregation, callback and completion broadcast remain under qj.
Removing the explicit stream-lock pair intentionally permits main uciok/readyok
operations during aggregation or between that printf and fflush. Per-operation
stdio locking is the reviewed fixed glibc/POSIX premise; exact timing/order or
multi-call stream-group equivalence is not claimed. Canonical DEV's multi-call
info output and both alternate policies are excluded by the caller.

This pure fixed source stage reads no files, process state, recipe or receipt.
"""
import hashlib

INPUT=(8859,'e868953700cc0a319b8293cde473d9c0fd44a29e5105f25e1cc114e601740f59')
OUTPUT=(8821,'00c48b5c6d74a45d68fe8280d45648e4405763c6c5742d8e11ed9736c71beb9c')
EDITS=((6563,6563,b'flockfile(stdout);'),
       (6707,6689,b'funlockfile(stdout);'))
COMPLEMENT=(8821,'00c48b5c6d74a45d68fe8280d45648e4405763c6c5742d8e11ed9736c71beb9c')


def _pin(data):
    return len(data),hashlib.sha256(data).hexdigest()


def transform_source(source):
    """Delete exactly the two owned calls and retain every other source byte."""
    if type(source) is not bytes or _pin(source)!=INPUT:
        raise ValueError('full-F result stream input differs')
    if source.count(b'printf("bestmove %s\\n",d);')!=1 or source.count(b'fflush(stdout);')!=3:
        raise ValueError('full-F result stream consumers differ')
    pieces=[];gaps=[];cursor=written=0
    for start,target,old in EDITS:
        gap=source[cursor:start]
        if (start<cursor or source[start:start+len(old)]!=old
                or source.count(old)!=1 or written+len(gap)!=target):
            raise ValueError('full-F result stream deletion span differs')
        pieces.append(gap);gaps.append(gap)
        cursor=start+len(old);written=target
    pieces.append(source[cursor:]);gaps.append(source[cursor:])
    candidate=b''.join(pieces)
    inverse=candidate;new_gaps=[];cursor=0
    for start,target,old in EDITS:
        new_gaps.append(candidate[cursor:target]);cursor=target
    new_gaps.append(candidate[cursor:])
    for start,target,old in reversed(EDITS):
        inverse=inverse[:target]+old+inverse[target:]
    if (_pin(candidate)!=OUTPUT or inverse!=source or gaps!=new_gaps
            or _pin(b''.join(gaps))!=COMPLEMENT):
        raise ValueError('full-F result stream output/inverse/complement differs')
    return candidate,{
        'family':'F','policy':'full','stage':'single-result-stdio-operation-locks',
        'input_bytes':INPUT[0],'input_sha256':INPUT[1],
        'output_bytes':OUTPUT[0],'output_sha256':OUTPUT[1],
        'raw_delta':-38,'deleted_calls':2,'exact_inverse':True,'each_gap_exact':True,
        'complement_bytes':COMPLEMENT[0],'complement_sha256':COMPLEMENT[1],
        'single_complete_bestmove_printf_retained':True,
        'qj_owned_fflush_before_completion_broadcast_retained':True,
        'intentional_multi_call_stream_group_change':True,
        'main_ack_interleaving':'permitted during aggregation and between result printf/fflush',
        'stdio_premise':'reviewed fixed glibc/POSIX per-operation stream locking',
        'exact_timing_order_group_equivalence_claimed':False,
        'DEV_and_alternate_policies':'caller bypass; no applicability claim',
        'external_reads':0,'compiler_codec_engine_executed_by_transform':0,
    }
