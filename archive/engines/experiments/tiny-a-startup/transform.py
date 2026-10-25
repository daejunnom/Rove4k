"""One exact phase-disjoint startup-counter rewrite; no selection/search."""
import hashlib
import re

CONTROL_SHA256='79284c72b64d087aa3127ea65b461aef8c7776355ea1c4ab9b2f81e59b4b48ed'
CHANGES=(
    (b'static int pending,ready,quitting;',b'static int pending=WORKERS,quitting;'),
    (b'pthread_mutex_lock(&mutex);ready++;pthread_cond_broadcast(&finished);',
     b'pthread_mutex_lock(&mutex);--pending;pthread_cond_broadcast(&finished);'),
    (b'pthread_mutex_lock(&mutex);while(ready<WORKERS)pthread_cond_wait(&finished,&mutex);pthread_mutex_unlock(&mutex);',
     b'wait();'),
)


def transform(source):
    if hashlib.sha256(source).hexdigest()!=CONTROL_SHA256:
        raise ValueError('historical A5140 readable input changed')
    result=source
    for old,new in CHANGES:
        if result.count(old)!=1:raise ValueError('startup rewrite occurrence changed')
        result=result.replace(old,new)
    if re.search(rb'\bready\b',result):raise ValueError('unexpected remaining ready consumer')
    return result
