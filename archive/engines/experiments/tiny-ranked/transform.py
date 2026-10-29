"""Pack a search-private priority into widened raw moves, using defined C.

The experiment admits one frozen readable Tiny A input. Public Move objects
remain raw; only search's local list temporarily contains high priority bits.
The parser, generator, board, TT and workers have no packed-priority consumer.
"""
import hashlib

BASELINE_SHA256='109fa749bc2a137fc1384a9afa429d3734249df908f057a58c1fe105f0c43504'


def once(text,old,new):
    if text.count(old)!=1:raise ValueError('frozen ranked source changed: '+old[:90])
    return text.replace(old,new)


def transform(source,shift=17):
    if shift not in (17,32):raise ValueError('only two declared priority layouts')
    if hashlib.sha256(source).hexdigest()!=BASELINE_SHA256:raise ValueError('unknown frozen readable Tiny A')
    text=source.decode()
    text=once(text,'typedef unsigned Move;','typedef uint64_t Move;')
    text=once(text,'    int scores[MOVES],count=gen(p,moves),legal=0,old=alpha,best=-MATE;',
                    '    int count=gen(p,moves),legal=0,old=alpha,best=-MATE;')
    text=once(text,'        scores[i]=m==tt?1000000:',
                    '        int priority=m==tt?1000000:')
    text=once(text,'        if(PROMO(m))scores[i]+=400000+PROMO(m)*1000;',
                    '        if(PROMO(m))priority+=400000+PROMO(m)*1000;\n'
                    f'        moves[i]=m|((Move)(priority+65536)<<{shift});')
    text=once(text,'        int j=i;for(int k=i+1;k<count;k++)if(scores[k]>scores[j])j=k;\n'
                    '        Move m=moves[j];moves[j]=moves[i];scores[j]=scores[i];',
                    f'        int j=i;for(int k=i+1;k<count;k++)if((moves[k]>>{shift})>(moves[j]>>{shift}))j=k;\n'
                    '        Move m='+('moves[j]&131071' if shift==17 else '(unsigned)moves[j]')+';moves[j]=moves[i];')
    # PROMO's macro result is now uint64_t. Cast only its priority contribution
    # to retain the original signed-int score domain before bias/packing.
    text=once(text,'priority+=400000+PROMO(m)*1000;',
                    'priority+=400000+(int)PROMO(m)*1000;')
    return text.encode(),{
        'representation':'Move uint64_t globally, high priority bits only in search-local list',
        'raw_move_bits':17,'priority_shift':shift,'priority_bias':65536,'priority_range':[-65536,1405000],
        'priority_comparison':'strict > on shifted priority only; equal priority retains scan order',
        'restoration':('mask17' if shift==17 else 'unsigned32 cast; unused low bits17..31 are zero')+' before make/capture/TT/previous/root/Worker data',
        'scope':'one frozen Tiny A readable input; no search/order/selectivity policy change intended',
    }
