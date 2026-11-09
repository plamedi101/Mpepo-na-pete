#!/usr/bin/env python3
"""Contrôles statiques des 33 pages (fr/en/es) : langue, canonical, hreflang, sélecteur, liens, sitemap, mesure d'audience.
Usage : python3 test_static.py <racine du site>"""
import json
import os
import re
import sys
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402
from i18nlib import norm  # noqa: E402

ROOT = os.path.abspath(sys.argv[1])
MEMO = json.load(open(os.path.join(HERE, 'translations.json'), encoding='utf-8'))
BEACON = 'https://static.cloudflareinsights.com/beacon.min.js'
TOKEN = '10a100695f7446c691727c713ffb19c8'

ok = ko = 0


def check(name, cond, detail=''):
    global ok, ko
    if cond:
        ok += 1
    else:
        ko += 1
        print('ÉCHEC', name, '→', detail)


def read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def visible_text(soup):
    s = BeautifulSoup(str(soup), 'lxml')
    for t in s(['script', 'style', 'svg', 'noscript']):
        t.decompose()
    return s.body.get_text(' ', strip=True)


def attr_texts(soup):
    out = []
    for el in soup.find_all(True):
        for a in ('alt', 'placeholder', 'aria-label', 'title'):
            if el.get(a):
                out.append(el[a])
    for m in soup.find_all('meta'):
        if m.get('name') == 'description' or m.get('property') in ('og:title', 'og:description'):
            out.append(m.get('content', ''))
    if soup.title:
        out.append(soup.title.get_text())
    return out


FR_ONLY = re.compile(r"\b(vous|votre|vos|nous|notre|nos|avec|dans|les|des|sont|aux|qui|mais|où|cette|ces|leur|leurs|être|avoir|très|aussi|peut|peuvent|enregistrement|réservation|billet|passeport|compagnie|vol)\b", re.I)
ES_AMBIGUOUS = {'nos', 'les', 'billet', 'vol', 'des', 'dans', 'ces', 'mais'}  # mots qui peuvent exister en espagnol/anglais
EN_ACCENT = re.compile(r'[àâçéèêëîïôûùüÿœñ¿¡áíóú]', re.I)
ALLOWED = {'Français', 'Español'}

LANG_FILES = {lg: [(fr, v[lg]) for fr, v in build.PATHS.items()] for lg in build.LANGS}
pages = [(fr, lg, path) for lg in build.LANGS for fr, path in LANG_FILES[lg]]
check('33 pages attendues', len(pages) == 33 and all(os.path.exists(os.path.join(ROOT, p)) for _, _, p in pages), len(pages))

