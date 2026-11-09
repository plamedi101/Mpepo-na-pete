#!/usr/bin/env python3
"""Bibliothèque de traduction des pages FlyFast (aucune dépendance externe).

Principe : les pages françaises sont la source. On les découpe en « segments » de texte (un segment = le contenu
d'un élément qui porte du texte, avec ses balises internes remplacées par des repères numérotés), on les traduit
dans un dictionnaire, puis on réécrit chaque page à l'identique en remplaçant seulement les textes.

Repères dans un segment :
  <a1>…</a1>, <strong1>…</strong1>, <span2>…</span2>   balise ouvrante/fermante d'origine (attributs conservés)
  {svg1}                                                 dessin SVG d'origine
  <br>                                                   saut de ligne
"""
import re
import posixpath
from html.parser import HTMLParser
from urllib.parse import quote, unquote

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
OPAQUE = {'script', 'style', 'svg'}                    # contenus jamais découpés en segments
TEXT_ATTRS = ('alt', 'placeholder', 'aria-label', 'title')
BLOCKISH = {'div', 'p', 'ul', 'ol', 'li', 'section', 'article', 'aside', 'nav', 'header', 'footer', 'main', 'form',
            'fieldset', 'table', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'details', 'summary', 'figure', 'blockquote'}
META_TEXT = {('name', 'description'), ('property', 'og:title'), ('property', 'og:description')}
WA_RE = re.compile(r'^(https://wa\.me/\d+\?text=)(.*)$')
PLACEHOLDER_RE = re.compile(r'</?[a-z]+\d*>|\{svg\d+\}')


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


# ---------------------------------------------------------------- découpage en jetons (conserve chaque octet)

class _Tokenizer(HTMLParser):
    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.line_offsets = [0]
        for m in re.finditer('\n', src):
            self.line_offsets.append(m.end())
        self.toks = []

    def _pos(self):
        line, col = self.getpos()
        return self.line_offsets[line - 1] + col

    def _add(self, kind, tag=None, attrs=None):
        self.toks.append([kind, self._pos(), tag, attrs])

    def handle_starttag(self, tag, attrs): self._add('start', tag, attrs)
    def handle_startendtag(self, tag, attrs): self._add('startend', tag, attrs)
    def handle_endtag(self, tag): self._add('end', tag)
    def handle_data(self, data): self._add('text')
    def handle_entityref(self, name): self._add('text')
    def handle_charref(self, name): self._add('text')
    def handle_comment(self, data): self._add('comment')
    def handle_decl(self, decl): self._add('decl')
    def handle_pi(self, data): self._add('pi')
    def unknown_decl(self, data): self._add('decl')


class Node:
    __slots__ = ('tag', 's', 'e', 'kids', 'parent')

    def __init__(self, tag, s, parent):
        self.tag, self.s, self.e, self.kids, self.parent = tag, s, s, [], parent


class Doc:
    """Un document découpé en jetons (chaque jeton garde son texte brut) et un arbre d'éléments."""

    def __init__(self, src):
        self.src = src
        tk = _Tokenizer(src)
        tk.feed(src)
        tk.close()
        self.toks = tk.toks
        # fusionner les jetons de texte adjacents et calculer les positions de fin
        merged = []
        for t in self.toks:
            if merged and t[0] == 'text' and merged[-1][0] == 'text':
                continue
            merged.append(t)
        self.toks = merged
        for i, t in enumerate(self.toks):
            t.append(self.toks[i + 1][1] if i + 1 < len(self.toks) else len(src))   # t[4] = fin
        self._check_tokens()
        self.root = self._build()

    def raw(self, i):
        t = self.toks[i]
        return self.src[t[1]:t[4]]

    def _check_tokens(self):
        assert self.toks[0][1] == 0
        for i, t in enumerate(self.toks):
            raw = self.raw(i)
            if t[0] in ('start', 'startend'):
                assert raw.lower().startswith('<' + t[2]), (raw[:60], t[2])
            elif t[0] == 'end':
                assert raw.lower().startswith('</' + t[2]), (raw[:60], t[2])
            elif t[0] == 'comment':
                assert raw.startswith('<!--'), raw[:40]

    def _build(self):
        root = Node('#root', -1, None)
        stack = [root]
        for i, t in enumerate(self.toks):
            kind, _, tag = t[0], t[1], t[2]
            top = stack[-1]
            if kind == 'start':
                n = Node(tag, i, top)
                top.kids.append(n)
                if tag not in VOID:
                    stack.append(n)
            elif kind == 'startend':
                n = Node(tag, i, top)
                top.kids.append(n)
            elif kind == 'end':
                if tag in VOID:
                    continue
                if top.tag != tag:
                    raise ValueError(f'balise <{top.tag}> (jeton {top.s}, «{self.raw(top.s)[:50]}») non fermée avant </{tag}>')
                top.e = i
                stack.pop()
            else:
                top.kids.append(i)
        if len(stack) != 1:
            raise ValueError('balises non fermées : ' + ', '.join(n.tag for n in stack[1:]))
        return root


