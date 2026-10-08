"""EPUB inventory, extraction coverage, and self-contained packaging in the configured target language."""
from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from html import escape
from pathlib import Path
import json
import mimetypes
import posixpath
import re
import subprocess
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED, ZIP_STORED

X = 'http://www.w3.org/1999/xhtml'
O = 'http://www.idpf.org/2007/opf'
D = 'http://purl.org/dc/elements/1.1/'
N = 'http://www.daisy.org/z3986/2005/ncx/'


def tag(e):
    return e.tag.rsplit('}', 1)[-1]


def resolve(base, href):
    path = posixpath.normpath(posixpath.join(posixpath.dirname(base), unquote(urlsplit(href).path)))
    if path.startswith('../') or path.startswith('/'):
        raise ValueError(f'Unsafe EPUB path: {href}')
    return path


def tokens(text):
    return re.findall(r'\w+', text.casefold())


def visible(e):
    if tag(e) in ('head', 'script', 'style'):
        return ''
    return ' '.join([e.text or ''] + [visible(c) + ' ' + (c.tail or '') for c in e])


def render(path, pandoc):
    result = subprocess.run([pandoc, str(path), '-f', 'markdown', '-t', 'html4', '--wrap=none'],
                            check=True, capture_output=True, text=True)
    return ET.fromstring('<div>' + result.stdout + '</div>')


class Source:
    def __init__(self, path):
        with ZipFile(path) as z:
            bad = z.testzip()
            if bad:
                raise ValueError(f'Corrupt ZIP member: {bad}')
            self.data = {n: z.read(n) for n in z.namelist() if not n.endswith('/')}
        container = ET.fromstring(self.data['META-INF/container.xml'])
        self.opf_path = next(e.attrib['full-path'] for e in container.iter() if tag(e) == 'rootfile')
        opf = ET.fromstring(self.data[self.opf_path])
        self.items = {}
        self.cover = None
        for e in opf.iter():
            if tag(e) == 'item':
                self.items[e.attrib['id']] = (resolve(self.opf_path, e.attrib['href']), e.attrib)
                if 'cover-image' in e.attrib.get('properties', '').split():
                    self.cover = resolve(self.opf_path, e.attrib['href'])
        for e in opf.iter():
            if tag(e) == 'meta' and e.attrib.get('name') == 'cover':
                item = self.items.get(e.attrib.get('content'))
                if item:
                    self.cover = item[0]
        self.spine = [self.items[e.attrib['idref']][0] for e in opf.iter() if tag(e) == 'itemref']
        self.docs = {n: ET.fromstring(self.data[n]) for n in self.spine
                     if n.lower().endswith(('.html', '.xhtml', '.htm'))}
        if not self.docs:
            raise ValueError('EPUB has no readable spine documents')
        self.title = next((e.text for e in opf.iter() if tag(e) == 'title'), path.stem)
        self.author = next((e.text for e in opf.iter() if tag(e) == 'creator'), '')
        self.toc = []
        self.cover_targets = {resolve(self.opf_path, e.attrib['href']) for e in opf.iter()
                              if tag(e) == 'reference' and e.attrib.get('type') == 'cover'}
        for path, attrs in self.items.values():
            if attrs.get('media-type') == 'application/x-dtbncx+xml':
                for e in ET.fromstring(self.data[path]).iter():
                    if tag(e) == 'content':
                        self.toc.append(resolve(path, e.attrib['src']))
                    elif tag(e) == 'navPoint':
                        label = next((visible(c).strip().casefold() for c in e if tag(c) == 'navLabel'), '')
                        if label == 'cover':
                            self.cover_targets.update(resolve(path, c.attrib['src']) for c in e if tag(c) == 'content')
            if 'nav' in attrs.get('properties', '').split():
                for e in ET.fromstring(self.data[path]).iter():
                    if tag(e) == 'a' and 'href' in e.attrib:
                        target = resolve(path, e.attrib['href'])
                        self.toc.append(target)
                        if ('cover' in e.attrib.get('{http://www.idpf.org/2007/ops}type', '').split()
                                or visible(e).strip().casefold() == 'cover'):
                            self.cover_targets.add(target)
        if not self.cover:
            # Some EPUB 2 packages declare a cover only in their image-only title page.
            for n in self.spine[:2]:
                doc = self.docs.get(n)
                if doc is not None and not tokens(visible(doc)):
                    img = next((e for e in doc.iter() if tag(e) in ('img', 'image')), None)
                    if img is not None:
                        href = img.attrib.get('src') or img.attrib.get('{http://www.w3.org/1999/xlink}href')
                        if href:
                            self.cover = resolve(n, href)
                            break

    def asset(self, href, bases=()):
        path = unquote(urlsplit(href).path)
        candidates = {resolve(b, path) for b in bases}
        candidates.add(path)
        matches = [n for n in candidates if n in self.data]
        if not matches:
            matches = [n for n in self.data if posixpath.basename(n) == posixpath.basename(path)]
        if len(set(matches)) != 1:
            raise ValueError(f'Image is missing or ambiguous in source EPUB: {href}')
        return matches[0]