alternates_by_page = {}
for fr, lg, path in pages:
    h = read(path)
    soup = BeautifulSoup(h, 'lxml')
    tag = f'[{path}]'
    check(f'{tag} <html lang>', soup.html.get('lang') == lg, soup.html.get('lang'))
    loc = {'fr': 'fr_FR', 'en': 'en_GB', 'es': 'es_ES'}[lg]
    og = [m.get('content') for m in soup.find_all('meta', property='og:locale')]
    check(f'{tag} og:locale', og == [loc], og)
    canon = [l.get('href') for l in soup.find_all('link', rel='canonical')]
    check(f'{tag} un seul canonical, vers la page elle-même', canon == [build.abs_url(path)], canon)
    alts = {l.get('hreflang'): l.get('href') for l in soup.find_all('link', rel='alternate') if l.get('hreflang')}
    want = {k: build.abs_url(build.PATHS[fr][k]) for k in build.LANGS}
    want['x-default'] = build.abs_url(build.PATHS[fr]['fr'])
    check(f'{tag} hreflang fr/en/es/x-default', alts == want, alts)
    alternates_by_page.setdefault(fr, []).append(alts)
    check(f'{tag} hreflang : un seul bloc', h.count('<!--i18n:head-->') == 1 and h.count('<!--/i18n:head-->') == 1)

    # sélecteur de langue
    bar = soup.find('nav', class_='langbar')
    check(f'{tag} sélecteur de langue présent, avant l’en-tête', bar is not None and bar.find_next('header', class_='site-header') is not None
          and h.index('class="langbar"') < h.index('class="site-header"'))
    if bar:
        links = bar.find_all('a')
        check(f'{tag} sélecteur : 3 liens fr/en/es', [a.get('lang') for a in links] == ['fr', 'en', 'es'] and [a.get('hreflang') for a in links] == ['fr', 'en', 'es'])
        check(f'{tag} sélecteur : noms de langue', [a.get_text() for a in links] == ['Français', 'English', 'Español'], [a.get_text() for a in links])
        cur = [a.get('lang') for a in links if a.get('aria-current')]
        check(f'{tag} sélecteur : langue courante marquée', cur == [lg], cur)
        for a in links:
            target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(ROOT, path)), a['href']))
            expect = os.path.normpath(os.path.join(ROOT, build.PATHS[fr][a['lang']]))
            check(f'{tag} sélecteur : lien {a["lang"]} → bonne page', target == expect, (a['href'], target, expect))
        check(f'{tag} sélecteur : nom accessible', bar.get('aria-label') == build.LANGBAR_LABEL[lg], bar.get('aria-label'))

    # script du chat et mesure d'audience
    scripts = [s for s in soup.find_all('script') if s.get('src')]
    chat = [s for s in scripts if 'flyfast-chat.js' in s['src']]
    check(f'{tag} un seul script de chat, version {build.CHAT_VERSION}', len(chat) == 1 and chat[0]['src'].endswith('flyfast-chat.js?v=' + build.CHAT_VERSION), [s['src'] for s in chat])
    if chat:
        target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(ROOT, path)), chat[0]['src'].split('?')[0]))
        check(f'{tag} le script du chat existe', os.path.exists(target), target)
        fr_base = BeautifulSoup(read(fr), 'lxml').find('script', src=re.compile('flyfast-chat')).get('data-base')
        check(f'{tag} data-base identique au français', chat[0].get('data-base') == fr_base, (chat[0].get('data-base'), fr_base))
    check(f'{tag} un seul script de mesure, jeton attendu, avant </body>', h.count(BEACON) == 1 and TOKEN in h and h.index(BEACON) < h.rindex('</body>'))

    # une seule page <h1>, ids uniques
    ids = [e.get('id') for e in soup.find_all(id=True)]
    check(f'{tag} ids uniques', len(ids) == len(set(ids)), [i for i in ids if ids.count(i) > 1])
    check(f'{tag} un seul h1', len(soup.find_all('h1')) == 1)

    # note de traduction : seulement sur les pages légales traduites
    notes = soup.find_all('p', class_='i18n-note')
    expect_note = (lg != 'fr' and fr in build.LEGAL_PAGES)
    check(f'{tag} note de traduction {"présente" if expect_note else "absente"}', len(notes) == (1 if expect_note else 0), len(notes))
    if expect_note and notes:
        link = notes[0].find('a')
        target = os.path.normpath(os.path.join(os.path.dirname(os.path.join(ROOT, path)), link['href']))
        check(f'{tag} note : lien vers l’original français', target == os.path.normpath(os.path.join(ROOT, fr)) and link.get('hreflang') == 'fr', link['href'])
        check(f'{tag} note : texte attendu', build.NOTE_TEXT[lg] in notes[0].get_text(' ', strip=True))

    # texte restant en français ?
    if lg != 'fr':
        texts = [visible_text(soup)] + attr_texts(soup)
        blob = ' '.join(texts)
        for w in ALLOWED:
            blob = blob.replace(w, ' ')
        hits = {m.group(0).lower() for m in FR_ONLY.finditer(blob)}
        if lg == 'es':
            hits -= ES_AMBIGUOUS
        if lg == 'en':
            hits -= {'passeport'} if False else set()
            check(f'{tag} aucun caractère accentué dans le texte anglais', not EN_ACCENT.search(blob), EN_ACCENT.findall(blob)[:10])
        check(f'{tag} aucun mot français résiduel', not hits, sorted(hits))
        # wa.me : texte prérempli dans la langue de la page
        for a in soup.find_all('a', href=re.compile(r'^https://wa\.me/\d+\?text=')):
            txt = unquote(a['href'].split('?text=', 1)[1])
            check(f'{tag} lien WhatsApp prérempli traduit', txt in {v[lg] for v in MEMO.values()}, txt)
    else:
        # français : aucun texte anglais/espagnol ajouté en dehors du sélecteur et des balises
        check(f'{tag} pas de note de traduction ni de texte étranger', 'courtesy translation' not in h and 'traducción de cortesía' not in h)

# structure HTML identique entre la page française et ses traductions (mêmes balises, dans le même ordre)
from i18nlib import Doc  # noqa: E402


def shape(src):
    return [(t[0], t[2]) for t in Doc(src).toks if t[0] in ('start', 'startend', 'end')]


for fr in build.PATHS:
    base = shape(build.strip_i18n(read(fr)))
    for lg in ('en', 'es'):
        got = shape(build.strip_i18n(read(build.PATHS[fr][lg])))
        check(f'[{build.PATHS[fr][lg]}] même structure HTML que la page française', base == got, (len(base), len(got)))

# cohérence des ensembles hreflang entre versions d'une même page
for fr, sets in alternates_by_page.items():
    check(f'[{fr}] mêmes balises hreflang dans les 3 langues', sets[0] == sets[1] == sets[2])

# sitemap
sm = read('sitemap.xml')
locs = re.findall(r'<loc>(.*?)</loc>', sm)
check('sitemap : 33 adresses distinctes', len(locs) == 33 and len(set(locs)) == 33, len(locs))
expected = {build.abs_url(p) for _, _, p in pages}
check('sitemap : adresses = pages du site', set(locs) == expected, set(locs) ^ expected)
check('sitemap : chaque adresse correspond à un fichier', all(os.path.exists(os.path.join(ROOT, unquote(urlsplit(u).path[len('/Mpepo-na-pete/'):]) or 'index.html') if not u.endswith('/') else os.path.join(ROOT, unquote(urlsplit(u).path[len('/Mpepo-na-pete/'):]), 'index.html')) for u in locs))
entries = re.findall(r'<url>(.*?)</url>', sm, re.S)
bad = []
for e in entries:
    loc = re.search(r'<loc>(.*?)</loc>', e).group(1)
    alts = dict(re.findall(r'hreflang="([^"]+)" href="([^"]+)"', e))
    if set(alts) != {'fr', 'en', 'es', 'x-default'} or loc not in alts.values():
        bad.append(loc)
check('sitemap : 4 alternatives par adresse, dont elle-même', not bad, bad)
check('sitemap : XML bien formé', BeautifulSoup(sm, 'xml').find('urlset') is not None)

# pages hors périmètre inchangées
stub = read('flyfast-blog/documents-visa-rdc-europe.html')
check('page de redirection ancienne : inchangée (sans sélecteur ni hreflang)', 'langbar' not in stub and 'hreflang' not in stub and 'cloudflareinsights' not in stub)

print(f'{ok}/{ok + ko} contrôles statiques réussis')
sys.exit(1 if ko else 0)