# ---------------------------------------------------------------- attributs d'une balise ouvrante

ATTR_RE = re.compile(r'''(\s)([^\s"'<>/=]+)(\s*=\s*)("([^"]*)"|'([^']*)'|([^\s"'>]+))''')


def attr_values(raw):
    """Renvoie [(nom, valeur brute)] pour une balise ouvrante."""
    out = []
    for m in ATTR_RE.finditer(raw):
        v = m.group(5) if m.group(5) is not None else (m.group(6) if m.group(6) is not None else m.group(7))
        out.append((m.group(2).lower(), v))
    return out


def rewrite_attrs(raw, fn):
    """Remplace la valeur de chaque attribut par fn(nom, valeur) (None = inchangé)."""
    def sub(m):
        name = m.group(2).lower()
        quote_ch = '"' if m.group(5) is not None else ("'" if m.group(6) is not None else '"')
        val = m.group(5) if m.group(5) is not None else (m.group(6) if m.group(6) is not None else m.group(7))
        new = fn(name, val)
        if new is None or new == val:
            return m.group(0)
        if quote_ch == '"':
            new = new.replace('"', '&quot;')
        return m.group(1) + m.group(2) + m.group(3) + quote_ch + new + quote_ch
    return ATTR_RE.sub(sub, raw)


# ---------------------------------------------------------------- unités de texte

def _has_text(doc, node):
    for k in node.kids:
        if isinstance(k, int) and doc.toks[k][0] == 'text' and doc.raw(k).strip():
            return True
    return False


class Unit:
    __slots__ = ('node', 'key', 'holders')

    def __init__(self, node, key, holders):
        self.node, self.key, self.holders = node, key, holders   # holders : repère -> texte brut d'origine


def _render_inner(doc, node, holders, counters):
    """Texte interne d'un élément, balises remplacées par des repères."""
    out = []
    for k in node.kids:
        if isinstance(k, int):
            t = doc.toks[k]
            if t[0] == 'text':
                out.append(doc.raw(k))
            elif t[0] == 'comment':
                pass
            continue
        tag = k.tag
        if tag == 'svg':
            counters['svg'] = counters.get('svg', 0) + 1
            name = f'svg{counters["svg"]}'
            holders[name] = doc.src[doc.toks[k.s][1]:doc.toks[k.e][4]]
            out.append('{' + name + '}')
        elif tag == 'br':
            out.append('<br>')
        elif tag in VOID or doc.toks[k.s][0] == 'startend':
            counters[tag] = counters.get(tag, 0) + 1
            name = f'{tag}{counters[tag]}'
            holders[name] = doc.raw(k.s)
            out.append(f'<{name}>')
        else:
            counters[tag] = counters.get(tag, 0) + 1
            name = f'{tag}{counters[tag]}'
            holders[name] = doc.raw(k.s)            # balise ouvrante d'origine
            out.append(f'<{name}>' + _render_inner(doc, k, holders, counters) + f'</{name}>')
    return ''.join(out)


def find_units(doc, warn=None):
    """Éléments portant du texte (hors script/style/svg), dans l'ordre du document."""
    units = []

    def walk(node):
        for k in node.kids:
            if isinstance(k, int):
                continue
            if k.tag in OPAQUE:
                continue
            if _has_text(doc, k):
                holders, counters = {}, {}
                key = norm(_render_inner(doc, k, holders, counters))
                units.append(Unit(k, key, holders))
                if warn is not None:
                    inner_tags = {n for n in re.findall(r'<([a-z]+)\d+>', key)}
                    if inner_tags & BLOCKISH:
                        warn(f'bloc imbriqué dans un segment : {key[:80]}')
            else:
                walk(k)

    walk(doc.root)
    return units


