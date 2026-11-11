#!/usr/bin/env python3
"""Génère les versions anglaise (en/) et espagnole (es/) du site FlyFast à partir des pages françaises.

Usage :
    python3 build.py <racine du site> [<dossier de sortie>]

  racine du site     dossier qui contient index.html, flyfast-blog/, flyfast-chat.js, sitemap.xml…
  dossier de sortie  copie complète du site, mise à jour (par défaut : la racine elle-même, sur place)

Principe : les pages françaises sont la source de vérité. Pour chaque page, le texte (éléments, attributs
alt/aria-label/placeholder/title, descriptions) est remplacé par sa traduction dans translations.json ; la structure
HTML, les styles et les scripts restent identiques. Le script peut être relancé à volonté : les ajouts qu'il fait aux
pages françaises (sélecteur de langue, balises hreflang) sont encadrés de repères et recalculés à chaque exécution.
"""
import datetime
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from i18nlib import (Doc, find_units, norm, attr_values, rewrite_attrs, expand_fragment, rewrite_url, relpath_to,
                     encode_wa_text, TEXT_ATTRS, META_TEXT, WA_RE)
from urllib.parse import unquote
import index_js
import patch_chat

BASE_URL = 'https://flyfastcheckin.com/'
BUILD_DATE = os.environ.get('BUILD_DATE') or datetime.date.today().isoformat()   # date « lastmod » du plan du site
LANGS = ('fr', 'en', 'es')
LANG_NAMES = {'fr': 'Français', 'en': 'English', 'es': 'Español'}
LANGBAR_LABEL = {'fr': 'Langue', 'en': 'Language', 'es': 'Idioma'}
OG_LOCALE = {'fr': 'fr_FR', 'en': 'en_GB', 'es': 'es_ES'}
CHAT_VERSION = '2'

# Pages : chemin français -> {langue: chemin dans le site}
_SLUGS = [
    # (français, anglais, espagnol) ; les pages traduites vivent dans en/ et es/
    ('index.html', 'index.html', 'index.html'),
    ('flyfast-blog/index.html', 'flyfast-blog/index.html', 'flyfast-blog/index.html'),
    ('flyfast-blog/bagages-soute-cabine-regles.html', 'flyfast-blog/checked-or-cabin-baggage-rules.html',
     'flyfast-blog/equipaje-facturado-o-de-cabina-normas.html'),
    ('flyfast-blog/documents-visa-voyage-europe.html', 'flyfast-blog/essential-documents-travelling-to-europe.html',
     'flyfast-blog/documentos-esenciales-para-viajar-a-europa.html'),
    ('flyfast-blog/enregistrement-en-ligne-guide-complet.html', 'flyfast-blog/how-to-check-in-online-complete-guide.html',
     'flyfast-blog/como-hacer-el-check-in-online-guia-completa.html'),
    ('flyfast-blog/esim-voyageurs-rester-connecte.html', 'flyfast-blog/esim-for-travellers-stay-connected-abroad.html',
     'flyfast-blog/esim-para-viajeros-conectado-en-el-extranjero.html'),
    ('flyfast-blog/jargon-voyage-gds-pnr-eticket.html', 'flyfast-blog/travel-jargon-gds-pnr-eticket.html',
     'flyfast-blog/jerga-del-viaje-gds-pnr-eticket.html'),
    ('confidentialite.html', 'privacy.html', 'privacidad.html'),
    ('mentions-legales.html', 'legal-notice.html', 'aviso-legal.html'),
    ('conditions-de-vente.html', 'terms-of-sale.html', 'condiciones-de-venta.html'),
    ('remboursement.html', 'refunds.html', 'reembolso.html'),
]
PATHS = {fr: {'fr': fr, 'en': 'en/' + en, 'es': 'es/' + es} for fr, en, es in _SLUGS}
LEGAL_PAGES = {'mentions-legales.html', 'conditions-de-vente.html', 'remboursement.html', 'confidentialite.html'}

