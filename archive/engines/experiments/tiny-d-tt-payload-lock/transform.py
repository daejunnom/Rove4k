#!/usr/bin/env python3
"""Exactly three native source fragments; one fixed payload-marker candidate."""
import hashlib

NAMES = ('tiny.h', 'board.c', 'search.c', 'runtime.c', 'hq.h', 'hq.c', 'start.S', 'image.ld')
CONTROL_SHA = {'tiny.h': 'e19749eb3315253e04171b89b8188df7e0db6b39ec4eb495187a6e158836823f', 'board.c': '3f04fedb7e449e69b47ac6f2b36eb89ebe193726ac5970b0ae3a4b28008e12dc', 'search.c': '48e0f21fee8091f1e5c5d08d606740f6ff8c56778a550af2bcfc282d655d974c', 'runtime.c': '5b20d4e60d60b5edfb4b7b5a15217346098f0bd9ccdd155a7369c90743e81ed1', 'hq.h': 'ad66a03cef5288010c4377b81ee3661320195545aee6c664a42d3828bfc8b412', 'hq.c': '50b246280ac1f0b9e1f20834f302b31e30221101abd979bbdc146fcae7c12b5f', 'start.S': '4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b', 'image.ld': '38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b'}
CANDIDATE_SHA = {'tiny.h': '3a47a510d6beba699eacd62debb732e0f4b03d160076c120c4b45e5f2a806714', 'board.c': '3f04fedb7e449e69b47ac6f2b36eb89ebe193726ac5970b0ae3a4b28008e12dc', 'search.c': '4767ae6d78462b64cde91cb827fb4986907f99c3de8ac0c40b8fe6b07777e616', 'runtime.c': 'da7a2eab5062a6d555e86d4959a7678b40e8c92d040b148fff39a89c726aa1ea', 'hq.h': 'ad66a03cef5288010c4377b81ee3661320195545aee6c664a42d3828bfc8b412', 'hq.c': '50b246280ac1f0b9e1f20834f302b31e30221101abd979bbdc146fcae7c12b5f', 'start.S': '4a6021518cfe67bee9e42806b596f4f0837e3e93487b1acfa115158ea019ba5b', 'image.ld': '38756c865914b52432572864446fcc58b791dfb508af8a33156d5c190c01044b'}

ENTRY_OLD = b"""typedef struct { atomic_flag lock; uint64_t key,data; } Entry;
"""
ENTRY_NEW = b"""typedef struct { uint64_t key; _Atomic uint64_t data; } Entry;
_Static_assert(sizeof(_Atomic uint64_t)==8&&_Alignof(Entry)>=8&&
    !(offsetof(Entry,data)%8)&&!(4096%_Alignof(Entry))&&
    __atomic_always_lock_free(8,0),"TT requires aligned lock-free uint64");
"""

PROBE_OLD = b"""static uint64_t probe(uint64_t key,int write,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    if(atomic_flag_test_and_set_explicit(&e->lock,memory_order_acquire))return 0;
    if(write)e->key=key,e->data=data;
    else data=e->key==key?e->data:0;
    atomic_flag_clear_explicit(&e->lock,memory_order_release);
    return data;
}
"""
PROBE_NEW = b"""static uint64_t probe(uint64_t key,int write,uint64_t data){
    Entry *e=table+(key&((1u<<TT_BITS)-1));
    uint64_t old=atomic_exchange_explicit(&e->data,1ULL<<63,memory_order_acquire);
    if(old>>63)return 0;
    if(write)e->key=key,old=data;
    else data=e->key==key?old:0;
    atomic_store_explicit(&e->data,old,memory_order_release);
    return data;
}
"""

CLEAR_OLD = b"""static void clear(void){for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=table[i].data=0;atomic_flag_clear(&table[i].lock);}}
"""
CLEAR_NEW = b"""static void clear(void){for(size_t i=0;i<((size_t)1<<TT_BITS);i++){table[i].key=0;atomic_init(&table[i].data,0);}}
"""

CHANGES = (("tiny.h",ENTRY_OLD,ENTRY_NEW),("search.c",PROBE_OLD,PROBE_NEW),("runtime.c",CLEAR_OLD,CLEAR_NEW))

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def apply(sources):
    if set(sources)!=set(NAMES) or any(not isinstance(raw,bytes) for raw in sources.values()):
        raise ValueError("exact eight native source bytes required")
    if {name:sha(raw) for name,raw in sources.items()}!=CONTROL_SHA:
        raise ValueError("unknown frozen native control sources")
    candidate=dict(sources)
    fragments={}
    for name,old,new in CHANGES:
        source=sources[name]
        if source.count(old)!=1 or old==new:
            raise ValueError("single fixed fragment absent: "+name)
        result=source.replace(old,new)
        if result.count(new)!=1 or result.replace(new,old)!=source:
            raise ValueError("inverse fragment differs: "+name)
        token=b"<only-fixed-TT-fragment>"
        if source.replace(old,token)!=result.replace(new,token):
            raise ValueError("source complement differs: "+name)
        candidate[name]=result
        fragments[name]={"control_bytes":len(source),"candidate_bytes":len(result),
                         "byte_change":len(result)-len(source),"one_replacement":True,
                         "old_fragment_sha256":sha(old),"new_fragment_sha256":sha(new),
                         "masked_complement_sha256":sha(source.replace(old,token)),"inverse_exact":True}
    if {name:sha(raw) for name,raw in candidate.items()}!=CANDIDATE_SHA:
        raise ValueError("unknown fixed candidate source identity")
    changed=[name for name in NAMES if candidate[name]!=sources[name]]
    if changed!=["tiny.h","search.c","runtime.c"]:
        raise ValueError("only Entry+admission/probe/clear may change")
    return candidate,{"variant_count":1,"changed_names":changed,"changed_source_count":3,
        "control_source_sha256":CONTROL_SHA,"candidate_source_sha256":CANDIDATE_SHA,
        "fragments":fragments,"all_other_five_native_exact":True,"inverse_complement_exact":True,
        "readable_native_source_byte_change":sum(row["byte_change"] for row in fragments.values()),
        "probe_signature_and_write_flag_preserved":True,"marker_bit":63,"payload_highest_reachable_bit":42,
        "source_scope":"Entry+compile-time aligned/always-lock-free admission, probe, quiescent clear only"}
