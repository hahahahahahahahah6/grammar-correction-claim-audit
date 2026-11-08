"""Read-only documentation scanning and module-local AST evidence."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import sys

from . import __version__, phrases


def prose(text):
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            lines.append('\n')
        elif fence is None:
            lines.append(line.replace('`', ''))
        else:
            lines.append('\n')
    return ''.join(lines)


def match_phrases(text):
    remaining = text.lower()

    def consume(vocabulary):
        nonlocal remaining
        matches = []
        for phrase in sorted(vocabulary, key=len, reverse=True):
            start = 0
            while True:
                offset = remaining.find(phrase, start)
                if offset < 0:
                    break
                matches.append({'phrase': phrase, 'offset': offset})
                remaining = remaining[:offset] + ' ' * len(phrase) + remaining[offset + len(phrase):]
                start = offset + len(phrase)
        return sorted(matches, key=lambda item: item['offset'])

    negative = consume(phrases.NOGRAMMARCORRECTION)
    return consume(phrases.GRAMMARCORRECTION), negative


def evidence(source):
    """Recognize calls without importing or executing the inspected source."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return False
    shadowed = {node.name for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    imports = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imports[alias.asname or alias.name] = (node.module or '') + '.' + alias.name
    instances = {}
    routes = {}
    for names, method in [(phrases.LANGUAGETOOL_CLASSES, 'correct'),
                          (phrases.GRAMFORMER_CLASSES, 'correct'),
                          (phrases.HAPPY_CLASSES, 'generate_text'),
                          (phrases.GINGER_CLASSES, 'parse')]:
        routes.update({name: method for name in names})

    def resolve(node):
        if isinstance(node, ast.Name):
            if node.id in shadowed:
                return ''
            return imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            base = resolve(node.value)
            if not base or node.attr in shadowed:
                return ''
            return base + '.' + node.attr
        if isinstance(node, (ast.Call, ast.Subscript)):
            return '<expression>'
        return ''

    def instance(node):
        if isinstance(node, ast.Name):
            return instances.get(node.id)
        if isinstance(node, ast.Call):
            name = resolve(node.func).split('.')[-1]
            if name not in shadowed:
                return routes.get(name)
        return None

    def called(node):
        if not isinstance(node, ast.Call):
            return False
        name = resolve(node.func).split('.')[-1]
        if name in phrases.GENERIC_NAMES and name not in shadowed:
            if isinstance(node.func, ast.Attribute):
                return True
            if isinstance(node.func, ast.Name) and node.func.id in imports:
                return True
        if isinstance(node.func, ast.Attribute):
            method = instance(node.func.value)
            if method and node.func.attr == method:
                return True
        return False

    def visit(node):
        if called(node):
            return True
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            if node.value is not None and visit(node.value):
                return True
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            kind = instance(node.value)
            for target in targets:
                if isinstance(target, ast.Name):
                    instances[target.id] = kind
            return False
        return any(visit(child) for child in ast.iter_child_nodes(node))

    return visit(tree)


SKIP = {'.git', '__pycache__', '.venv', 'venv', 'env', '.env', 'virtualenv', '.tox', '.nox'}


def audit(repo, ignore=(), verbose=False):
    root = Path(repo)
    if not root.is_dir():
        raise OSError('Repository is not a directory: ' + str(root))
    documents = []
    has_evidence = False

    def ignored(path):
        return any(path.startswith(prefix) for prefix in ignore)

    def report(message):
        if verbose:
            print(message, file=sys.stderr)

    def walk_error(error):
        raise error

    report('Scope: README.md, docs/**/*.md, tests/**; Python modules recursively')
    for directory, dirs, files in os.walk(root, onerror=walk_error):
        base = Path(directory)
        kept = []
        for name in sorted(dirs):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if name in SKIP or path.is_symlink() or (path / 'pyvenv.cfg').exists() or ignored(rel) or ignored(rel + '/'):
                report('Skipped directory ' + rel)
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            path = base / name
            rel = path.relative_to(root).as_posix()
            if ignored(rel) or path.is_symlink():
                report('Skipped ' + rel)
                continue
            test = 'tests' in path.relative_to(root).parts[:-1]
            doc = rel == 'README.md' or (rel.startswith('docs/') and path.suffix == '.md')
            scoped = doc or (test and path.suffix in {'.md', '.py', '.txt', '.rst'})
            if path.suffix != '.py' and not scoped:
                report('Outside scope ' + rel)
                continue
            source = path.read_text(encoding='utf-8')
            if path.suffix == '.py':
                found = evidence(source)
                has_evidence = has_evidence or found
                report('Python ' + rel + ': evidence=' + str(found))
            if scoped:
                positive, negative = match_phrases(prose(source))
                documents.append((rel, test, positive, negative))
                report('Prose ' + rel + ': positive=' + str(len(positive)) + ', denial=' + str(len(negative)))
    shipped_positive = any(positive for _, test, positive, _ in documents if not test)
    findings = []
    for rel, test, positive, negative in documents:
        candidates = []
        if not has_evidence and (not test or not shipped_positive):
            candidates += [(item, 'documented-grammar-correction-claim-false', 'MEDIUM' if test else 'HIGH', 'Documented capability has no recognized source evidence.') for item in positive]
        if has_evidence and not test:
            candidates += [(item, 'documented-no-grammar-correction-claim-false', 'HIGH', 'Documented denial conflicts with recognized source evidence.') for item in negative]
        for item, rule, severity, message in candidates:
            findings.append(dict(rule=rule, severity=severity, path=rel, phrase=item['phrase'], verdict='FAIL', message=message))
    return findings


class Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, self.prog + ': error: ' + message + '\n')


def main(argv=None):
    parser = Parser(prog='grammar-correction-claim-audit')
    parser.add_argument('--version', action='version', version=__version__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('audit')
    command.add_argument('repo', nargs='?', default='.')
    command.add_argument('--json', action='store_true')
    command.add_argument('--verbose', action='store_true')
    command.add_argument('--ignore', action='append', default=[], metavar='PREFIX')
    command.add_argument('--fail-on', choices=['high', 'medium'], default='high')
    args = parser.parse_args(argv)
    try:
        findings = audit(args.repo, args.ignore, args.verbose)
    except (OSError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        for finding in findings:
            print('{severity} {rule} {path}: {message}'.format(**finding))
    else:
        print('PASS')
    return 2 if any(item['severity'] == 'HIGH' or args.fail_on == 'medium' for item in findings) else 0
