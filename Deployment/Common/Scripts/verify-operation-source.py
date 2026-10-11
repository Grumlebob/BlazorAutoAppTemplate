"""Require green exact-code main CI while allowing reviewed ordinary documentation descendants.

This gate is only for native setup and maintenance. Release consumers still require
the exact release source, main-push CI, artifact, manifest and registry digest.
"""
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
FINDER = Path(__file__).parent / 'Component/lib/find-successful-ci-run.py'


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode('utf-8').strip()


def ordinary_documentation(path):
    value = PurePosixPath(path)
    if (value.is_absolute() or '\\' in path or any(part in ('.','..') for part in value.parts)
            or value.suffix not in ('.md','.mdx')):
        return False
    if any(part.casefold() in ('scripts','tests','fixtures','ansible','compose','inventory','workflows') for part in value.parts[:-1]):
        return False
    if value.name in ('README.md','AGENTS.md'):
        return True
    if len(value.parts) == 1:
        return value.name in ('CONTRIBUTING.md','SECURITY.md','LICENSE.md','CHANGELOG.md')
    return value.parts[0] in ('docs','Plans','Deployment')


def documentation_diff(parent, child):
    # No rename inference: both the deleted and added names/modes are checked.
    raw = subprocess.check_output(['git','diff','--raw','--no-abbrev','--no-renames','-z',parent,child,'--'],cwd=ROOT)
    fields = raw.decode('utf-8').split('\0')
    if fields[-1] == '':
        fields.pop()
    if len(fields) % 2:
        return False
    for index in range(0,len(fields),2):
        metadata, path = fields[index:index+2]
        values = metadata.split()
        if (len(values) != 5 or not values[0].startswith(':')
                or values[0][1:] not in ('000000','100644') or values[1] not in ('000000','100644')
                or values[4] not in ('A','M','D') or not ordinary_documentation(path)):
            return False
        for mode, identity in zip((values[0][1:],values[1]),values[2:4]):
            if mode == '000000':
                continue
            if not re.fullmatch('[0-9a-f]{40}',identity) or int(git('cat-file','-s',identity)) > 2*1024*1024:
                return False
            content = subprocess.check_output(['git','cat-file','blob',identity],cwd=ROOT).decode('utf-8')
            if '\0' in content:
                return False
    return True


def exact_ci(sha):
    query = subprocess.run([sys.executable,str(FINDER),'--target-sha',sha,'--json'],capture_output=True,text=True)
    value = json.loads(query.stdout)
    if not isinstance(value,dict) or (query.returncode == 0) != (value.get('outcome') == 'success'):
        raise ValueError('CI gate response is malformed')
    return value


def select_source(history, query=exact_ci, unchanged=documentation_diff):
    if not history or len(history) > 101 or any(not re.fullmatch('[0-9a-f]{40}',sha) for sha in history):
        raise ValueError('Require bounded complete first-parent source history')
    for index, sha in enumerate(history[:100]):
        result = query(sha)
        if result.get('outcome') == 'success':
            if result.get('selected',{}).get('head_sha') != sha:
                raise ValueError('Successful CI does not match the verified code source')
            return {**result,'operation_source_sha':history[0],'validated_code_sha':sha,'documentation_commits':index}
        # An actual failed, pending or changing current run must never be hidden.
        if result.get('outcome') != 'no_eligible_run':
            raise ValueError('Current eligible CI has not passed; refusing ancestor fallback')
        if index+1 >= len(history) or not unchanged(history[index+1],sha):
            raise ValueError('Unvalidated code/configuration change or incomplete history')
    raise ValueError('Documentation history exceeds the safe bound')


def main():
    target = os.environ.get('GITHUB_SHA','')
    if (os.environ.get('GITHUB_REF') != 'refs/heads/main' or not re.fullmatch('[0-9a-f]{40}',target)
            or os.environ.get('GIT_DIR') or os.environ.get('GIT_WORK_TREE')
            or git('rev-parse','HEAD') != target or git('rev-parse','--is-shallow-repository') != 'false'):
        raise ValueError('Require the pinned trusted main checkout with full history')
    history = git('rev-list','--first-parent','--max-count=101',target).splitlines()
    result = select_source(history)
    print(json.dumps(result,sort_keys=True,separators=(',',':')))
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError,OSError,KeyError,TypeError,subprocess.SubprocessError):
        print('Operation source CI gate failed; no release or unvalidated code fallback is permitted.',file=sys.stderr)
        sys.exit(1)
