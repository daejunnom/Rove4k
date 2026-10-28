"""Offline transfer-to-materialization tests; no AWS or engine execution."""
from dataclasses import replace
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

try:
    from . import league_seed_materialize as materializer
    from . import league_seed_layout as layout
    from .league_seed_pipeline import stage_and_inspect
    from .test_cloud_runtime import archive_bytes
    from .test_league_seed_layout import pinned_fixture
    from .test_league_seed_pipeline import transfer_spec_for
    from .test_league_seed_transfer import Client
except ImportError:
    import league_seed_materialize as materializer
    import league_seed_layout as layout
    from league_seed_pipeline import stage_and_inspect
    from test_cloud_runtime import archive_bytes
    from test_league_seed_layout import pinned_fixture
    from test_league_seed_pipeline import transfer_spec_for
    from test_league_seed_transfer import Client


@unittest.skipUnless(os.name == 'posix' and hasattr(os, 'O_NOFOLLOW')
                     and hasattr(os, 'O_DIRECTORY') and hasattr(os, 'pread'),
                     'Linux/POSIX no-follow positioned I/O required')
class MaterializeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.stage_root = base / 'staging'
        self.target_root = base / 'target'
        for path in (self.stage_root, self.target_root):
            path.mkdir(mode=0o700)
            os.chmod(path, 0o700)
        self.fixture, raw, pins = pinned_fixture()
        self.spec = transfer_spec_for(raw, pins['expected_manifest_sha256'], self.fixture.seed['source_origin'])
        self.snapshot = stage_and_inspect(self.spec, Client(data=raw), self.stage_root)
        self.handles = []

    def tearDown(self):
        for handle in reversed(self.handles):
            handle.close()
        self.snapshot.close()
        self.temp.cleanup()

    def materialize(self, spec=None, root=None):
        handle = self.snapshot.materialize(spec or self.spec, root or self.target_root)
        self.handles.append(handle)
        return handle

    def test_original_logical_name_resolves_to_sealed_alias_bytes(self):
        handle = self.materialize()
        self.assertEqual(handle.read_member('origin/A/build/main.c', self.spec), self.fixture.files['origin/A/build/main.c'])
        self.assertEqual(handle.read_member('origin/A/build/native/x', self.spec), self.fixture.files['origin/A/build/native/x'])
        relative = Path(handle.physical_for('origin/A/build/main.c', self.spec))
        self.assertFalse(relative.is_absolute())
        resolved = handle.root_path / relative
        self.assertEqual(resolved, handle.root_path / 'origin/A/__rove_seed_build_v1__/main.c')
        self.assertNotIn('/build/', resolved.as_posix())
        self.assertEqual(resolved.read_bytes(), self.fixture.files['origin/A/build/main.c'])
        self.assertEqual(stat.S_IMODE(resolved.stat().st_mode), self.fixture.seed['members']['origin/A/build/main.c']['mode'])
        handle.verify_for(self.spec)
        scope = handle.scope()
        self.assertTrue(scope['materialized'])
        for claim in ('host_authenticated', 'producer_authenticated', 'go_authorized', 'runtime_qualified'):
            self.assertIs(scope[claim], False)
        self.assertFalse((handle.root_path / 'origin/A/build').exists())
        with self.assertRaises(ValueError):
            handle.read_member('origin/A/unknown', self.spec)

    def test_independent_request_change_is_rejected_before_and_after_creation(self):
        other = replace(self.spec, request=replace(self.spec.request, seed_version_id='other-version'))
        with self.assertRaises(ValueError):
            self.snapshot.materialize(other, self.target_root)
        self.assertEqual(list(self.target_root.iterdir()), [])
        handle = self.materialize()
        with self.assertRaises(ValueError):
            handle.verify_for(other)
        with self.assertRaises(ValueError):
            handle.read_member('origin/A/build/native/x', other)
        with self.assertRaises(ValueError):
            handle.physical_for('origin/A/build', other)

    def test_other_valid_layout_cannot_replace_original_on_individual_reads(self):
        handle = self.materialize()
        alternative, _, _ = pinned_fixture()
        alternative.files['origin/A/build/main.c'] = b'/* different fixture */\n'
        alternative.reseal()
        raw, manifest_sha = archive_bytes(alternative.seed, alternative.files)
        import hashlib
        other = layout.build_layout(raw, expected_archive_sha256=hashlib.sha256(raw).hexdigest(),
                                    expected_archive_bytes=len(raw), expected_manifest_sha256=manifest_sha,
                                    expected_origin=alternative.seed['source_origin'])
        original = handle._layout
        try:
            # The other layout is independently well-formed, and this member's
            # bytes did not change. Its membership alone must not authorize it.
            handle._layout = other
            with self.assertRaises(ValueError):
                handle.read_member('origin/A/build/native/x', self.spec)
            with self.assertRaises(ValueError):
                handle.physical_for('origin/A/build', self.spec)
        finally:
            handle._layout = original

    def test_written_file_content_mode_and_link_changes_are_detected(self):
        handle = self.materialize()
        selected = handle.root_path / handle.physical_for('origin/A/build/main.c', self.spec)
        size = selected.stat().st_size
        selected.write_bytes(b'X' * size)
        with self.assertRaises(ValueError):
            handle.verify_for(self.spec)

        handle = self.materialize()
        selected = handle.root_path / handle.physical_for('origin/A/build/main.c', self.spec)
        os.chmod(selected, 0o777)
        with self.assertRaises(ValueError):
            handle.verify_for(self.spec)

        handle = self.materialize()
        selected = handle.root_path / handle.physical_for('origin/A/build/main.c', self.spec)
        alias = self.target_root / 'hardlink-probe'
        os.link(selected, alias)
        with self.assertRaises(ValueError):
            handle.read_member('origin/A/build/main.c', self.spec)

    def test_swapped_file_or_directory_link_is_not_followed(self):
        handle = self.materialize()
        target = handle.root_path / handle.physical_for('origin/A/build/main.c', self.spec)
        moved = target.with_name('prior')
        target.rename(moved)
        target.symlink_to(moved.name)
        with self.assertRaises((ValueError, OSError)):
            handle.read_member('origin/A/build/main.c', self.spec)
        with self.assertRaises((ValueError, OSError)):
            handle.verify_for(self.spec)

    def test_alias_directory_symlink_replacement_is_not_followed(self):
        handle = self.materialize()
        target = handle.root_path / 'origin/A/__rove_seed_build_v1__'
        moved = target.with_name('previous-dir')
        target.rename(moved)
        target.symlink_to(moved.name, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            handle.read_member('origin/A/build/main.c', self.spec)
        with self.assertRaises((ValueError, OSError)):
            handle.verify_for(self.spec)

    def test_directory_entry_replacement_does_not_retarget_owned_tree(self):
        handle = self.materialize()
        target = handle.root_path
        target.rename(target.with_name(target.name + '-moved'))
        target.symlink_to(self.stage_root, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            handle.read_member('origin/A/build/main.c', self.spec)
        with self.assertRaises((ValueError, OSError)):
            handle.verify_for(self.spec)

    def test_unexpected_file_in_materialized_tree_is_not_accepted(self):
        handle = self.materialize()
        (handle.root_path / 'unexpected.txt').write_text('unexpected', encoding='utf-8')
        with self.assertRaises(ValueError):
            handle.verify_for(self.spec)

    def test_close_preserves_files_and_refuses_further_access(self):
        handle = self.materialize()
        root = handle.root_path
        handle.close()
        self.handles.remove(handle)
        self.assertTrue(root.is_dir())
        with self.assertRaises((ValueError, OSError)):
            handle.read_member('origin/A/build/main.c', self.spec)

    def test_untrusted_or_linked_parent_does_not_receive_output(self):
        linked = self.target_root.parent / 'linked-target'
        linked.symlink_to(self.target_root, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.snapshot.materialize(self.spec, linked)
        self.assertEqual(list(self.target_root.iterdir()), [])
        os.chmod(self.target_root, 0o755)
        with self.assertRaises((ValueError, OSError)):
            self.snapshot.materialize(self.spec, self.target_root)
        self.assertEqual(list(self.target_root.iterdir()), [])

    def test_independent_materializations_do_not_collide(self):
        first = self.materialize()
        second = self.materialize()
        self.assertNotEqual(first.root_path, second.root_path)
        self.assertEqual(first.read_member('origin/A/build/x', self.spec), second.read_member('origin/A/build/x', self.spec))
        self.assertEqual(len(list(self.target_root.iterdir())), 2)

    def test_partial_output_survives_write_failure_without_a_valid_handle(self):
        with mock.patch.object(materializer.os, 'write', side_effect=OSError('injected failure')):
            with self.assertRaises(materializer.MaterializationError) as captured:
                self.snapshot.materialize(self.spec, self.target_root)
        partial = captured.exception.candidate
        self.assertFalse(captured.exception.path_verified)
        self.assertTrue(partial.is_dir())
        self.assertEqual(list(self.target_root.iterdir()), [partial])
        self.assertTrue(any(partial.rglob('*')))

    def test_file_close_failure_still_closes_containing_directory(self):
        real_open, real_close = os.open, os.close
        created = {}
        attempted = []

        def track_open(path, flags, mode=0o777, *, dir_fd=None):
            fd = real_open(path, flags, mode, dir_fd=dir_fd)
            if flags & os.O_CREAT and not created:
                created.update(file=fd, directory=dir_fd)
            return fd

        def fail_first_file_close(fd):
            attempted.append(fd)
            if created.get('file') == fd and not created.get('failed'):
                created['failed'] = True
                real_close(fd)
                raise OSError('injected file close error')
            return real_close(fd)

        with mock.patch.object(materializer.os, 'open', side_effect=track_open), \
                mock.patch.object(materializer.os, 'close', side_effect=fail_first_file_close):
            with self.assertRaises(materializer.MaterializationError) as caught:
                self.snapshot.materialize(self.spec, self.target_root)
        self.assertTrue(created.get('failed'))
        self.assertIn(created['directory'], attempted)
        self.assertTrue(caught.exception.candidate.is_dir())
        self.assertTrue(any('injected file close error' in item for item in caught.exception.close_errors))
        with self.assertRaises(OSError):
            os.fstat(created['directory'])

    def test_handle_close_error_is_not_hidden_by_an_outer_exception_handler(self):
        handle = self.materialize()
        root_fd, parent_fd = handle._root_fd, handle._parent_fd
        real_close, attempted = os.close, []

        def close_then_fail_root(fd):
            attempted.append(fd)
            real_close(fd)
            if fd == root_fd:
                raise OSError('injected root close error')

        try:
            raise ValueError('unrelated outer exception')
        except ValueError:
            with mock.patch.object(materializer.os, 'close', side_effect=close_then_fail_root):
                with self.assertRaises(materializer.DescriptorCloseError) as caught:
                    handle.close()
        self.handles.remove(handle)
        self.assertEqual(attempted, [root_fd, parent_fd])
        self.assertTrue(any('injected root close error' in item for item in caught.exception.close_errors))
        for fd in (root_fd, parent_fd):
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_nested_close_failures_preserve_all_reported_errors(self):
        real_open, real_close = os.open, os.close
        created, failed = {}, set()

        def track_open(path, flags, mode=0o777, *, dir_fd=None):
            fd = real_open(path, flags, mode, dir_fd=dir_fd)
            if isinstance(path, str) and path.startswith('tree-') and dir_fd is not None:
                created.setdefault('root', fd)
            if flags & os.O_CREAT and 'file' not in created:
                created.update(file=fd, directory=dir_fd)
            return fd

        def fail_owned_closes(fd):
            if fd in (created.get('file'), created.get('directory'), created.get('root')) and fd not in failed:
                failed.add(fd)
                real_close(fd)
                raise OSError('injected nested close error ' + str(fd))
            return real_close(fd)

        with mock.patch.object(materializer.os, 'open', side_effect=track_open), \
                mock.patch.object(materializer.os, 'close', side_effect=fail_owned_closes):
            with self.assertRaises(materializer.MaterializationError) as caught:
                self.snapshot.materialize(self.spec, self.target_root)
        self.assertEqual(failed, {created['file'], created['directory'], created['root']})
        errors = caught.exception.close_errors
        self.assertTrue(any('injected nested close error ' + str(created['file']) in error for error in errors))
        self.assertTrue(any('injected nested close error ' + str(created['directory']) in error for error in errors))
        self.assertTrue(any('injected nested close error ' + str(created['root']) in error for error in errors))
        self.assertTrue(caught.exception.candidate.is_dir())


if __name__ == '__main__':
    unittest.main()
