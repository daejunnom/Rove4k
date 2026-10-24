"""Fixed-recipe source packages; no search or bootstrap rewriting.

The caller owns the exact bootstrap, prefix and compression decisions. The
three-line header reads its stream from stdin, so xz writes decoded Python to
stdout. Its failure exit, Python argv and exec behavior match the byte-offset
launcher; source/native/lifetime qualification remains the caller's concern.
"""
import lzma


XZ_STDIN_HEADER = (b'#!/bin/sh\np=$(tail -n+4 "$0"|xz -d)||exit\n'
                   b'exec python3 -c "$p" "$0" "$@"\n')


def package(bootstrap, compression, *, prefix):
    """Encode one LZMA1 ALONE stream with the caller's complete prefix."""
    if not isinstance(bootstrap, bytes) or not isinstance(prefix, bytes):
        raise TypeError('immutable bootstrap and prefix bytes required')
    if (compression['format'], compression['filter'], compression['check']) != ('lzma-alone', 'LZMA1', 'NONE'):
        raise ValueError('source package requires the explicit LZMA1 ALONE recipe')
    preset = compression['preset'] | (lzma.PRESET_EXTREME if compression['extreme'] else 0)
    match_finder = {'BT4': lzma.MF_BT4, 'BT2': lzma.MF_BT2, 'HC4': lzma.MF_HC4}[compression['mf']]
    filters = [{'id': lzma.FILTER_LZMA1, 'preset': preset,
                'lc': compression['lc'], 'lp': compression['lp'], 'pb': compression['pb'],
                'mf': match_finder, 'dict_size': compression['dictionary_bytes'],
                'nice_len': compression['nice_len']}]
    return prefix + lzma.compress(bootstrap, format=lzma.FORMAT_ALONE,
                                  check=lzma.CHECK_NONE, filters=filters)
