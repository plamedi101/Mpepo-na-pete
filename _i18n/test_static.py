#!/usr/bin/env python3
"""Contrôles statiques des 36 pages (fr/en/es) : langue, canonical, hreflang, sélecteur, liens, sitemap, mesure d'audience, liens partenaires.
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
check('36 pages attendues', len(pages) == 36 and all(os.path.exists(os.path.join(ROOT, p)) for _, _, p in pages), len(pages))

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

    # bandeau de l'offre de lancement (build.PROMO ; None = aucun bandeau)
    promos = soup.find_all('aside', class_='promo')
    if build.PROMO:
        p_label, p_lead, p_text = build.PROMO[lg]
        flat = lambda s: re.sub(r'\s+', ' ', s).strip()  # noqa: E731
        want_text = flat(BeautifulSoup(f'<p><strong>{p_lead}</strong> {p_text}</p>', 'lxml').get_text())
        check(f'{tag} bandeau de lancement : un seul, entre le sélecteur de langue et l’en-tête',
              len(promos) == 1 and h.count('<!--i18n:promo-->') == 1
              and h.index('class="langbar"') < h.index('class="promo"') < h.index('class="site-header"'))
        if promos:
            check(f'{tag} bandeau : nom accessible et texte dans la langue de la page',
                  promos[0].get('aria-label') == p_label and flat(promos[0].get_text()) == want_text, flat(promos[0].get_text()))
    else:
        check(f'{tag} aucun bandeau de lancement', not promos and '<!--i18n:promo-->' not in h)

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

    # affiliation Travelpayouts « Drive » (build.TP_DRIVE_SRC ; None = aucun script)
    # règle voulue : blog = bandeau de consentement (flyfast-consent.js) qui ne charge Drive qu'après « Accepter » ;
    # accueil (formulaires, passeport) = seulement pour la vérification Travelpayouts (?init_marker=), sans bandeau ; pages légales = rien
    tp_src = build.TP_DRIVE_SRC
    tp = re.findall(r'<!--i18n:tp-->(.*?)<!--/i18n:tp-->', h, re.S)
    consent_tags = [s for s in scripts if 'flyfast-consent' in s['src']]
    if not tp_src:
        check(f'{tag} aucune affiliation Travelpayouts', not tp and '<!--i18n:tp-->' not in h and 'emrldco' not in h and 'flyfast-consent' not in h)
    else:
        want_mode = 'verify' if fr == 'index.html' else 'consent' if fr.startswith('flyfast-blog/') else None
        check(f'{tag} affiliation : règle de chargement attendue ({want_mode or "aucun script"})', build.tp_mode(fr) == want_mode, build.tp_mode(fr))
        if want_mode is None:
            check(f'{tag} affiliation : ni script Travelpayouts ni bandeau sur cette page',
                  not tp and '<!--i18n:tp-->' not in h and 'emrldco' not in h and 'flyfast-consent' not in h)
        else:
            in_head = h.count('<!--i18n:tp-->') == 1 and h.count('<!--/i18n:tp-->') == 1 and h.index('<!--i18n:tp-->') < h.index('</head>') < h.index('<body')
            check(f'{tag} affiliation : un seul bloc Travelpayouts, dans l’en-tête', len(tp) == 1 and in_head, len(tp))
            if tp and want_mode == 'verify':
                blk = tp[0]
                check(f'{tag} affiliation : script attendu, ajouté une seule fois', blk.count(tp_src) == 1 and h.count(tp_src) == 1
                      and blk.count('document.head.appendChild(script)') == 1, blk)
                check(f'{tag} affiliation : une seule adresse, en https, sur le domaine Travelpayouts', re.findall(r'https?://[^\s\'"]+', blk) == [tp_src], blk)
                check(f'{tag} affiliation : chargement limité à ?init_marker= (page à formulaires)',
                      'init_marker' in blk and blk.index('init_marker') < blk.index('document.createElement') < blk.index(tp_src), blk)
                check(f'{tag} affiliation : pas de bandeau de consentement sur la page à formulaires', not consent_tags and 'flyfast-consent' not in h)
            if tp and want_mode == 'consent':
                blk = tp[0]
                cs = consent_tags[0] if len(consent_tags) == 1 else None
                check(f'{tag} bandeau : un seul script flyfast-consent.js, dans le bloc, en defer, version {build.CONSENT_VERSION}',
                      cs is not None and cs.has_attr('defer') and cs['src'].endswith('flyfast-consent.js?v=' + build.CONSENT_VERSION) and 'flyfast-consent.js' in blk,
                      [s['src'] for s in consent_tags])
                if cs is not None:
                    here_dir = os.path.dirname(os.path.join(ROOT, path))
                    check(f'{tag} bandeau : le fichier du script existe', os.path.exists(os.path.normpath(os.path.join(here_dir, cs['src'].split('?')[0]))), cs['src'])
                    check(f'{tag} bandeau : adresse du script Travelpayouts passée par data-drive, et nulle part ailleurs dans la page',
                          cs.get('data-drive') == tp_src and h.count(tp_src) == 1, cs.get('data-drive'))
                    check(f'{tag} bandeau : le bloc ne charge rien lui-même (aucun code de chargement, aucune autre adresse)',
                          'createElement' not in blk and 'appendChild' not in blk and re.findall(r'https?://[^\s\'"]+', blk) == [tp_src], blk)
                    dp_page, _, dp_frag = cs.get('data-privacy', '').partition('#')
                    want_priv = build.PATHS['confidentialite.html'][lg]
                    check(f'{tag} bandeau : data-privacy → section « Liens partenaires » de la page Confidentialité, dans la langue de la page',
                          os.path.normpath(os.path.join(here_dir, dp_page)) == os.path.normpath(os.path.join(ROOT, want_priv)) and dp_frag == build.PRIVACY_ANCHOR,
                          cs.get('data-privacy'))
                    foot = [a.get('href') for a in soup.select('.site-footer a[href]')]
                    check(f'{tag} bandeau : le pied de page a le lien Confidentialité (le lien « Gérer les cookies » s’y place)', dp_page in foot, (dp_page, foot))
            check(f'{tag} affiliation : aucun <script src> Travelpayouts écrit en dur', not [s for s in scripts if 'emrldco' in s['src'] or 'travelpayouts' in s['src']])

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

# numéro WhatsApp : un seul numéro dans tout le site (liens wa.me, constantes JavaScript, chat) et le numéro affiché est le même
wa_numbers, shown_numbers = set(), set()
for fr, lg, path in pages:
    h = read(path)
    wa_numbers |= set(re.findall(r'https://wa\.me/(\d+)', h)) | set(re.findall(r"WHATSAPP_NUMBER = '(\d+)'", h))
    for m in re.finditer(r'\+(\d{2})(?:&nbsp;|\s)(\d{3})(?:&nbsp;|\s)(\d{3})(?:&nbsp;|\s)(\d{4})', h):
        shown_numbers.add(''.join(m.groups()))
wa_numbers |= set(re.findall(r"WHATSAPP_NUMBER = '(\d+)'", read('flyfast-chat.js')))
check('numéro WhatsApp : un seul numéro dans les liens wa.me et le JavaScript du site', len(wa_numbers) == 1, sorted(wa_numbers))
check('numéro WhatsApp : le numéro affiché est celui des liens', shown_numbers == wa_numbers, (sorted(shown_numbers), sorted(wa_numbers)))

# bandeau de consentement (flyfast-consent.js, écrit à la main) : textes fr/en/es, durée du choix, et accord avec la page Confidentialité
check('bandeau : build.CONSENT_JS = flyfast-consent.js, à la racine', build.CONSENT_JS == 'flyfast-consent.js' and os.path.exists(os.path.join(ROOT, 'flyfast-consent.js')))
if os.path.exists(os.path.join(ROOT, build.CONSENT_JS)):
    js = read(build.CONSENT_JS)
    check('bandeau : le script n’écrit en dur aucune adresse http(s) et n’utilise ni eval ni document.write',
          not re.search(r'https?://', js) and 'eval(' not in js and 'document.write' not in js)
    days = re.search(r'MAX_AGE = (\d+) \* 24 \* 60 \* 60 \* 1000', js)
    check('bandeau : le choix est valable 6 mois (180 à 186 jours), comme l’annonce la page Confidentialité', bool(days) and 180 <= int(days.group(1)) <= 186, days and days.group(1))
    labels = {}
    for m in re.finditer(r"\b(fr|en|es): \{\s*title: '(.*?)',\s*text: '(.*?)',\s*more: '(.*?)', accept: '(.*?)', refuse: '(.*?)', manage: '(.*?)'\s*\}", js, re.S):
        labels[m.group(1)] = dict(zip(('title', 'text', 'more', 'accept', 'refuse', 'manage'), m.groups()[1:]))
    check('bandeau : textes complets en français, anglais et espagnol', set(labels) == {'fr', 'en', 'es'} and all(all(v) for v in labels.values()), sorted(labels))
    check('bandeau : les trois textes sont différents', len({v['text'] for v in labels.values()}) == len(labels) and len({v['title'] for v in labels.values()}) == len(labels))
    for lg in build.LANGS:
        priv_path = build.PATHS['confidentialite.html'][lg]
        psoup = BeautifulSoup(read(priv_path), 'lxml')
        anchor = psoup.find(id=build.PRIVACY_ANCHOR)
        check(f'[{priv_path}] section « Liens partenaires » : ancre #{build.PRIVACY_ANCHOR} sur un titre h2', anchor is not None and anchor.name == 'h2'
              and len(psoup.find_all(id=build.PRIVACY_ANCHOR)) == 1)
        flat_priv = re.sub(r'\s+', ' ', visible_text(psoup))
        if lg in labels:
            check(f'[{priv_path}] la page décrit le bandeau avec son titre et le lien « {labels[lg]["manage"]} » tels qu’affichés',
                  labels[lg]['title'] in flat_priv and labels[lg]['manage'] in flat_priv and '6 mois' in flat_priv.replace('6 months', '6 mois').replace('6 meses', '6 mois'),
                  (labels[lg]['title'], labels[lg]['manage']))

# liens partenaires Travelpayouts : les 25 adresses attendues (copiées du tableau « Liens affiliés FlyFast », écrites ici à la main et non produites
# par le même code que les pages), sur la page Partenaires et dans des encarts d'articles, toujours signalées « lien partenaire » et en rel="sponsored"
PARTNERS = [  # (nom affiché, adresse, catégorie)
    ('Airalo', 'https://airalo.tpk.lu/9i7gb9lL', 'esim'),
    ('Saily', 'https://saily.tpk.lu/zQ1D2Kmj', 'esim'),
    ('Yesim', 'https://yesim.tpk.lu/YUvsOXNi', 'esim'),
    ('Drimsim', 'https://drimsim.tpk.lu/tLx1W3uA', 'esim'),
    ('GigSky', 'https://gigsky.tpk.lu/UoHQdMmn', 'esim'),
    ('Aviasales', 'https://aviasales.tpk.lu/kmpXoLyk', 'vols'),
    ('Kiwi.com', 'https://kiwi.tpk.lu/t0yc0Rl9', 'vols'),
    ('AirHelp', 'https://airhelp.tpk.lu/eSSgZDvB', 'indemnisation'),
    ('Compensair', 'https://compensair.tpk.lu/F1LEvLd2', 'indemnisation'),
    ('Radical Storage', 'https://radicalstorage.tpk.lu/F9C312c6', 'consigne'),
    ('Kiwitaxi', 'https://kiwitaxi.tpk.lu/His9TbTt', 'transferts'),
    ('Welcome Pickups', 'https://tpk.lu/FRE7nqR6', 'transferts'),
    ('GetTransfer.com', 'https://gettransfer.tpk.lu/01NAKgyE', 'transferts'),
    ('intui.travel', 'https://intui.tpk.lu/Yaqn96qv', 'transferts'),
    ('Auto Europe', 'https://autoeurope.tpk.lu/iCy7GSOU', 'voiture'),
    ('Economybookings.com', 'https://economybookings.tpk.lu/2zzY4K2X', 'voiture'),
    ('GetRentacar.com', 'https://getrentacar.tpk.lu/aeaXhK3g', 'voiture'),
    ('Localrent.com', 'https://localrent.tpk.lu/uKKZ58ty', 'voiture'),
    ('QEEQ', 'https://qeeq.tpk.lu/ltQV4yJI', 'voiture'),
    ('BikesBooking.com', 'https://bikesbooking.tpk.lu/UzKYOob3', 'deux-roues'),
    ('Klook', 'https://klook.tpk.lu/se1N0mjr', 'activites'),
    ('Tiqets', 'https://tiqets.tpk.lu/IIjrvQh8', 'activites'),
    ('Go City', 'https://gocity.tpk.lu/RmZQRdQu', 'activites'),
    ('WeGoTrip', 'https://wegotrip.tpk.lu/pcxYgQVB', 'activites'),
    ('KKday', 'https://kkday.tpk.lu/sZmlkGuB', 'activites'),
]
CATEGORY_IDS = ['esim', 'vols', 'indemnisation', 'consigne', 'transferts', 'voiture', 'deux-roues', 'activites']
BOXES = {  # article -> catégories de son encart « Services partenaires » (dans l'ordre)
    'flyfast-blog/esim-voyageurs-rester-connecte.html': ['esim'],
    'flyfast-blog/bagages-soute-cabine-regles.html': ['consigne'],
    'flyfast-blog/enregistrement-en-ligne-guide-complet.html': ['transferts', 'indemnisation'],
    'flyfast-blog/jargon-voyage-gds-pnr-eticket.html': ['vols'],
    'flyfast-blog/documents-visa-voyage-europe.html': ['voiture', 'deux-roues', 'activites'],
}
P_TAG = {'fr': 'lien partenaire', 'en': 'partner link', 'es': 'enlace de socio'}
P_NAME = {'fr': 'Partenaires', 'en': 'Partners', 'es': 'Socios'}
NOTE_FR = 'Ce sont des liens partenaires&nbsp;: si vous réservez ou achetez après un clic, FlyFast peut recevoir une commission, sans coût supplémentaire pour vous.'
TPK = re.compile(r'^https://([a-z0-9-]+\.)?tpk\.lu/')
flat = lambda s: re.sub(r'\s+', ' ', s).strip()  # noqa: E731


def note_text(lg):
    return NOTE_FR if lg == 'fr' else MEMO[NOTE_FR][lg]


def tpk_links(node):
    return [a for a in node.find_all('a', href=True) if TPK.match(a['href'])]


def resolve(from_page, href):
    return os.path.normpath(os.path.join(os.path.dirname(os.path.join(ROOT, from_page)), href.split('#')[0]))


def link_ok(a, lg):
    """Nouvel onglet, rel sponsored + noopener, et la mention « lien partenaire » juste après le lien."""
    nxt = a.find_next_sibling()
    return (a.get('target') == '_blank' and {'sponsored', 'noopener'} <= set(a.get('rel') or [])
            and nxt is not None and a.next_sibling is nxt and nxt.name == 'span' and 'p-tag' in (nxt.get('class') or [])
            and nxt.get_text(strip=True) == P_TAG[lg])


by_cat = {c: [(n, u) for n, u, cc in PARTNERS if cc == c] for c in CATEGORY_IDS}
all_urls = [u for _, u, _ in PARTNERS]
check('liens partenaires : 25 adresses attendues, toutes différentes, toutes en https sur tpk.lu',
      len(PARTNERS) == 25 and len(set(all_urls)) == 25 and all(TPK.match(u) for u in all_urls))

for fr, lg, path in pages:
    psoup = BeautifulSoup(read(path), 'lxml')
    tag = f'[{path}]'
    want_n = 25 if fr == 'partenaires.html' else sum(len(by_cat[g]) for g in BOXES.get(fr, []))
    links = tpk_links(psoup)
    check(f'{tag} liens partenaires : {want_n} lien(s) attendu(s) sur cette page, pas un de plus', len(links) == want_n, len(links))
    check(f'{tag} liens partenaires : aucun lien du site ne pointe vers une adresse Travelpayouts autre que tpk.lu',
          not [a['href'] for a in psoup.find_all('a', href=True) if re.search(r'travelpayouts|emrldco|c\d+\.travelpayouts', a['href'], re.I)])
    # pied de page : lien vers la page Partenaires dans la langue de la page
    to_partners = os.path.normpath(os.path.join(ROOT, build.PATHS['partenaires.html'][lg]))
    foot = [a for a in psoup.select('.site-footer a[href]') if resolve(path, a['href']) == to_partners]
    check(f'{tag} pied de page : un lien « {P_NAME[lg]} » vers la page Partenaires de la langue',
          len(foot) == 1 and foot[0].get_text(strip=True) == P_NAME[lg] and (foot[0].get('aria-current') == 'page') == (fr == 'partenaires.html'),
          [(a['href'], a.get_text(strip=True), a.get('aria-current')) for a in foot])

    if fr == 'partenaires.html':
        check(f'{tag} les 25 adresses attendues, chacune une seule fois', sorted(a['href'] for a in links) == sorted(all_urls),
              sorted(set(all_urls) ^ {a['href'] for a in links}))
        check(f'{tag} chaque lien : nouvel onglet, rel="sponsored noopener", mention « {P_TAG[lg]} » juste après',
              all(link_ok(a, lg) for a in links), [a['href'] for a in links if not link_ok(a, lg)])
        want_names = {u: n for n, u, _ in PARTNERS}
        check(f'{tag} le nom affiché est celui du partenaire', {a['href']: a.get_text(strip=True) for a in links} == want_names)
        secs = psoup.select('section.pcat')
        check(f'{tag} 8 catégories dans l’ordre voulu, avec leur ancre reprise par la navigation',
              [s.get('id') for s in secs] == CATEGORY_IDS and [a.get('href') for a in psoup.select('nav.jump a')] == ['#' + c for c in CATEGORY_IDS],
              [s.get('id') for s in secs])
        check(f'{tag} chaque catégorie contient ses partenaires, dans l’ordre', all([a['href'] for a in tpk_links(s)] == [u for _, u in by_cat[s.get('id')]] for s in secs))
        check(f'{tag} chaque catégorie a un titre h2 relié à sa section', all(s.get('aria-labelledby') and s.find(id=s['aria-labelledby']) is not None
                                                                          and s.find(id=s['aria-labelledby']).name == 'h2' for s in secs))
        summ = psoup.select('aside.summary')
        check(f'{tag} encadré de transparence : la commission est annoncée, sans coût supplémentaire',
              len(summ) == 1 and flat(BeautifulSoup(f'<p>{note_text(lg)}</p>', 'lxml').get_text()) in flat(summ[0].get_text(' ', strip=True)))
        priv = [a for a in summ[0].find_all('a', href=True)] if summ else []
        check(f'{tag} encadré de transparence : lien vers la section « Liens partenaires » de la page Confidentialité de la langue',
              len(priv) == 1 and resolve(path, priv[0]['href']) == os.path.normpath(os.path.join(ROOT, build.PATHS['confidentialite.html'][lg]))
              and priv[0]['href'].endswith('#' + build.PRIVACY_ANCHOR), [a['href'] for a in priv])
        check(f'{tag} aucun encart ni script de suivi : la page ne charge rien de Travelpayouts avant le clic',
              'emrldco' not in read(path) and 'flyfast-consent' not in read(path) and not psoup.select('aside.partners'))
        check(f'{tag} bouton d’enregistrement en bas de page', len(psoup.select('aside.cta a.btn[href]')) == 1)

    if fr in BOXES:
        boxes = psoup.select('aside.partners')
        check(f'{tag} encart « Services partenaires » : un seul, avant l’appel à l’action et hors du texte de l’article',
              len(boxes) == 1 and boxes[0].find_next_sibling('aside', class_='cta') is not None and boxes[0].find_parent(class_='post-body') is None, len(boxes))
        if len(boxes) == 1:
            box = boxes[0]
            want = [u for g in BOXES[fr] for _, u in by_cat[g]]
            check(f'{tag} encart : les liens attendus ({", ".join(BOXES[fr])}), dans l’ordre', [a['href'] for a in tpk_links(box)] == want, [a['href'] for a in tpk_links(box)])
            check(f'{tag} encart : chaque lien est signalé « {P_TAG[lg]} » et ouvert comme lien partenaire', all(link_ok(a, lg) for a in tpk_links(box)))
            check(f'{tag} encart : la commission est annoncée avant les liens',
                  flat(BeautifulSoup(f'<p>{note_text(lg)}</p>', 'lxml').get_text()) in flat(box.find('p', class_='note').get_text(' ', strip=True)))
            check(f'{tag} encart : titre h2 qui nomme l’encart', box.get('aria-labelledby') == 'partners-title' and box.find(id='partners-title') is not None
                  and box.find(id='partners-title').name == 'h2')
            more = box.select('p.more a[href]')
            check(f'{tag} encart : lien « voir tous nos partenaires » vers la page Partenaires de la langue',
                  len(more) == 1 and resolve(path, more[0]['href']) == to_partners, [a['href'] for a in more])
            check(f'{tag} encart : les groupes sont titrés (h3) et décrits',
                  len(box.select('div.pgroup')) == len(BOXES[fr]) and all(g.find('h3') and g.find('p', class_='p-intro') for g in box.select('div.pgroup')))

    if fr == 'flyfast-blog/index.html':
        entries = psoup.select('.post-list a.post-link[href]')
        check(f'{tag} liste du blog : une entrée mène à la page Partenaires de la langue', [a for a in entries if resolve(path, a['href']) == to_partners] != [] and len(entries) == 6,
              [a['href'] for a in entries])
    if fr == 'index.html':
        faq = [d for d in psoup.select('.faq-list details') if any(resolve(path, a['href']) == to_partners for a in d.find_all('a', href=True))]
        check(f'{tag} FAQ : une question sur les liens partenaires, avec le lien vers la page Partenaires', len(faq) == 1, len(faq))
    if fr == 'confidentialite.html':
        sect = psoup.find(id=build.PRIVACY_ANCHOR)
        paras, el = [], sect.find_next_sibling() if sect else None
        while el is not None and el.name == 'p':
            paras.append(el)
            el = el.find_next_sibling()
        check(f'{tag} section « Liens partenaires » : cite la page Partenaires, Travelpayouts et le clic',
              len(paras) >= 4 and any(resolve(path, a['href']) == to_partners for p in paras for a in p.find_all('a', href=True))
              and 'Travelpayouts' in paras[1].get_text() and '<' not in paras[0].get_text(), len(paras))

# sitemap
sm = read('sitemap.xml')
locs = re.findall(r'<loc>(.*?)</loc>', sm)
check('sitemap : 36 adresses distinctes', len(locs) == 36 and len(set(locs)) == 36, len(locs))
expected = {build.abs_url(p) for _, _, p in pages}
check('sitemap : adresses = pages du site', set(locs) == expected, set(locs) ^ expected)
check('sitemap : chaque adresse correspond à un fichier', all(os.path.exists(os.path.join(ROOT, unquote(urlsplit(u).path[len('/'):]) or 'index.html') if not u.endswith('/') else os.path.join(ROOT, unquote(urlsplit(u).path[len('/'):]), 'index.html')) for u in locs))
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
