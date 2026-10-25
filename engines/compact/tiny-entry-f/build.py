#!/usr/bin/env python3
"""Build the maintained minimal F entry from Git source and fixed decisions.

There are no experiment-directory, old build.json or executable inputs. The
resource/compiler profile is fixed. Grace cleanup and Full F are default; --policy material-noise or
--policy material-move-tt selects a declared alternate policy. --dev preserves the pinned full diagnostic form.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def sha(data):return hashlib.sha256(data).hexdigest()


def normalized(path):
    data=path.read_bytes().replace(b'\r\n',b'\n')
    if b'\r' in data:raise ValueError('lone CR in owned text input: '+str(path))
    return data


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result


COUNTER_SCHEMA={'noop_definitions':1,'conditional_calls':{'hits':1,'qs':1,'corr_uses':1},
                'unconditional_calls':['ply_aborts','hist_updates','cont_updates','corr_updates','f_probes',
                                       'f_lower','f_upper','f_converged','f_conflicts'],
                'shipping_pvs_calls':0,'total_calls_removed':12}


def strip_counters(source):
    """Admit exactly the qualified beta-only DEV=0 no-op counter schema."""
    text=source.decode()
    text,definitions=re.subn(r'(?m)^#define COUNT\(w,f\) \(\(void\)0\)\n','',text)
    for statement in ('if(bound)COUNT(w,hits);','if(depth<=0)COUNT(w,qs);','if(correction)COUNT(w,corr_uses);'):
        if text.count(statement)!=1:raise ValueError('beta-only conditional counter schema changed: '+statement)
        text=text.replace(statement,'')
    allowed=set(COUNTER_SCHEMA['unconditional_calls']);found=re.findall(r'COUNT\(w,(\w+)\);',text)
    if set(found)!=allowed or len(found)!=len(allowed) or definitions!=1:
        raise ValueError('beta-only shipping diagnostic schema changed')
    text=re.sub(r'COUNT\(w,\w+\);','',text)
    if 'COUNT(' in text:raise ValueError('unexpected diagnostic call remains')
    return text.encode(),{'removed_noop_counter_calls':len(found)+3,'shipping_pvs_calls':0}


def compile_c(command,source,directory):
    directory.mkdir()
    result=subprocess.run(command,input=source,cwd=directory,capture_output=True,timeout=90)
    (directory/'compiler.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError('compiler failed; stderr preserved in '+str(directory))
    return (directory/'x').read_bytes()


# Keep predecessor identities literal: selecting a wrapper never redefines its input.
FULL_WRAPPER_PREDECESSOR={'source_bytes': 7830, 'source_sha256': '43bc67816e91077c4cfd182ec6ba44aed7d0223d012cff82f5366ad58da63582', 'native_bytes': 18576, 'native_sha256': '3aaaacf7891a2a4660f45d75b2b3e550ab40bf01c0c1766768517719cd1e63ec', 'bootstrap_bytes': 9646, 'bootstrap_sha256': 'c5c42eb0522a499593f1233c0093bb44e964f1066b88fc2b84512c8e62c4fa12', 'whole_bytes': 4590, 'whole_sha256': '0582b96a9f0197108b5892fb6d3ab0705225ceefd3370e06314924735bc51899'}
PREVIOUS_WRAPPER_EXPECTED={'grace': {'full': {'bootstrap_bytes': 9615, 'bootstrap_sha256': '8bb9cf75ba9c7dd70b874769fe1f99129ce8cdd699858565b8d4ffdd87f576ad', 'whole_bytes': 4576, 'whole_sha256': '1c4be9d1dfbfbf38798fe00eda039f6c866dd3f6779c6c920c8c2ec40d02c6e1'}, 'material-noise': {'bootstrap_bytes': 10293, 'bootstrap_sha256': '9073fc78e4f19c3e3c872b2795784945a2080d075926ec92a836b4a100d1ea3e', 'whole_bytes': 4616, 'whole_sha256': '081326724a237f55c6e72c1590f3fbc51043fe03e8d0196ce6057874dc72bdd1'}, 'material-move-tt': {'bootstrap_bytes': 9526, 'bootstrap_sha256': 'f23373ba8da0153298f3e846acfe6713794870a8a3f8f5a2a89982167d7d67d3', 'whole_bytes': 4342, 'whole_sha256': '0387f9aad6cd1244f86d8c2bc1a5314a1c50fbb376826c7c7a1e04178618cd57'}}, 'kill': {'full': {'bootstrap_bytes': 9548, 'bootstrap_sha256': '53041259a11d2f5cbdf4dfc7efbf3b5afea408ce3a378564ad69d168b56eb69a', 'whole_bytes': 4551, 'whole_sha256': '125e20e91a7562b3973008042ba3ece1c0ecbe41156390d2eda01a28d92b4a70'}, 'material-noise': {'bootstrap_bytes': 10226, 'bootstrap_sha256': 'cceeb116f6f62c404df3e026791eab2f48187d694908192236fe2dce12fac8de', 'whole_bytes': 4591, 'whole_sha256': '1e9ac418edd4677bb823deaeca2993abfa2c8d78e90b9ae4c41101e01d69e059'}, 'material-move-tt': {'bootstrap_bytes': 9459, 'bootstrap_sha256': '51763c557f18d7a0ea0d3b52ed6ed018517026a5492350b02ecc1b0bfc834b9d', 'whole_bytes': 4311, 'whole_sha256': 'b1a53dd8946e201d55659848f9b03a114a656b2ac53aa144e512c47abc0746e4'}}, 'legacy': {'full': {'bootstrap_bytes': 9646, 'bootstrap_sha256': 'c5c42eb0522a499593f1233c0093bb44e964f1066b88fc2b84512c8e62c4fa12', 'whole_bytes': 4590, 'whole_sha256': '0582b96a9f0197108b5892fb6d3ab0705225ceefd3370e06314924735bc51899'}, 'material-noise': {'bootstrap_bytes': 10497, 'bootstrap_sha256': '958ed7d9290a131eb2b9f8e96fde3dfeb27b4284e89fccd71aab27faa8a1169b', 'whole_bytes': 4697, 'whole_sha256': 'd764d8f31e561bd173f24980fdc64a9666154738eb6daedb4c21eb3912a2e1d2'}, 'material-move-tt': {'bootstrap_bytes': 9730, 'bootstrap_sha256': '44c7a210177be3f5ed01c4f97fb30c9ca6a46bab34878121e9e6b7dd28974c8c', 'whole_bytes': 4425, 'whole_sha256': '39d082412b24be71c6dd93402dfb2f649b22ef56c808a1c55837e283b55b92a4'}}, 'shell': {'full': {'whole_bytes': 4026, 'whole_sha256': '488cd3f627ee21537001bd9df1c2fab7aa07f8a962355d69bf4c5968df8d5fd0', 'shell_header_bytes': 316, 'shell_header_sha256': 'a784b94f1099ab89161b084c127e84a480652953f9b16fabdb3b3e49d6f93973'}}}
WRAPPER_EXPECTED={'grace': {'full': {'bootstrap_bytes': 9421, 'bootstrap_sha256': '4cc341ab941290a551c7396094491ecac4a90448a0554e5c37a0a787855d610b', 'whole_bytes': 4547, 'whole_sha256': '92231fe356dc332983c2d95a5bb6e4580afac2a27fbee036fc92cac7a4666a17', 'source_bytes': 7712, 'source_sha256': '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'}, 'material-noise': {'bootstrap_bytes': 10217, 'bootstrap_sha256': 'da1bfa93e66d7e55aed0a66dcd9290f08449f7b0b8443b13dbdf9d041d1f8f5b', 'whole_bytes': 4594, 'whole_sha256': 'e26562b7d469639c715fa43254eac9fef1e4e87faf9c9ef0439a0d9b9cc11916'}, 'material-move-tt': {'bootstrap_bytes': 9450, 'bootstrap_sha256': '83f0b704c8084ec69f7fc8c224575854a9c41a24f39f42e0784f6166251e82c8', 'whole_bytes': 4325, 'whole_sha256': 'e6977187aa55326b984844de050a673c6b3b05c782e1a3d1809cdc100e8837b1'}}, 'kill': {'full': {'bootstrap_bytes': 9363, 'bootstrap_sha256': 'dacb9c87891665e3d94b5eca27c5a4d9c639dad555dbf02c1dda1ae4682082b0', 'whole_bytes': 4519, 'whole_sha256': 'c795fa68961db06dc87f1d0d93aac28644b23f4f8fd2183c2001162a9db149c3', 'source_bytes': 7712, 'source_sha256': '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'}, 'material-noise': {'bootstrap_bytes': 10159, 'bootstrap_sha256': '35082c88bd3829f66d89d01597b56b56fd3cf11eacb4d38dd5f064ca6cc8fe22', 'whole_bytes': 4566, 'whole_sha256': '786b207ea92de9c37cc6687f58f1d96b3ad9dc89adf01716a76c5d438eef4269'}, 'material-move-tt': {'bootstrap_bytes': 9392, 'bootstrap_sha256': 'df013153b6c2debbb9589a215ff6b16d706b1ea2ac86773610ffca621a2455fc', 'whole_bytes': 4297, 'whole_sha256': '7d9b5778c8b7e695f6e29e92905067f5885bd121f19b8a79efdb56d0af451a44'}}, 'legacy': {'full': {'bootstrap_bytes': 9646, 'bootstrap_sha256': 'c5c42eb0522a499593f1233c0093bb44e964f1066b88fc2b84512c8e62c4fa12', 'whole_bytes': 4590, 'whole_sha256': '0582b96a9f0197108b5892fb6d3ab0705225ceefd3370e06314924735bc51899', 'source_bytes': 7830, 'source_sha256': '43bc67816e91077c4cfd182ec6ba44aed7d0223d012cff82f5366ad58da63582'}, 'material-noise': {'bootstrap_bytes': 10497, 'bootstrap_sha256': '958ed7d9290a131eb2b9f8e96fde3dfeb27b4284e89fccd71aab27faa8a1169b', 'whole_bytes': 4697, 'whole_sha256': 'd764d8f31e561bd173f24980fdc64a9666154738eb6daedb4c21eb3912a2e1d2'}, 'material-move-tt': {'bootstrap_bytes': 9730, 'bootstrap_sha256': '44c7a210177be3f5ed01c4f97fb30c9ca6a46bab34878121e9e6b7dd28974c8c', 'whole_bytes': 4425, 'whole_sha256': '39d082412b24be71c6dd93402dfb2f649b22ef56c808a1c55837e283b55b92a4'}}, 'shell': {'full': {'whole_bytes': 4018, 'whole_sha256': 'b559c980e3146bd76ac62d2ad4d6176240e8a284b186a22b592f9be8b8877d8e', 'shell_header_bytes': 316, 'shell_header_sha256': 'a784b94f1099ab89161b084c127e84a480652953f9b16fabdb3b3e49d6f93973', 'source_bytes': 7712, 'source_sha256': '546df93f9d7f6e6f8b8bdf76b8e3d5e7f9c92913f33db7bd77deec8d50bef20e'}}}
EXPRESSION_PREDECESSOR_EXPECTED={'grace': {'bootstrap_bytes': 9449, 'bootstrap_sha256': 'd8546d6bffb2c81856e6f54975f6121d97cf53948b16386793012088cb6991f6', 'whole_bytes': 4553, 'whole_sha256': '42d2cc763a891019d40550debcb29959c73179e89988bc44f6b94e9e15e94633', 'source_bytes': 7740, 'source_sha256': 'f99f1c48e8a77d1f9483b09d46f2d68f7b1e92ea94dd437d708cc3e5a10dcfa9'}, 'kill': {'bootstrap_bytes': 9391, 'bootstrap_sha256': '1758a41818a25558cd8bd99e7ff0fd938678326fb9caf78bddc7cc87169f5e7a', 'whole_bytes': 4529, 'whole_sha256': '2a7e012769abd59740cb7e7cd4664d688064568924f3e404ed2adc626cda5f4d', 'source_bytes': 7740, 'source_sha256': 'f99f1c48e8a77d1f9483b09d46f2d68f7b1e92ea94dd437d708cc3e5a10dcfa9'}, 'shell': {'whole_bytes': 4026, 'whole_sha256': 'c0ba0e13d0c81d3f779996e1782d04d5c1f294cdb120192e749d480ddc8b372b', 'shell_header_bytes': 316, 'shell_header_sha256': 'a784b94f1099ab89161b084c127e84a480652953f9b16fabdb3b3e49d6f93973', 'source_bytes': 7740, 'source_sha256': 'f99f1c48e8a77d1f9483b09d46f2d68f7b1e92ea94dd437d708cc3e5a10dcfa9'}}
PRECOMPACT_BOOTSTRAP={'full': (9646, 'c5c42eb0522a499593f1233c0093bb44e964f1066b88fc2b84512c8e62c4fa12'), 'material-noise': (10324, '8f7622dda07bc4afe047aff82a4ebe23417c241f5d899abb52671a971f3a4741'), 'material-move-tt': (9557, '96d427e54c624dbd859ea2113434ca57c20eb61a20cb6e0649b7d0f5b40067a5')}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--dev',action='store_true',help='also reproduce the unchanged full-F semantic diagnostic C and ELF')
    parser.add_argument('--wrapper',choices=('grace','kill','legacy','shell'),default='grace',help='build-only compiler cleanup contract; kill removes the compiler graceful signal opportunity')
    parser.add_argument('--policy',choices=('full','material-noise','material-move-tt'),default='full',help='development build selection only; no UCI option')
    args=parser.parse_args();out=args.out.resolve()
    if args.wrapper=='shell' and args.policy!='full':parser.error('the measured source shell wrapper supports only full F')
    if not args.out.is_absolute() or out.exists() or out==REPO or REPO in out.parents or any((p/'.git').exists() for p in (out,*out.parents)):
        parser.error('a new absolute output outside any Git checkout is required')
    if platform.system()!='Linux' or platform.machine() not in ('x86_64','amd64'):
        parser.error('the qualified fixed target is Linux x86-64')
    ordinary_recipe=normalized(HERE/'recipe.json')
    recipe=json.loads(ordinary_recipe)
    if recipe['format']!=1 or recipe['family']!='F' or recipe['profile']!={'workers':2,'tt_bits':18,'ply':128,'dev_default':False}:
        raise ValueError('unsupported entry recipe/profile')
    if recipe['counter_schema']!=COUNTER_SCHEMA:raise ValueError('unsupported beta-only counter schema')
    material_expected={'source_bytes': 8508, 'source_sha256': 'a7b50f5d084b558c1fb07f3c4c572afa29291a4982ddd00fd783f187a3f74c93', 'native_bytes': 18576, 'native_sha256': '24ae0622c5a0fd10191950f53e0f6ea5d3e3d05fbb1b20aaa72c2b5f2754873f', 'whole_bytes': 4697, 'whole_sha256': 'd764d8f31e561bd173f24980fdc64a9666154738eb6daedb4c21eb3912a2e1d2', 'bootstrap_sha256': '958ed7d9290a131eb2b9f8e96fde3dfeb27b4284e89fccd71aab27faa8a1169b', 'bootstrap_bytes': 10497}
    if recipe['alternate_policies']['material-noise']['expected_overrides']!=material_expected:
        raise ValueError('fixed MaterialNoise-v1 expectations differ')
    move_tt_expected={'source_bytes': 7741, 'source_sha256': '6d3fa3e0099285dd9efe8934f7b419fdd204f80ed4eaf502ad64a9f5b2e12122', 'native_bytes': 18576, 'native_sha256': '1a964e23bc8967b6eb74714389b4d94fd0e505d5d1eba3616775b7e4b0a522d5', 'whole_bytes': 4425, 'whole_sha256': '39d082412b24be71c6dd93402dfb2f649b22ef56c808a1c55837e283b55b92a4', 'bootstrap_sha256': '44c7a210177be3f5ed01c4f97fb30c9ca6a46bab34878121e9e6b7dd28974c8c', 'bootstrap_bytes': 9730}
    move_tt_compression={'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True, 'lc': 0, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4', 'dictionary_bytes': 67108864, 'nice_len': 32}
    if recipe['alternate_policies']['material-move-tt']['expected_overrides']!=move_tt_expected or recipe['alternate_policies']['material-move-tt']['compression']!=move_tt_compression:
        raise ValueError('fixed MoveTT expectations/codec differ')
    original_compression={'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 9, 'extreme': True, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT4', 'dictionary_bytes': 67108864, 'nice_len': 32}
    full_compression={'format': 'lzma-alone', 'filter': 'LZMA1', 'preset': 6, 'extreme': False, 'lc': 2, 'lp': 0, 'pb': 0, 'check': 'NONE', 'mf': 'BT2', 'dictionary_bytes': 16384, 'nice_len': 24}
    if recipe['compression']!=full_compression:raise ValueError('fixed full/reference codec differs')
    if recipe['alternate_policies']['material-noise']['compression']!=original_compression:
        raise ValueError('fixed MaterialNoise-v1 codec differs')
    wrappers=recipe['wrapper_contracts']
    if wrappers['default']!='grace' or wrappers['selected_overrides']!=WRAPPER_EXPECTED or wrappers['predecessor_expected']['full']!=FULL_WRAPPER_PREDECESSOR:
        raise ValueError('fixed wrapper choices/predecessor differ')
    if any(recipe['expected'][key]!=value for key,value in WRAPPER_EXPECTED['grace']['full'].items()):
        raise ValueError('default full grace identity differs')
    if wrappers['predecessor_expected']['material-noise']!=material_expected or wrappers['predecessor_expected']['material-move-tt']!=move_tt_expected:
        raise ValueError('alternate wrapper predecessors differ')
    full_expected=dict(recipe['expected']);full_expected.update(FULL_WRAPPER_PREDECESSOR)
    if args.policy!='full':
        selected=recipe['alternate_policies'][args.policy]
        recipe=json.loads(ordinary_recipe)
        recipe['expected'].update(move_tt_expected if args.policy=='material-move-tt' else material_expected)
        recipe['compression']=dict(selected['compression'])
        recipe['launcher']=dict(selected['launcher'])
        recipe['full_reference_qualified_receipt']=recipe['qualified_receipt']
        recipe['qualified_receipt']=selected['qualified_receipt']
    predecessor_expected=dict(wrappers['predecessor_expected'][args.policy])
    if args.wrapper!='legacy':recipe['launcher']=dict(json.loads(ordinary_recipe)['launcher'])
    recipe['expected'].update(WRAPPER_EXPECTED[args.wrapper][args.policy])
    if args.wrapper=='shell':
        for key in ('bootstrap_bytes','bootstrap_sha256'):del recipe['expected'][key]
        recipe['launcher']={'kind':'source-shell-bash-ignore-after-compile-v1','bytes':316,
            'sha256':'a784b94f1099ab89161b084c127e84a480652953f9b16fabdb3b3e49d6f93973'}
    recipe['selected_policy']=args.policy;recipe['selected_wrapper']=args.wrapper
    effective_recipe=(json.dumps(recipe,indent=2)+'\n').encode()
    out.mkdir(parents=True);frozen=out/'inputs';frozen.mkdir()
    report={'complete':False,'family':'F','scope':'maintained F EP and shipping input pipeline; fixed reviewed identities, not 4KiB acceptance',
            'resources':recipe['profile'],'policy':args.policy,'wrapper':args.wrapper,'ordinary_recipe_sha256':sha(ordinary_recipe),
            'effective_recipe_sha256':sha(effective_recipe),'expected_contract':recipe['expected'],'full_reference_expected':full_expected,
            'inputs':{},'attempts':[],
            'qualified_receipt_reuse':recipe['qualified_receipt'],
            'wrapper_contract':{'selected':args.wrapper,'predecessor_expected':predecessor_expected,
                'selected_expected':WRAPPER_EXPECTED[args.wrapper][args.policy],
                'qualification':'fixed cost and source proof only until a fresh build/runtime receipt is recorded',
                'historical_receipt_scope':'unchanged engine/search/native contract; no new wrapper runtime inferred'},
            'tools':{name:subprocess.check_output(command,text=True).splitlines()[0] for name,command in
                     {'cc':['cc','--version'],'ld':['ld','--version'],'python':['python3','--version'],'lzma':['lzma','--version']}.items()}}
    def save():(out/'build.json').write_text(json.dumps(report,indent=2)+'\n')
    save()
    try:
        verifier_root=out/'selected-verifier';verifier_entry=verifier_root/'engines/compact/tiny-entry-f'
        verifier_snapshot=recipe['shell_verifier_snapshot_sha256'] if args.wrapper=='shell' else recipe['selected_verifier_snapshot_sha256']
        for relative,pin in verifier_snapshot.items():
            data=normalized(REPO/relative)
            if sha(data)!=pin:raise ValueError('selected verifier snapshot changed: '+relative)
            target=verifier_root/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        verifier_entry.mkdir(parents=True,exist_ok=True)
        (verifier_entry/'recipe.json').write_bytes(effective_recipe)
        verifier_path=verifier_root/'engines/scripts/verify_shell.py' if args.wrapper=='shell' else verifier_entry/'verify.py'
        verifier_command=[sys.executable,'-B',str(verifier_path),'--build',str(out)]
        if args.wrapper=='shell':verifier_command+=['--recipe',str(verifier_entry/'recipe.json')]
        report['selected_verifier']={'path':str(verifier_path),'recipe':str(verifier_entry/'recipe.json'),
                                     'unchanged_source':True,'policy':args.policy,'wrapper':args.wrapper,'sources':verifier_snapshot,
                                     'contract':'separate Bash delayed cleanup' if args.wrapper=='shell' else 'strict Python compiler owner',
                                     'command':verifier_command+['--out','<new absolute output>']}
        for name,expected in recipe['local_input_sha256'].items():
            data=normalized(HERE/name)
            if sha(data)!=expected:raise ValueError('entry input differs from qualified recipe: '+name)
            (frozen/name).write_bytes(data);report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for name in ('recipe.json','build.py'):
            data=normalized(HERE/name);(frozen/name).write_bytes(data)
            report['inputs'][name]={'bytes':len(data),'sha256':sha(data)}
        for relative,expected in recipe['helper_sha256'].items():
            path=REPO/relative;raw=path.read_bytes();data=normalized(path)
            if sha(data)!=expected:raise ValueError('tracked helper version changed: '+relative)
            (frozen/path.name).write_bytes(data)
            report['inputs'][relative]={'bytes':len(data),'sha256':sha(data),'working_bytes_sha256':sha(raw),'LF_normalization':raw!=data}
        composition=module('entry_source_composition',frozen/'source_composition.py')
        shared,shared_inputs=composition.freeze_shared(REPO,frozen,recipe['shared_source_sha256'])
        report['inputs'].update(shared_inputs)
        specialize=module('entry_specialize',frozen/'specialize.py').specialize_c
        compact=module('entry_minify',frozen/'minify.py').compact_source
        lexer=module('entry_fixed_tokens',frozen/'rename_c.py')
        literal=module('entry_literal',frozen/'pack_stream.py').source_literal
        compiler_owner=module('entry_compiler_group',frozen/'compiler_group.py')
        compiler_group=compiler_owner.transform_bootstrap
        compiler_stdin=module('entry_compiler_stdin',frozen/'compiler_stdin.py')
        seek_owner=module('entry_compiler_seek',frozen/'compiler_seek.py')
        compiler_seek=seek_owner.transform_bootstrap
        source_package=module('entry_source_package',frozen/'source_package.py')
        full_bootstrap=module('entry_full_bootstrap',frozen/'bootstrap_full.py').prepare_template
        common=module('entry_shipping_common',frozen/'shipping_common.py')
        refine=module('entry_shipping_refinements',frozen/'shipping_refinements.py')
        dead_state=module('entry_material_state',frozen/'shipping_material_state.py')
        integer_forms=module('entry_integer_forms',frozen/'shipping_integer_forms.py')
        terminal=module('entry_F_terminal',frozen/'shipping_terminal.py')
        hash_policy=module('entry_F_hash_policy',frozen/'shipping_hash_policy.py')
        include_forms=module('entry_include_forms',frozen/'shipping_includes.py')
        mixer_forms=module('entry_mixer_literals',frozen/'shipping_mixer_literals.py')
        clamp=module('entry_F_clamp',frozen/'shipping_clamp.py')
        source_forms=module('entry_F_source_forms',frozen/'shipping_source_forms.py')
        clock_forms=module('entry_clock_presence',frozen/'shipping_clock.py')
        result_stream=module('entry_F_result_stream',frozen/'shipping_result_stream.py')
        depth_repetition=module('entry_F_depth_repetition',frozen/'shipping_depth_repetition.py')
        macro_literals=module('entry_F_macro_literals',frozen/'shipping_macro_literals.py')
        int_token=module('entry_F_int_token',frozen/'shipping_int_token.py')
        history_depth=module('entry_F_history_depth',frozen/'shipping_history_depth.py')
        lazy_fallback=module('entry_shared_lazy_fallback',frozen/'shipping_lazy_fallback.py')
        qs_cutoff=module('entry_F_qs_cutoff',frozen/'shipping_qs_cutoff.py')
        history_path=module('entry_F_history_path',frozen/'shipping_history_path.py')
        alpha=module('entry_fixed_F_alpha',frozen/'shipping_alpha.py').transform_source
        storage=module('entry_fixed_F_storage',frozen/'shipping_storage.py').transform_source
        scope_module=module('entry_bound_F_scope',frozen/'shipping_scope.py')
        scope=scope_module.transform_source;members=scope_module.transform_members
        semantics=module('entry_fixed_F_semantics',frozen/'shipping_semantics.py')
        input_profile=module('entry_fixed_F_input',frozen/'shipping_input.py')
        declarations=module('entry_fixed_F_declarations',frozen/'shipping_declarations.py').transform_source
        hce=module('entry_fixed_F_HCE',frozen/'shipping_hce.py').transform_source
        types=module('entry_fixed_F_types',frozen/'shipping_types.py').transform_source
        unit_bound=module('entry_fixed_F_unit_bound',frozen/'shipping_unit_bound.py').transform_source
        startup=module('entry_fixed_F_startup',frozen/'shipping_startup.py').transform_source
        global_names=module('entry_fixed_F_global_names',frozen/'shipping_global_names.py').transform_source
        capture=module('entry_fixed_F_capture',frozen/'shipping_capture.py').transform_source
        material_noise=module('entry_fixed_F_material_noise',frozen/'shipping_material_noise.py').transform_source
        material_names=module('entry_fixed_F_material_names',frozen/'shipping_material_names.py').transform_source
        material_capture=module('entry_fixed_F_material_capture',frozen/'shipping_material_capture.py').transform_source
        move_tt=module('entry_fixed_F_move_TT',frozen/'shipping_move_tt.py').transform_source
        move_tt_names=module('entry_fixed_F_move_TT_names',frozen/'shipping_move_tt_names.py').transform_source
        expressions=module('entry_fixed_F_expressions',frozen/'shipping_material_expressions.py').transform_source
        fixed_names=module('entry_fixed_F_names',frozen/'shipping_names.py').transform_source
        fixed_selector=module('entry_fixed_F_selector',frozen/'shipping_selector.py').transform_source
        local_rank=module('entry_fixed_F_rank',frozen/'shipping_rank.py').transform_source
        digit_fd=module('entry_F_digit_fd',frozen/'shipping_digit_fd.py')
        condition_form=module('entry_F_one_condition',frozen/'shipping_condition.py')
        walker_form=module('entry_F_direct_walker',frozen/'shipping_walker.py')
        integer_expressions=module('entry_F_integer_expressions',frozen/'shipping_integer_expressions.py')
        square_successor=module('entry_F_square_successor',frozen/'shipping_square_successor.py')
        return_token=module('entry_F_return_token',frozen/'shipping_return_token.py')
        four_locals=module('entry_F_four_locals',frozen/'shipping_four_locals.py')
        depth_bound=module('entry_F_depth_bound',frozen/'shipping_depth_bound.py')
        pool_state=module('entry_F_pool_state',frozen/'shipping_pool_state.py')
        frequency=module('entry_F_frequency',frozen/'shipping_frequency.py')
        format_loop=module('entry_F_format_loop',frozen/'shipping_format_loop.py')
        quiet_order=module('entry_F_quiet_order',frozen/'shipping_quiet_order.py')
        from_inline=module('entry_F_from_inline',frozen/'shipping_from.py')
        mtd_state=module('entry_F_mtd_state',frozen/'shipping_mtd_state.py')
        go_boundary=module('entry_F_go_boundary',frozen/'shipping_go_boundary.py')
        quiet_slot=module('entry_F_quiet_slot',frozen/'shipping_quiet_slot.py')
        static_alias=module('entry_F_static_alias',frozen/'shipping_static_alias.py')
        source_expression=module('entry_F_source_expression',frozen/'shipping_expression.py')
        # Keep this base for every unchanged shipping readable/spelling guard.
        canonical=composition.assemble((frozen/'engine.c').read_bytes(),shared,expected_sha256=recipe['assembled_source_sha256']['engine.c']);template=(frozen/'bootstrap.py.in').read_bytes();prefix=(frozen/'launcher.sh').read_bytes()
        marker=b'__ROVE_SOURCE_LITERAL__'
        if template.count(marker)!=1 or len(prefix)!=77:raise ValueError('bootstrap recipe changed')
        legacy_template,legacy_prefix=template,prefix
        if args.policy=='full' or args.wrapper!='legacy':
            # One fixed marker-template choice; shared legacy consumers
            # retain the original template and its published artifacts.
            template=full_bootstrap(template)
            template,template_metadata=digit_fd.transform_template(template)
            report['digit_fd_template']=template_metadata
            prefix=source_package.XZ_STDIN_HEADER
        selected_prefix=source_package.shell_header(kind='source',compiler=recipe['compiler'],child_reaping='ignore-after-compile') if args.wrapper=='shell' else prefix
        if len(selected_prefix)!=recipe['launcher']['bytes'] or sha(selected_prefix)!=recipe['launcher']['sha256']:
            raise ValueError('fixed selected launcher changed')
        selected_compression={'full':full_compression,'material-noise':original_compression,
                              'material-move-tt':move_tt_compression}[args.policy]
        if recipe['compression']!=selected_compression:raise ValueError('fixed selected LZMA1 recipe changed')
        compression=recipe['compression']
        expected=recipe['expected']
        def generate(directory,dev=False):
            preprocess_source=canonical;semantic_metadata=None;input_metadata=None;before_names=None
            if dev:
                preprocess_source,semantic_metadata=semantics.transform_readable(canonical)
                preprocess_source,input_metadata=input_profile.transform_readable(preprocess_source)
            active,observations=specialize({'main.c':preprocess_source},directory,recipe['preprocessor']+['-DDEV='+str(int(dev))],os.environ.copy())
            data=compact(active['main.c'],'c')
            counters=None;alpha_metadata=None;storage_metadata=None;scope_metadata=None;member_metadata=None;declaration_metadata=None;hce_metadata=None;type_metadata=None;unit_bound_metadata=None;startup_metadata=None;global_names_metadata=None;capture_metadata=None;policy_metadata=None;material_names_metadata=None;material_capture_metadata=None;move_tt_metadata=None;move_tt_names_metadata=None;expressions_metadata=None;common_metadata=None
            if not dev:
                data,counters=strip_counters(data);files={'main.c':data}
                for old,new in recipe['resource_literals']:
                    count=sum(token==old for _,_,token in lexer._identifier_spans(files['main.c'].decode()))
                    if count!=recipe['resource_token_counts'][old]:raise ValueError('fixed resource token count changed: '+old)
                    files=lexer._replace(files,old,new)
                for old,new in recipe['function_spellings']:
                    files=lexer._replace(files,old,new)
                data=files['main.c']
                data,alpha_metadata=alpha(data,family='F',lexer=lexer,readable=canonical)
                data,storage_metadata=storage(data,family='F',readable=canonical)
                data,scope_metadata=scope(data)
                data,member_metadata=members(data)
                data,semantic_metadata=semantics.transform_source(data,readable=canonical)
                semantic_readable,_=semantics.transform_readable(canonical)
                data,input_metadata=input_profile.transform_source(data,readable=semantic_readable)
                data,declaration_metadata=declarations(data,readable=canonical)
                data,hce_metadata=hce(data)
                data,type_metadata=types(data,readable=canonical,lexer=lexer)
                data,unit_bound_metadata=unit_bound(data)
                data,startup_metadata=startup(data)
                if args.policy in ('material-noise','material-move-tt'):
                    full_reference,_=global_names(data);full_reference,_=capture(full_reference)
                    raw_full_reference={'bytes':len(full_reference),'sha256':sha(full_reference)}
                    full_reference,full_common_metadata=common.transform_source(full_reference,family='F',policy='full')
                    full_reference,refinement=refine.transform_source(full_reference,family='F',policy='full')
                    full_common_metadata['refinements']=refinement
                    full_reference,dead_state_metadata=dead_state.transform_source(full_reference,family='F',policy='full')
                    full_common_metadata['material_state']=dead_state_metadata
                    full_reference,integer_metadata=integer_forms.transform_source(full_reference,family='F',policy='full')
                    full_common_metadata['integer_forms']=integer_metadata
                    full_reference,terminal_metadata=terminal.transform_source(full_reference)
                    full_common_metadata['terminal_shared_legal_loop']=terminal_metadata
                    full_reference,hash_metadata=hash_policy.transform_source(full_reference,family='F')
                    full_common_metadata['hash_policy']=hash_metadata
                    full_reference,include_metadata=include_forms.transform_source(full_reference,family='F',policy='full')
                    full_common_metadata['literal_include_forms']=include_metadata
                    full_reference,mixer_metadata=mixer_forms.transform_source(full_reference,family='F',policy='full')
                    full_common_metadata['mixer_literals']=mixer_metadata
                    full_reference,clamp_metadata=clamp.transform_source(full_reference)
                    full_common_metadata['correction_clamp']=clamp_metadata
                    full_reference,forms_metadata=source_forms.transform_source(full_reference)
                    full_common_metadata['source_forms']=forms_metadata
                    full_reference,clock_metadata=clock_forms.transform_source(full_reference,family='F')
                    full_common_metadata['clock_presence']=clock_metadata
                    full_reference,stream_metadata=result_stream.transform_source(full_reference)
                    full_common_metadata['result_stream']=stream_metadata
                    full_reference,depth_metadata=depth_repetition.transform_source(full_reference)
                    full_common_metadata['depth_repetition']=depth_metadata
                    full_reference,macro_metadata=macro_literals.transform_source(full_reference,family='F')
                    full_common_metadata['fixed_macro_literals']=macro_metadata
                    full_reference,int_metadata=int_token.transform_source(full_reference,family='F')
                    full_common_metadata['plain_int_keyword_token']=int_metadata
                    full_reference,history_metadata=history_depth.transform_source(full_reference,family='F')
                    full_common_metadata['derived_history_depth']=history_metadata
                    full_reference,lazy_metadata=lazy_fallback.transform_source(full_reference,family='F')
                    full_common_metadata['lazy_fallback']=lazy_metadata
                    full_reference,qs_metadata=qs_cutoff.transform_source(full_reference,family='F')
                    full_common_metadata['qs_legal_cutoff']=qs_metadata
                    full_reference,path_metadata=history_path.transform_source(full_reference,family='F')
                    full_common_metadata['history_path']=path_metadata
                    full_reference,names_metadata=fixed_names(full_reference)
                    full_common_metadata['fixed_names']=names_metadata
                    full_reference,selector_metadata=fixed_selector(full_reference,family='F')
                    full_common_metadata['fixed2_selector']=selector_metadata
                    full_reference,rank_metadata=local_rank(full_reference)
                    full_common_metadata['local_HCE_rank']=rank_metadata
                    full_reference,digit_metadata=digit_fd.transform_source(full_reference)
                    full_common_metadata['digit_guard']=digit_metadata
                    full_reference,condition_metadata=condition_form.transform_source(full_reference)
                    full_common_metadata['shared_condition']=condition_metadata
                    full_reference,walker_metadata=walker_form.transform_source(full_reference)
                    full_common_metadata['direct_walker']=walker_metadata
                    full_reference,integer_metadata=integer_expressions.transform_source(full_reference)
                    full_common_metadata['fixed_integer_expressions']=integer_metadata
                    full_reference,successor_metadata=square_successor.transform_source(full_reference)
                    full_common_metadata['valid_square_successor']=successor_metadata
                    full_reference,return_metadata=return_token.transform_source(full_reference)
                    full_common_metadata['return_keyword_token']=return_metadata
                    full_reference,local_metadata=four_locals.transform_source(full_reference)
                    full_common_metadata['four_local_spellings']=local_metadata
                    full_reference,depth_bound_metadata=depth_bound.transform_source(full_reference)
                    full_common_metadata['depth_bound_metadata']=depth_bound_metadata
                    full_reference,pool_metadata=pool_state.transform_source(full_reference)
                    full_common_metadata['pool_depth_job_token']=pool_metadata
                    full_reference,frequency_metadata=frequency.transform_source(full_reference)
                    full_common_metadata['frequency_spellings']=frequency_metadata
                    full_reference,format_metadata=format_loop.transform_source(full_reference)
                    full_common_metadata['format_loop']=format_metadata
                    full_reference,order_metadata=quiet_order.transform_source(full_reference)
                    full_common_metadata['quiet_order_inline']=order_metadata
                    full_reference,from_metadata=from_inline.transform_source(full_reference)
                    full_common_metadata['from_macro_inline']=from_metadata
                    full_reference,mtd_metadata=mtd_state.transform_source(full_reference)
                    full_common_metadata['mtd_local_state']=mtd_metadata
                    full_reference,go_metadata=go_boundary.transform_source(full_reference)
                    full_common_metadata['sole_go_boundary']=go_metadata
                    full_reference,slot_metadata=quiet_slot.transform_source(full_reference)
                    full_common_metadata['quiet_continuation_slot']=slot_metadata
                    if len(full_reference)!=full_expected['source_bytes'] or sha(full_reference)!=full_expected['source_sha256']:
                        raise ValueError('default full-F source generation changed')
                    data,policy_metadata=material_noise(data)
                    data,material_names_metadata=material_names(data)
                    data,material_capture_metadata=material_capture(data)
                    if args.policy=='material-move-tt':
                        raw_material_reference={'bytes':len(data),'sha256':sha(data)}
                        material_cleaned,material_common_metadata=common.transform_source(data,family='F',policy='material-noise')
                        material_cleaned,refinement=refine.transform_source(material_cleaned,family='F',policy='material-noise')
                        material_common_metadata['refinements']=refinement
                        material_cleaned,dead_state_metadata=dead_state.transform_source(material_cleaned,family='F',policy='material-noise')
                        material_common_metadata['material_state']=dead_state_metadata
                        material_cleaned,integer_metadata=integer_forms.transform_source(material_cleaned,family='F',policy='material-noise')
                        material_common_metadata['integer_forms']=integer_metadata
                        material_cleaned,include_metadata=include_forms.transform_source(material_cleaned,family='F',policy='material-noise')
                        material_common_metadata['literal_include_forms']=include_metadata
                        material_cleaned,mixer_metadata=mixer_forms.transform_source(material_cleaned,family='F',policy='material-noise')
                        material_common_metadata['mixer_literals']=mixer_metadata
                        if len(material_cleaned)!=material_expected['source_bytes'] or sha(material_cleaned)!=material_expected['source_sha256']:
                            raise ValueError('existing material-noise source generation changed')
                        material_reference={'bytes':len(material_cleaned),'sha256':sha(material_cleaned),
                                            'stage':'after-shipping-common','raw_source':raw_material_reference,
                                            'shipping_common':material_common_metadata}
                        data,move_tt_metadata=move_tt(data)
                        data,move_tt_names_metadata=move_tt_names(data)
                        data,expressions_metadata=expressions(data)
                        move_tt_metadata['separate_material_reference_source_generation']=material_reference
                    policy_metadata['separate_full_reference_source_generation']={'bytes':len(full_reference),'sha256':sha(full_reference),
                        'stage':'after-shipping-common','raw_source':raw_full_reference,'shipping_common':full_common_metadata}
                else:
                    data,global_names_metadata=global_names(data)
                    data,capture_metadata=capture(data)
                data,common_metadata=common.transform_source(data,family='F',policy=args.policy)
                data,refinement=refine.transform_source(data,family='F',policy=args.policy)
                common_metadata['refinements']=refinement
                data,dead_state_metadata=dead_state.transform_source(data,family='F',policy=args.policy)
                common_metadata['material_state']=dead_state_metadata
                data,integer_metadata=integer_forms.transform_source(data,family='F',policy=args.policy)
                common_metadata['integer_forms']=integer_metadata
                if args.policy=='full':
                    data,terminal_metadata=terminal.transform_source(data)
                    common_metadata['terminal_shared_legal_loop']=terminal_metadata
                    data,hash_metadata=hash_policy.transform_source(data,family='F')
                    common_metadata['hash_policy']=hash_metadata
                data,include_metadata=include_forms.transform_source(data,family='F',policy=args.policy)
                common_metadata['literal_include_forms']=include_metadata
                data,mixer_metadata=mixer_forms.transform_source(data,family='F',policy=args.policy)
                common_metadata['mixer_literals']=mixer_metadata
                if args.policy=='full':
                    data,clamp_metadata=clamp.transform_source(data)
                    common_metadata['correction_clamp']=clamp_metadata
                    data,forms_metadata=source_forms.transform_source(data)
                    common_metadata['source_forms']=forms_metadata
                    data,clock_metadata=clock_forms.transform_source(data,family='F')
                    common_metadata['clock_presence']=clock_metadata
                    data,stream_metadata=result_stream.transform_source(data)
                    common_metadata['result_stream']=stream_metadata
                    data,depth_metadata=depth_repetition.transform_source(data)
                    common_metadata['depth_repetition']=depth_metadata
                    data,macro_metadata=macro_literals.transform_source(data,family='F')
                    common_metadata['fixed_macro_literals']=macro_metadata
                    data,int_metadata=int_token.transform_source(data,family='F')
                    common_metadata['plain_int_keyword_token']=int_metadata
                    data,history_metadata=history_depth.transform_source(data,family='F')
                    common_metadata['derived_history_depth']=history_metadata
                    data,lazy_metadata=lazy_fallback.transform_source(data,family='F')
                    common_metadata['lazy_fallback']=lazy_metadata
                    data,qs_metadata=qs_cutoff.transform_source(data,family='F')
                    common_metadata['qs_legal_cutoff']=qs_metadata
                    data,path_metadata=history_path.transform_source(data,family='F')
                    common_metadata['history_path']=path_metadata
                    before_names=data
                    data,names_metadata=fixed_names(data)
                    common_metadata['fixed_names']=names_metadata
                    data,selector_metadata=fixed_selector(data,family='F')
                    common_metadata['fixed2_selector']=selector_metadata
                    data,rank_metadata=local_rank(data)
                    common_metadata['local_HCE_rank']=rank_metadata
                    data,digit_metadata=digit_fd.transform_source(data)
                    common_metadata['digit_guard']=digit_metadata
                    data,condition_metadata=condition_form.transform_source(data)
                    common_metadata['shared_condition']=condition_metadata
                    data,walker_metadata=walker_form.transform_source(data)
                    common_metadata['direct_walker']=walker_metadata
                    data,integer_metadata=integer_expressions.transform_source(data)
                    common_metadata['fixed_integer_expressions']=integer_metadata
                    data,successor_metadata=square_successor.transform_source(data)
                    common_metadata['valid_square_successor']=successor_metadata
                    data,return_metadata=return_token.transform_source(data)
                    common_metadata['return_keyword_token']=return_metadata
                    data,local_metadata=four_locals.transform_source(data)
                    common_metadata['four_local_spellings']=local_metadata
                    data,depth_bound_metadata=depth_bound.transform_source(data)
                    common_metadata['depth_bound_metadata']=depth_bound_metadata
                    data,pool_metadata=pool_state.transform_source(data)
                    common_metadata['pool_depth_job_token']=pool_metadata
                    data,frequency_metadata=frequency.transform_source(data)
                    common_metadata['frequency_spellings']=frequency_metadata
                    data,format_metadata=format_loop.transform_source(data)
                    common_metadata['format_loop']=format_metadata
                    data,order_metadata=quiet_order.transform_source(data)
                    common_metadata['quiet_order_inline']=order_metadata
                    data,from_metadata=from_inline.transform_source(data)
                    common_metadata['from_macro_inline']=from_metadata
                    data,mtd_metadata=mtd_state.transform_source(data)
                    common_metadata['mtd_local_state']=mtd_metadata
                    data,go_metadata=go_boundary.transform_source(data)
                    common_metadata['sole_go_boundary']=go_metadata
                    data,slot_metadata=quiet_slot.transform_source(data)
                    common_metadata['quiet_continuation_slot']=slot_metadata
                    if args.wrapper!='legacy':
                        data,alias_metadata=static_alias.transform_source(data)
                        common_metadata['static_keyword_alias']=alias_metadata
                        data,expression_metadata=source_expression.transform_source(data)
                        common_metadata['scalar_expression_compaction']=expression_metadata
            return data,observations,counters,alpha_metadata,storage_metadata,scope_metadata,member_metadata,semantic_metadata,input_metadata,declaration_metadata,hce_metadata,type_metadata,unit_bound_metadata,startup_metadata,global_names_metadata,capture_metadata,policy_metadata,material_names_metadata,material_capture_metadata,move_tt_metadata,move_tt_names_metadata,expressions_metadata,common_metadata,before_names
        def package(source):
            final_source=source
            if args.policy=='full' and args.wrapper!='legacy':source=source_expression.restore_source(source)
            selected_source=source
            if args.policy=='full' and args.wrapper!='legacy':source=static_alias.restore_source(source)
            previous_literal=lambda data:common.source_literal(data,literal)
            successor_literal=lambda data:square_successor.source_literal(data,previous_literal)
            return_literal=lambda data:return_token.source_literal(data,successor_literal)
            four_literal=lambda data:four_locals.source_literal(data,return_literal)
            depth_literal=lambda data:depth_bound.source_literal(data,four_literal)
            pool_literal=lambda data:pool_state.source_literal(data,depth_literal)
            frequency_literal=lambda data:frequency.source_literal(data,pool_literal)
            format_literal=lambda data:format_loop.source_literal(data,frequency_literal)
            quiet_literal=lambda data:quiet_order.source_literal(data,format_literal)
            from_literal=lambda data:from_inline.source_literal(data,quiet_literal)
            mtd_literal=lambda data:mtd_state.source_literal(data,from_literal)
            go_literal=lambda data:go_boundary.source_literal(data,mtd_literal)
            guarded_source=quiet_slot.restore_source(source) if args.policy=='full' else source
            expression,_=(go_literal(guarded_source) if args.policy=='full' else previous_literal(source))
            if ast.literal_eval(expression)!=guarded_source:raise ValueError('selected opaque C literal differs')
            script=(template if args.policy=='full' else legacy_template).replace(marker,expression.encode())
            script,group_metadata=compiler_group(script)
            report['compiler_group']=group_metadata
            if args.policy=='full':
                if len(script)!=9786 or sha(script)!='0cf100bec81e83b3fd05fb8c3e9e61144e6d0aa75429e361573e6f44cfb38c58':
                    raise ValueError('full-F compiler-owner predecessor differs')
                # Consume every old source/literal/owner guard before forwarding
                # only the new opaque C expression into that unchanged owner.
                guarded_script=script
                next_expression,_=quiet_slot.source_literal(source,go_literal)
                old_literal,new_literal=expression.encode(),next_expression.encode()
                if script.count(old_literal)!=1 or ast.literal_eval(next_expression)!=source:
                    raise ValueError('full-F quiet source expression differs')
                script=script.replace(old_literal,new_literal,1)
                if script.replace(new_literal,old_literal,1)!=guarded_script:
                    raise ValueError('full-F quiet bootstrap full inverse differs')
                def opaque_tree(data,expected_source):
                    tree=ast.parse(data)
                    matches=[node for node in ast.walk(tree) if isinstance(node,ast.Constant) and node.value==expected_source]
                    if len(matches)!=1:raise ValueError('one opaque full-F C literal required')
                    matches[0].value=b'__OWNED_FULL_F_SOURCE__'
                    return ast.dump(tree,include_attributes=False)
                if opaque_tree(guarded_script,guarded_source)!=opaque_tree(script,source):
                    raise ValueError('full-F owner outside source AST differs')
                replayed,group_metadata=compiler_group(template.replace(marker,new_literal))
                if replayed!=script:raise ValueError('full-F owner replay with quiet source differs')
                report['compiler_group']=group_metadata
                report['quiet_slot_bootstrap']={'old_owner_guard_consumed':True,'old_owner_bytes':len(guarded_script),
                    'old_owner_sha256':sha(guarded_script),'new_owner_bytes':len(script),'new_owner_sha256':sha(script),
                    'source_expression_only':True,'full_inverse':True,'outside_source_AST_equal':True,
                    'fresh_owner_metadata':True}
                script,stdin_metadata=compiler_stdin.transform_bootstrap(script,shared_wait=True)
                report['compiler_stdin']=stdin_metadata
                script,seek_metadata=compiler_seek(script,owner_metadata=stdin_metadata,
                    prepare_owner=compiler_stdin.transform_bootstrap,restore_owner=compiler_stdin.restore_bootstrap)
                report['compiler_seek']=seek_metadata
            # Consume the exact predecessor bootstrap and whole before applying
            # any new template/transport/cleanup choice. No expected auto-fill.
            if len(script)!=predecessor_expected['bootstrap_bytes'] or sha(script)!=predecessor_expected['bootstrap_sha256']:
                raise ValueError('selected wrapper predecessor bootstrap differs')
            predecessor_prefix=prefix if args.policy=='full' else legacy_prefix
            control=source_package.package(script,compression,prefix=predecessor_prefix)
            if len(control)!=predecessor_expected['whole_bytes'] or sha(control)!=predecessor_expected['whole_sha256']:
                raise ValueError('selected wrapper predecessor whole differs')
            report['wrapper_contract']['predecessor_guard_consumed']={'bootstrap':{'bytes':len(script),'sha256':sha(script)},
                'whole':{'bytes':len(control),'sha256':sha(control)},'source_literal_value_equal':True}
            if args.wrapper=='legacy':return control,script
            if args.wrapper=='shell':
                # The direct-source shell is a separate restoration contract.
                # Keep the original full owner guards above, but do not label
                # this shell header a Python bootstrap or reuse strict runtime.
                header=source_package.shell_header(kind='source',compiler=recipe['compiler'],child_reaping='ignore-after-compile')
                if len(header)!=expected['shell_header_bytes'] or sha(header)!=expected['shell_header_sha256']:
                    raise ValueError('fixed shell header differs')
                previous=EXPRESSION_PREDECESSOR_EXPECTED['shell']
                previous_whole=source_package.package_shell(selected_source,compression,kind='source',compiler=recipe['compiler'],child_reaping='ignore-after-compile')
                if len(previous_whole)!=previous['whole_bytes'] or sha(previous_whole)!=previous['whole_sha256']:
                    raise ValueError('source expression shell predecessor whole differs')
                data=source_package.package_shell(final_source,compression,kind='source',compiler=recipe['compiler'],child_reaping='ignore-after-compile')
                report['wrapper_contract'].update(representation='source-shell-header',contract=recipe['wrapper_contracts']['shell_contract'],
                    shell_header={'bytes':len(header),'sha256':sha(header)},
                    payload={'bytes':len(data)-len(header),'source_bytes':len(final_source),'source_sha256':sha(final_source)},
                    expression_predecessor_whole={'bytes':len(previous_whole),'sha256':sha(previous_whole)},
                    compiler_owner_lifetime_equivalence_claimed=False)
                return data,header
            if args.policy!='full':
                old_owner=script
                script,group_metadata=compiler_group(template.replace(marker,expression.encode()))
                inverse=script
                for before,after in (
                    (b" fd=os.open(d+'/x',0)\n",b" fd=os.open(d+'/x',os.O_RDONLY)\n"),
                    (b'for s in 2,15:signal.signal(s,stop)\n',b'signal.signal(2,stop);signal.signal(15,stop)\n'),
                    (b'for s in 2,15:signal.signal(s,signal.SIG_DFL)\n',b'signal.signal(2,signal.SIG_DFL);signal.signal(15,signal.SIG_DFL)\n'),
                    (b'cwd=d,env=dict(os.environ,TMPDIR=d),stdin=',b'cwd=d,env=e,stdin='),
                    (b" d=tempfile.mkdtemp(prefix='r4-')\n",b" d=tempfile.mkdtemp(prefix='r4-')\n e=dict(os.environ,TMPDIR=d)\n")):
                    if inverse.count(before)!=1:raise ValueError('reduced prepared owner inverse span differs')
                    inverse=inverse.replace(before,after,1)
                if inverse!=old_owner or ast.dump(ast.parse(inverse),include_attributes=False)!=ast.dump(ast.parse(old_owner),include_attributes=False):
                    raise ValueError('reduced prepared owner full inverse differs')
                report['compiler_group']=group_metadata
                report['reduced_prepared_template']={'old_owner_guard_consumed':True,'new_owner_metadata':True,
                    'owner_complete_byte_and_AST_inverse':True,'source_expression_unchanged':True,
                    'source_digit_transform_called':False,'template_helper_historical_policy_label':'full-fixed2',
                    'selected_engine_policy':args.policy}
                before_transport=script
                script,stdin_metadata=compiler_stdin.transform_bootstrap(script,shared_wait=True)
                report['compiler_stdin']=stdin_metadata
                script,seek_metadata=compiler_seek(script,owner_metadata=stdin_metadata,
                    prepare_owner=compiler_stdin.transform_bootstrap,restore_owner=compiler_stdin.restore_bootstrap)
                if compiler_stdin.restore_bootstrap(seek_owner.restore_bootstrap(script,seek_metadata),stdin_metadata)!=before_transport:
                    raise ValueError('reduced prepared W1/W2/seek inverse differs')
                report['compiler_seek']=seek_metadata
            if (len(script),sha(script))!=PRECOMPACT_BOOTSTRAP[args.policy]:
                raise ValueError('fixed precompact bootstrap differs')
            before_normalization=script
            script,normalization=compiler_owner.normalize_bootstrap(script)
            if not normalization['identity'] or compiler_owner.restore_bootstrap(script,normalization)!=before_normalization:
                raise ValueError('prepared owner normalization is no longer identity')
            before_cleanup=script
            script,cleanup=compiler_owner.compact_cleanup(script,state=True,wait=False,termination=args.wrapper)
            if compiler_owner.restore_bootstrap(script,cleanup)!=before_cleanup:
                raise ValueError('compact cleanup full inverse differs')
            report['wrapper_contract'].update(normalization=normalization,cleanup=cleanup)
            previous=PREVIOUS_WRAPPER_EXPECTED[args.wrapper][args.policy]
            if (len(script),sha(script))!=(previous['bootstrap_bytes'],previous['bootstrap_sha256']):
                raise ValueError('private owner predecessor bootstrap differs')
            if args.policy=='full':
                old_script=script
                aliased_expression,_=static_alias.source_literal(selected_source,lambda data:quiet_slot.source_literal(data,go_literal))
                if script.count(next_expression.encode())!=1:raise ValueError('one full static alias source literal required')
                script=script.replace(next_expression.encode(),aliased_expression.encode(),1)
                if script.replace(aliased_expression.encode(),next_expression.encode(),1)!=old_script or opaque_tree(old_script,source)!=opaque_tree(script,selected_source):
                    raise ValueError('static alias owner inverse/outside-source AST differs')
                report['wrapper_contract']['static_alias']={'source_only':True,'full_inverse':True,'outside_source_AST_equal':True,
                    'input_source':{'bytes':len(source),'sha256':sha(source)},'selected_source':{'bytes':len(selected_source),'sha256':sha(selected_source)}}
            before_private=script
            script,private_owner=compiler_owner.compact_private_owner(script,termination=args.wrapper)
            if compiler_owner.restore_bootstrap(script,private_owner)!=before_private:raise ValueError('private owner full inverse differs')
            report['wrapper_contract']['private_owner']=private_owner
            if args.policy=='full':
                previous=EXPRESSION_PREDECESSOR_EXPECTED[args.wrapper]
                if (len(script),sha(script))!=(previous['bootstrap_bytes'],previous['bootstrap_sha256']):
                    raise ValueError('source expression predecessor bootstrap differs')
                previous_whole=source_package.package(script,compression,prefix=prefix)
                if len(previous_whole)!=previous['whole_bytes'] or sha(previous_whole)!=previous['whole_sha256']:
                    raise ValueError('source expression predecessor whole differs')
                before_expression=script
                final_expression,_=source_expression.source_literal(final_source,lambda data:(aliased_expression,'actual-static-alias-literal'))
                if script.count(aliased_expression.encode())!=1:raise ValueError('one scalar expression source literal required')
                script=script.replace(aliased_expression.encode(),final_expression.encode(),1)
                if script.replace(final_expression.encode(),aliased_expression.encode(),1)!=before_expression or opaque_tree(before_expression,selected_source)!=opaque_tree(script,final_source):
                    raise ValueError('scalar expression owner inverse/outside-source AST differs')
                report['wrapper_contract']['scalar_expression']={'source_only':True,'full_inverse':True,'outside_source_AST_equal':True,
                    'previous_bootstrap':{'bytes':len(before_expression),'sha256':sha(before_expression)},
                    'previous_whole':{'bytes':len(previous_whole),'sha256':sha(previous_whole)},
                    'input_source':{'bytes':len(selected_source),'sha256':sha(selected_source)},
                    'selected_source':{'bytes':len(final_source),'sha256':sha(final_source)}}
            ast.parse(script)
            data=source_package.package(script,compression,prefix=prefix)
            return data,script
        first=None;first_dev=None
        for index in (1,2):
            directory=out/('attempt-'+str(index));directory.mkdir()
            source,observations,counters,alpha_metadata,storage_metadata,scope_metadata,member_metadata,semantic_metadata,input_metadata,declaration_metadata,hce_metadata,type_metadata,unit_bound_metadata,startup_metadata,global_names_metadata,capture_metadata,policy_metadata,material_names_metadata,material_capture_metadata,move_tt_metadata,move_tt_names_metadata,expressions_metadata,common_metadata,before_names=generate(directory/'preprocess')
            if len(source)!=expected['source_bytes'] or sha(source)!=expected['source_sha256']:raise ValueError('compact C identity mismatch')
            (directory/'main.c').write_bytes(source)
            if before_names is not None:(directory/'source-before-names.c').write_bytes(before_names)
            native=compile_c(recipe['compiler'],source,directory/'native')
            if len(native)!=expected['native_bytes'] or sha(native)!=expected['native_sha256']:raise ValueError('native ELF identity mismatch')
            whole,script=package(source)
            script_kind='shell_header' if args.wrapper=='shell' else 'bootstrap'
            if len(whole)!=expected['whole_bytes'] or sha(whole)!=expected['whole_sha256'] or len(script)!=expected[script_kind+'_bytes'] or sha(script)!=expected[script_kind+'_sha256']:
                raise ValueError('complete launcher identity mismatch')
            (directory/'x').write_bytes(whole);(directory/'x').chmod(0o755);(directory/('shell-header.sh' if args.wrapper=='shell' else 'bootstrap.py')).write_bytes(script)
            current=(source,native,whole,script,before_names)
            if first is None:first=current
            elif current!=first:raise ValueError('independent generation did not reproduce bytes')
            row={'attempt':index,'source_bytes':len(source),'source_sha256':sha(source),'native_bytes':len(native),'native_sha256':sha(native),
                 'whole_bytes':len(whole),'whole_sha256':sha(whole),script_kind+'_sha256':sha(script),'preprocessor':observations,
                 'wrapper':args.wrapper,'representation':'source-shell-header' if args.wrapper=='shell' else 'Python-bootstrap',
                 'counter_removal':counters,'shipping_alpha':alpha_metadata,'shipping_storage':storage_metadata,
                 'shipping_scope':scope_metadata,'shipping_members':member_metadata,'shipping_semantics':semantic_metadata,'shipping_input':input_metadata,'shipping_declarations':declaration_metadata,'shipping_hce':hce_metadata,'shipping_types':type_metadata,'shipping_unit_bound':unit_bound_metadata,'shipping_startup':startup_metadata,'shipping_global_names':global_names_metadata,'shipping_capture':capture_metadata,'shipping_policy':policy_metadata,'shipping_material_names':material_names_metadata,'shipping_material_capture':material_capture_metadata,'shipping_move_tt':move_tt_metadata,'shipping_move_tt_names':move_tt_names_metadata,'shipping_material_expressions':expressions_metadata,'shipping_common':common_metadata,
                 'source_before_names':({'bytes':len(before_names),'sha256':sha(before_names),
                                         'path':str(directory/'source-before-names.c')} if before_names is not None else None)}
            if args.dev:
                dev,dev_observations,_,dev_alpha,dev_storage,dev_scope,dev_members,dev_semantics,dev_input,dev_declarations,dev_hce,dev_types,dev_unit_bound,dev_startup,dev_global_names,dev_capture,dev_policy,dev_material_names,dev_material_capture,dev_move_tt,dev_move_tt_names,dev_expressions,dev_common,dev_before_names=generate(directory/'preprocess-dev',True)
                if dev_before_names is not None:raise ValueError('diagnostic source entered fixed names stage')
                if dev_alpha is not None or dev_storage is not None or dev_scope is not None or dev_members is not None or dev_declarations is not None or dev_hce is not None or dev_types is not None or dev_unit_bound is not None or dev_startup is not None or dev_global_names is not None or dev_capture is not None or dev_policy is not None or dev_material_names is not None or dev_material_capture is not None or dev_move_tt is not None or dev_move_tt_names is not None or dev_expressions is not None or dev_common is not None:raise ValueError('diagnostic source entered shipping spelling stage')
                if dev_semantics is None or dev_semantics['stage']!='readable-before-DEV-specialization':raise ValueError('diagnostic semantic stage missing')
                if dev_input is None or dev_input['stage']!='readable-before-DEV-specialization' or dev_input['shipping_relation_checked']:
                    raise ValueError('diagnostic input-profile stage differs')
                if sha(dev)!=expected['dev_source_sha256']:raise ValueError('diagnostic C differs from current semantic recipe')
                dev_command=recipe['dev_compiler']
                dev_native=compile_c(dev_command,dev,directory/'dev');(directory/'dev/main.c').write_bytes(dev)
                if sha(dev_native)!=expected['dev_native_sha256']:raise ValueError('diagnostic ELF differs from current semantic recipe')
                if first_dev is None:first_dev=(dev,dev_native)
                elif first_dev!=(dev,dev_native):raise ValueError('diagnostic bytes did not reproduce')
                row['dev']={'source_sha256':sha(dev),'native_sha256':sha(dev_native),'command':dev_command,'preprocessor':dev_observations,
                            'expected_identity_match':True,'old_DEV_identity_claimed':False,
                            'policy_scope':'unchanged full-F reference diagnostics; not material-model DEV coverage','semantic':dev_semantics,
                            'input_profile':dev_input,'prior_EP_DEV_identity_verified':True}
            report['attempts'].append(row);save()
        (out/'main.c').write_bytes(first[0]);(out/'native').mkdir();(out/'native/x').write_bytes(first[1]);(out/'native/x').chmod(0o755)
        if first[4] is not None:
            (out/'source-before-names.c').write_bytes(first[4])
            report['source_before_names']={'path':str(out/'source-before-names.c'),
                                          'bytes':len(first[4]),'sha256':sha(first[4]),
                                          'scope':'full shipping source immediately before fixed local-name replay; F8 consumer input'}
        (out/'x').write_bytes(first[2]);(out/'x').chmod(0o755);(out/('shell-header.sh' if args.wrapper=='shell' else 'bootstrap.py')).write_bytes(first[3])
        if first_dev:
            (out/'dev').mkdir();(out/'dev/main.c').write_bytes(first_dev[0]);(out/'dev/x').write_bytes(first_dev[1]);(out/'dev/x').chmod(0o755)
        report.update(complete=True,source_reproduced=True,native_reproduced=True,whole_reproduced=True,
                      actual={'command':[str(out/'x')],'native':str(out/'native/x'),'source':str(out/'main.c'),
                              'whole_sha256':sha(first[2]),'native_sha256':sha(first[1]),'source_sha256':sha(first[0])},
                      diagnostic_exact_control=bool(first_dev),
                      diagnostic_identity_scope='current literal DEV source and ELF reproduced; prior EP diagnostic tuple compared exactly, not assumed',under_4096_bytes=len(first[2])<=4096)
        save();print(json.dumps({'complete':True,'out':str(out),'policy':args.policy,'wrapper':args.wrapper,
                                'resources':recipe['profile'],'whole_bytes':len(first[2]),'source_sha256':sha(first[0]),
                                'native_sha256':sha(first[1]),'whole_sha256':sha(first[2]),'diagnostic_exact_control':bool(first_dev)}),flush=True)
    except Exception as error:
        report['error']=repr(error);save();raise


if __name__=='__main__':main()
