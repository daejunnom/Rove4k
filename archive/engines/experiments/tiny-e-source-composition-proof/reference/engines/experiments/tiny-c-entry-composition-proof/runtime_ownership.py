import subprocess
import signal

def run_owned_verifier(command, out, report, save, timeout=35, grace=5):
    """Own the verifier from Popen through every save, wait and exception."""
    with (out / 'verifier.stdout').open('wb') as stdout, (out / 'verifier.stderr').open('wb') as stderr:
        proc = subprocess.Popen(command, cwd=out, stdout=stdout, stderr=stderr)
        try:
            report['owned_subprocess'] = {'pid': proc.pid, 'command': command, 'terminal': False}
            save()
            status = proc.wait(timeout=timeout)
            report['owned_subprocess'].update(returncode=proc.returncode, terminal=True)
            save()
            return status, proc.pid
        except BaseException as original:
            row = report.get('owned_subprocess')
            if not isinstance(row, dict):
                row = {'pid': proc.pid, 'command': command}
                report['owned_subprocess'] = row
            report['settled'] = False
            report['wrapper_settlement'] = 'unproven after owned verifier failure'
            row['exception'] = repr(original)
            def preserve():
                # A failed receipt write must not mask the initiating exception
                # or prevent ownership cleanup of the already-created process.
                try:
                    save()
                except BaseException:
                    pass
            preserve()
            if proc.poll() is None:
                try:
                    proc.send_signal(signal.SIGINT)
                    row['interrupt_sent'] = True
                except BaseException as error:
                    row['interrupt_error'] = repr(error)
                try:
                    proc.wait(timeout=grace)
                except BaseException as error:
                    row['grace_wait_error'] = repr(error)
                    row['forced_kill'] = True
                    report['unsettled_failure'] = True
                    preserve()  # Record uncertainty BEFORE forced kill/reap.
                    try:
                        proc.kill()
                    except BaseException as kill_error:
                        row['kill_error'] = repr(kill_error)
                    try:
                        proc.wait(timeout=grace)
                    except BaseException as reap_error:
                        row['reap_error'] = repr(reap_error)
            row.update(returncode=proc.poll(), terminal=proc.returncode is not None)
            if not row['terminal']:
                report['unsettled_failure'] = True
            preserve()
            raise

