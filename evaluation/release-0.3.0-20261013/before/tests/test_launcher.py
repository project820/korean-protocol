import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class LauncherTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('launcher', ROOT / 'distribution/launcher.py')
        self.launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.launcher)
        self.temp = tempfile.TemporaryDirectory(prefix='korean protocol ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.bundle = self.root / 'preview bundle'
        (self.bundle / 'runtime').mkdir(parents=True)
        shutil.copy2(ROOT / 'runtime/kproto.py', self.bundle / 'runtime/kproto.py')
        self.script = self.bundle / 'start.py'
        shutil.copy2(ROOT / 'distribution/launcher.py', self.script)
        self.state = self.root / 'state'
        self.home = self.root / 'codex home'
        self.home.mkdir()
        self.target = self.home / 'AGENTS.md'
        self.target.write_text('사용자의 기존 지침을 유지한다.\n', encoding='utf-8')
        runtime = self.launcher.load_runtime(self.bundle)
        for name in runtime.CONTENT_PATHS:
            path = self.bundle / name
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.suffix == '.json':
                array = 'rules' if name.startswith('specification/') else 'entries'
                value = {'schema_version': '1.0', 'version': '0.1.0', array: [{'id': 'fixture'}]}
                path.write_text(json.dumps(value), encoding='utf-8')
            else:
                path.write_text('뜻과 조건을 유지한다.\n', encoding='utf-8')
        self.args = ['--host', 'codex', '--state-dir', str(self.state), '--codex-home', str(self.home)]

    def run_main(self, answers, result=0):
        output = io.StringIO()
        with mock.patch.object(self.launcher, '__file__', str(self.script)), \
                mock.patch('builtins.input', side_effect=answers), \
                mock.patch.object(self.launcher.subprocess, 'run', return_value=mock.Mock(returncode=result, stderr='')) as child, \
                redirect_stdout(output):
            code = self.launcher.main(self.args)
        return code, output.getvalue(), child

    def test_decline_install_and_removal_does_not_write_or_spawn(self):
        code, output, child = self.run_main(['1', 'n', '3', 'n', '0'])
        self.assertEqual(0, code)
        child.assert_not_called()
        self.assertFalse(self.state.exists())
        self.assertEqual('사용자의 기존 지침을 유지한다.\n', self.target.read_text())
        self.assertIn(str(self.target), output)
        self.assertIn('서명 없는 미리보기', output)
        self.assertIn('오프라인', output)
        self.assertIn('자동 업데이트', output)

    def test_install_dispatch_uses_interpreter_absolute_paths_and_offline_options(self):
        code, output, child = self.run_main(['1', 'y', '0'])
        self.assertEqual(0, code)
        command = child.call_args.args[0]
        self.assertEqual(sys.executable, command[0])
        self.assertEqual(str(self.bundle / 'runtime/kproto.py'), command[1])
        self.assertIn('--local-snapshot', command)
        self.assertEqual('user', command[command.index('--scope') + 1])
        self.assertEqual('codex', command[command.index('--host') + 1])
        self.assertEqual('off', command[command.index('--autoupdate') + 1])
        self.assertEqual('0.2.0', command[command.index('--version') + 1])
        self.assertEqual(str(self.bundle), command[command.index('--bundle') + 1])
        self.assertFalse(child.call_args.kwargs.get('shell', False))

    def test_nonzero_runtime_exit_is_shown_and_returned(self):
        code, output, child = self.run_main(['1', 'y'], result=7)
        self.assertEqual(7, code)
        self.assertIn('7', output)
        child.assert_called_once()

    def test_status_does_not_create_state(self):
        code, output, child = self.run_main(['2', '0'])
        self.assertEqual(0, code)
        self.assertFalse(self.state.exists())
        child.assert_not_called()
        self.assertIn('미설치', output)

    def test_interrupted_or_closed_input_has_no_traceback_or_writes(self):
        for exception, expected in ((EOFError(), 0), (KeyboardInterrupt(), 130)):
            with self.subTest(exception=type(exception).__name__):
                code, output, child = self.run_main([exception])
                self.assertEqual(expected, code)
                self.assertNotIn('Traceback', output)
                self.assertFalse(self.state.exists())
                child.assert_not_called()

    def test_target_preview_uses_codex_home_and_nonempty_override(self):
        override = self.home / 'AGENTS.override.md'
        override.write_text('별도 지침이다.\n')
        args = ['--host', 'codex', '--state-dir', str(self.state)]
        with mock.patch.dict(os.environ, {'CODEX_HOME': str(self.home)}):
            with mock.patch.object(self.launcher, '__file__', str(self.script)), \
                    mock.patch('builtins.input', side_effect=['0']), redirect_stdout(io.StringIO()) as output:
                self.assertEqual(0, self.launcher.main(args))
        self.assertIn(str(override), output.getvalue())

    def test_blank_override_uses_agents_md(self):
        (self.home / 'AGENTS.override.md').write_text(' \n')
        code, output, child = self.run_main(['0'])
        self.assertEqual(0, code)
        self.assertIn('Codex 사용자 범위 대상: ' + str(self.target), output)
        child.assert_not_called()

    def test_uninstall_shows_recorded_target_and_delegates_without_reselecting_home(self):
        self.state.mkdir(mode=0o700)
        recorded = self.root / 'previous home/AGENTS.override.md'
        (self.state / 'state.json').write_text(json.dumps({'target': str(recorded), 'version': '0.1.0', 'trust': 'signed'}))
        code, output, child = self.run_main(['3', 'y', '0'])
        self.assertEqual(0, code)
        self.assertIn('제거 대상: ' + str(recorded), output)
        self.assertIn('설치 기록의 신뢰 상태: signed', output)
        self.assertEqual([sys.executable, str(self.bundle / 'runtime/kproto.py'),
                          '--state-dir', str(self.state), 'uninstall'], child.call_args.args[0])

    def test_real_decline_does_not_create_state_or_bundle_bytecode(self):
        original = self.target.read_bytes()
        before = sorted(str(path.relative_to(self.bundle)) for path in self.bundle.rglob('*'))
        result = subprocess.run([sys.executable, str(self.script), *self.args],
                                input='1\nn\n3\nn\n0\n', cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(self.state.exists())
        self.assertEqual(original, self.target.read_bytes())
        self.assertEqual(before, sorted(str(path.relative_to(self.bundle)) for path in self.bundle.rglob('*')))

    def test_invalid_state_returns_runtime_error_without_mutation(self):
        self.state.mkdir(mode=0o700)
        state_file = self.state / 'state.json'
        state_file.write_text('[]')
        before = state_file.read_bytes()
        code, output, child = self.run_main([])
        self.assertEqual(2, code)
        self.assertIn('실행기 오류', output)
        self.assertEqual(before, state_file.read_bytes())
        child.assert_not_called()

    def test_root_resolution_uses_script_location_and_source_parent_only(self):
        self.assertEqual(self.bundle, self.launcher.find_bundle(self.script))
        source = self.bundle / 'distribution/launcher.py'
        self.assertEqual(self.bundle, self.launcher.find_bundle(source))
        with self.assertRaises(FileNotFoundError):
            self.launcher.find_bundle(self.root / 'unrelated/start.py')

    def test_default_state_uses_runtime_platform_parent_and_codex_specific_name(self):
        runtime = self.launcher.load_runtime(self.bundle)
        self.assertEqual(runtime.default_state_dir().parent / 'korean-protocol-codex',
                         self.launcher.default_state_dir(runtime))

    def test_help_does_not_load_runtime_or_write(self):
        result = subprocess.run([sys.executable, str(self.script), '--help'], cwd=self.root,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('--codex-home', result.stdout)
        self.assertIn('--claude-home', result.stdout)
        self.assertIn('--host', result.stdout)
        self.assertFalse(self.state.exists())

    def test_first_host_choice_exit_or_closed_input_creates_no_files(self):
        self.args = []
        for answers, expected in ((['0'],0),([EOFError()],0),([KeyboardInterrupt()],130)):
            with self.subTest(answers=answers):
                before=sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*'))
                code,output,child=self.run_main(answers)
                self.assertEqual(expected,code)
                self.assertIn('1. Codex',output)
                self.assertIn('2. Claude Code',output)
                self.assertNotIn('사용자 범위 대상',output)
                child.assert_not_called()
                self.assertEqual(before,sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*')))

    def test_first_host_choice_routes_to_claude_install_with_separate_default_state(self):
        home=self.root/'claude home'
        self.args=['--claude-home',str(home)]
        with mock.patch.dict(os.environ,{'HOME':str(self.root),'CLAUDE_CONFIG_DIR':str(self.root/'env claude')}):
            code,output,child=self.run_main(['invalid','2','1','y','0'])
        self.assertEqual(0,code)
        self.assertIn('Claude Code 사용자 범위 대상: '+str(home/'rules/korean-protocol.md'),output)
        command=child.call_args.args[0]
        self.assertEqual('claude-code',command[command.index('--host')+1])
        self.assertEqual(str(home),command[command.index('--claude-home')+1])
        self.assertEqual('0.2.0',command[command.index('--version')+1])
        self.assertTrue(command[command.index('--state-dir')+1].endswith('korean-protocol-claude-code'))
        self.assertNotIn('--codex-home',command)
        self.assertFalse(home.exists())

    def test_first_host_choice_routes_to_codex_menu_without_writes(self):
        self.args=['--state-dir',str(self.state),'--codex-home',str(self.home)]
        code,output,child=self.run_main(['1','0'])
        self.assertEqual(0,code)
        self.assertIn('Codex 사용자 범위 대상: '+str(self.target),output)
        self.assertFalse(self.state.exists())
        child.assert_not_called()

    def test_explicit_claude_status_uses_config_environment_without_writes(self):
        home=self.root/'env claude'
        self.args=['--host','claude-code','--state-dir',str(self.state)]
        with mock.patch.dict(os.environ,{'CLAUDE_CONFIG_DIR':str(home)}):
            code,output,child=self.run_main(['2','0'])
        self.assertEqual(0,code)
        self.assertIn(str(home/'rules/korean-protocol.md'),output)
        self.assertFalse(home.exists())
        self.assertFalse(self.state.exists())
        child.assert_not_called()

    def test_real_first_choice_decline_does_not_create_bytecode_or_state(self):
        before=sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*'))
        result=subprocess.run([sys.executable,'-B',str(self.script)],input='0\n',cwd=self.root,
                              env=dict(os.environ,HOME=str(self.root)),capture_output=True,text=True,timeout=10)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('2. Claude Code',result.stdout)
        self.assertEqual(before,sorted(str(path.relative_to(self.root)) for path in self.root.rglob('*')))

    def test_real_claude_install_reinstall_status_and_uninstall_preserve_rules(self):
        home=self.root/'isolated HOME'
        home.mkdir()
        claude=home/'.claude'
        (claude/'rules').mkdir(parents=True)
        target=claude/'rules/korean-protocol.md'
        original=b'User rule\r\n'
        target.write_bytes(original)
        (claude/'CLAUDE.md').write_bytes(b'User main instructions\n')
        (claude/'rules/other.md').write_bytes(b'Other rule\n')
        args=['--host','claude-code','--state-dir',str(self.state)]
        environment=dict(os.environ,HOME=str(home))
        environment.pop('CLAUDE_CONFIG_DIR',None)
        result=subprocess.run([sys.executable,str(self.script),*args],input='1\ny\n1\ny\n2\n3\ny\n0\n',cwd=self.root,
                              env=environment,capture_output=True,text=True,timeout=20)
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertIn('설치됨',result.stdout)
        self.assertIn(str(target),result.stdout)
        self.assertEqual(original,target.read_bytes())
        self.assertEqual(b'User main instructions\n',(claude/'CLAUDE.md').read_bytes())
        self.assertEqual(b'Other rule\n',(claude/'rules/other.md').read_bytes())
        self.assertEqual('off',json.loads((self.state/'config.json').read_text())['mode'])

    def test_real_install_status_uninstall_from_path_with_spaces_and_other_cwd(self):
        original = self.target.read_bytes()
        result = subprocess.run([sys.executable, str(self.script), *self.args],
                                input='1\ny\n2\n3\ny\n0\n', cwd=self.root,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertIn('설치됨', result.stdout)
        self.assertEqual(original, self.target.read_bytes())
        config = json.loads((self.state / 'config.json').read_text())
        self.assertEqual('off', config['mode'])


if __name__ == '__main__':
    unittest.main()
