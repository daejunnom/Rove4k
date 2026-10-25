"""Exact owned fixed A/F package routine; managed subprocess I/O is injected."""
import ast
import lzma
from pathlib import Path

def read(path):
    data=Path(path).read_bytes().replace(b'\r\n',b'\n')
    if b'\r'in data:raise ValueError('lone CR')
    return data

def package(source,selected,recipe,literal):
    template=read(Path(selected)/'bootstrap.py.in');prefix=read(Path(selected)/'launcher.sh');compression=recipe['compression']
    marker=b'__ROVE_SOURCE_LITERAL__'
    if template.count(marker)!=1:raise ValueError('source literal marker changed')
    expression,kind=literal(source);script=template.replace(marker,expression.encode());ast.parse(script)
    if compression['format']=='lzma-alone':
        expected={'format':'lzma-alone','filter':'LZMA1','preset':9,'extreme':True,'lc':2,'lp':0,'pb':0,'check':'NONE',
                  'dictionary_bytes':67108864,'header_hex':'0200000004ffffffffffffffff'}
        if compression!=expected or len(prefix)!=77:raise ValueError('fixed A codec/prefix changed')
        payload=lzma.compress(script,format=lzma.FORMAT_ALONE,check=lzma.CHECK_NONE,
            filters=[{'id':lzma.FILTER_LZMA1,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])
        if payload[:13]!=bytes.fromhex(expected['header_hex']):raise ValueError('ALONE header changed')
        format=lzma.FORMAT_ALONE;command=['lzma','-dc']
    else:
        if compression!={'format':'xz','filter':'LZMA2','preset':9,'extreme':True,'lc':2,'lp':0,'pb':0,'check':'CRC64'} or len(prefix)!=75:
            raise ValueError('fixed F codec/prefix changed')
        payload=lzma.compress(script,format=lzma.FORMAT_XZ,check=lzma.CHECK_CRC64,
            filters=[{'id':lzma.FILTER_LZMA2,'preset':9|lzma.PRESET_EXTREME,'lc':2,'lp':0,'pb':0}])
        format=lzma.FORMAT_XZ;command=['xz','-dc']
    decoder=lzma.LZMADecompressor(format=format)
    if decoder.decompress(payload)!=script or not decoder.eof or decoder.unused_data:raise ValueError('strict payload decode differs')
    cli=subprocess.run(command,input=payload,capture_output=True,timeout=15)
    if cli.returncode or cli.stderr or cli.stdout!=script:raise ValueError('independent CLI decode differs')
    return prefix+payload,script,kind
