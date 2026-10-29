"""Experimental single settlement-failure result for the closed C grace owner.

The existing wait/kill call order, deadlines and last reap are retained. This
is optional source generation, not a new default cleanup or a runtime option.
The complete-file cost tied or lost against the maintained owner; the raw
cleanup reduction is not a compressed-file saving.
"""
import ast
import hashlib


def _require(value,message):
    if not value:raise ValueError(message)


def _pin(data):return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}


def _private(parts):
    result=[]
    for role,value in parts:
        if role=='helpers':
            value=(value.replace('return False','return 0').replace('return True','return 1')
                .replace('n.isdecimal()','n.isdigit()').replace('kill(','k(')
                .replace('def wait(','def w(').replace('live(','l('))
        elif role=='cleanup':
            value=value.replace('if p is not None:','if p:').replace('kill(','k(').replace('not wait(','not w(')
        elif role=='directory_cleanup':value=value.replace('if d is not None:','if d:')
        result.append((role,value))
    return result


def _admit(script,owner):
    _require(type(script)is bytes and b'\r'not in script,'LF immutable private owner required')
    _,cleanup,directory=owner.render_cleanup(state=True,shared=True)
    regions=[('helpers',owner._GROUP_SHARED),('cleanup',cleanup),('directory_cleanup',directory)]
    result=script
    for (role,old),(_,new)in zip(regions,_private(regions)):
        old,new=old.encode(),new.encode()
        _require(result.count(new)==1,'one complete private '+role+' region required')
        result=result.replace(new,old,1)
    parts=owner._admit_prepared(result,cleanup={'state':True,'wait':False,'termination':'grace'})
    canonical=_private(owner._prepared_parts(parts,state=True,wait=False,termination='grace'))
    _require(owner._joined(canonical)==script,'unknown private grace owner scaffold')
    return parts,canonical


def transform_bootstrap(script,*,owner,variant='demorgan'):
    """Fold one exact state=True/private/wait=False grace cleanup.

    ``owner`` is the caller's frozen compiler_group module. Both alternatives
    require its closed k() helper's implicit None return and w()'s truth-only
    result. The original w(0), w(5), conditional k(9)/w(5), k(9), group w(5,1)
    and p.wait sequence remains. Unknown, repeated, kill and wait=True scaffolds
    are rejected, rather than silently using the maintained owner.
    """
    _require(variant in ('demorgan','short-or'),'explicit settlement fold variant required')
    parts,regions=_admit(script,owner)
    condition={'demorgan':'not w(5)and(k(9)or not w(5))or k(9)or not w(5,1)',
               'short-or':'not(w(5)or k(9)or w(5))or k(9)or not w(5,1)'}[variant]
    replacement=(' finally:\n  '+owner._MASK+'\n  if p:\n   if not w(0):k(q)\n   if '+
                 condition+':d=None;raise SystemExit(125)\n   p.wait()\n').encode()
    old=dict(regions)['cleanup'].encode();at=script.index(old)
    candidate=script[:at]+replacement+script[at+len(old):]
    for raw in(script,candidate):
        tree=ast.parse(raw);owner._owners(tree)[1].finalbody=[ast.Pass()]
        if raw==script:before=ast.dump(tree,include_attributes=False)
        else:_require(before==ast.dump(tree,include_attributes=False),'AST outside compiler cleanup differs')
    proof={'kind':'experimental-settlement-fold-v1','variant':variant,
        'input':_pin(script),'output':_pin(candidate),'raw_delta':len(candidate)-len(script),
        'span':{'start':at,'old':old.decode(),'new':replacement.decode()},
        'protected_prefix':_pin(script[:at]),'protected_suffix':_pin(script[at+len(old):]),
        'outside_cleanup_AST_equal':True,'source_expression':_pin(parts['source'].encode()),
        'contract':{'state_authority':'path','termination':'grace','wait':False,
            'kill_returns_None':True,'wait_result_consumption':'truth only',
            'helper_calls_and_exception_order':'unchanged','normal_wait':'blocking WNOWAIT',
            'separate_leader_and_group_deadlines':'unchanged',
            'group_settlement_before_last_reap':True,'125_workspace_preservation':True,
            'observation_exclusions':['private source/line trace and exact traceback location']},
        'runtime_qualified':False,'maintained_default_changed':False}
    _require(restore_bootstrap(candidate,proof)==script,'complete settlement inverse differs')
    return candidate,proof


def restore_bootstrap(candidate,proof):
    _require(type(candidate)is bytes and proof.get('kind')=='experimental-settlement-fold-v1'
             and _pin(candidate)==proof.get('output'),'settlement candidate pin differs')
    span=proof['span'];at=span['start'];old,new=span['old'].encode(),span['new'].encode()
    _require(candidate[at:at+len(new)]==new,'settlement inverse span differs')
    result=candidate[:at]+old+candidate[at+len(new):]
    _require(_pin(result)==proof['input'] and _pin(result[:at])==proof['protected_prefix']
             and _pin(result[at+len(old):])==proof['protected_suffix'],'settlement inverse input differs')
    return result