def start_tag_attr_segments(raw, tag):
    """Valeurs d'attribut à traduire dans une balise ouvrante : liste de textes bruts."""
    segs = []
    attrs = attr_values(raw)
    names = dict(attrs)
    for name, val in attrs:
        if name in TEXT_ATTRS and val.strip():
            segs.append(val)
        elif name == 'content' and tag == 'meta':
            for (a, b) in META_TEXT:
                if names.get(a) == b:
                    segs.append(val)
        elif name == 'href':
            m = WA_RE.match(val)
            if m:
                segs.append(unquote(m.group(2)))
    return segs


def all_attr_segments(doc):
    """Segments d'attributs, dans l'ordre du document (hors contenu des script/style)."""
    segs = []
    skip_depth = 0
    for i, t in enumerate(doc.toks):
        if t[0] in ('start', 'startend'):
            segs.extend(start_tag_attr_segments(doc.raw(i), t[2]))
    return segs


# ---------------------------------------------------------------- vérification des repères

def tokens_of(s):
    return PLACEHOLDER_RE.findall(s)


def check_fragment(fr_key, tr, where=''):
    """Même repères, même nombre, imbrication correcte. Renvoie la liste des problèmes."""
    problems = []
    a, b = sorted(tokens_of(fr_key)), sorted(tokens_of(tr))
    if a != b:
        problems.append(f'{where}repères différents : {a} ≠ {b}')
        return problems
    stack = []
    for tk in tokens_of(tr):
        if tk.startswith('</'):
            name = tk[2:-1]
            if not stack or stack[-1] != name:
                problems.append(f'{where}imbrication incorrecte autour de </{name}>')
                break
            stack.pop()
        elif tk.startswith('<') and tk != '<br>':
            stack.append(tk[1:-1])
    if stack:
        problems.append(f'{where}balises non fermées : {stack}')
    # pas d'autre balise HTML, pas de & isolé
    rest = PLACEHOLDER_RE.sub('', tr)
    if re.search(r'<|>', rest):
        problems.append(f'{where}chevron isolé dans « {rest[:60]} »')
    if re.search(r'&(?!(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);)', tr):
        problems.append(f'{where}« & » non échappé dans « {tr[:60]} »')
    return problems


def expand_fragment(tr, holders, start_tag_fn):
    """Remplace les repères par le balisage d'origine (balises ouvrantes passées par start_tag_fn)."""
    def sub(m):
        tk = m.group(0)
        if tk == '<br>':
            return '<br>'
        if tk.startswith('{svg'):
            return holders[tk[1:-1]]
        if tk.startswith('</'):
            name = tk[2:-1]
            return '</' + re.sub(r'\d+$', '', name) + '>'
        name = tk[1:-1]
        return start_tag_fn(holders[name])
    return PLACEHOLDER_RE.sub(sub, tr)


# ---------------------------------------------------------------- liens relatifs entre langues

def relpath_to(target, from_file):
    d = posixpath.dirname(from_file) or '.'
    r = posixpath.relpath(target, d)
    return r


def rewrite_url(value, fr_file, new_file, page_map):
    """Réécrit un lien relatif d'une page française pour la page `new_file`.

    page_map : chemin français -> chemin dans la langue cible (pages traduites). Les autres fichiers (images,
    script) restent à leur place. Les liens absolus, ancres seules, mailto:, tel:, data: sont inchangés.
    """
    if not value or value.startswith('#') or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', value) or value.startswith('//'):
        return value
    m = re.match(r'^([^?#]*)(\?[^#]*)?(#.*)?$', value)
    path, query, frag = m.group(1), m.group(2) or '', m.group(3) or ''
    if path == '':
        return value
    target = posixpath.normpath(posixpath.join(posixpath.dirname(fr_file), path))
    if path.endswith('/'):
        target = target.rstrip('/') + '/'
    target = page_map.get(target, target)
    return relpath_to(target, new_file) + query + frag


def encode_wa_text(text):
    return quote(text, safe="-_.!~*'()")
