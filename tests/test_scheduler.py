"""Scheduler operations use a modeled launchd; never operate the user's jobs."""
import importlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.k = importlib.import_module('runtime.kproto')
        self.temp = tempfile.TemporaryDirectory(prefix='scheduler state ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.home = self.root/'home'
        self.home.mkdir()
        self.ctrl = self.k.Controller(self.root/'state')
        self.runtime = self.ctrl.root/'agent-tool/runtime/kproto.py'
        self.runtime.parent.mkdir(parents=True)
        shutil.copy2(self.k.__file__, self.runtime)
        self.target = self.root/'AGENTS.md'
        self.target.write_bytes(b'original')
        self.k.atomic_write(self.ctrl.state_path, self.k.json_bytes({'target': str(self.target), 'trust': 'signed'}))
        self.loaded = None
        self.calls = []
        self.bootstrap_failure = False
        self.bootout_failure = False
        self.unknown = False
        self.mismatch = False
        for patcher in (mock.patch.object(self.k, '__file__', str(self.runtime)),
                        mock.patch.object(self.k.sys, 'platform', 'darwin'),
                        mock.patch.object(Path, 'home', return_value=self.home),
                        mock.patch.object(self.k, 'launchctl', side_effect=self.launchctl)):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.ctrl.configure(mode='scheduled', source='https://example.test/kproto')
        self.path, self.label = self.ctrl._agent_path()

    def launchctl(self, *args):
        self.calls.append(args)
        code, output = 0, ''
        if args[0] == 'print':
            if len(args[1].split('/')) == 2:
                code = 5 if self.unknown else 0
            elif self.unknown:
                code = 5
            elif self.loaded is None:
                code = 113
            else:
                path, job = self.loaded
                program = '/other/python' if self.mismatch else job['ProgramArguments'][0]
                output = '\tpath = '+str(path)+'\n\tprogram = '+program+'\n\targuments = {\n'
                output += ''.join('\t\t'+value+'\n' for value in job['ProgramArguments'])+'\t}\n'
        elif args[0] == 'bootstrap':
            if self.bootstrap_failure:
                code = 5
            else:
                self.loaded = (Path(args[2]), plistlib.loads(Path(args[2]).read_bytes()))
        elif args[0] == 'bootout':
            if self.bootout_failure:
                code = 5
            else:
                self.loaded = None
        else:
            self.fail('Unexpected launchctl operation: '+str(args))
        return subprocess.CompletedProcess(args, code, output, '')

    def test_register_persists_owned_job_and_verifies_actual_state(self):
        status = self.ctrl.register_scheduler()
        self.assertTrue(status['registered'])
        self.assertTrue(status['persisted'])
        job = plistlib.loads(self.path.read_bytes())
        self.assertEqual({'Minute': 0}, job['StartCalendarInterval'])
        self.assertNotIn('StartInterval', job)
        self.assertEqual(str(self.runtime), job['ProgramArguments'][1])
        self.assertNotIn('EnvironmentVariables', job)
        bootstrap_calls = [call for call in self.calls if call[0] == 'bootstrap']
        self.ctrl.register_scheduler()
        self.assertEqual(bootstrap_calls, [call for call in self.calls if call[0] == 'bootstrap'])
        self.loaded = None
        self.assertFalse(self.ctrl.status()['scheduler']['registered'])
        self.assertTrue(self.ctrl.status()['scheduler']['persisted'])

    def test_register_requires_durable_signed_public_scheduled_installation(self):
        for field, value in [('mode', 'off'), ('token_env', 'PRIVATE_TOKEN'), ('source', '')]:
            original = self.ctrl._config()
            cfg = dict(original, **{field: value})
            self.k.atomic_write(self.ctrl.config_path, self.k.json_bytes(cfg))
            with self.assertRaises(self.k.ProtocolError):
                self.ctrl.register_scheduler()
            self.k.atomic_write(self.ctrl.config_path, self.k.json_bytes(original))
        with mock.patch.object(self.k, '__file__', str(self.root/'clone/runtime/kproto.py')):
            with self.assertRaises(self.k.InputError):
                self.ctrl.register_scheduler()
        self.k.atomic_write(self.ctrl.state_path, self.k.json_bytes({'trust': 'local-snapshot'}))
        with self.assertRaises(self.k.TrustError):
            self.ctrl.register_scheduler()
        self.assertFalse(any(call[0] == 'bootstrap' for call in self.calls))

    def test_file_and_loaded_label_collisions_are_preserved(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'unrelated')
        with self.assertRaises(self.k.ConflictError):
            self.ctrl.register_scheduler()
        self.assertEqual(b'unrelated', self.path.read_bytes())
        self.path.unlink()
        self.loaded = (self.root/'unrelated.plist', {'ProgramArguments': ['/other/python']})
        with self.assertRaises(self.k.ConflictError):
            self.ctrl.register_scheduler()
        self.assertFalse(self.path.exists())
        self.assertFalse(any(call[0] in ('bootstrap', 'bootout') for call in self.calls))

    def test_off_removes_only_owned_live_job_and_generated_output(self):
        self.ctrl.register_scheduler()
        output = Path(self.ctrl._config()['scheduler']['path'])
        self.ctrl.configure(mode='off')
        self.assertIsNone(self.loaded)
        self.assertFalse(self.path.exists())
        self.assertFalse(output.exists())
        self.assertEqual('disabled', self.ctrl.status()['scheduler']['status'])
        self.assertIn(('bootout', 'gui/'+str(os.getuid())+'/'+self.label), self.calls)

    def test_modified_disk_job_and_live_identity_fail_closed(self):
        self.ctrl.register_scheduler()
        data = self.path.read_bytes()
        self.path.write_bytes(data+b'\n')
        with self.assertRaises(self.k.ConflictError):
            self.ctrl.configure(mode='off')
        self.assertEqual(data+b'\n', self.path.read_bytes())
        self.assertEqual('conflict', self.ctrl.status()['scheduler']['status'])
        self.path.write_bytes(data)
        self.mismatch = True
        with self.assertRaises(self.k.ConflictError):
            self.ctrl.unregister_scheduler()
        self.assertTrue(self.path.exists())
        self.assertFalse(any(call[0] == 'bootout' for call in self.calls))

    def test_unknown_status_preserves_job_and_never_reports_absent(self):
        self.ctrl.register_scheduler()
        self.unknown = True
        status = self.ctrl.status()['scheduler']
        self.assertIsNone(status['registered'])
        self.assertEqual('unknown', status['status'])
        with self.assertRaises(self.k.WriteError):
            self.ctrl.unregister_scheduler()
        self.assertTrue(self.path.exists())
        self.assertFalse(any(call[0] == 'bootout' for call in self.calls))

    def test_loaded_argument_collision_does_not_remove_other_command(self):
        self.ctrl.register_scheduler()
        path, job = self.loaded
        other = dict(job, ProgramArguments=job['ProgramArguments'][:-1]+['--other-command'])
        self.loaded = (path, other)
        with self.assertRaises(self.k.ConflictError):
            self.ctrl.configure(mode='off')
        self.assertEqual((path, other), self.loaded)
        self.assertTrue(self.path.exists())
        self.assertFalse(any(call[0] == 'bootout' for call in self.calls))

    def test_bootstrap_failure_rolls_back_owned_plist(self):
        self.bootstrap_failure = True
        with self.assertRaisesRegex(self.k.WriteError, 'owned LaunchAgent was removed'):
            self.ctrl.register_scheduler()
        self.assertFalse(self.path.exists())
        self.assertNotIn('launch_agent', self.ctrl._config()['scheduler'])

    def test_unconfirmed_bootout_preserves_plist_for_retry(self):
        self.ctrl.register_scheduler()
        self.bootout_failure = True
        with self.assertRaises(self.k.WriteError):
            self.ctrl.configure(mode='off')
        self.assertTrue(self.path.exists())
        self.assertEqual('scheduled', self.ctrl._config()['mode'])
        self.bootout_failure = False
        self.ctrl.configure(mode='off')
        self.assertFalse(self.path.exists())

    def test_partial_registration_keeps_explicit_cleanup_route(self):
        original = self.launchctl
        def partial(*args):
            result = original(*args)
            if args[0] == 'bootstrap':
                self.unknown = True
            return result
        with mock.patch.object(self.k, 'launchctl', side_effect=partial):
            with self.assertRaisesRegex(self.k.WriteError, 'cleanup is incomplete'):
                self.ctrl.register_scheduler()
        self.assertTrue(self.path.exists())
        self.assertIn('launch_agent', self.ctrl._config()['scheduler'])
        self.assertIsNone(self.ctrl.status()['scheduler']['registered'])
        self.unknown = False
        self.ctrl.unregister_scheduler()
        self.assertFalse(self.path.exists())

    def test_uninstall_disables_owned_scheduler_and_restores_user_bytes(self):
        bundle = self.root/'bundle'
        for name in self.k.CONTENT_PATHS:
            path = bundle/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({'schema_version':'1.0','version':'0.1.0','rules' if name.startswith('specification/') else 'entries':[{'id':'fixture'}]}) if name.endswith('.json') else 'Content\n')
        self.k.atomic_write(self.ctrl.state_path, self.k.json_bytes({}))
        self.ctrl.install_snapshot(bundle, self.target, '0.1.0')
        state = self.ctrl._state()
        state['trust'] = 'signed'
        self.k.atomic_write(self.ctrl.state_path, self.k.json_bytes(state))
        self.ctrl.register_scheduler()
        self.ctrl.uninstall()
        self.assertEqual(b'original', self.target.read_bytes())
        self.assertFalse(self.path.exists())
        self.assertFalse(self.ctrl.status()['installed'])

    def test_print_nested_identity_does_not_authorize_removal(self):
        self.ctrl.register_scheduler()
        real = self.launchctl
        def nested(*args):
            value = real(*args)
            if args[0] == 'print' and self.loaded:
                value.stdout = value.stdout.replace('\tpath =', '\t\tpath =')
            return value
        with mock.patch.object(self.k, 'launchctl', side_effect=nested):
            with self.assertRaises(self.k.ConflictError):
                self.ctrl.unregister_scheduler()
        self.assertTrue(self.path.exists())

    def test_fifo_job_and_lock_are_rejected_without_blocking(self):
        self.ctrl.register_scheduler()
        self.path.unlink()
        os.mkfifo(self.path)
        self.assertFalse(self.ctrl.status()['scheduler']['persisted'])
        with self.assertRaises(self.k.InputError):
            self.ctrl.unregister_scheduler()
        self.assertFalse(any(call[0] == 'bootout' for call in self.calls))
        other = self.root/'other.plist'
        os.mkfifo(other.parent/('.'+other.name+'.kproto-lock'))
        with self.assertRaises(self.k.ConflictError):
            with self.ctrl._target_lock(other):
                self.fail('FIFO lock must not be accepted')

    def test_status_reports_removed_symlinked_or_writable_plist_conflict(self):
        self.ctrl.register_scheduler()
        data = self.path.read_bytes()
        self.path.chmod(0o666)
        self.assertEqual('conflict', self.ctrl.status()['scheduler']['status'])
        self.path.chmod(0o600)
        self.path.unlink()
        self.assertEqual('conflict', self.ctrl.status()['scheduler']['status'])
        other = self.root/'same-bytes.plist'
        other.write_bytes(data)
        self.path.symlink_to(other)
        self.assertEqual('conflict', self.ctrl.status()['scheduler']['status'])
        with self.assertRaises(self.k.InputError):
            self.ctrl.unregister_scheduler()
        self.assertTrue(self.path.is_symlink())


if __name__ == '__main__':
    unittest.main()
