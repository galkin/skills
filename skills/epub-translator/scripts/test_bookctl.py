"""Regression tests for data-loss and incomplete-publication cases. Requires Pandoc."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import base64
import importlib.util
import json
import re
import shutil
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bookctl as ctl
from epubio import Source, inventory, validate

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
FIRST = 'Amber birds gather beneath tall trees while winter winds carry small seeds across distant hills and quiet rivers each morning.'
SECOND = 'Silver fish swim through deep water while summer sunlight reaches broad leaves near ancient stone walls beside the peaceful eastern village.'


def fixture(root, target_code='ru', target_name='Russian', labels=None):
    (root / 'source').mkdir()
    book = root / 'books/demo'
    for name in ('en', 'ru'):
        (book / name).mkdir(parents=True)
    (root / 'dist').mkdir()
    ctl.save(root / 'translation.json', {
        'source_language': {'code': 'en', 'name': 'English'},
        'target_language': {'code': target_code, 'name': target_name},
    })
    with ZipFile(root / 'source/demo.epub', 'w') as z:
        z.writestr('META-INF/container.xml', '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OPS/book.opf"/></rootfiles></container>')
        z.writestr('OPS/book.opf', '<package xmlns="http://www.idpf.org/2007/opf" xmlns:dc="http://purl.org/dc/elements/1.1/"><metadata><dc:title>Demo</dc:title><dc:creator>Author</dc:creator></metadata><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/><item id="two" href="two.xhtml" media-type="application/xhtml+xml"/><item id="image" href="art.png" media-type="image/png" properties="cover-image"/></manifest><spine><itemref idref="one"/><itemref idref="two"/></spine></package>')
        z.writestr('OPS/one.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>First</h1><p>'+FIRST+'</p><p><a href="two.xhtml#second">Next</a></p><img src="art.png"/></body></html>')
        z.writestr('OPS/two.xhtml', '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1 id="second">Second</h1><p>'+SECOND+'</p></body></html>')
        z.writestr('OPS/art.png', PNG)
    image = '<span class="image placeholder" data-original-image-src="art.png"></span>'
    (book / 'en/01-first.md').write_text('# First\n\n'+FIRST+'\n\n[Next](two.xhtml#second)\n\n'+image+'\n')
    (book / 'en/02-second.md').write_text('# Second\n\n'+SECOND+'\n')
    (book / 'ru/01-first.md').write_text('# Первая\n\nЯнтарные птицы собираются под высокими деревьями, пока зимние ветры каждое утро несут маленькие семена над далёкими холмами и тихими реками.\n\n[Далее](two.xhtml#second)\n\n'+image+'\n')
    (book / 'ru/02-second.md').write_text('# Вторая\n\nСеребряные рыбы плывут в глубокой воде, пока летнее солнце освещает широкие листья у старых каменных стен возле тихой восточной деревни.\n')
    default_labels = {'contents': 'Содержание', 'cover': 'Обложка'} if target_code == 'ru' else {'contents': 'Contents', 'cover': 'Cover'}
    ctl.save(book / 'metadata.json', {'title':'Пример','author':'Автор','labels': labels or default_labels})
    return book


def build_epub(root, target_code='ru', target_name='Russian', labels=None):
    book = fixture(root, target_code=target_code, target_name=target_name, labels=labels)
    args = SimpleNamespace(books=['demo'])
    assert not ctl.cmd_verify_source(args, root)
    ctl.cmd_mark(SimpleNamespace(book='demo', files=[], all=True, stage='reviewed',
                                  reviewer='test', note='Fixture manually aligned'), root)
    assert not ctl.cmd_build(args, root)
    return book, root / f'dist/demo.{target_code}.epub'


def opf_identifier(epub_path):
    with ZipFile(epub_path) as z:
        return re.search(r'<dc:identifier[^>]*>([^<]+)</dc:identifier>',
                          z.read('EPUB/content.opf').decode()).group(1)


class SkillIdentityTests(unittest.TestCase):
    def test_entrypoints_use_skill_name(self):
        self.assertEqual(ctl.SKILL.name, 'epub-translator')
        skill = (ctl.SKILL/'SKILL.md').read_text()
        self.assertRegex(skill, r'(?m)^name: epub-translator$')
        self.assertIn('$epub-translator', (ctl.SKILL/'agents/openai.yaml').read_text())
        for path in ctl.SKILL.rglob('*'):
            if path.is_file() and path.suffix in ('.md', '.yaml', '.py', '.sh') and path.name != 'test_bookctl.py':
                self.assertNotIn('book-translator', path.read_text(), path)


@unittest.skipUnless(shutil.which('pandoc'), 'Pandoc is required')
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(prefix='bookctl-test-')
        self.root = Path(self.temp.name)
        self.book = fixture(self.root)
        self.args = SimpleNamespace(books=['demo'])

    def tearDown(self):
        self.temp.cleanup()

    def reviewed(self):
        self.assertFalse(ctl.cmd_verify_source(self.args, self.root))
        ctl.cmd_mark(SimpleNamespace(book='demo', files=[], all=True, stage='reviewed', reviewer='test', note='Fixture manually aligned'), self.root)

    def test_missing_original_section_rejected_even_when_file_sets_match(self):
        (self.book / 'en/02-second.md').unlink()
        (self.book / 'ru/02-second.md').unlink()
        issues, _ = ctl.source_check(self.root, 'demo')
        self.assertTrue(any('two.xhtml' in s for s in issues), issues)
        self.assertFalse((self.book / 'extraction.json').exists())

    def test_review_hashes_invalidate_after_edit(self):
        self.reviewed()
        p = self.book / 'ru/02-second.md'
        p.write_text(p.read_text() + '\nДополнение.\n')
        config = ctl.translation_config(self.root)
        self.assertEqual(ctl.stage_for(self.book, self.book/'en'/p.name, p, config), 'stale')
        self.assertTrue(any('review' in s for s in ctl.translation_issues(self.root, 'demo', config)))

    def test_structural_damage_is_fatal(self):
        p = self.book / 'ru/01-first.md'
        p.write_text(p.read_text().replace('(two.xhtml#second)', '(wrong.xhtml)'))
        self.assertTrue(ctl.structural_issues(self.book/'en'/p.name, p))
        p.write_text('')
        self.assertEqual(ctl.structural_issues(self.book/'en'/p.name, p), ['Empty translation'])

    def test_baseline_cannot_be_silently_reset(self):
        self.reviewed()
        p = self.book/'en/02-second.md'
        p.write_text(p.read_text()+'\nModified original.\n')
        before = (self.book/'extraction.json').read_bytes()
        self.assertTrue(ctl.cmd_verify_source(self.args, self.root))
        self.assertEqual((self.book/'extraction.json').read_bytes(), before)

    def test_verify_source_creates_missing_baseline(self):
        self.assertFalse((self.book/'extraction.json').exists())
        self.assertFalse(ctl.cmd_verify_source(self.args, self.root))
        self.assertTrue((self.book/'extraction.json').exists())
        self.assertEqual(ctl.baseline_issues(self.root, 'demo'), [])

    def test_baseline_mismatch_detected_once_by_verify_check_and_build(self):
        self.reviewed()
        p = self.book/'en/02-second.md'
        p.write_text(p.read_text()+'\nModified original.\n')
        before = (self.book/'extraction.json').read_bytes()
        changed = 'Immutable extraction changed: english_files; investigate, do not silently re-baseline'
        for command, args in ((ctl.cmd_verify_source, self.args),
                              (ctl.cmd_check, SimpleNamespace(books=['demo'], structure_only=True)),
                              (ctl.cmd_build, self.args)):
            with self.subTest(command=command.__name__), patch('builtins.print') as out:
                self.assertTrue(command(args, self.root))
                lines = [c.args[0] for c in out.call_args_list]
                self.assertEqual(lines.count('  ERROR: '+changed), 1, lines)
        self.assertEqual((self.book/'extraction.json').read_bytes(), before)
        self.assertFalse((self.root/'dist/demo.ru.epub').exists())

    def test_check_requires_baseline(self):
        with patch('builtins.print') as out:
            self.assertTrue(ctl.cmd_check(SimpleNamespace(books=['demo'], structure_only=True), self.root))
        self.assertTrue(any('No extraction baseline' in c.args[0] for c in out.call_args_list))

    def test_check_requires_build_metadata(self):
        self.reviewed()
        ctl.save(self.book/'metadata.json', {'title': 'Пример', 'author': 'Автор', 'labels': {'cover': 'Обложка'}})
        with patch('builtins.print') as out:
            self.assertTrue(ctl.cmd_check(SimpleNamespace(books=['demo'], structure_only=False), self.root))
        self.assertTrue(any('labels.contents' in c.args[0] for c in out.call_args_list))
        with patch('builtins.print'):
            self.assertFalse(ctl.cmd_check(SimpleNamespace(books=['demo'], structure_only=True), self.root))

    def test_mark_rejects_changed_baseline(self):
        self.reviewed()
        p = self.book/'en/02-second.md'
        p.write_text(p.read_text()+'\nModified original.\n')
        with self.assertRaisesRegex(ValueError, 'Immutable extraction changed'):
            ctl.cmd_mark(SimpleNamespace(book='demo', files=['01-first.md'], all=False,
                                          stage='translated', reviewer=None, note=None), self.root)

    def test_legacy_translating_receipt_is_untracked(self):
        self.assertFalse(ctl.cmd_verify_source(self.args, self.root))
        en, ru = self.book/'en/01-first.md', self.book/'ru/01-first.md'
        ctl.save(ctl.receipt_path(self.book, en.name), {
            'stage': 'translating', 'source_sha256': ctl.digest(en),
            'translation_sha256': ctl.digest(ru), 'reviewer': None, 'note': None,
            'source_language': 'en', 'target_language': 'ru'})
        config = ctl.translation_config(self.root)
        self.assertEqual(ctl.stage_for(self.book, en, ru, config), 'untracked')
        ru.write_text(ru.read_text()+'\nПродолжение.\n')
        self.assertEqual(ctl.stage_for(self.book, en, ru, config), 'untracked')
        with patch('builtins.print'):
            ctl.cmd_status(self.args, self.root)
            self.assertTrue(ctl.cmd_build(self.args, self.root))
        self.assertTrue(any('01-first.md: no current semantic-review receipt' == s
                            for s in ctl.translation_issues(self.root, 'demo', config)))

    def test_translating_stage_is_not_accepted(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit):
            ctl.parser().parse_args(['mark', 'demo', '01-first.md', '--stage', 'translating'])

    def test_build_validates_package_and_preserves_output_on_failure(self):
        import epubio
        self.reviewed()
        out = self.root/'dist/demo.ru.epub'
        out.write_bytes(b'previous output')
        def reject(*args, **kwargs):
            raise ValueError('staged package rejected')
        with patch.object(epubio, 'validate', reject):
            with self.assertRaisesRegex(ValueError, 'staged package rejected'):
                ctl.cmd_build(self.args, self.root)
        self.assertEqual(out.read_bytes(), b'previous output')

    def test_build_requires_reviews_and_preserves_previous_output(self):
        ctl.cmd_verify_source(self.args, self.root)
        out = self.root/'dist/demo.ru.epub'
        out.write_bytes(b'previous output')
        self.assertTrue(ctl.cmd_build(self.args, self.root))
        self.assertEqual(out.read_bytes(), b'previous output')

    def test_build_preserves_images_links_and_is_repeatable(self):
        self.reviewed()
        self.assertFalse(ctl.cmd_build(self.args, self.root))
        out = self.root/'dist/demo.ru.epub'
        first = out.read_bytes()
        validate(out, 2)
        with ZipFile(out) as z:
            self.assertIn('section-002.xhtml#вторая', z.read('EPUB/section-001.xhtml').decode())
            self.assertTrue(any(z.read(n) == PNG for n in z.namelist() if '/media/' in n))
            self.assertIn('<dc:language>ru</dc:language>', z.read('EPUB/content.opf').decode())
        self.assertFalse(ctl.cmd_build(self.args, self.root))
        self.assertEqual(first, out.read_bytes())

    def test_package_validation_raises_value_error_not_assertion(self):
        # assert is stripped under python -O; package checks must survive it.
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        out = self.root/'dist/demo.ru.epub'
        with self.assertRaisesRegex(ValueError, 'Navigation has 2/3 sections'):
            validate(out, 3)
        with ZipFile(out) as z:
            data = {n: z.read(n) for n in z.namelist()}
        broken = self.root/'broken.epub'
        with ZipFile(broken, 'w') as z:
            for n in sorted(data):
                z.writestr(n, b'text/plain' if n == 'mimetype' else data[n])
        with self.assertRaisesRegex(ValueError, 'mimetype'):
            validate(broken)

    def test_failed_package_does_not_replace_output(self):
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        out = self.root/'dist/demo.ru.epub'
        before = out.read_bytes()
        ctl.save(self.book/'metadata.json', {'title':'Пример','author':'Автор',
                                              'labels':{'contents':'Содержание','cover':'Обложка'},
                                              'link_targets':{'two.xhtml#second':'missing.md'}})
        with self.assertRaises(ValueError):
            ctl.cmd_build(self.args, self.root)
        self.assertEqual(before, out.read_bytes())

    def rewrite_epub(self, transform):
        path = self.root/'source/demo.epub'
        with ZipFile(path) as z:
            data = {n:z.read(n) for n in z.namelist()}
        transform(data)
        with ZipFile(path, 'w') as z:
            for n, blob in data.items():
                z.writestr(n, blob)

    def test_missing_toc_target_requires_cover_identity(self):
        def add_toc(data):
            data['OPS/book.opf'] = data['OPS/book.opf'].replace(b'</manifest>', b'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>')
            data['OPS/toc.ncx'] = b'<ncx><navMap><navPoint><navLabel><text>Epilogue</text></navLabel><content src="missing.xhtml"/></navPoint></navMap></ncx>'
        self.rewrite_epub(add_toc)
        self.assertIn('Source TOC target missing: OPS/missing.xhtml', ctl.source_check(self.root, 'demo')[0])
        self.assertTrue(ctl.cmd_verify_source(self.args, self.root))
        self.assertFalse((self.book/'extraction.json').exists())

    def test_explicit_cover_toc_target_can_be_carried_separately(self):
        def add_toc(data):
            data['OPS/book.opf'] = data['OPS/book.opf'].replace(b'</manifest>', b'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>')
            data['OPS/toc.ncx'] = b'<ncx><navMap><navPoint><navLabel><text>Cover</text></navLabel><content src="missing.xhtml"/></navPoint><navPoint><navLabel><text>Epilogue</text></navLabel><content src="epilogue.xhtml"/></navPoint></navMap></ncx>'
        self.rewrite_epub(add_toc)
        issues, _ = ctl.source_check(self.root, 'demo')
        self.assertEqual(issues, ['Source TOC target missing: OPS/epilogue.xhtml'])
        def remove_epilogue(data):
            data['OPS/toc.ncx'] = data['OPS/toc.ncx'].replace(b'<navPoint><navLabel><text>Epilogue</text></navLabel><content src="epilogue.xhtml"/></navPoint>', b'')
        self.rewrite_epub(remove_epilogue)
        self.assertEqual(ctl.source_check(self.root, 'demo')[0], [])
        self.rewrite_epub(lambda data: data.pop('OPS/art.png'))
        self.assertIn('Source TOC target missing: OPS/missing.xhtml', ctl.source_check(self.root, 'demo')[0])

    def test_epub3_cover_landmark_does_not_hide_other_missing_targets(self):
        def add_nav(data):
            data['OPS/book.opf'] = data['OPS/book.opf'].replace(b'</manifest>', b'<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/></manifest>')
            data['OPS/nav.xhtml'] = b'<html xmlns:epub="http://www.idpf.org/2007/ops"><body><nav><a epub:type="cover" href="missing.xhtml">Artwork</a><a href="epilogue.xhtml">Epilogue</a></nav></body></html>'
        self.rewrite_epub(add_nav)
        self.assertEqual(ctl.source_check(self.root, 'demo')[0], ['Source TOC target missing: OPS/epilogue.xhtml'])

    def test_opf_guide_identifies_missing_cover_target(self):
        def add_guide(data):
            data['OPS/book.opf'] = data['OPS/book.opf'].replace(b'</manifest>', b'<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/></manifest>').replace(b'</package>', b'<guide><reference type="cover" href="missing.xhtml"/></guide></package>')
            data['OPS/toc.ncx'] = b'<ncx><navMap><navPoint><navLabel><text>Artwork</text></navLabel><content src="missing.xhtml"/></navPoint></navMap></ncx>'
        self.rewrite_epub(add_guide)
        self.assertEqual(ctl.source_check(self.root, 'demo')[0], [])

    def test_opening_cover_accepts_optional_extracted_page(self):
        def add_cover(data):
            data['OPS/book.opf'] = data['OPS/book.opf'].replace(b'</manifest>', b'<item id="coverpage" href="cover.xhtml" media-type="application/xhtml+xml"/></manifest>').replace(b'<spine>', b'<spine><itemref idref="coverpage"/>')
            data['OPS/cover.xhtml'] = b'<html><body><img src="art.png"/></body></html>'
        self.rewrite_epub(add_cover)
        self.assertEqual(ctl.source_check(self.root, 'demo')[0], [])
        for locale in ('en', 'ru'):
            folder = self.book/locale
            (folder/'02-second.md').rename(folder/'03-second.md')
            (folder/'01-first.md').rename(folder/'02-first.md')
            (folder/'01-cover.md').write_text('![](art.png)\n')
        issues, mapping = ctl.source_check(self.root, 'demo')
        self.assertEqual(issues, [])
        self.assertEqual(mapping['OPS/cover.xhtml'], '01-cover.md')
        self.reviewed()
        self.assertFalse(ctl.cmd_build(self.args, self.root))
        validate(self.root/'dist/demo.ru.epub', 3)

    def test_explicit_markdown_anchors_must_be_preserved(self):
        en, ru = self.book/'en/02-second.md', self.book/'ru/02-second.md'
        for source, target in (
            ('# Chapter {#retained-anchor}', '# Глава {#lost-anchor}'),
            ('# Chapter {#retained-anchor}', '# Глава'),
            ('[Text]{#retained-anchor}', '[Текст]{#lost-anchor}'),
        ):
            with self.subTest(source=source, target=target):
                en.write_text(source+'\n')
                ru.write_text(target+'\n')
                self.assertTrue(ctl.structural_issues(en, ru))
        en.write_text('# Chapter {#retained-anchor}\n')
        ru.write_text('# Глава {#retained-anchor}\n')
        self.assertEqual(ctl.structural_issues(en, ru), [])

    def test_image_only_spine_page_must_be_extracted(self):
        def add_map(data):
            opf = data['OPS/book.opf'].decode().replace('</manifest>', '<item id="map" href="map.xhtml" media-type="application/xhtml+xml"/><item id="map-image" href="map.png" media-type="image/png"/></manifest>').replace('</spine>', '<itemref idref="map"/></spine>')
            data['OPS/book.opf'] = opf.encode()
            data['OPS/map.xhtml'] = b'<html><body><img src="map.png"/></body></html>'
            data['OPS/map.png'] = PNG+b'map'
        self.rewrite_epub(add_map)
        issues, _ = ctl.source_check(self.root, 'demo')
        self.assertTrue(any('image-only' in s or 'map.png' in s for s in issues), issues)
        placeholder = '<span data-original-image-src="map.png"></span>'
        for locale in ('en','ru'):
            (self.book/locale/'03-map.md').write_text(placeholder)
        self.assertEqual(ctl.source_check(self.root, 'demo')[0], [])
        self.reviewed()
        self.assertFalse(ctl.cmd_build(self.args, self.root))
        with ZipFile(self.root/'dist/demo.ru.epub') as z:
            self.assertIn('<img ', z.read('EPUB/section-003.xhtml').decode())
            self.assertIn(PNG+b'map', [z.read(n) for n in z.namelist()])

    def test_split_source_link_points_to_first_segment(self):
        first = ' '.join('first'+str(i) for i in range(100))
        second = ' '.join('second'+str(i) for i in range(200))
        def split(data):
            data['OPS/two.xhtml'] = ('<html><body><p>'+first+'</p><p>'+second+'</p></body></html>').encode()
            data['OPS/one.xhtml'] = data['OPS/one.xhtml'].replace(b'two.xhtml#second', b'two.xhtml')
        self.rewrite_epub(split)
        for locale in ('en','ru'):
            p = self.book/locale/'01-first.md'
            p.write_text(p.read_text().replace('two.xhtml#second','two.xhtml'))
            (self.book/locale/'02-second.md').write_text(first)
            (self.book/locale/'03-tail.md').write_text(second)
        issues, mapping = ctl.source_check(self.root, 'demo')
        self.assertEqual(issues, [])
        self.assertEqual(mapping['OPS/two.xhtml'], '02-second.md')
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        with ZipFile(self.root/'dist/demo.ru.epub') as z:
            self.assertIn('section-002.xhtml#section-start', z.read('EPUB/section-001.xhtml').decode())

    def test_edit_between_review_check_and_render_is_not_published(self):
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        output = self.root/'dist/demo.ru.epub'
        before = output.read_bytes()
        original = ctl.readiness_issues
        def edit_after_check(*args, **kwargs):
            result = original(*args, **kwargs)
            p = self.book/'ru/02-second.md'
            p.write_text(p.read_text()+'\nНепроверенное изменение.\n')
            return result
        with patch.object(ctl, 'readiness_issues', edit_after_check):
            with self.assertRaises(ValueError):
                ctl.cmd_build(self.args, self.root)
        self.assertEqual(before, output.read_bytes())

    def test_repair_refuses_changed_existing_file_before_copying(self):
        (self.book/'en/02-second.md').unlink()
        existing = (self.book/'en/01-first.md').read_bytes()
        def extractor(epub, out, depth):
            out.mkdir()
            (out/'01-first.md').write_bytes(existing+b'\nChanged.\n')
            (out/'02-second.md').write_text('# Second\n\n'+SECOND+'\n')
        with patch.object(ctl, 'run_extractor', extractor):
            with self.assertRaises(ValueError):
                ctl.cmd_extract(SimpleNamespace(books=['demo'], repair_missing=True, depth=None), self.root)
        self.assertEqual(existing, (self.book/'en/01-first.md').read_bytes())
        self.assertFalse((self.book/'en/02-second.md').exists())

    def test_russian_build_uses_configured_language(self):
        with TemporaryDirectory(prefix='bookctl-test-ru-') as td:
            _, out = build_epub(Path(td))
            with ZipFile(out) as z:
                opf = z.read('EPUB/content.opf').decode()
                self.assertIn('<dc:language>ru</dc:language>', opf)
                self.assertIn('xml:lang="ru"', opf)
                section = z.read('EPUB/section-001.xhtml').decode()
                self.assertIn('lang="ru"', section)
                self.assertIn('xml:lang="ru"', section)

    def test_spanish_build_uses_configured_language(self):
        with TemporaryDirectory(prefix='bookctl-test-es-') as td:
            _, out = build_epub(Path(td), target_code='es', target_name='Spanish',
                                 labels={'contents': 'Índice', 'cover': 'Portada'})
            with ZipFile(out) as z:
                opf = z.read('EPUB/content.opf').decode()
                self.assertIn('<dc:language>es</dc:language>', opf)
                self.assertIn('xml:lang="es"', opf)
                section = z.read('EPUB/section-001.xhtml').decode()
                self.assertIn('lang="es"', section)
                self.assertIn('xml:lang="es"', section)
                self.assertIn('Índice', z.read('EPUB/nav.xhtml').decode())
                self.assertIn('Portada', z.read('EPUB/title.xhtml').decode())

    def test_spanish_build_has_no_russian_leakage(self):
        with TemporaryDirectory(prefix='bookctl-test-es-leak-') as td:
            _, out = build_epub(Path(td), target_code='es', target_name='Spanish',
                                 labels={'contents': 'Índice', 'cover': 'Portada'})
            with ZipFile(out) as z:
                for name in z.namelist():
                    if name == 'mimetype':
                        continue
                    text = z.read(name).decode('utf-8', 'ignore')
                    self.assertNotIn('Содержание', text, name)
                    self.assertNotIn('Обложка', text, name)

    def test_missing_translation_config_fails_cleanly(self):
        (self.root/'translation.json').unlink()
        with self.assertRaises(ValueError):
            ctl.cmd_status(self.args, self.root)
        with self.assertRaises(ValueError):
            ctl.cmd_build(self.args, self.root)

    def test_invalid_translation_config_rejected(self):
        for data in (
            [],
            'string',
            {},
            {'source_language': {'code': 'en', 'name': 'English'}, 'target_language': {'code': 'en', 'name': 'English'}},
            {'source_language': {'code': 'en', 'name': 'English'}},
            {'source_language': {'code': '', 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': 'en', 'name': ''}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': ' ', 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': '../es', 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': 'en/us', 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': 'en\\us', 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': 'en', 'name': 'English'}, 'target_language': {'code': 'EN', 'name': 'English'}},
            {'source_language': 'en', 'target_language': {'code': 'ru', 'name': 'Russian'}},
            {'source_language': {'code': 1, 'name': 'English'}, 'target_language': {'code': 'ru', 'name': 'Russian'}},
        ):
            with self.subTest(data=data):
                ctl.save(self.root/'translation.json', data)
                with self.assertRaises(ValueError):
                    ctl.translation_config(self.root)

    def test_translation_config_matches_case_insensitively_despite_casing(self):
        ctl.save(self.root/'translation.json', {
            'source_language': {'code': ' en ', 'name': ' English '},
            'target_language': {'code': 'RU', 'name': 'Russian'},
        })
        config = ctl.translation_config(self.root)
        self.assertEqual(config['source_language']['code'], 'en')
        self.assertEqual(config['target_language']['code'], 'RU')

    def test_mark_requires_translation_config(self):
        (self.root/'translation.json').unlink()
        with self.assertRaises(ValueError):
            ctl.cmd_mark(SimpleNamespace(book='demo', files=['01-first.md'], all=False,
                                          stage='translated', reviewer=None, note=None), self.root)

    def test_check_requires_translation_config(self):
        (self.root/'translation.json').unlink()
        with self.assertRaises(ValueError):
            ctl.cmd_check(SimpleNamespace(books=['demo'], structure_only=False), self.root)

    def test_init_without_language_args_on_fresh_workspace_fails(self):
        with TemporaryDirectory(prefix='bookctl-test-init-') as td:
            root = Path(td)
            with self.assertRaises(ValueError):
                ctl.cmd_init(SimpleNamespace(source_language=None, source_language_name=None,
                                              target_language=None, target_language_name=None), root)
            self.assertFalse((root/'translation.json').exists())
            self.assertFalse((root/'series/glossary.md').exists())

    def test_init_with_language_args_creates_config_and_succeeds(self):
        with TemporaryDirectory(prefix='bookctl-test-init-') as td:
            root = Path(td)
            ctl.cmd_init(SimpleNamespace(source_language='en', source_language_name='English',
                                          target_language='es', target_language_name='Spanish'), root)
            config = ctl.translation_config(root)
            self.assertEqual(config['target_language']['code'], 'es')
            self.assertTrue((root/'series/glossary.md').exists())

    def test_init_never_silently_overwrites_existing_config(self):
        with TemporaryDirectory(prefix='bookctl-test-init-') as td:
            root = Path(td)
            ctl.cmd_init(SimpleNamespace(source_language='en', source_language_name='English',
                                          target_language='ru', target_language_name='Russian'), root)
            ctl.cmd_init(SimpleNamespace(source_language='en', source_language_name='English',
                                          target_language='es', target_language_name='Spanish'), root)
            config = ctl.translation_config(root)
            self.assertEqual(config['target_language']['code'], 'ru')

    def test_switching_language_pair_invalidates_review_receipts(self):
        self.reviewed()
        config = ctl.translation_config(self.root)
        en, ru = self.book/'en/01-first.md', self.book/'ru/01-first.md'
        self.assertEqual(ctl.stage_for(self.book, en, ru, config), 'reviewed')
        # Switch the configured target language without touching any translation/receipt files.
        ctl.save(self.root/'translation.json', {
            'source_language': {'code': 'en', 'name': 'English'},
            'target_language': {'code': 'es', 'name': 'Spanish'},
        })
        new_config = ctl.translation_config(self.root)
        self.assertEqual(ctl.stage_for(self.book, en, ru, new_config), 'stale')
        issues = ctl.translation_issues(self.root, 'demo', new_config)
        self.assertTrue(any('review' in s for s in issues), issues)
        # The old Russian text must not be publishable as a reviewed Spanish edition.
        self.assertTrue(ctl.cmd_build(self.args, self.root))
        self.assertFalse((self.root/'dist/demo.es.epub').exists())

    def test_build_rechecks_translation_json_before_publication(self):
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        output = self.root/'dist/demo.ru.epub'
        before = output.read_bytes()
        original = ctl.readiness_issues
        def switch_language_after_check(*args, **kwargs):
            result = original(*args, **kwargs)
            ctl.save(self.root/'translation.json', {
                'source_language': {'code': 'en', 'name': 'English'},
                'target_language': {'code': 'es', 'name': 'Spanish'},
            })
            return result
        with patch.object(ctl, 'readiness_issues', switch_language_after_check):
            with self.assertRaises(ValueError):
                ctl.cmd_build(self.args, self.root)
        self.assertEqual(before, output.read_bytes())
        self.assertFalse((self.root/'dist/demo.es.epub').exists())

    def test_translation_json_changed_right_after_authoritative_read_aborts_build(self):
        # The parsed config and the pre-publication recheck come from the same
        # publication_inputs bytes, so a change right after that read -- before any
        # check runs -- must still abort instead of publishing a mismatched edition.
        self.reviewed()
        ctl.cmd_build(self.args, self.root)
        output = self.root/'dist/demo.ru.epub'
        before = output.read_bytes()
        original_inputs = ctl.publication_inputs
        calls = {'n': 0}
        def mutate_after_first_read(*args, **kwargs):
            calls['n'] += 1
            result = original_inputs(*args, **kwargs)
            if calls['n'] == 1:
                ctl.save(self.root/'translation.json', {
                    'source_language': {'code': 'en', 'name': 'English'},
                    'target_language': {'code': 'es', 'name': 'Spanish'},
                })
            return result
        with patch.object(ctl, 'publication_inputs', mutate_after_first_read):
            with self.assertRaises(ValueError):
                ctl.cmd_build(self.args, self.root)
        # The previously built Russian edition must be untouched, and no new Russian or
        # (incorrectly reviewed) Spanish EPUB must have been published.
        self.assertEqual(before, output.read_bytes())
        self.assertFalse((self.root/'dist/demo.es.epub').exists())
        self.assertEqual(sorted(p.name for p in (self.root/'dist').iterdir()), ['demo.ru.epub'])

    def test_identical_content_different_language_pair_changes_identifier(self):
        with TemporaryDirectory(prefix='bookctl-test-id-') as td:
            root = Path(td)
            _, out_ru = build_epub(root)
            id_ru = opf_identifier(out_ru)
            # Reuse the exact same translated files and metadata; only the configured
            # target language changes.
            ctl.save(root/'translation.json', {
                'source_language': {'code': 'en', 'name': 'English'},
                'target_language': {'code': 'es', 'name': 'Spanish'},
            })
            ctl.cmd_mark(SimpleNamespace(book='demo', files=[], all=True, stage='reviewed',
                                          reviewer='test', note='Re-attest under switched config'), root)
            self.assertFalse(ctl.cmd_build(SimpleNamespace(books=['demo']), root))
            id_es = opf_identifier(root/'dist/demo.es.epub')
        self.assertNotEqual(id_ru, id_es)

    def test_identifier_unaffected_by_display_name_change(self):
        with TemporaryDirectory(prefix='bookctl-test-id-name-') as td:
            root = Path(td)
            build_epub(root, target_code='es', target_name='Spanish',
                       labels={'contents': 'Índice', 'cover': 'Portada'})
            id_before = opf_identifier(root/'dist/demo.es.epub')
            # Same canonical language codes; only the display name changes.
            ctl.save(root/'translation.json', {
                'source_language': {'code': 'en', 'name': 'English'},
                'target_language': {'code': 'es', 'name': 'Español'},
            })
            self.assertFalse(ctl.cmd_build(SimpleNamespace(books=['demo']), root))
            id_after = opf_identifier(root/'dist/demo.es.epub')
        self.assertEqual(id_before, id_after)

    def test_identifier_unaffected_by_language_code_casing(self):
        with TemporaryDirectory(prefix='bookctl-test-id-case-') as td:
            root = Path(td)
            build_epub(root, target_code='es', target_name='Spanish',
                       labels={'contents': 'Índice', 'cover': 'Portada'})
            id_lower = opf_identifier(root/'dist/demo.es.epub')
            # Same canonical codes under different casing.
            ctl.save(root/'translation.json', {
                'source_language': {'code': 'EN', 'name': 'English'},
                'target_language': {'code': 'ES', 'name': 'Spanish'},
            })
            self.assertFalse(ctl.cmd_build(SimpleNamespace(books=['demo']), root))
            id_upper = opf_identifier(root/'dist/demo.es.epub')
        self.assertEqual(id_lower, id_upper)


if __name__ == '__main__':
    unittest.main()
