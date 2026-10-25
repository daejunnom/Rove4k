"""Existing compiler-owner lifetime fixtures on the explicit fold experiment."""
import os
from pathlib import Path
import signal
import sys
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'scripts'))
import test_compiler_group as baseline
import fold


class SourceContracts(unittest.TestCase):
    def test_complete_inverse_and_closed_source(self):
        prepared=baseline.prepared()
        selected,_=baseline.group.compact_cleanup(prepared)
        private,_=baseline.group.compact_private_owner(selected)
        for variant in('demorgan','short-or'):
            candidate,proof=fold.transform_bootstrap(private,owner=baseline.group,variant=variant)
            self.assertEqual(fold.restore_bootstrap(candidate,proof),private)
            self.assertTrue(proof['outside_cleanup_AST_equal'])
            self.assertIn(repr(baseline.SOURCE).encode(),candidate)
            self.assertEqual(candidate.count(b'd=None;raise SystemExit(125)'),1)
            with self.assertRaises(ValueError):fold.transform_bootstrap(candidate,owner=baseline.group)
            with self.assertRaises(ValueError):fold.restore_bootstrap(candidate+b'\n',proof)

    def test_unknown_policy_helper_and_scaffold_are_rejected(self):
        prepared=baseline.prepared()
        for termination,wait in(('grace',True),('kill',False)):
            selected,_=baseline.group.compact_cleanup(prepared,termination=termination,wait=wait)
            selected,_=baseline.group.compact_private_owner(selected,termination=termination,wait=wait)
            with self.assertRaises(ValueError):fold.transform_bootstrap(selected,owner=baseline.group)
        selected,_=baseline.group.compact_cleanup(prepared)
        selected,_=baseline.group.compact_private_owner(selected)
        for raw in(selected+b'pass\n',selected.replace(b'def k(s):',b'def other(s):',1),
                   selected.replace(b"'/proc'",b"'/tmp'",1)):
            with self.assertRaises(ValueError):fold.transform_bootstrap(raw,owner=baseline.group)
        with self.assertRaises(ValueError):fold.transform_bootstrap(selected,owner=baseline.group,variant='other')


class FoldRuntimeContracts(baseline.RuntimeContracts):
    private_owner=True
    variant='demorgan'

    def fixture(self,*args,**kwargs):
        prepare=baseline.group.compact_private_owner
        def folded(script,**choices):
            selected,prior=prepare(script,**choices)
            self.assertFalse(choices['wait']);self.assertEqual(choices['termination'],'grace')
            result,proof=fold.transform_bootstrap(selected,owner=baseline.group,variant=self.variant)
            self.assertEqual(fold.restore_bootstrap(result,proof),selected)
            return result,{'prior':prior,'fold':proof}
        with patch.object(baseline.group,'compact_private_owner',folded):
            return super().fixture(*args,**kwargs)

    def test_waitable_leader_still_drains_its_surviving_grandchild_before_reap(self):
        root=self.root/'grandchild';root.mkdir();ready=root/'child-ready';leader=root/'leader'
        child=root/'child.py'
        child.write_text('import os,time\nfrom pathlib import Path\nPath('+repr(str(ready))+').write_text(str(os.getpid()))\nwhile True:time.sleep(30)\n')
        body='subprocess.Popen([sys.executable,'+repr(str(child))+'])\nwhile not Path('+repr(str(ready))+').exists():time.sleep(.005)\nPath('+repr(str(leader))+').write_text(str(os.getpid()))\n'
        _,scratch,rows,output,_,_=self.fixture('leader-first',body)
        self.assertEqual(output,b'argument:env:input\n');pid=int(ready.read_text())
        self.assertTrue(any(r['event']=='signal_group'and r['waitable']and any(m['pid']==pid and m['state']!='Z'for m in r['members'])for r in rows))
        reap=next(r for r in rows if r['event']=='product_reap')
        self.assertTrue(reap['waitable']);self.assertTrue(all(m['pid']==reap['pid']or m['state']=='Z'for m in reap['members']))
        self.assertEqual(list(scratch.iterdir()),[])

    def test_cancel_keeps_parent_status_and_distinguishes_grace_from_kill(self):
        root=self.root/'cancel-grace'
        body='def stop(s,f):\n Path('+repr(str(root/'term'))+').write_text(str(s))\n raise SystemExit(0)\nsignal.signal(signal.SIGTERM,stop)\nPath('+repr(str(root/'ready'))+').write_text("ready")\nwhile True:time.sleep(30)\n'
        _,scratch,rows,_,_,marker=self.fixture('cancel-grace',body,cancel=True)
        self.assertTrue(marker.exists());self.assertEqual(list(scratch.iterdir()),[])
        self.assertTrue(any(r['event']=='primary'and r['code']==143 for r in rows))

    def test_compiler_self_signals_preserve_original_negative_status(self):
        for signum in(9,15):
            body='signal.signal(signal.SIGTERM,signal.SIG_DFL)\nos.kill(os.getpid(),'+str(signum)+')\n'
            _,scratch,rows,_,_,_=self.fixture('compiler-signal-'+str(signum),body,expected=256-signum)
            primary=next(r for r in rows if r['event']=='primary')
            self.assertEqual(primary['kind'],'SystemExit');self.assertEqual(primary['code'],-signum)
            self.assertEqual(list(scratch.iterdir()),[])


class ShortOrRuntimeContracts(FoldRuntimeContracts):
    variant='short-or'


if __name__=='__main__':unittest.main()