NOTE_TEXT = {
    'en': 'This page is a courtesy translation of the French original. If there is any difference, the French version prevails.',
    'es': 'Esta página es una traducción de cortesía del original en francés. En caso de discrepancia, prevalece la versión francesa.',
}
NOTE_LINK = {'en': 'Read the French original', 'es': 'Leer el original en francés'}

GENERATED_NOTE = ('<!-- Page générée par _i18n/build.py à partir de la page française et de _i18n/translations.json : '
                  'ne pas la modifier ici. -->\n')

GLOBE = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
         'stroke-linejoin="round" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9"/>'
         '<path d="M3 12h18M12 3c2.6 2.6 3.9 5.6 3.9 9s-1.3 6.4-3.9 9c-2.6-2.6-3.9-5.6-3.9-9s1.3-6.4 3.9-9z"/></svg>')

CSS_BLOCK = """/*i18n*/
  .langbar{background:var(--mist);border-bottom:1px solid var(--line);font-size:.875rem;line-height:1.2;}
  .langbar .container{display:flex;align-items:center;justify-content:flex-end;gap:2px;min-height:38px;}
  .langbar svg{width:16px;height:16px;flex:none;margin-right:6px;color:var(--muted);}
  .langbar a{display:inline-flex;align-items:center;min-height:38px;padding:0 9px;color:var(--muted);font-weight:500;text-decoration:none;}
  .langbar a:hover{color:var(--navy);text-decoration:underline;text-underline-offset:3px;}
  .langbar a[aria-current]{color:var(--navy);font-weight:600;box-shadow:inset 0 -2px 0 var(--sky);}
  .i18n-note{margin-top:20px;max-width:68ch;padding:12px 16px;border-left:4px solid var(--gold);border-radius:0 var(--radius) var(--radius) 0;background:var(--gold-soft,#FFF6DC);color:var(--ink);font-size:.9375rem;line-height:1.5;}
  .i18n-note a{color:var(--sky-text);text-underline-offset:3px;}
/*/i18n*/
"""


def abs_url(path):
    if path == 'index.html':
        return BASE_URL
    if path.endswith('/index.html'):
        return BASE_URL + path[:-len('index.html')]
    return BASE_URL + path


def strip_i18n(src):
    """Retire de la page tout ce que ce script y a ajouté (pour pouvoir le recalculer)."""
    src = re.sub(r'<!--i18n:head-->.*?<!--/i18n:head-->\n', '', src, flags=re.S)
    src = re.sub(r'<!--i18n:langbar-->.*?<!--/i18n:langbar-->\n', '', src, flags=re.S)
    src = re.sub(r'<!--i18n:note-->.*?<!--/i18n:note-->\n?', '', src, flags=re.S)
    src = re.sub(r'/\*i18n\*/.*?/\*/i18n\*/\n', '', src, flags=re.S)
    return src


def tag_name(raw):
    return re.match(r'<([a-zA-Z0-9]+)', raw).group(1).lower()


class Translator:
    def __init__(self, memo, lang, fr_path):
        self.memo, self.lang, self.fr_path = memo, lang, fr_path
        self.new_path = PATHS[fr_path][lang]
        self.page_map = {k: v[lang] for k, v in PATHS.items()}
        self.missing = []

    def tr(self, key):
        key = norm(key)
        if key not in self.memo:
            self.missing.append(key)
            return key
        return self.memo[key][self.lang]

    def attr_fn(self, raw):
        tag = tag_name(raw)
        names = dict(attr_values(raw))

        def fn(name, val):
            if tag == 'html' and name == 'lang':
                return self.lang
            if name in TEXT_ATTRS and val.strip():
                return self.tr(val)
            if name == 'content' and tag == 'meta':
                if names.get('property') == 'og:locale':
                    return OG_LOCALE[self.lang]
                for a, b in META_TEXT:
                    if names.get(a) == b:
                        return self.tr(val)
                return None
            if name == 'href':
                m = WA_RE.match(val)
                if m:
                    return m.group(1) + encode_wa_text(self.tr(unquote(m.group(2))))
                if tag == 'link' and names.get('rel') == 'canonical':
                    return abs_url(self.new_path)
                return rewrite_url(val, self.fr_path, self.new_path, self.page_map)
            if name == 'src':
                return rewrite_url(val, self.fr_path, self.new_path, self.page_map)
            return None
        return fn

    def start_tag(self, raw):
        return rewrite_attrs(raw, self.attr_fn(raw))


