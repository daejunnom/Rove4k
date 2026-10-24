"""Narrow the owned fixed-Loose shipping Worker's bounded search state.

The caller admits shipping mode 0 only and has already installed search.c.in and
the complete-root callback/controller. This is a guarded source recipe for those
    owned declarations, not a general C layout or integer-range optimizer.
"""

import re


def _once(text, old, new, description):
    if text.count(old) != 1:
        raise ValueError(f'compact worker requires exactly one {description}')
    return text.replace(old, new, 1)


def compact_worker_state(files):
    """Return copied sources and observations for the fixed shipping domain.

    Legal mailbox coordinates map bijectively to 0..63. History/continuation
    start at zero and update with h+b-h*b/16384. For h,b in 0..16384 this stays
    in 0..16384. Shipping's root depth is MAXPLY-2 and recursive depth never
    increases, so MAXPLY<=130 bounds b=depth*depth by 16384. The helper takes
    int values: its largest product is 268435456, before any uint16_t store.

    Correction starts at zero and updates with c+e-c/64, |e|<=256; the interval
    -16384..16384 is invariant under C's division toward zero. int16_t therefore
    preserves it exactly. None of these arrays is shared between live workers.
    Full PV diagnostics remain conditional C source; shipping only publishes
    each ply's first move, and the unused callback reply read is removed here.
    """
    result = dict(files)
    try:
        header = result['c/rove.h'].decode()
        search = result['c/search.c'].decode()
    except KeyError as error:
        raise ValueError('compact worker requires c/rove.h and c/search.c') from error
    if '\r' in header or '\r' in search:
        raise ValueError('compact worker requires caller-normalized LF C sources')

    limits = re.findall(r'(?m)^#define MAXPLY ([0-9]+)[ \t]*$', header)
    if len(limits) != 1 or not 2 <= int(limits[0]) <= 130:
        raise ValueError('compact worker requires one literal MAXPLY in 2..130')
    maximum = int(limits[0])
    bonus = re.search(r'\bcompact_bonus\s*\(\s*int\s+value\s*,\s*int\s+bonus\s*\)'
                      r'\s*\{\s*return\s+value\s*\+\s*bonus\s*-\s*value\s*\*\s*bonus'
                      r'\s*/\s*16384\s*;\s*\}', search)
    if not bonus or not re.search(r'\bcompact_pv\s*\(', search):
        raise ValueError('compact worker requires compact_bonus and compact_pv helpers')
    if '#if ROVE_DEV || ROVE_PARALLEL != 0' not in search or 'w->pvlen[ply]=1;' not in search:
        raise ValueError('compact worker requires shipping first-move PV specialization')
    if re.search(r'\bint\s*\*\s*[A-Za-z_]\w*\s*=\s*&\s*w\s*->\s*'
                 r'(?:history|continuation|correction)\b', search):
        raise ValueError('compact worker cannot retain wide pointers to narrowed learning state')
    for name, data in result.items():
        if name != 'c/search.c' and name.endswith(('.c', '.h')):
            if re.search(r'\bw\s*->\s*history\s*\[', data.decode()):
                raise ValueError(f'compact worker encountered history access outside owned search: {name}')
    if re.search(r'\bROVE_SQUARE\b', header):
        raise ValueError('compact worker square macro already exists')

    header = _once(header,
                   'int history[2][128][128], continuation[13][13];',
                   'uint16_t history[2][64][64], continuation[13][13];',
                   'canonical history/continuation declaration')
    header = _once(header, 'int correction[2][1024];',
                   'int16_t correction[2][1024];', 'canonical correction declaration')
    header = _once(header, 'pv[MAXPLY][MAXPLY]', 'pv[MAXPLY][1]',
                   'canonical triangular PV backing declaration')
    header = header.replace(f'#define MAXPLY {maximum}',
                            f'#define MAXPLY {maximum}\n'
                            '#define ROVE_SQUARE(q) ((((q)>>1)&56)|((q)&7))', 1)

    # The three known accesses are the move-score read and the update's LHS/RHS.
    # Reject any new receiver/index form instead of leaving a 128-square access
    # against a 64-square array. Both canonical local move names are admitted.
    access = re.compile(r'w->history\[p->side<0\]\[FROM\((m|move)\)\]\[TO\(\1\)\]')
    history_count = len(re.findall(r'\bw\s*->\s*history\s*\[', search))
    if history_count != 3:
        raise ValueError(f'compact worker requires three owned history accesses, got {history_count}')
    search, mapped = access.subn(lambda match:
        f'w->history[p->side<0][ROVE_SQUARE(FROM({match[1]}))]'
        f'[ROVE_SQUARE(TO({match[1]}))]', search)
    if mapped != history_count:
        raise ValueError(f'compact worker mapped {mapped} of {history_count} history accesses')
    unmapped = re.sub(r'w->history\[p->side<0\]\[ROVE_SQUARE\(FROM\((m|move)\)\)\]'
                      r'\[ROVE_SQUARE\(TO\(\1\)\)\]', '', search)
    if re.search(r'\bw\s*->\s*history\s*\[', unmapped):
        raise ValueError('compact worker retained an unmapped history access')
    search = _once(search, 'if(w->pvlen[0]>1)r.reply=w->pv[0][1];', '',
                   'unused fixed-Loose callback PV reply read')

    result['c/rove.h'] = header.encode()
    result['c/search.c'] = search.encode()
    return result, [{
        'applied': True,
        'operation': 'fixed-loose-bounded-worker-state',
        'contract': 'shipping mode 0 only; same learning values and mapped legal-square history; first-move PV only',
        'maxply': maximum,
        'maximum_history_bonus': (maximum-2)**2,
        'history_range': [0, 16384],
        'correction_range': [-16384, 16384],
        'history_accesses_mapped': mapped,
        'history_bytes_before': 2*128*128*4,
        'history_bytes_after': 2*64*64*2,
        'continuation_bytes_before': 13*13*4,
        'continuation_bytes_after': 13*13*2,
        'correction_bytes_before': 2*1024*4,
        'correction_bytes_after': 2*1024*2,
        'pv_bytes_before': maximum*maximum*4,
        'pv_bytes_after': maximum*4,
    }]
