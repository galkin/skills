#!/usr/bin/env python3
"""Resumable EPUB translation: inspect, verify, record reviews, and build."""
from __future__ import annotations

import argparse
from hashlib import sha256
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from zipfile import BadZipFile

from epubio import Source, inventory, package, render, tag, validate, visible

SKILL = Path(__file__).resolve().parent.parent


def natural_key(value):
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r'(\d+)', value)]


def md_files(directory):
    return sorted((p for p in directory.glob('*.md') if re.match(r'^\d+-', p.name)), key=lambda p: natural_key(p.name))


def tool(name):
    found = shutil.which(name)
    local = Path.home() / '.local/bin' / name
    if found:
        return found
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    raise ValueError(f'Missing {name}; run scripts/bootstrap.sh')


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def tree_hashes(directory):
    return {str(p.relative_to(directory)): digest(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else (default if default is not None else {})


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
        temp = Path(f.name)
    temp.replace(path)


# Conservative, deliberately non-exhaustive BCP-47-like tag: letters/digits in hyphen-separated
# subtags (en, ru, es, pt-BR, zh-Hans, en-US). Rejects path/filesystem characters (/, \, ..) and
# whitespace so a language code can never be mistaken for a path segment.
LANGUAGE_CODE_RE = re.compile(r'^[A-Za-z0-9]+(-[A-Za-z0-9]+)*$')


def validate_language(label, lang):
    if not isinstance(lang, dict):
        raise ValueError(f'translation.json {label} must be an object')
    code, name = lang.get('code'), lang.get('name')
    if not isinstance(code, str) or not isinstance(name, str):
        raise ValueError(f'translation.json {label} requires string code and name')
    code, name = code.strip(), name.strip()
    if not code or not name:
        raise ValueError(f'translation.json {label} requires non-empty code and name')
    if not LANGUAGE_CODE_RE.match(code):
        raise ValueError(f'translation.json {label} code must be a safe BCP-47-like tag (letters, '
                          f'digits and hyphens only, e.g. en, pt-BR, zh-Hans): {lang.get("code")!r}')
    return {'code': code, 'name': name}


def validate_translation_config(data):
    if not isinstance(data, dict):
        raise ValueError('translation.json must be a JSON object')
    source = validate_language('source_language', data.get('source_language'))
    target = validate_language('target_language', data.get('target_language'))
    if source['code'].casefold() == target['code'].casefold():
        raise ValueError('translation.json source_language and target_language codes must differ')
    return {'source_language': source, 'target_language': target}


def translation_config(root):
    """Single source of truth for the configured source/target languages. See init/configure."""
    path = root / 'translation.json'
    if not path.exists():
        raise ValueError('Missing translation.json; run configure or init with language options')
    return validate_translation_config(load(path))


def describe_translation(config):
    source, target = config['source_language'], config['target_language']
    return f"Translation: {source['name']} ({source['code']}) -> {target['name']} ({target['code']})"


def selected(root, names):
    available = [p.stem for p in sorted((root / 'source').glob('*.epub'), key=lambda p: natural_key(p.name))]
    if any(n not in available for n in names):
        raise ValueError('Unknown source book: ' + ', '.join(n for n in names if n not in available))
    return sorted(set(names), key=natural_key) if names else available


def book_paths(root, name):
    book = root / 'books' / name
    return book, book / 'en', book / 'ru', root / 'source' / (name + '.epub')


def snapshot(root, name):
    # 'english_files' mirrors the en/ directory name; it holds source files in any language.
    book, en, _, source = book_paths(root, name)
    return {'source_sha256': digest(source), 'english_files': tree_hashes(en)}


def baseline_issues(root, name, required=True):
    book, _, _, _ = book_paths(root, name)
    manifest = load(book / 'extraction.json')
    if not manifest:
        return ['No extraction baseline; run verify-source after inspecting coverage'] if required else []
    now = snapshot(root, name)
    issues = []
    for key in now:
        if now[key] != manifest.get(key):
            issues.append(f'Immutable extraction changed: {key}; investigate, do not silently re-baseline')
    return issues


def source_check(root, name):
    _, en, _, epub = book_paths(root, name)
    files = md_files(en)
    if not files:
        return ['No extracted source Markdown'], {}
    return inventory(Source(epub), files, tool('pandoc'))


class TechnicalHTML(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.structure = []
        self.feed(text)

    def handle_starttag(self, name, attrs):
        # Reader-visible alt/title may be translated; technical attributes stay exact.
        self.structure.append((name, sorted((k, v) for k, v in attrs if k not in ('alt', 'title'))))

    def handle_endtag(self, name):
        self.structure.append(('/' + name, []))


def structural_issues(en_file, ru_file, pandoc=None):
    source, target = en_file.read_text(), ru_file.read_text()
    if not target.strip():
        return ['Empty translation']
    issues = []
    if len(target) / max(1, len(source)) < .35:
        issues.append('Suspiciously short translation; compare the full source')
    if TechnicalHTML(source).structure != TechnicalHTML(target).structure:
        issues.append('HTML structure or technical attributes differ')
    # Parse Markdown, so reference links, nested destinations, lists and emphasis are included.
    pandoc = pandoc or tool('pandoc')
    docs = []
    for p in (en_file, ru_file):
        # Disabling automatic IDs separates author-supplied anchors from heading
        # slugs that naturally change when the visible heading is translated.
        result = subprocess.run([pandoc, str(p), '-f', 'markdown-auto_identifiers', '-t', 'json'], check=True, capture_output=True, text=True)
        docs.append(json.loads(result.stdout))

    def signature(doc):
        result = []
        def walk(x):
            if isinstance(x, dict):
                kind, content = x.get('t'), x.get('c')
                if kind == 'Header':
                    result.append(('heading', content[0], content[1][0]))
                elif kind in ('Link', 'Image'):
                    result.append((kind, content[-1][0]))
                elif kind in ('Strong', 'Emph', 'HorizontalRule', 'BulletList', 'OrderedList', 'BlockQuote', 'CodeBlock'):
                    result.append((kind, None))
                if kind in ('Div', 'Span', 'CodeBlock', 'Link', 'Image') and content[0][0]:
                    result.append(('anchor', content[0][0]))
                if kind == 'Link':
                    walk(content[1])
                elif kind != 'Image':
                    for v in x.values():
                        walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(doc.get('blocks', []))
        return result
    if signature(docs[0]) != signature(docs[1]):
        issues.append('Markdown headings, explicit anchors, links, images, emphasis, lists or block structure differ')
    return issues


def receipt_path(book, filename):
    return book / 'state' / (filename + '.json')


def stage_for(book, en, ru, config):
    if not ru.exists():
        return 'missing'
    state = load(receipt_path(book, en.name))
    if state.get('stage') not in ('translated', 'reviewed'):
        return 'untracked'
    # The receipt's language pair must match the configured one (case-insensitively);
    # a receipt without it proves nothing about the pair it was reviewed against.
    source_code = config['source_language']['code'].casefold()
    target_code = config['target_language']['code'].casefold()
    if (state.get('source_sha256') != digest(en) or state.get('translation_sha256') != digest(ru)
            or str(state.get('source_language', '')).casefold() != source_code
            or str(state.get('target_language', '')).casefold() != target_code):
        return 'stale'
    return state['stage']


def translation_issues(root, name, config, require_review=True):
    book, en, ru, _ = book_paths(root, name)
    source_files, target_files = {p.name for p in md_files(en)}, {p.name for p in md_files(ru)}
    issues = [f'Missing translation file: {n}' for n in sorted(source_files - target_files)]
    issues += [f'Unexpected translation file: {n}' for n in sorted(target_files - source_files)]
    for n in sorted(source_files & target_files):
        issues += [f'{n}: {s}' for s in structural_issues(en / n, ru / n)]
        if require_review and stage_for(book, en / n, ru / n, config) != 'reviewed':
            issues.append(f'{n}: no current semantic-review receipt')
    return issues


def metadata_issues(book):
    metadata = load(book / 'metadata.json')
    issues = []
    if not metadata.get('title') or not metadata.get('author'):
        issues.append('metadata.json requires translated title and author')
    labels = metadata.get('labels', {})
    if not labels.get('contents'):
        issues.append('metadata.json requires labels.contents')
    if not labels.get('cover'):
        issues.append('metadata.json requires labels.cover')
    return issues


def report(name, issues):
    print(name + ':')
    for issue in issues:
        print('  ERROR: ' + issue)
    if not issues:
        print('  OK')


def language_args(args):
    return (args.source_language, args.source_language_name, args.target_language, args.target_language_name)


def build_translation_config(args):
    source_code, source_name, target_code, target_name = language_args(args)
    config = {'source_language': {'code': source_code, 'name': source_name},
              'target_language': {'code': target_code, 'name': target_name}}
    return validate_translation_config(config)


def cmd_init(args, root):
    for directory in ('source', 'books', 'series', 'dist'):
        (root / directory).mkdir(parents=True, exist_ok=True)
    path = root / 'translation.json'
    if path.exists():
        print(describe_translation(translation_config(root)))
    elif all(language_args(args)):
        config = build_translation_config(args)
        save(path, config)
        print(describe_translation(config))
    else:
        raise ValueError('Fresh workspace has no translation.json; pass --source-language, '
                          '--source-language-name, --target-language and --target-language-name '
                          '(or run configure for an existing legacy workspace)')
    glossary = root / 'series/glossary.md'
    if not glossary.exists():
        glossary.write_text('# Series glossary\n\n| Source | Translation | Notes |\n|---|---|---|\n')
    style = root / 'series/style-guide.md'
    if not style.exists():
        shutil.copyfile(SKILL / 'assets/style-guide.md', style)
    for name in selected(root, []):
        (root / 'books' / name / 'ru').mkdir(parents=True, exist_ok=True)
    print('Workspace initialized; existing files kept')


def cmd_configure(args, root):
    path = root / 'translation.json'
    if path.exists():
        print(describe_translation(translation_config(root)))
        print('translation.json already exists; not modified')
        return False
    if not all(language_args(args)):
        raise ValueError('configure requires --source-language, --source-language-name, '
                          '--target-language and --target-language-name')
    config = build_translation_config(args)
    save(path, config)
    print(describe_translation(config))
    return False


def run_extractor(epub, output, depth):
    command = [tool('epub2md')]
    if depth is not None:
        command += ['--depth', str(depth)]
    env = dict(os.environ)
    env['PATH'] = str(Path(tool('pandoc')).parent) + os.pathsep + env.get('PATH', '')
    subprocess.run(command + [str(epub), str(output)], check=True, env=env)
    if not md_files(output):
        raise ValueError('Extractor produced no Markdown')


def cmd_extract(args, root):
    for name in selected(root, args.books):
        book, en, ru, epub = book_paths(root, name)
        ru.mkdir(parents=True, exist_ok=True)
        if md_files(en) and not args.repair_missing:
            print(f'skip {name}: existing extraction; use check-source to audit it')
            continue
        with tempfile.TemporaryDirectory(prefix='book-extract-') as td:
            out = Path(td) / 'en'
            run_extractor(epub, out, args.depth)
            issues, _ = inventory(Source(epub), md_files(out), tool('pandoc'))
            if issues:
                raise ValueError('Extraction coverage failed: ' + '; '.join(issues))
            # Plan the whole repair before copying anything. Existing bytes are immutable.
            staged = tree_hashes(out)
            baseline = load(book / 'extraction.json')
            if baseline:
                if baseline.get('source_sha256') != digest(epub):
                    raise ValueError('Source EPUB changed; repair cannot reset its baseline')
                for rel, h in baseline.get('english_files', {}).items():
                    if staged.get(rel) != h:
                        raise ValueError(f'Fresh extraction disagrees with recorded baseline: {rel}')
            for rel, h in tree_hashes(en).items():
                if rel not in staged or staged[rel] != h:
                    raise ValueError(f'{name}: extraction differs at {rel}; existing source Markdown kept. Inspect a temporary extraction manually.')
            for rel in staged:
                dest = en / rel
                if not dest.exists():
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(out / rel, dest)
            state = snapshot(root, name)
            state['depth'] = args.depth
            save(book / 'extraction.json', state)
            print(f'{name}: extracted and verified {len(md_files(en))} files')


def cmd_verify_source(args, root):
    failed = False
    for name in selected(root, args.books):
        issues, _ = source_check(root, name)
        issues += baseline_issues(root, name, required=False)
        report(name, issues)
        if issues:
            failed = True
        else:
            book, _, _, _ = book_paths(root, name)
            path = book / 'extraction.json'
            if not path.exists():
                save(path, snapshot(root, name))
                print('  recorded immutable source baseline')
    return failed


def cmd_check_source(args, root):
    failed = False
    for name in selected(root, args.books):
        issues, _ = source_check(root, name)
        report(name, issues)
        failed |= bool(issues)
    return failed


def cmd_status(args, root):
    config = translation_config(root)
    print(describe_translation(config))
    for name in selected(root, args.books):
        book, en, ru, _ = book_paths(root, name)
        counts = {}
        for p in md_files(en):
            stage = stage_for(book, p, ru / p.name, config)
            counts[stage] = counts.get(stage, 0) + 1
        baseline = 'verified' if not baseline_issues(root, name) else 'unverified/changed'
        print(f'{name}: en={len(md_files(en))} ru={len(md_files(ru))} extraction={baseline} stages={json.dumps(counts)}')


def cmd_mark(args, root):
    book, en, ru, _ = book_paths(root, args.book)
    if args.book not in selected(root, [args.book]):
        raise ValueError('Unknown book')
    config = translation_config(root)
    names = [p.name for p in md_files(en)] if args.all else args.files
    if not names:
        raise ValueError('Specify filenames or --all')
    if args.stage == 'reviewed' and (not args.reviewer or not args.note):
        raise ValueError('Semantic review requires --reviewer and --note; recording is an attestation, not an automated review')
    baseline = baseline_issues(root, args.book)
    if baseline:
        raise ValueError('; '.join(baseline))
    records = []
    for name in names:
        if name not in {p.name for p in md_files(en)} or not (ru / name).exists():
            raise ValueError(f'Unknown or missing translation: {name}')
        issues = structural_issues(en / name, ru / name)
        if issues:
            raise ValueError(f'{name}: ' + '; '.join(issues))
        records.append((name, {'stage': args.stage, 'source_sha256': digest(en / name),
                               'translation_sha256': digest(ru / name), 'reviewer': args.reviewer,
                               'note': args.note,
                               'source_language': config['source_language']['code'],
                               'target_language': config['target_language']['code']}))
    for name, record in records:
        save(receipt_path(book, name), record)
    print(f'{args.book}: recorded {args.stage} for {len(records)} files')


def readiness_issues(root, name, config, structure_only=False):
    """Every check that blocks publication; check and build share this set.

    Returns (issues, mapping); structure_only skips review receipts and metadata.
    """
    issues, mapping = source_check(root, name)
    issues += baseline_issues(root, name)
    issues += translation_issues(root, name, config, require_review=not structure_only)
    if not structure_only:
        issues += metadata_issues(book_paths(root, name)[0])
    return issues, mapping


def publication_inputs(root, name):
    """Every input whose change after checking must abort publication.

    translation.json is read first, so the parsed config and the recheck share its bytes.
    Register a new build input here and nowhere else.
    """
    book, _, ru, _ = book_paths(root, name)
    translation, metadata = root / 'translation.json', book / 'metadata.json'
    return {'translation.json': translation.read_bytes() if translation.exists() else None,
            'extraction': snapshot(root, name),
            'translations': tree_hashes(ru),
            'receipts': tree_hashes(book / 'state'),
            'metadata.json': metadata.read_bytes() if metadata.exists() else None}


def publish(root, name):
    """Check one book, package it in staging and replace its EPUB only if inputs held still.

    Returns (issues, output). Blocking issues leave the previous EPUB untouched;
    a failed package or an input changed during the build raises and also keeps it.
    """
    inputs = publication_inputs(root, name)
    if inputs['translation.json'] is None:
        raise ValueError('Missing translation.json; run configure or init with language options')
    translation = validate_translation_config(json.loads(inputs['translation.json']))
    book, en, ru, epub = book_paths(root, name)
    output = root / 'dist' / f'{name}.{translation["target_language"]["code"]}.epub'
    issues, mapping = readiness_issues(root, name, translation)
    if issues:
        return issues, output
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='book-build-', dir=output.parent) as td:
        staged = Path(td) / 'book.epub'
        package(Source(epub), md_files(ru), en, mapping, json.loads(inputs['metadata.json']),
                translation, tool('pandoc'), staged)
        if publication_inputs(root, name) != inputs:
            raise ValueError('Inputs changed during build; existing EPUB preserved')
        staged.replace(output)
    return [], output


def cmd_check(args, root):
    config = translation_config(root)
    failed = False
    for name in selected(root, args.books):
        issues, _ = readiness_issues(root, name, config, structure_only=args.structure_only)
        report(name, issues)
        failed |= bool(issues)
    if args.structure_only:
        print('Structural checks only; semantic completeness is not established.')
    return failed


def cmd_build(args, root):
    names = selected(root, args.books)
    if not names:
        raise ValueError('No source EPUBs')
    failed = False
    for name in names:
        issues, output = publish(root, name)
        if issues:
            report(name, issues)
            failed = True
        else:
            print(f'built {output}')
    return failed


def cmd_doctor(args, root):
    failed = False
    if sys.version_info < (3, 10):
        print('ERROR: Python 3.10 or newer is required')
        failed = True
    try:
        print(describe_translation(translation_config(root)))
    except ValueError as e:
        print(f'ERROR: {e}')
        failed = True
    # uv only installs epub2md (see bootstrap.sh); a ready epub2md does not need it.
    for name in ('python3', 'pandoc', 'epub2md'):
        try:
            path = tool(name)
            option = '--help' if name == 'epub2md' else '--version'
            p = subprocess.run([path, option], capture_output=True, text=True, timeout=20)
            if p.returncode:
                raise ValueError(f'exits {p.returncode}')
            print(f'{name}: {path}; {(p.stdout or p.stderr).splitlines()[0]}')
            if name == 'epub2md':
                print('  --depth ' + ('advertised' if '--depth' in p.stdout else 'not advertised; default extraction uses auto mode; explicit depth is checked during extraction'))
        except (ValueError, subprocess.TimeoutExpired) as e:
            print(f'ERROR: {name}: {e}')
            failed = True
    for p in ('series/glossary.md', 'series/style-guide.md'):
        if not (root / p).is_file():
            print(f'ERROR: missing {p}; run init')
            failed = True
    for name in selected(root, args.books):
        book, en, ru, source = book_paths(root, name)
        try:
            src = Source(source)
            print(f'{name}: spine={len(src.spine)}, TOC targets={len(set(src.toc))}, cover={bool(src.cover)}, en={len(md_files(en))}, ru={len(md_files(ru))}')
            if md_files(en):
                issues, _ = source_check(root, name)
                issues += baseline_issues(root, name, required=False)
                report(name, issues)
                failed |= bool(issues)
            if not ru.is_dir():
                print(f'ERROR: missing {ru}; run init')
                failed = True
        except (ValueError, KeyError) as e:
            print(f'ERROR: {name}: {e}')
            failed = True
    return failed


def cmd_check_package(args, root):
    target_code = translation_config(root)['target_language']['code']
    for name in selected(root, args.books):
        validate(root / 'dist' / f'{name}.{target_code}.epub', len(md_files(root / 'books' / name / 'en')))
        print(f'{name}: ZIP, XML, resources, anchors and navigation OK')


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=Path.cwd())
    sub = p.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init', help='Create missing workspace files without replacing existing ones')
    configure = sub.add_parser('configure', help='Create translation.json for an existing (legacy) workspace without touching other data')
    for language_parser in (init, configure):
        language_parser.add_argument('--source-language', help='Source language BCP 47 code, e.g. en')
        language_parser.add_argument('--source-language-name', help='Source language display name, e.g. English')
        language_parser.add_argument('--target-language', help='Target language BCP 47 code, e.g. ru')
        language_parser.add_argument('--target-language-name', help='Target language display name, e.g. Russian')
    for name in ('doctor', 'status', 'verify-source', 'check-source', 'check-package', 'build'):
        sub.add_parser(name).add_argument('books', nargs='*')
    extract = sub.add_parser('extract', help='Extract in staging; install verified output without overwriting existing source Markdown')
    extract.add_argument('books', nargs='*')
    extract.add_argument('--depth', type=int, help='Explicit extractor depth; omit for auto mode')
    extract.add_argument('--repair-missing', action='store_true', help='Restore missing files only after comparing all existing bytes')
    check = sub.add_parser('check')
    check.add_argument('books', nargs='*')
    check.add_argument('--structure-only', action='store_true', help='Diagnose structure without requiring semantic-review receipts or metadata')
    mark = sub.add_parser('mark', help='Record translation/review state against current file hashes')
    mark.add_argument('book')
    mark.add_argument('files', nargs='*')
    mark.add_argument('--all', action='store_true')
    mark.add_argument('--stage', required=True, choices=('translated', 'reviewed'))
    mark.add_argument('--reviewer')
    mark.add_argument('--note')
    return p


def main():
    args = parser().parse_args()
    if getattr(args, 'depth', None) is not None and args.depth < 1:
        raise SystemExit('ERROR: depth must be positive')
    try:
        failed = globals()['cmd_' + args.command.replace('-', '_')](args, args.root.expanduser().resolve())
        return 1 if failed else 0
    except (ValueError, OSError, KeyError, ET.ParseError, BadZipFile, subprocess.CalledProcessError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
