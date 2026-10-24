"""Own ordinary A/F input-only shipping generation; no native or codec calls."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import types

def sha(data):return hashlib.sha256(data).hexdigest()
def need(v,m):
    if not v:raise ValueError(m)
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result

def source(root,family,directory,run):
    root=Path(root);entry=root/'engines/compact'/('tiny-entry-'+family.lower())
    recipe=json.loads((entry/'recipe.json').read_text());readable=(entry/'engine.c').read_bytes()
    need(sha(readable)==recipe['expected']['readable_sha256'],'readable source changed')
    helpers=root/'engines/scripts';specialize=module('qA_specialize_'+family,helpers/'specialize.py')
    def managed(command,*,cwd,env,check,stdout,stderr,timeout):
        need(check and stdout==subprocess.PIPE and stderr==subprocess.PIPE,'specialization I/O changed')
        return run(command,cwd,None,timeout)
    specialize.subprocess=types.SimpleNamespace(run=managed,PIPE=subprocess.PIPE)
    compact=module('qA_minify_'+family,helpers/'minify.py').compact_source
    lexer=module('qA_lexer_'+family,helpers/'rename_c.py')
    active,observations=specialize.specialize_c({'main.c':readable},directory,
        recipe['preprocessor']+['-DDEV=0'],os.environ.copy())
    data=compact(active['main.c'],'c')
    if family=='A':
        strip=module('qA_stitch',root/'engines/compact/tiny-a/stitch.py').strip_dev_counters
        data,_=strip(data);pairs=recipe['fixed_renames']+recipe['resource_literals']+recipe['function_spellings']
    elif family=='F':
        old=module('qA_F_original_builder',entry/'build.py');data,_=old.strip_counters(data)
        for old_name,new in recipe['resource_literals']:
            count=sum(t==old_name for a,b,t in lexer._identifier_spans(data.decode()))
            need(count==recipe['resource_token_counts'][old_name],'fixed F resource count drift')
        pairs=recipe['resource_literals']+recipe['function_spellings']
    else:raise ValueError('unknown family')
    files={'main.c':data}
    for old_name,new in pairs:files=lexer._replace(files,old_name,new)
    data=files['main.c']
    alpha=module('qA_prior_alpha_'+family,entry/'shipping_alpha.py').transform_source
    data,_=alpha(data,family=family,lexer=lexer,readable=readable)
    storage=module('qA_prior_storage_'+family,helpers/'fixed_shipping_storage.py').transform_source
    data,_=storage(data,family=family,readable=readable)
    need(len(data)==recipe['expected']['source_bytes']and sha(data)==recipe['expected']['source_sha256'],
         'exact current shipping input differs')
    return data,observations,readable,lexer
