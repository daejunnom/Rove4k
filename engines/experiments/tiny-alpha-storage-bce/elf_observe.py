"""Read-only full ELF64 byte inventory; no normalization or acceptance rule."""
import hashlib
import struct


def sha(data):return hashlib.sha256(data).hexdigest()


def describe(data):
    if len(data)<64 or data[:7]!=b'\x7fELF\x02\x01\x01':raise ValueError('expected ELF64 little-endian version1')
    values=struct.unpack_from('<HHIQQQIHHHHHH',data,16)
    keys=['type','machine','version','entry','phoff','shoff','flags','ehsize','phentsize','phnum','shentsize','shnum','shstrndx']
    header=dict(zip(keys,values))
    if header['ehsize']!=64 or header['shentsize']!=64 or header['shnum']==0 or header['shstrndx']>=header['shnum']:
        raise ValueError('outside frozen nonextended ELF64 table domain')
    def take(offset,size):
        if offset<0 or size<0 or offset+size>len(data):raise ValueError('ELF range outside file')
        return data[offset:offset+size]
    sections=[]
    for index in range(header['shnum']):
        offset=header['shoff']+index*header['shentsize'];raw=take(offset,64)
        fields=struct.unpack('<IIQQQQIIQQ',raw)
        section=dict(zip(['name_offset','type','flags','address','offset','size','link','info','alignment','entry_size'],fields))
        section.update(index=index,header_hex=raw.hex());sections.append(section)
    strings=sections[header['shstrndx']];strings=take(strings['offset'],strings['size'])
    for section in sections:
        end=strings.find(b'\0',section['name_offset'])
        if end<0:raise ValueError('unterminated section name')
        section['name']=strings[section['name_offset']:end].decode('ascii')
        payload=b'' if section['type']==8 else take(section['offset'],section['size'])
        section.update(file_bytes=len(payload),sha256=sha(payload),allocated=bool(section['flags']&2),NOBITS=section['type']==8)
        if section['name']=='.note.gnu.build-id':section['note_bytes_hex']=payload.hex()
    if len({s['name'] for s in sections})!=len(sections):raise ValueError('ambiguous duplicate section names')
    ph=take(header['phoff'],header['phentsize']*header['phnum'])
    return {'bytes':len(data),'sha256':sha(data),'ELF_header':header,'ELF_header_hex':data[:64].hex(),
        'ELF_header_sha256':sha(data[:64]),'program_header_bytes':len(ph),'program_header_sha256':sha(ph),'sections':sections}


def compare(control,candidate):
    old=describe(control);new=describe(candidate);a={s['name']:s for s in old['sections']};b={s['name']:s for s in new['sections']}
    changes=[]
    for name in sorted(set(a)|set(b)):
        left=a.get(name);right=b.get(name)
        if left!=right:
            changes.append({'name':name,'content_equal':left is not None and right is not None and left['sha256']==right['sha256'] and left['file_bytes']==right['file_bytes'],
                'section_header_equal':left is not None and right is not None and left['header_hex']==right['header_hex'],
                'control':left,'candidate':right})
    equal_contents=[name for name in sorted(set(a)&set(b)) if a[name]['sha256']==b[name]['sha256'] and a[name]['file_bytes']==b[name]['file_bytes']]
    difference=next((i for i,(x,y) in enumerate(zip(control,candidate)) if x!=y),min(len(control),len(candidate)))
    categories={}
    for label,names in [('text',['.text']),('rodata',['.rodata']),('data',['.data','.bss']),('dynamic_symbols',['.dynsym','.dynstr']),
                        ('relocations',sorted(n for n in set(a)|set(b) if n.startswith(('.rela','.rel.')))),
                        ('build_id',['.note.gnu.build-id']),('nonallocated_symbols',['.symtab','.strtab']),('section_names',['.shstrtab'])]:
        categories[label]={name:{'present_control':name in a,'present_candidate':name in b,'content_equal':name in equal_contents,
            'control_sha256':a.get(name,{}).get('sha256'),'candidate_sha256':b.get(name,{}).get('sha256')} for name in names}
    return {'scope':'read-only section/ELF metadata observation; NOT semantic or ABI qualification; fullnative failure unchanged',
        'full_native_equal':control==candidate,'first_difference':difference,'control':old,'candidate':new,
        'ELF_header_equal':old['ELF_header_hex']==new['ELF_header_hex'],'program_headers_equal':old['program_header_sha256']==new['program_header_sha256'],
        'categories':categories,'section_changes':changes,'equal_content_sections':equal_contents,'strip_or_byte_normalization':False}