def translate_source(fr_src, fr_path, lang, memo):
    """Page française (sans ajouts) -> même page dans la langue demandée (texte et liens seulement)."""
    doc = Doc(fr_src)
    t = Translator(memo, lang, fr_path)
    edits = []
    inner = set()
    for u in find_units(doc):
        a, b = doc.toks[u.node.s][4], doc.toks[u.node.e][1]
        old_inner = fr_src[a:b]
        lead = re.match(r'\s*', old_inner).group(0)
        trail = re.search(r'\s*$', old_inner).group(0)
        new_inner = lead + expand_fragment(t.tr(u.key), u.holders, t.start_tag) + trail
        edits.append((a, b, new_inner))
        inner.update(range(u.node.s + 1, u.node.e))
    for i, tok in enumerate(doc.toks):
        if tok[0] in ('start', 'startend') and i not in inner:
            raw = doc.raw(i)
            new = t.start_tag(raw)
            if new != raw:
                edits.append((tok[1], tok[4], new))
    edits.sort()
    out, pos = [], 0
    for a, b, text in edits:
        assert a >= pos, ('modifications qui se chevauchent', a, pos)
        out.append(fr_src[pos:a])
        out.append(text)
        pos = b
    out.append(fr_src[pos:])
    return ''.join(out), t.missing


def insert_once(src, anchor, text, before=True, what=''):
    assert src.count(anchor) == 1, f'{src.count(anchor)} ancre(s) « {anchor[:50]} » ({what})'
    i = src.index(anchor)
    if not before:
        i += len(anchor)
    return src[:i] + text + src[i:]


def head_block(fr_path, lang, need_canonical):
    lines = ['<!--i18n:head-->']
    if need_canonical:
        lines.append(f'<link rel="canonical" href="{abs_url(PATHS[fr_path][lang])}">')
    for lg in LANGS:
        lines.append(f'<link rel="alternate" hreflang="{lg}" href="{abs_url(PATHS[fr_path][lg])}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{abs_url(PATHS[fr_path]["fr"])}">')
    lines.append('<!--/i18n:head-->')
    return '\n'.join(lines) + '\n'


def langbar_block(fr_path, lang):
    here = PATHS[fr_path][lang]
    links = []
    for lg in LANGS:
        cur = ' aria-current="true"' if lg == lang else ''
        links.append(f'<a href="{relpath_to(PATHS[fr_path][lg], here)}" lang="{lg}" hreflang="{lg}"{cur}>{LANG_NAMES[lg]}</a>')
    return ('<!--i18n:langbar-->\n'
            f'<nav class="langbar" aria-label="{LANGBAR_LABEL[lang]}">\n'
            f'  <div class="container">{GLOBE}{"".join(links)}</div>\n'
            '</nav>\n'
            '<!--/i18n:langbar-->\n')


def note_block(fr_path, lang):
    here = PATHS[fr_path][lang]
    href = relpath_to(PATHS[fr_path]['fr'], here)
    return ('<!--i18n:note-->'
            f'<p class="i18n-note">{NOTE_TEXT[lang]} <a href="{href}" hreflang="fr">{NOTE_LINK[lang]}</a>.</p>'
            '<!--/i18n:note-->\n')