def inventory(source, files, pandoc):
    """Compare all spine prose against extraction; retain mapping for original links.

    Token-window coverage is a diagnostic, not proof of semantic completeness.
    Short sections are compared in full; long sections include a tail window.
    """
    rendered = {p.name: render(p, pandoc) for p in files}
    texts = {name: tokens(visible(doc)) for name, doc in rendered.items()}
    extracted_images = Counter()
    file_images = defaultdict(set)
    image_issues = []
    for p in files:
        for el in rendered[p.name].iter():
            href = el.attrib.get('data-original-image-src') or (el.attrib.get('src') if tag(el) == 'img' else None)
            if not href:
                continue
            try:
                local = (p.parent / unquote(urlsplit(href).path)).resolve()
                if local.is_relative_to(p.parent.resolve()) and local.is_file():
                    blob = local.read_bytes()
                    matches = [n for n, b in source.data.items() if b == blob]
                    if len(matches) != 1:
                        raise ValueError(f'{p.name}: image bytes not uniquely identified in source: {href}')
                    asset = matches[0]
                else:
                    asset = source.asset(href)
                file_images[p.name].add(asset)
                extracted_images[asset] += 1
            except ValueError as e:
                image_issues.append(str(e))
    source_images = Counter()
    index = defaultdict(set)
    for name, words in texts.items():
        for i in range(max(0, len(words) - 7)):
            index[tuple(words[i:i + 8])].add(name)
    issues, mapping, covered = image_issues, {}, set()
    order = {p.name: i for i, p in enumerate(files)}
    previous = -1
    for src in source.spine:
        if src not in source.docs:
            continue
        words = tokens(visible(source.docs[src]))
        images = []
        for el in source.docs[src].iter():
            href = (el.attrib.get('src') if tag(el) == 'img' else
                    el.attrib.get('{http://www.w3.org/1999/xlink}href') if tag(el) == 'image' else None)
            if href:
                images.append(resolve(src, href))
        is_cover_page = not words and images and set(images) == {source.cover} and src in source.spine[:2]
        if is_cover_page:
            # The opening cover is optional in extraction because packaging carries it
            # separately. If extracted, retain its mapping and accept that section.
            candidates = [n for n in texts if not texts[n] and file_images[n] == set(images)]
            if len(candidates) == 1:
                mapping[src] = candidates[0]
                covered.add(candidates[0])
            elif len(candidates) > 1:
                issues.append(f'{src}: opening cover has multiple extracted sections')
            continue
        source_images.update(images)
        if not words:
            if images:
                candidates = [n for n in texts if set(images) <= file_images[n]]
                if len(candidates) != 1:
                    issues.append(f'{src}: image-only page has no unique extracted section')
                else:
                    mapping[src] = candidates[0]
                    covered.add(candidates[0])
            continue
        hits = Counter()
        first_positions = {}
        total = matched = 0
        if len(words) < 8:
            needle = ' '.join(words)
            for name, target in texts.items():
                if needle in ' '.join(target):
                    hits[name] += 1
            total, matched = 1, bool(hits)
        else:
            for i in list(range(0, len(words) - 7, 4)) + [len(words) - 8]:
                names = index.get(tuple(words[i:i + 8]), set())
                total += 1
                matched += bool(names)
                for name in names:
                    hits[name] += 1
                    first_positions.setdefault(name, i)
        if matched / total < .95:
            issues.append(f'{src}: only {matched}/{total} text windows found in extracted source Markdown')
        if hits:
            meaningful = [n for n in hits if hits[n] >= max(1, min(3, total // 4))]
            if len(words) >= 8 and meaningful:
                # A file-only href means the beginning, not the largest split segment.
                best = min(meaningful, key=lambda n: (first_positions[n], -hits[n], order[n]))
            else:
                best = min(hits, key=lambda n: (-hits[n], len(texts[n]), order[n]))
            mapping[src] = best
            # Count meaningful matches; avoid marking a missing section covered by one common phrase.
            covered.update(n for n, score in hits.items() if score >= max(1, min(3, total // 4)))
            current = order[best]
            if matched / total >= .95 and current < previous:
                issues.append(f'{src}: extracted reading order goes backwards at {best}')
            if matched / total >= .95:
                previous = current
    for asset, count in source_images.items():
        if extracted_images[asset] < count:
            issues.append(f'{asset}: only {extracted_images[asset]}/{count} source image occurrences extracted')
    for name in texts.keys() - covered:
        issues.append(f'{name}: no corresponding source spine text (extra or unmapped section)')
    numbers = [int(p.name.split('-', 1)[0]) for p in files]
    if numbers != list(range(1, len(numbers) + 1)):
        issues.append('Source filenames must form a contiguous numeric sequence starting at 1')
    missing_toc = sorted(set(source.toc) - set(source.data))
    # Publishers sometimes leave a dangling cover-page TOC entry. Only an explicitly
    # identified cover target with available artwork can be carried separately.
    if source.cover in source.data:
        missing_toc = [n for n in missing_toc if n not in source.cover_targets]
    issues.extend(f'Source TOC target missing: {n}' for n in missing_toc)
    return issues, mapping


def xml_page(title, content, lang):
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            f'<html xmlns="{X}" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">'
            f'<head><title>{escape(title)}</title><link rel="stylesheet" href="style.css" type="text/css" /></head>'
            f'<body>{content}</body></html>').encode()


def package(source, files, en_dir, mapping, metadata, translation, pandoc, output):
    """Render in staging and write one XHTML per source Markdown file."""
    title, author = metadata['title'], metadata['author']
    reader_labels = metadata['labels']
    contents_label, cover_label = reader_labels['contents'], reader_labels['cover']
    lang = translation['target_language']['code']
    data = {'mimetype': b'application/epub+zip',
            'META-INF/container.xml': b'<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>',
            'EPUB/style.css': b'body{line-height:1.45}img{max-width:100%;height:auto}h1,h2,h3{page-break-after:avoid}'}
    paths = {p.name: f'section-{i:03}.xhtml' for i, p in enumerate(files, 1)}
    labels, documents = {}, {}
    aliases = {}
    resources = {}

    def add_asset(href, file):
        if urlsplit(href).scheme == 'data':
            return href
        if urlsplit(href).scheme or urlsplit(href).netloc:
            raise ValueError(f'{file}: remote image is not self-contained: {href}')
        local = (en_dir / unquote(urlsplit(href).path)).resolve()
        if local.is_relative_to(en_dir.resolve()) and local.is_file():
            blob, ext = local.read_bytes(), local.suffix
        else:
            src = source.asset(href, [s for s, n in mapping.items() if n == file])
            blob, ext = source.data[src], Path(src).suffix
        target = 'media/' + sha256(blob).hexdigest()[:20] + ext.lower()
        data['EPUB/' + target] = blob
        resources[target] = mimetypes.guess_type(target)[0] or 'application/octet-stream'
        return target

    for p in files:
        doc = render(p, pandoc)
        headings = [e for e in doc.iter() if tag(e) in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6')]
        first = next((e for e in doc if visible(e).strip()), None)
        labels[p.name] = metadata.get('sections', {}).get(p.name) or (
            visible(headings[0]).strip() if headings else visible(first).strip()[:100] if first is not None else p.stem)
        for el in doc.iter():
            if 'data-original-image-src' in el.attrib:
                href = el.attrib['data-original-image-src']
                el.tag, el.attrib, el.text = 'img', {'src': add_asset(href, p.name), 'alt': ''}, None
            elif tag(el) == 'img' and 'src' in el.attrib:
                el.set('src', add_asset(el.attrib['src'], p.name))
        # Preserve source heading anchors for translated Markdown #links.
        en_heads = [e for e in render(en_dir / p.name, pandoc).iter() if tag(e).startswith('h') and 'id' in e.attrib]
        for a, b in zip(en_heads, headings):
            if 'id' in a.attrib and 'id' in b.attrib:
                aliases[(p.name, a.attrib['id'])] = b.attrib['id']
        doc.insert(0, ET.Element('span', {'id': 'section-start'}))
        documents[p.name] = doc

    basename_map = defaultdict(set)
    for src, name in mapping.items():
        basename_map[posixpath.basename(src)].add(name)
    for name, doc in documents.items():
        for el in doc.iter():
            href = el.attrib.get('href')
            if not href or urlsplit(href).scheme or urlsplit(href).netloc:
                continue
            u = urlsplit(href)
            target = None
            override = metadata.get('link_targets', {}).get(href)
            if override:
                u = urlsplit(override)
                target = u.path
            elif not u.path:
                target = name
            elif unquote(u.path) in paths:
                target = unquote(u.path)
            else:
                candidates = {mapping[s] for s in mapping if s == unquote(u.path)}
                for src, owner in mapping.items():
                    if owner == name:
                        candidate = resolve(src, u.path)
                        if candidate in mapping:
                            candidates.add(mapping[candidate])
                if not candidates:
                    candidates = basename_map[posixpath.basename(unquote(u.path))]
                if len(candidates) == 1:
                    target = next(iter(candidates))
            if target not in paths:
                raise ValueError(f'{name}: cannot map internal link {href}; configure metadata.json link_targets')
            anchor = unquote(u.fragment)
            if anchor:
                anchor = aliases.get((target, anchor), anchor)
                ids = {e.attrib.get('id') for e in documents[target].iter()}
                if anchor not in ids:
                    raise ValueError(f'{name}: missing anchor {href}; configure an explicit link_targets override')
            el.set('href', paths[target] + '#' + (anchor or 'section-start'))
        content = ''.join(ET.tostring(e, encoding='unicode') for e in doc)
        data['EPUB/' + paths[name]] = xml_page(labels[name], content, lang)

    cover = None
    if source.cover:
        blob = source.data[source.cover]
        cover = 'media/cover' + Path(source.cover).suffix.lower()
        data['EPUB/' + cover] = blob
        resources[cover] = mimetypes.guess_type(cover)[0] or 'image/jpeg'
    title_html = (f'<img src="{cover}" alt="{escape(cover_label)}" />' if cover else '') + f'<h1>{escape(title)}</h1><p>{escape(author)}</p>'
    data['EPUB/title.xhtml'] = xml_page(title, title_html, lang)
    links = ''.join(f'<li><a href="{paths[p.name]}#section-start">{escape(labels[p.name])}</a></li>' for p in files)
    data['EPUB/nav.xhtml'] = xml_page(contents_label, '<nav epub:type="toc" id="toc"><h1>' + escape(contents_label) + '</h1><ol>' + links + '</ol></nav>', lang)
    # Include the canonical (casefolded) language-pair codes, not the whole translation config,
    # so identical content/metadata built as different language editions (e.g. ru vs es) never
    # collide on the same dc:identifier, while a display-name-only change (e.g. "Spanish" ->
    # "Español" with the same codes) does not spuriously change it.
    language_pair = {'source': translation['source_language']['code'].casefold(),
                      'target': translation['target_language']['code'].casefold()}
    identifier = 'urn:sha256:' + sha256((''.join(p.read_text() for p in files) + json.dumps(metadata, sort_keys=True) + json.dumps(language_pair, sort_keys=True)).encode()).hexdigest()
    points = ''.join(f'<navPoint id="n{i}" playOrder="{i}"><navLabel><text>{escape(labels[p.name])}</text></navLabel><content src="{paths[p.name]}#section-start" /></navPoint>' for i, p in enumerate(files, 1))
    data['EPUB/toc.ncx'] = (f'<?xml version="1.0"?><ncx xmlns="{N}" version="2005-1"><head><meta name="dtb:uid" content="{identifier}"/></head><docTitle><text>{escape(title)}</text></docTitle><navMap>{points}</navMap></ncx>').encode()
    manifest = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/><item id="css" href="style.css" media-type="text/css"/><item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>'
    manifest += ''.join(f'<item id="s{i}" href="{paths[p.name]}" media-type="application/xhtml+xml"/>' for i, p in enumerate(files, 1))
    manifest += ''.join(f'<item id="r{i}" href="{path}" media-type="{mime}"' + (' properties="cover-image"' if path == cover else '') + '/>' for i, (path, mime) in enumerate(sorted(resources.items())))
    spine = '<itemref idref="title"/>' + ''.join(f'<itemref idref="s{i}"/>' for i in range(1, len(files) + 1))
    # Fixed timestamps make equal inputs produce equal bytes; no build-time UUID/date.
    data['EPUB/content.opf'] = (f'<?xml version="1.0"?><package xmlns="{O}" xmlns:dc="{D}" version="3.0" unique-identifier="book-id" xml:lang="{lang}"><metadata><dc:identifier id="book-id">{identifier}</dc:identifier><dc:title>{escape(title)}</dc:title><dc:creator>{escape(author)}</dc:creator><dc:language>{lang}</dc:language><meta property="dcterms:modified">2000-01-01T00:00:00Z</meta></metadata><manifest>{manifest}</manifest><spine toc="ncx">{spine}</spine></package>').encode()
    from zipfile import ZipInfo
    with ZipFile(output, 'w') as z:
        for n in ['mimetype'] + sorted(set(data) - {'mimetype'}):
            info = ZipInfo(n, date_time=(2000, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_STORED if n == 'mimetype' else ZIP_DEFLATED
            z.writestr(info, data[n])
    validate(output, len(files))


def validate(path, expected_sections=None):
    with ZipFile(path) as z:
        # Explicit raises, not assert: python -O must not skip package validation.
        if z.testzip() is not None:
            raise ValueError('Corrupt EPUB archive')
        if z.infolist()[0].filename != 'mimetype' or z.infolist()[0].compress_type != ZIP_STORED:
            raise ValueError('Invalid EPUB mimetype placement')
        if z.read('mimetype') != b'application/epub+zip':
            raise ValueError('Invalid EPUB mimetype content')
        names = set(z.namelist())
        docs = {n: ET.fromstring(z.read(n)) for n in names if n.endswith(('.xml', '.opf', '.ncx', '.xhtml'))}
        ids = {n: {e.attrib.get('id') for e in doc.iter()} for n, doc in docs.items()}
        for n, doc in docs.items():
            for e in doc.iter():
                for attr in ('href', 'src', 'full-path'):
                    href = e.attrib.get(attr)
                    if not href or urlsplit(href).scheme or urlsplit(href).netloc:
                        continue
                    u = urlsplit(href)
                    target = unquote(u.path) if attr == 'full-path' else resolve(n, href) if u.path else n
                    if target not in names:
                        raise ValueError(f'{n}: missing resource {href}')
                    if u.fragment and unquote(u.fragment) not in ids.get(target, set()):
                        raise ValueError(f'{n}: missing anchor {href}')
        if expected_sections is not None:
            count = sum(tag(e) == 'a' for e in docs['EPUB/nav.xhtml'].iter())
            if count != expected_sections:
                raise ValueError(f'Navigation has {count}/{expected_sections} sections')
