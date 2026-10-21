"""Pure fixed full-F template preparation, shared by fixed worker profiles.

The caller admits the legacy template and owns source insertion and encoding.
This helper accepts immutable template bytes only; it reads no files or
environment and has no compiler, profile, artifact, report or network input.
The exact 988-byte legacy input becomes the existing 955-byte full template.
"""
import hashlib


_INPUT_SHA256 = '159c5fe166f4b0804471e9d3a70d8f055a510858a6ae33f0ed6b4cfd17fca6f9'
_EDITS = (
    (b' e=dict(os.environ,TMPDIR=d)\n', b''),
    (b'cwd=d,env=e,stdin=subprocess.PIPE',
     b'cwd=d,env=dict(os.environ,TMPDIR=d),stdin=subprocess.PIPE'),
    (b'signal.signal(2,stop);signal.signal(15,stop)\n',
     b'for s in 2,15:signal.signal(s,stop)\n'),
    (b'signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n',
     b'for s in 2,15:signal.signal(s,signal.SIG_DFL)\n'),
)


def prepare_template(template: bytes) -> bytes:
    """Return the exact existing full template from its fixed legacy bytes."""
    if not isinstance(template, bytes):
        raise TypeError('immutable template bytes required')
    if hashlib.sha256(template).hexdigest() != _INPUT_SHA256:
        raise ValueError('fixed full-F legacy template changed')
    for old, new in _EDITS:
        template = template.replace(old, new, 1)
    return template