def decorate(src, fr_path, lang):
    """Ajoute à une page (déjà dans sa langue) : hreflang/canonical, sélecteur de langue, styles, version du chat."""
    src = re.sub(r'(flyfast-chat\.js)\?v=\d+', r'\1?v=' + CHAT_VERSION, src)
    need_canonical = not re.search(r'<link[^>]+rel="canonical"', src)
    src = insert_once(src, '<link rel="icon"', head_block(fr_path, lang, need_canonical), True, 'icône')
    src = insert_once(src, '</style>', CSS_BLOCK, True, 'styles')
    src = insert_once(src, '<header class="site-header">', langbar_block(fr_path, lang), True, 'en-tête')
    if lang != 'fr' and fr_path in LEGAL_PAGES:
        m = re.search(r'</h1>\s*(<p class="lead">.*?</p>)?', src, re.S)
        assert m, 'titre introuvable'
        src = src[:m.end()] + '\n    ' + note_block(fr_path, lang).rstrip('\n') + src[m.end():]
    return src


def patch_home_script(src, lang):
    """Traduit le script de la page d'accueil (messages des formulaires)."""
    m = re.search(r'<script>\n(\(function \(\) \{.*?)</script>', src, re.S)
    assert m, 'script de la page d’accueil introuvable'
    return src[:m.start(1)] + index_js.patch_script(m.group(1), lang) + src[m.end(1):]


def build_sitemap():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for lang in LANGS:
        for fr_path, _, _ in _SLUGS:
            lines.append('  <url>')
            lines.append(f'    <loc>{abs_url(PATHS[fr_path][lang])}</loc>')
            lines.append(f'    <lastmod>{BUILD_DATE}</lastmod>')
            for lg in LANGS:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{lg}" href="{abs_url(PATHS[fr_path][lg])}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{abs_url(PATHS[fr_path]["fr"])}"/>')
            lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


def main():
    root = os.path.abspath(sys.argv[1])
    out = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else root
    if out != root:
        if os.path.exists(out):
            shutil.rmtree(out)
        shutil.copytree(root, out, ignore=shutil.ignore_patterns('.git'))
    memo = json.load(open(os.path.join(HERE, 'translations.json'), encoding='utf-8'))

    # Script du chat : partir de la version française d'origine
    fr_chat = os.path.join(HERE, 'flyfast-chat.fr.js')
    chat_src = open(fr_chat if os.path.exists(fr_chat) else os.path.join(out, 'flyfast-chat.js'), encoding='utf-8').read()
    assert 'var STRINGS = {' not in chat_src, 'flyfast-chat.fr.js doit être la version française d’origine'
    chat_out = ('/* Fichier généré par _i18n/build.py à partir de _i18n/flyfast-chat.fr.js : ne pas le modifier ici. */\n'
                + patch_chat.patch_chat(chat_src))
    open(os.path.join(out, 'flyfast-chat.js'), 'w', encoding='utf-8').write(chat_out)

    all_missing = {}
    written = []
    for fr_path in PATHS:
        fr_file = os.path.join(out, fr_path)
        fr_src = strip_i18n(open(fr_file, encoding='utf-8').read())
        # français : ajouts seulement
        open(fr_file, 'w', encoding='utf-8').write(decorate(fr_src, fr_path, 'fr'))
        written.append(fr_path)
        for lang in ('en', 'es'):
            page, missing = translate_source(fr_src, fr_path, lang, memo)
            if missing:
                all_missing.setdefault(fr_path, []).extend(missing)
            if fr_path == 'index.html':
                page = patch_home_script(page, lang)
            page = decorate(page, fr_path, lang)
            page = insert_once(page, '<head>\n', GENERATED_NOTE, False, 'tête')
            dest = os.path.join(out, PATHS[fr_path][lang])
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            open(dest, 'w', encoding='utf-8').write(page)
            written.append(PATHS[fr_path][lang])
    if all_missing:
        for p, keys in all_missing.items():
            print('TRADUCTION MANQUANTE dans', p)
            for k in keys:
                print('   ', k[:120])
        sys.exit(1)
    open(os.path.join(out, 'sitemap.xml'), 'w', encoding='utf-8').write(build_sitemap())
    print(f'{len(written)} pages écrites, sitemap et flyfast-chat.js mis à jour dans {out}')


if __name__ == '__main__':
    main()
