"""Prove native operations accept only green identical code, never release fallback."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('operation_source',Path(__file__).resolve().parents[1]/'verify-operation-source.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def isolated_git_environment():
    """Environment for fixture git commands. Inherited GIT_* variables, such as GIT_DIR from a
    hook, would otherwise redirect `git -C <temporary> init/config` into the caller's repository."""
    return {key:value for key,value in os.environ.items() if not key.upper().startswith('GIT_')}


class OperationSourceTests(unittest.TestCase):
    current, parent = 'a'*40, 'b'*40

    def setUp(self):
        environment=patch.dict(os.environ,isolated_git_environment(),clear=True)
        environment.start()
        self.addCleanup(environment.stop)

    def success(self, sha):
        return {'outcome':'success','selected':{'head_sha':sha,'id':42,'run_attempt':1}}

    def test_exact_green_source_needs_no_fallback(self):
        with patch.object(module,'documentation_diff') as difference:
            value=module.select_source([self.current],query=self.success,unchanged=difference)
        self.assertEqual(self.current,value['validated_code_sha'])
        self.assertEqual(0,value['documentation_commits'])
        difference.assert_not_called()

    def test_docs_only_missing_run_reuses_verified_parent(self):
        value=module.select_source([self.current,self.parent],
            query=lambda sha:self.success(sha) if sha==self.parent else {'outcome':'no_eligible_run'},
            unchanged=lambda parent,child:True)
        self.assertEqual(self.parent,value['validated_code_sha'])
        self.assertEqual(self.current,value['operation_source_sha'])
        self.assertEqual(1,value['documentation_commits'])

    def test_failed_pending_changed_and_invalid_ci_cannot_be_hidden(self):
        for outcome in ('failed','waiting','selected_run_changed','selected_attempt_changed','invalid_provenance'):
            with self.subTest(outcome=outcome), self.assertRaises(ValueError):
                module.select_source([self.current,self.parent],query=lambda sha:{'outcome':outcome},unchanged=lambda *_:True)

    def test_code_change_or_missing_history_cannot_fall_back(self):
        for history in ([self.current],[self.current,self.parent]):
            with self.subTest(history=history), self.assertRaises(ValueError):
                module.select_source(history,query=lambda sha:{'outcome':'no_eligible_run'},unchanged=lambda *_:False)

    def test_mismatched_success_and_excess_history_fail(self):
        with self.assertRaises(ValueError):
            module.select_source([self.current],query=lambda sha:self.success(self.parent))
        for history in ([],['bad'],[self.current]*102):
            with self.subTest(count=len(history)), self.assertRaises(ValueError):
                module.select_source(history,query=self.success)
        with self.assertRaises(ValueError):
            module.select_source([self.current]*101,query=lambda sha:{'outcome':'no_eligible_run'},unchanged=lambda *_:True)

    def test_only_ordinary_documentation_paths_qualify(self):
        for path in ('AGENTS.md','README.md','docs/Test.md','Plans/Delivery.md','Deployment/LocalSingleNode/AgentSetup.md','docs/Guide.mdx'):
            with self.subTest(path=path):
                self.assertTrue(module.ordinary_documentation(path))
        for path in ('Scripts/source.md','.github/workflows/source.md','Deployment/LocalSingleNode/ansible/template.md',
                     'Deployment/LocalSingleNode/Scripts/Tests/fixture.md','docs/../build.md','/docs/Guide.md',
                     'docs\\Guide.md','docs/config.yml','GrumPlates/source.md','config.md'):
            with self.subTest(path=path):
                self.assertFalse(module.ordinary_documentation(path))

    def repository(self, directory):
        def git(*args):
            return subprocess.check_output(['git','-C',str(directory),*args],stderr=subprocess.DEVNULL,text=True,
                                            env=isolated_git_environment()).strip()
        git('init','-q')
        git('config','user.name','Fixture')
        git('config','user.email','fixture@example.invalid')
        (directory/'docs').mkdir()
        (directory/'docs/Guide.md').write_text('Initial documentation\n')
        (directory/'source.py').write_text('source = 1\n')
        git('add','docs/Guide.md','source.py')
        git('commit','-qm','Fixture baseline')
        return git

    def test_fixture_repository_ignores_inherited_git_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            sentinel,work=root/'sentinel',root/'work'
            sentinel.mkdir()
            work.mkdir()
            subprocess.run(['git','init','-q',str(sentinel)],check=True,env=isolated_git_environment())
            before=(sentinel/'.git'/'config').read_text()
            with patch.dict(os.environ,{'GIT_DIR':str(sentinel/'.git'),'GIT_WORK_TREE':str(sentinel)}):
                git=self.repository(work)
            self.assertEqual(before,(sentinel/'.git'/'config').read_text())
            self.assertTrue((work/'.git').is_dir())
            self.assertEqual('Fixture',git('config','user.name'))

    def test_real_complete_diff_checks_both_rename_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)
            git=self.repository(directory)
            parent=git('rev-parse','HEAD')
            git('mv','docs/Guide.md','docs/Renamed.mdx')
            git('commit','-qm','Rename ordinary documentation')
            child=git('rev-parse','HEAD')
            with patch.object(module,'ROOT',directory):
                self.assertTrue(module.documentation_diff(parent,child))
            git('mv','source.py','docs/Source.md')
            git('commit','-qm','Disguised source rename')
            with patch.object(module,'ROOT',directory):
                self.assertFalse(module.documentation_diff(child,git('rev-parse','HEAD')))

    def test_real_diff_rejects_executable_symlink_and_code(self):
        for kind in ('executable','symlink','code','binary'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                directory=Path(temporary)
                git=self.repository(directory)
                parent=git('rev-parse','HEAD')
                if kind=='executable':
                    git('update-index','--chmod=+x','docs/Guide.md')
                elif kind=='symlink':
                    (directory/'docs/Guide.md').unlink()
                    (directory/'docs/Guide.md').symlink_to('../source.py')
                    git('add','docs/Guide.md')
                elif kind=='binary':
                    (directory/'docs/Guide.md').write_bytes(b'not\0ordinary documentation')
                    git('add','docs/Guide.md')
                else:
                    (directory/'source.py').write_text('source = 2\n')
                    git('add','source.py')
                git('commit','-qm','Unsafe fallback fixture')
                with patch.object(module,'ROOT',directory):
                    self.assertFalse(module.documentation_diff(parent,git('rev-parse','HEAD')))

    def test_cli_requires_pinned_full_main_checkout(self):
        env={'GITHUB_SHA':self.current,'GITHUB_REF':'refs/heads/main'}
        for ref,head,shallow in (('refs/heads/feature',self.current,'false'),('refs/heads/main',self.parent,'false'),('refs/heads/main',self.current,'true')):
            with patch.dict(os.environ,{**env,'GITHUB_REF':ref},clear=True), patch.object(module,'git',side_effect=[head,shallow]), self.assertRaises(ValueError):
                module.main()

    def test_release_consumers_retain_exact_provenance(self):
        root=Path(__file__).resolve().parents[4]
        for filename in ('cd-localsinglenode.yml','cd-localcluster.yml','cd-cloud.yml'):
            text=(root/'.github/workflows'/filename).read_text()
            self.assertNotIn('verify-operation-source.py',text)
            self.assertIn('find-successful-ci-run',text)


if __name__=='__main__':
    unittest.main()
