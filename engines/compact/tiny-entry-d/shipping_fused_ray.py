"""Scalar shipping ray fusion. HQ and every DEV retain the old walker.

Generation order is direction/ray order for scalar shipping sliders. This is
an explicit ordering policy change, not equal search trajectory or strength.
The canonical native/board.c remains the readable old source. No I/O occurs.
"""
import hashlib

INPUT = (9011, '559e4589325152a493e565730581521d1c16ab5dea20cc8dc51ccc2505c30437')
OUTPUT = (10371, '53458b95da840708cf39c2b144f0d75bddcbd1c541d64b66cdbffba8d298a86a')
OFFSET = 4542
OLD = b'static int walk(const Board *p,Move *moves,int sq,int s){\n    int n=0;\n    uint64_t occupied=d_occupancy(p->b);\n    for(int from=0;from<128;from++){\n        if(from&0x88){from+=7;continue;}\n        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;\n        if(a>=3&&a<=5){\n            uint64_t destinations=d_sliding(occupied,(unsigned)from,(unsigned)a);\n            while(destinations){\n                int bit=__builtin_ctzll(destinations),to=(bit&7)+(bit>>3)*16;\n                destinations&=destinations-1;\n                if(!moves&&to==sq)return 1;\n                if(moves&&p->b[to]*s<=0)add(moves,&n,from,to,!!p->b[to]);\n            }\n            continue;\n        }\n        if(moves&&a==1){\n            int to=from+s*16;\n            if(!(to&0x88)&&!p->b[to]){\n                add(moves,&n,from,to,2);\n                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);\n            }\n        }\n        int first=a==1?(s>0?12:14):a==2?0:8;\n        int last=a==1?first+2:a==2?8:16;\n        for(int i=first;i<last;i++){\n            int to=from+steps[i];if(to&0x88)continue;\n            int target=p->b[to];\n            if(!moves&&to==sq)return 1;\n            if(target*s>0||(moves&&a==1&&!target&&to!=p->e))continue;\n            if(moves)add(moves,&n,from,to,a==1?3:!!target);\n        }\n        if(moves&&a==6){\n            int home=s>0?4:116,shift=s>0?0:2;\n            if(from==home&&!attacked(p,home,-s)){\n                for(int d=1;d>=-1;d-=2)\n                    if((p->c&((d>0?1:2)<<shift))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);\n                }\n        }\n    }\n    return n;\n}'
SCALAR = b'static int walk(const Board *p,Move *moves,int sq,int s){\n    int n=0;\n    for(int from=0;from<128;from++){\n        if(from&0x88){from+=7;continue;}\n        int a=abs(p->b[from]);if(p->b[from]*s<=0)continue;\n        if(moves&&a==1){\n            int to=from+s*16;\n            if(!(to&0x88)&&!p->b[to]){\n                add(moves,&n,from,to,2);\n                if((from>>4)==(s>0?1:6)&&!p->b[to+s*16])add(moves,&n,from,to+s*16,0);\n            }\n        }\n        int first=a==1?(s>0?12:14):a==2?0:a==3?12:8;\n        int last=a==1?first+2:a==2?8:a==4?12:16;\n        for(int i=first;i<last;i++){\n            int step=steps[i];\n            for(int to=from+step;!(to&0x88);to+=step){\n                int target=p->b[to];\n                if(!moves&&to==sq)return 1;\n                if(target*s>0||(moves&&a==1&&!target&&to!=p->e))break;\n                if(moves)add(moves,&n,from,to,a==1?3:!!target);\n                if(target||a<3||a==6)break;\n            }\n        }\n        if(moves&&a==6){\n            int home=s>0?4:116,shift=s>0?0:2;\n            if(from==home&&!attacked(p,home,-s)){\n                for(int d=1;d>=-1;d-=2)\n                    if((p->c&((d>0?1:2)<<shift))&&!p->b[home+d]&&!p->b[home+2*d]&&(d>0||!p->b[home-3])&&!attacked(p,home+d,-s))add(moves,&n,from,home+2*d,0);\n                }\n        }\n    }\n    return n;\n}'
GAPS = ('cff8681f9861c3b5343139b7f00231bf0caf9ab8ba43bdf8f060cda2f8fdec1b', '54cec10bbe5660faa5b430d49a7ff24ae33f6bcd65c80a93f606f1ff93b28525')

def transform_source(source):
    if not isinstance(source, bytes) or b'\r' in source:
        raise ValueError('expected normalized LF Board source bytes')
    digest = lambda data: hashlib.sha256(data).hexdigest()
    if (len(source), digest(source)) != INPUT:
        raise ValueError('unknown canonical Board source')
    end = OFFSET + len(OLD)
    if source[OFFSET:end] != OLD or source.count(OLD) != 1:
        raise ValueError('walker literal differs')
    prefix, suffix = source[:OFFSET], source[end:]
    if (digest(prefix), digest(suffix)) != GAPS:
        raise ValueError('protected Board complement differs')
    replacement = b'#if D_HQ || DEV\n' + OLD + b'\n#else\n' + SCALAR + b'\n#endif'
    data = prefix + replacement + suffix
    if (len(data), digest(data)) != OUTPUT:
        raise ValueError('generated Board source differs')
    if data[:OFFSET] + OLD + data[OFFSET+len(replacement):] != source:
        raise ValueError('walker inverse differs')
    return data, {'id': 'scalar-shipping-fused-rays-v1',
                  'input_sha256': INPUT[1], 'output_sha256': OUTPUT[1],
                  'offset': OFFSET, 'old_bytes': len(OLD), 'new_bytes': len(replacement),
                  'protected_gaps_sha256': list(GAPS), 'inverse_exact': True,
                  'selection': 'D_HQ==0 && DEV==0 only; old walker otherwise',
                  'ordering': 'scalar sliders direction-major near-to-far; legal Move set retained',
                  'Board_ABI_changed': False}
