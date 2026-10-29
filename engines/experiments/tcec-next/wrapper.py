"""Equivalent GCC C option spelling for the entry-owned-unlink wrapper.

Only -x c -> -xc and -o "$f" -> -o"$f" are joined. GCC accepts the same
language/output option arguments in joined form. Native compilation, actual
JIT identity and pipeline failure checks remain required, not inferred here.
"""


def header(packaging, unlink, compiler):
    command=list(compiler)
    if command.count('-x')!=1 or command[command.index('-x')+1]!='c':
        raise ValueError('one explicit C input-language option required')
    if command.count('-o')!=1 or command[command.index('-o')+1]!='x':
        raise ValueError('one private output x required')
    data=unlink.tcec_header(packaging,compiler=command)
    if data.count(b' -x c ')!=1 or data.count(b' -o "$f"')!=1:
        raise ValueError('known C wrapper option spelling required')
    result=data.replace(b' -x c ',b' -xc ').replace(b' -o "$f"',b' -o"$f"')
    if len(result)!=len(data)-2 or len(result.splitlines())!=5:
        raise ValueError('joined options changed the source stream boundary')
    return result


def package(packaging, unlink, source, compression, compiler):
    return packaging.package(source,compression,prefix=header(packaging,unlink,compiler))


def contract(packaging, unlink, compiler):
    result=unlink.contract(packaging,compiler=compiler)
    result.update(compiler_option_spelling='GCC joined -xc and -oPATH; language/output values unchanged')
    return result
