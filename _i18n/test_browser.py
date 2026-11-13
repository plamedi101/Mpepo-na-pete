#!/usr/bin/env python3
"""Tests dans un vrai navigateur des trois langues (fr/en/es) : pages, sélecteur de langue, chat, formulaire, avis.

Le service d'enregistrement (Worker Cloudflare) et Turnstile sont simulés : aucun envoi réel.
Usage : python3 test_browser.py <url de base, ex. http://127.0.0.1:8766/>
"""
import json
import os
import re
import sys
import urllib.parse

from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build  # noqa: E402

BASE = sys.argv[1]
SHOTS = os.environ.get('SHOTS', os.path.join(os.environ.get('TMPDIR', '/tmp'), 'flyfast-shots'))
os.makedirs(SHOTS, exist_ok=True)
API = 'https://flyfast-api.flyfast-checkin.workers.dev'
WA_PREFIX = 'https://wa.me/201282226808?text='
NB = ' '
LANGS = ('fr', 'en', 'es')

results = []


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))


def wa_text(href):
    assert href.startswith(WA_PREFIX), href
    return urllib.parse.unquote(href[len(WA_PREFIX):])


def noise(msg):
    return any(s in msg for s in ('fonts.g', 'Failed to load resource', 'ERR_', 'challenges.cloudflare', 'flyfast-api', 'cloudflareinsights', 'emrldco'))


# --------------------------------------------------------------------------------------------------- textes attendus
REQUIRED_IDS = ['name', 'passport', 'nationality', 'dob', 'contact', 'airline', 'flightnum', 'pnr', 'ticket', 'datetime']
X = {
    'fr': dict(
        required=['Indiquez votre nom complet, comme sur le passeport.', 'Indiquez votre numéro de passeport.', 'Indiquez votre nationalité.',
                  'Indiquez votre date de naissance.', 'Indiquez votre numéro WhatsApp.', 'Indiquez la compagnie aérienne.',
                  'Indiquez le numéro de vol.', 'Indiquez la référence de réservation (PNR).', 'Indiquez le numéro de billet.',
                  'Indiquez la date et l’heure du vol.'],
        consent='Cochez la case pour accepter les conditions.', incomplete='Complétez les champs signalés pour continuer.',
        saving='Enregistrement de votre demande…', sending='Envoi en cours…', send='Envoyer ma demande',
        done_title='Demande enregistrée', done_title_pl='Demandes enregistrées',
        done_label='Notez votre numéro de dossier' + NB + ':', done_label_pl='Notez vos numéros de dossier' + NB + ':',
        done_wa='Bonjour FlyFast, j’ai envoyé ma demande d’enregistrement sur le site. Mon numéro de dossier : FF-AB12CD',
        done_wa_pl='Bonjour FlyFast, j’ai envoyé ma demande d’enregistrement sur le site. Mes numéros de dossier : FF-AB12CD, FF-ZZ99YY',
        passport='Indiquez un numéro de passeport valide.', contact='Indiquez un numéro WhatsApp valide, avec l’indicatif du pays.',
        flightnum='Indiquez un numéro de vol valide, par exemple ET 704.', pnr='Indiquez la référence de réservation (PNR) : 5 à 8 caractères.',
        s500='Le service est momentanément indisponible. Réessayez dans quelques minutes.',
        captcha='La vérification anti-robot a échoué. Rechargez la page et réessayez.',
        fail='L’envoi n’a pas abouti. Vérifiez votre connexion et réessayez.', r429='Trop de tentatives en peu de temps. Patientez un moment, puis réessayez.',
        wa_opens='WhatsApp s’ouvre avec votre demande. Appuyez sur Envoyer dans WhatsApp pour la transmettre.',
        legacy=["Bonjour FlyFast, voici ma demande d'enregistrement :", 'Nom : NGOY KALENGA Jean', 'Passeport : OP1234567', 'Nationalité : Française',
                'Date de naissance : 17/05/1990', 'Compagnie : Ethiopian Airlines', 'Vol : ET 704', 'PNR : X7YQ2P', 'Numéro de billet : 071-1234567890',
                'Date/heure du vol : 24/12/2026 14:20', 'Mon WhatsApp : +33 6 12 34 56 78', 'Je confirme avoir lu et accepté les conditions du service.'],
        summary='Note moyenne' + NB + ': 4,7 sur 5, d’après 8 avis', badge='Client vérifié', date='octobre 2026', star5='5 sur 5',
        more='Voir les 2 autres avis', less='Réduire la liste', more1='Voir les 1 autre avis',
        r_name='Indiquez votre prénom.', r_rating='Choisissez une note de 1 à 5.', r_short='Votre avis est trop court (10 caractères minimum).',
        r_ref='Numéro de dossier invalide. Il ressemble à FF-AB12CD.',
        r_consent='Cochez la case pour accepter la publication de votre prénom et de votre avis.',
        r_send='Envoyer mon avis', r_sending='Envoi en cours…', r_sending_status='Envoi de votre avis…',
        r_pub='Merci' + NB + '! Votre avis est publié.', r_pending='Merci' + NB + '! Votre avis sera publié après relecture par notre équipe.',
        r_fail=None, r_unavailable=None,
        srv_name='Indiquez votre prénom (lettres uniquement, 40 caractères maximum).', srv_text='Les liens et adresses e-mail ne sont pas acceptés dans un avis.',
        rating_text='5 sur 5', menu_open='Ouvrir le menu', menu_close='Fermer le menu', ts='fr', locale_menu='fr',
        chat=dict(launch='Discuter', title='Une question' + NB + '?', close='Fermer la fenêtre de discussion',
                  chips=['Comment ça marche' + NB + '?', 'Combien ça coûte' + NB + '?', 'Mon vol part bientôt', 'Conseils de voyage'],
                  default='Bonjour FlyFast, j’ai une question.', chip0='Bonjour FlyFast, comment fonctionne l’enregistrement de mon vol ?',
                  free_in='Quels documents faut-il ?', free_out='Bonjour FlyFast, Quels documents faut-il ?', greet_in='Bonjour, un conseil svp', formlink='formulaire sécurisé',
                  send='Envoyer sur WhatsApp', label='Votre message'),
    ),
    'en': dict(
        required=['Enter your full name, as on your passport.', 'Enter your passport number.', 'Enter your nationality.', 'Enter your date of birth.',
                  'Enter your WhatsApp number.', 'Enter the airline.', 'Enter the flight number.', 'Enter the booking reference (PNR).',
                  'Enter the ticket number.', 'Enter the date and time of the flight.'],
        consent='Tick the box to accept the terms.', incomplete='Complete the highlighted fields to continue.',
        saving='Saving your request…', sending='Sending…', send='Send my request',
        done_title='Request recorded', done_title_pl='Requests recorded',
        done_label='Note your request number:', done_label_pl='Note your request numbers:',
        done_wa='Hello FlyFast, I sent my check-in request on the website. My request number: FF-AB12CD',
        done_wa_pl='Hello FlyFast, I sent my check-in request on the website. My request numbers: FF-AB12CD, FF-ZZ99YY',
        passport='Enter a valid passport number.', contact='Enter a valid WhatsApp number, including the country code.',
        flightnum='Enter a valid flight number, for example ET 704.', pnr='Enter the booking reference (PNR): 5 to 8 characters.',
        s500='The service is temporarily unavailable. Please try again in a few minutes.',
        captcha='The anti-robot check failed. Reload the page and try again.',
        fail='Sending failed. Check your connection and try again.', r429='Too many attempts in a short time. Please wait a moment, then try again.',
        wa_opens='WhatsApp opens with your request. Tap Send in WhatsApp to transmit it.',
        legacy=['Hello FlyFast, here is my check-in request:', 'Name: NGOY KALENGA Jean', 'Passport: OP1234567', 'Nationality: Française',
                'Date of birth: 17/05/1990', 'Airline: Ethiopian Airlines', 'Flight: ET 704', 'PNR: X7YQ2P', 'Ticket number: 071-1234567890',
                'Flight date/time: 24/12/2026 14:20', 'My WhatsApp: +33 6 12 34 56 78', 'I confirm that I have read and accepted the terms of service.'],
        summary='Average rating: 4.7 out of 5, based on 8 reviews', badge='Verified customer', date='October 2026', star5='5 out of 5',
        more='Show 2 more reviews', less='Show fewer reviews', more1='Show 1 more review',
        r_name='Enter your first name.', r_rating='Choose a rating from 1 to 5.', r_short='Your review is too short (10 characters minimum).',
        r_ref='Invalid request number. It looks like FF-AB12CD.',
        r_consent='Tick the box to agree to the publication of your first name and your review.',
        r_send='Send my review', r_sending='Sending…', r_sending_status='Sending your review…',
        r_pub='Thank you! Your review is published.', r_pending='Thank you! Your review will be published after our team has checked it.',
        srv_name='Enter your first name (letters only, 40 characters maximum).', srv_text='Links and e-mail addresses are not accepted in a review.',
        rating_text='5 out of 5', menu_open='Open menu', menu_close='Close menu', ts='en',
        chat=dict(launch='Chat', title='A question?', close='Close the chat window',
                  chips=['How does it work?', 'How much does it cost?', 'My flight leaves soon', 'Travel advice'],
                  default='Hello FlyFast, I have a question.', chip0='Hello FlyFast, how does the check-in of my flight work?',
                  free_in='Which documents do I need?', free_out='Hello FlyFast, Which documents do I need?', greet_in='Hi, quick question please', formlink='secure form',
                  send='Send on WhatsApp', label='Your message'),
    ),
    'es': dict(
        required=['Indique su nombre completo, tal como figura en el pasaporte.', 'Indique su número de pasaporte.', 'Indique su nacionalidad.',
                  'Indique su fecha de nacimiento.', 'Indique su número de WhatsApp.', 'Indique la aerolínea.', 'Indique el número de vuelo.',
                  'Indique el código de reserva (PNR).', 'Indique el número de billete.', 'Indique la fecha y la hora del vuelo.'],
        consent='Marque la casilla para aceptar las condiciones.', incomplete='Complete los campos señalados para continuar.',
        saving='Registrando su solicitud…', sending='Enviando…', send='Enviar mi solicitud',
        done_title='Solicitud registrada', done_title_pl='Solicitudes registradas',
        done_label='Anote su número de solicitud:', done_label_pl='Anote sus números de solicitud:',
        done_wa='Hola FlyFast, he enviado mi solicitud de check-in a través del sitio web. Mi número de solicitud: FF-AB12CD',
        done_wa_pl='Hola FlyFast, he enviado mi solicitud de check-in a través del sitio web. Mis números de solicitud: FF-AB12CD, FF-ZZ99YY',
        passport='Indique un número de pasaporte válido.', contact='Indique un número de WhatsApp válido, con el prefijo del país.',
        flightnum='Indique un número de vuelo válido, por ejemplo ET 704.', pnr='Indique el código de reserva (PNR): de 5 a 8 caracteres.',
        s500='El servicio no está disponible momentáneamente. Inténtelo de nuevo dentro de unos minutos.',
        captcha='El control antirrobot ha fallado. Recargue la página e inténtelo de nuevo.',
        fail='No se pudo enviar. Compruebe su conexión e inténtelo de nuevo.', r429='Demasiados intentos en poco tiempo. Espere un momento y vuelva a intentarlo.',
        wa_opens='WhatsApp se abre con su solicitud. Pulse Enviar en WhatsApp para transmitirla.',
        legacy=['Hola FlyFast, esta es mi solicitud de check-in:', 'Nombre: NGOY KALENGA Jean', 'Pasaporte: OP1234567', 'Nacionalidad: Française',
                'Fecha de nacimiento: 17/05/1990', 'Aerolínea: Ethiopian Airlines', 'Vuelo: ET 704', 'PNR: X7YQ2P', 'Número de billete: 071-1234567890',
                'Fecha y hora del vuelo: 24/12/2026 14:20', 'Mi WhatsApp: +33 6 12 34 56 78', 'Confirmo que he leído y aceptado las condiciones del servicio.'],
        summary='Nota media: 4,7 de 5, según 8 opiniones', badge='Cliente verificado', date='octubre de 2026', star5='5 de 5',
        more='Ver 2 opiniones más', less='Ver menos opiniones', more1='Ver 1 opinión más',
        r_name='Indique su nombre de pila.', r_rating='Elija una valoración de 1 a 5.', r_short='Su opinión es demasiado corta (mínimo 10 caracteres).',
        r_ref='Número de solicitud no válido. Tiene este aspecto: FF-AB12CD.',
        r_consent='Marque la casilla para aceptar la publicación de su nombre de pila y de su opinión.',
        r_send='Enviar mi opinión', r_sending='Enviando…', r_sending_status='Enviando su opinión…',
        r_pub='¡Gracias! Su opinión está publicada.', r_pending='¡Gracias! Su opinión se publicará tras la revisión de nuestro equipo.',
        srv_name='Indique su nombre de pila (solo letras, 40 caracteres como máximo).',
        srv_text='No se aceptan enlaces ni direcciones de correo electrónico en una opinión.',
        rating_text='5 de 5', menu_open='Abrir el menú', menu_close='Cerrar el menú', ts='es',
        chat=dict(launch='Chatear', title='¿Tiene una pregunta?', close='Cerrar la ventana de chat',
                  chips=['¿Cómo funciona?', '¿Cuánto cuesta?', 'Mi vuelo sale pronto', 'Consejos de viaje'],
                  default='Hola FlyFast, tengo una pregunta.', chip0='Hola FlyFast, ¿cómo funciona el check-in de mi vuelo?',
                  free_in='¿Qué documentos necesito?', free_out='Hola FlyFast, ¿Qué documentos necesito?', greet_in='Hola, una consulta por favor', formlink='formulario seguro',
                  send='Enviar por WhatsApp', label='Su mensaje'),
    ),
}
FIELD_VALUES = {
    'f-name': 'NGOY KALENGA Jean', 'f-passport': 'OP1234567', 'f-nationality': 'Française', 'f-dob': '1990-05-17',
    'f-contact': '+33 6 12 34 56 78', 'f-airline': 'Ethiopian Airlines', 'f-flightnum': 'ET 704', 'f-pnr': 'X7YQ2P',
    'f-ticket': '071-1234567890', 'f-datetime': '24/12/2026 14:20',
}

# --------------------------------------------------------------------------------------------------- service simulé
M = {}


def reviews_payload(n=8):
    revs = []
    for i in range(n):
        revs.append({'rating': 5 if i % 2 == 0 else 4, 'verified': i % 2 == 0, 'text': f'Avis numéro {i + 1} : service rapide.', 'name': ['Jean', 'Maria', 'Paul', 'Awa'][i % 4], 'date': '2026-10-12'})
    return {'ok': True, 'average': 4.7, 'count': n, 'reviews': revs}


def api_route(route, request):
    cors = {'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,OPTIONS'}
    path = urllib.parse.urlsplit(request.url).path
    if request.method == 'OPTIONS':
        return route.fulfill(status=204, headers=cors)

    def send(status, body):
        route.fulfill(status=status, headers=cors, content_type='application/json', body=json.dumps(body, ensure_ascii=False))

    if path == '/api/reviews' and request.method == 'GET':
        return send(200, reviews_payload(M.get('n_reviews', 8)))
    if path == '/api/requests':
        mode = M.get('request', 'ok')
        M.setdefault('posts', []).append(('requests', request.post_data))
        if mode == 'abort':
            return route.abort()
        if mode == 'ok':
            M['ref_i'] = M.get('ref_i', 0) + 1
            return send(200, {'ok': True, 'ref': ['FF-AB12CD', 'FF-ZZ99YY'][(M['ref_i'] - 1) % 2]})
        if mode == 'fields':
            return send(400, {'ok': False, 'error': 'invalid', 'message': 'Complétez les champs signalés pour continuer.', 'fields': {
                'passport': 'Indiquez un numéro de passeport valide.', 'contact': 'Indiquez un numéro WhatsApp valide, avec l’indicatif du pays.',
                'flightnum': 'Indiquez un numéro de vol valide, par exemple ET 704.', 'pnr': 'Indiquez la référence de réservation (PNR) : 5 à 8 caractères.',
                'consent': 'Cochez la case pour accepter les conditions.'}})
        if mode == '429':
            return send(429, {'ok': False, 'error': 'rate', 'message': 'Trop de tentatives. Réessayez un peu plus tard.'})
        if mode == '500':
            return send(500, {'ok': False, 'error': 'server', 'message': 'Le service est momentanément indisponible. Réessayez dans quelques minutes.'})
        if mode == 'captcha':
            return send(403, {'ok': False, 'error': 'captcha', 'message': 'La vérification anti-robot a échoué. Rechargez la page et réessayez.'})
        if mode == 'unknown':
            return send(500, {'ok': False, 'error': 'x', 'message': 'Message inattendu du service.'})
        if mode == 'nomessage':
            return send(500, {})
    if path == '/api/reviews' and request.method == 'POST':
        mode = M.get('review', 'published')
        if mode == 'abort':
            return route.abort()
        if mode == 'published':
            return send(200, {'ok': True, 'published': True})
        if mode == 'pending':
            return send(200, {'ok': True, 'published': False})
        if mode == 'fields':
            return send(400, {'ok': False, 'error': 'invalid', 'message': 'Complétez les champs signalés pour continuer.', 'fields': {
                'name': 'Indiquez votre prénom (lettres uniquement, 40 caractères maximum).', 'rating': 'Choisissez une note de 1 à 5.',
                'text': 'Les liens et adresses e-mail ne sont pas acceptés dans un avis.',
                'ref': 'Numéro de dossier invalide. Il ressemble à FF-AB12CD.', 'consent': 'Cochez la case pour accepter la publication de votre prénom et de votre avis.'}})
        if mode == '429':
            return send(429, {'ok': False, 'error': 'rate', 'message': 'Trop de tentatives. Réessayez un peu plus tard.'})
        if mode == '500':
            return send(500, {'ok': False, 'error': 'server', 'message': 'Le service est momentanément indisponible. Réessayez dans quelques minutes.'})
    return send(404, {'ok': False, 'message': 'Introuvable.'})


TURNSTILE_STUB = """
window.__tsCalls = [];
(function () {
  var cbs = {};
  window.turnstile = {
    render: function (sel, opts) { var id = 'w' + (window.__tsCalls.length + 1); window.__tsCalls.push({ sel: sel, language: opts.language, action: opts.action, appearance: opts.appearance }); cbs[id] = opts.callback; return id; },
    execute: function (id) { var cb = cbs[id]; setTimeout(function () { cb('tok_1234567890abcdef'); }, 5); },
    reset: function () {}
  };
  if (window.ffTurnstileReady) { window.ffTurnstileReady(); }
})();
"""


def new_context(browser, **kw):
    ctx = browser.new_context(**kw)
    ctx.route(API + '/**', api_route)
    ctx.route('https://challenges.cloudflare.com/turnstile/**', lambda r: r.fulfill(status=200, content_type='application/javascript', body=TURNSTILE_STUB))
    ctx.route(re.compile(r'https://(fonts\.googleapis\.com|fonts\.gstatic\.com|static\.cloudflareinsights\.com)/.*'), lambda r: r.abort())
    # Travelpayouts Drive : jamais de vrai appel pendant les tests (la requête est comptée côté navigateur, puis remplacée par un script vide)
    ctx.route(re.compile(r'https://emrldco\.com/.*'), lambda r: r.fulfill(status=200, content_type='application/javascript', body='/* Travelpayouts Drive : simulé par les tests */'))
    return ctx


def open_home(browser, lang, **kw):
    ctx = new_context(browser, **kw)
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and not noise(m.text) else None)
    page.goto(BASE + build.PATHS['index.html'][lang], wait_until='load')
    page.evaluate("window.__opened = []; window.open = function (u, t) { window.__opened.push(u); return {}; }; undefined")
    page.wait_for_function("document.querySelector('#reviews-list') !== null")
    return ctx, page, errors


def texts_ids(page, ids):
    return page.evaluate("(ids) => ids.map(i => { const e = document.getElementById(i); return e ? (e.hidden ? null : e.textContent) : undefined; })", ids)


def fill_all(page):
    for k, v in FIELD_VALUES.items():
        page.fill('#' + k, v)
    page.check('#f-consent')


def wait_idle(page):
    page.wait_for_function("document.getElementById('submit-btn').disabled === false")


def french_residue(text, lang):
    """Renvoie les mots français trouvés dans un texte censé être en anglais ou en espagnol."""
    if lang == 'fr':
        return []
    words = re.findall(r"\b(vous|votre|vos|nous|notre|avec|dans|les|des|sont|aux|qui|mais|cette|ces|enregistr\w+|réservation|passeport|compagnie|dossier|demande|avis|champs|réessayez|case|cochez|indiquez|complétez|merci)\b", text, re.I)
    if lang == 'es':
        words = [w for w in words if w.lower() not in ('nos', 'les', 'demande')]
    return words


with sync_playwright() as p:
    b = p.chromium.launch()

    # ============================================================== 1. toutes les pages : console, débordement, sélecteur
    for viewport, vname in (({'width': 1280, 'height': 900}, 'bureau'), ({'width': 390, 'height': 844}, 'mobile')):
        ctx = new_context(b, viewport=viewport, device_scale_factor=1)
        for lang in LANGS:
            for fr_path, v in build.PATHS.items():
                path = v[lang]
                page = ctx.new_page()
                errors = []
                page.on('pageerror', lambda e, errors=errors: errors.append('pageerror: ' + str(e)))
                page.on('console', lambda m, errors=errors: errors.append(m.text) if m.type == 'error' and not noise(m.text) else None)
                resp = page.goto(BASE + path, wait_until='load')
                page.wait_for_timeout(120)
                info = page.evaluate("""() => {
                  const bar = document.querySelector('.langbar');
                  const r = bar ? bar.getBoundingClientRect() : null;
                  const links = bar ? [...bar.querySelectorAll('a')].map(a => { const q = a.getBoundingClientRect(); return {w: q.width, h: q.height, l: q.left, r: q.right}; }) : [];
                  const hdr = document.querySelector('.site-header').getBoundingClientRect();
                  return {
                    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
                    barTop: r ? r.top : null, barH: r ? r.height : null, hdrTop: hdr.top, links, vw: innerWidth,
                    roots: document.querySelectorAll('#ffc-root').length, lang: document.documentElement.lang,
                  };
                }""")
                tag = f'[{vname} {path}]'
                check(f'{tag} réponse 200', resp is not None and resp.status == 200, resp.status if resp else None)
                check(f'{tag} aucune erreur de console', not errors, errors)
                check(f'{tag} pas de défilement horizontal', info['overflow'] <= 0, info['overflow'])
                check(f'{tag} sélecteur de langue visible, en haut, au-dessus de l’en-tête', info['barTop'] == 0 and 36 <= info['barH'] <= 48 and info['hdrTop'] >= info['barH'] - 1, info)
                check(f'{tag} liens du sélecteur dans l’écran et assez grands', all(l['l'] >= 0 and l['r'] <= info['vw'] and l['h'] >= 36 and l['w'] >= 36 for l in info['links']), info['links'])
                check(f'{tag} un seul bouton de chat', info['roots'] == 1)
                page.close()
        ctx.close()

    # ============================================================== 2. sélecteur : navigation réelle entre les langues
    ctx = new_context(b, viewport={'width': 1280, 'height': 900})
    for fr_path in ('index.html', 'conditions-de-vente.html', 'flyfast-blog/bagages-soute-cabine-regles.html'):
        for start in LANGS:
            for target in LANGS:
                if start == target:
                    continue
                page = ctx.new_page()
                page.goto(BASE + build.PATHS[fr_path][start], wait_until='load')
                page.click(f'.langbar a[lang="{target}"]')
                page.wait_for_load_state('load')
                loc = urllib.parse.urlsplit(page.url).path
                check(f'sélecteur : {fr_path} {start}→{target}', loc.endswith('/' + build.PATHS[fr_path][target]) and page.evaluate('document.documentElement.lang') == target, loc)
                page.close()
    ctx.close()

    # ============================================================== 3. chat dans chaque langue (page d'accueil et blog)
    for lang in LANGS:
        c = X[lang]['chat']
        ctx = new_context(b, viewport={'width': 1280, 'height': 900})
        page = ctx.new_page()
        page.goto(BASE + build.PATHS['index.html'][lang], wait_until='load')
        page.wait_for_timeout(150)
        tag = f'[chat {lang}]'
        check(f'{tag} libellé du bouton', page.inner_text('.ffc-launch').strip() == c['launch'], page.inner_text('.ffc-launch'))
        page.click('.ffc-launch')
        check(f'{tag} titre', page.inner_text('#ffc-title') == c['title'], page.inner_text('#ffc-title'))
        check(f'{tag} bouton fermer', page.get_attribute('.ffc-close', 'aria-label') == c['close'], page.get_attribute('.ffc-close', 'aria-label'))
        check(f'{tag} étiquette du champ', page.inner_text('.ffc-label') == c['label'], page.inner_text('.ffc-label'))
        check(f'{tag} bouton d’envoi', page.inner_text('.ffc-send').strip() == c['send'], page.inner_text('.ffc-send'))
        chips = [e.inner_text() for e in page.query_selector_all('.ffc-chip')]
        check(f'{tag} sujets', chips == c['chips'], chips)
        check(f'{tag} message par défaut', wa_text(page.get_attribute('.ffc-send', 'href')) == c['default'], wa_text(page.get_attribute('.ffc-send', 'href')))
        page.click('.ffc-chip >> nth=0')
        check(f'{tag} premier sujet prérempli', page.input_value('#ffc-text') == c['chip0'], page.input_value('#ffc-text'))
        page.fill('#ffc-text', '')
        page.type('#ffc-text', c['free_in'])
        check(f'{tag} texte libre : salutation ajoutée', wa_text(page.get_attribute('.ffc-send', 'href')) == c['free_out'], wa_text(page.get_attribute('.ffc-send', 'href')))
        page.fill('#ffc-text', '')
        page.type('#ffc-text', c['greet_in'])
        check(f'{tag} texte qui commence déjà par une salutation : inchangé', wa_text(page.get_attribute('.ffc-send', 'href')) == c['greet_in'], wa_text(page.get_attribute('.ffc-send', 'href')))
        notes = page.inner_text('#ffc-panel')
        check(f'{tag} lien du formulaire sécurisé', page.inner_text('.ffc-formlink') == c['formlink'] and page.get_attribute('.ffc-formlink', 'href') == '#enregistrer')
        check(f'{tag} aucun mot français dans le panneau', not french_residue(notes, lang), french_residue(notes, lang))
        page.screenshot(path=f'{SHOTS}/chat-{lang}.png')
        page.close()
        page = ctx.new_page()
        page.goto(BASE + build.PATHS['flyfast-blog/index.html'][lang], wait_until='load')
        page.wait_for_timeout(150)
        page.click('.ffc-launch')
        check(f'{tag} blog : lien du formulaire vers la page d’accueil de la même langue',
              page.get_attribute('.ffc-formlink', 'href') == '../index.html#enregistrer', page.get_attribute('.ffc-formlink', 'href'))
        ctx.close()

    # ============================================================== 4. page d'accueil : formulaires, messages, avis
    for lang in LANGS:
        e = X[lang]
        tag = f'[accueil {lang}]'
        M.clear()
        ctx, page, errors = open_home(b, lang, viewport={'width': 1280, 'height': 900})

        # --- avis affichés
        page.wait_for_function("document.querySelectorAll('#reviews-list figure').length > 0")
        check(f'{tag} résumé des avis', page.inner_text('#reviews-summary').strip() == e['summary'], repr(page.inner_text('#reviews-summary')))
        check(f'{tag} badge « client vérifié »', page.inner_text('#reviews-list figure .badge >> nth=0') == e['badge'])
        check(f'{tag} date du premier avis', page.inner_text('#reviews-list figure .review-date >> nth=0') == e['date'], page.inner_text('#reviews-list figure .review-date >> nth=0'))
        check(f'{tag} étoiles : libellé accessible', page.get_attribute('#reviews-list figure .stars >> nth=0', 'aria-label') == e['star5'])
        check(f'{tag} 6 avis visibles et bouton « voir les autres »', page.evaluate("[...document.querySelectorAll('#reviews-list figure')].filter(f => !f.hidden).length") == 6
              and page.inner_text('#reviews-more') == e['more'], page.inner_text('#reviews-more'))
        page.click('#reviews-more')
        check(f'{tag} bouton après dépliage', page.inner_text('#reviews-more') == e['less'] and page.evaluate("[...document.querySelectorAll('#reviews-list figure')].filter(f => !f.hidden).length") == 8)
        page.click('#reviews-more')

        # --- envoi vide : 11 erreurs dans la langue
        page.click('#submit-btn')
        vals = texts_ids(page, ['e-' + i for i in REQUIRED_IDS] + ['e-consent'])
        check(f'{tag} 10 messages de champ obligatoire', vals[:10] == e['required'], vals[:10])
        check(f'{tag} message de consentement', vals[10] == e['consent'], vals[10])
        check(f'{tag} statut « complétez les champs »', page.inner_text('#form-status') == e['incomplete'], page.inner_text('#form-status'))
        check(f'{tag} focus sur le premier champ', page.evaluate('document.activeElement.id') == 'f-name')

        # --- erreurs renvoyées par le service (en français) : traduites
        fill_all(page)
        M['request'] = 'fields'
        page.click('#submit-btn')
        page.wait_for_function("document.getElementById('submit-btn').disabled === false && document.getElementById('form-status').textContent !== ''")
        got = {k: v for k, v in zip(['passport', 'contact', 'flightnum', 'pnr', 'consent'], texts_ids(page, ['e-passport', 'e-contact', 'e-flightnum', 'e-pnr', 'e-consent']))}
        check(f'{tag} erreurs du service traduites', got == {'passport': e['passport'], 'contact': e['contact'], 'flightnum': e['flightnum'], 'pnr': e['pnr'], 'consent': e['consent']}, got)
        check(f'{tag} statut après erreurs du service', page.inner_text('#form-status') == e['incomplete'], page.inner_text('#form-status'))
        check(f'{tag} Turnstile reçoit la langue de la page', page.evaluate('window.__tsCalls[0] && window.__tsCalls[0].language') == e['ts'], page.evaluate('window.__tsCalls'))
        check(f'{tag} bouton d’envoi remis à zéro', page.inner_text('#submit-btn') == e['send'], page.inner_text('#submit-btn'))

        # --- autres réponses du service
        for mode, key in (('429', 'r429'), ('500', 's500'), ('captcha', 'captcha'), ('nomessage', 'fail'), ('abort', 'fail')):
            M['request'] = mode
            page.click('#submit-btn')
            page.wait_for_function("document.getElementById('submit-btn').disabled === false && document.getElementById('form-status').textContent !== ''")
            st = page.inner_text('#form-status')
            check(f'{tag} réponse « {mode} » : message dans la langue', st == e[key], st)
            check(f'{tag} réponse « {mode} » : bouton WhatsApp de secours proposé', page.evaluate("!document.getElementById('form-fallback').hidden"))
        M['request'] = 'unknown'
        page.click('#submit-btn')
        page.wait_for_function("document.getElementById('submit-btn').disabled === false")
        check(f'{tag} message inconnu du service : affiché tel quel', page.inner_text('#form-status') == 'Message inattendu du service.', page.inner_text('#form-status'))

        # --- secours WhatsApp : message complet dans la langue
        page.evaluate("window.__opened = []")
        page.click('#fallback-btn')
        opened = page.evaluate('window.__opened')
        check(f'{tag} secours WhatsApp : une seule ouverture', len(opened) == 1, opened)
        if opened:
            lines = wa_text(opened[0]).split('\n')
            check(f'{tag} secours WhatsApp : message complet dans la langue', lines == e['legacy'], lines)
        check(f'{tag} secours WhatsApp : statut', page.inner_text('#form-status') == e['wa_opens'], page.inner_text('#form-status'))

        # --- envoi réussi, puis second passager
        M['request'] = 'ok'
        seen = page.evaluate("""() => { window.__log = []; const s = document.getElementById('form-status'), b = document.getElementById('submit-btn');
            new MutationObserver(() => window.__log.push(['status', s.textContent])).observe(s, {childList: true, characterData: true, subtree: true});
            new MutationObserver(() => window.__log.push(['btn', b.textContent])).observe(b, {childList: true, characterData: true, subtree: true}); return 1; }""")
        page.click('#submit-btn')
        page.wait_for_function("!document.getElementById('form-done').hidden")
        log = page.evaluate('window.__log')
        check(f'{tag} message « enregistrement en cours » pendant l’envoi', ['status', e['saving']] in log, log)
        check(f'{tag} bouton « envoi en cours » pendant l’envoi', ['btn', e['sending']] in log, log)
        check(f'{tag} confirmation : titre et consigne (un dossier)', page.inner_text('#done-title') == e['done_title'] and page.evaluate("document.getElementById('done-label').textContent") == e['done_label'],
              (page.inner_text('#done-title'), page.evaluate("document.getElementById('done-label').textContent")))
        check(f'{tag} confirmation : numéro affiché', page.inner_text('#done-refs') == 'FF-AB12CD')
        check(f'{tag} confirmation : message WhatsApp (un dossier)', wa_text(page.get_attribute('#done-wa', 'href')) == e['done_wa'], wa_text(page.get_attribute('#done-wa', 'href')))
        page.click('#done-another')
        fill_all(page)
        page.click('#submit-btn')
        page.wait_for_function("!document.getElementById('form-done').hidden")
        check(f'{tag} confirmation : titre et consigne au pluriel', page.inner_text('#done-title') == e['done_title_pl'] and page.evaluate("document.getElementById('done-label').textContent") == e['done_label_pl'],
              (page.inner_text('#done-title'), page.evaluate("document.getElementById('done-label').textContent")))
        check(f'{tag} confirmation : message WhatsApp (deux dossiers)', wa_text(page.get_attribute('#done-wa', 'href')) == e['done_wa_pl'], wa_text(page.get_attribute('#done-wa', 'href')))
        page.screenshot(path=f'{SHOTS}/done-{lang}.png', full_page=False)

        # --- formulaire d'avis : validations locales
        page.evaluate("document.getElementById('review-form').scrollIntoView()")
        page.click('#review-submit')
        rv = texts_ids(page, ['e-r-name', 'e-r-rating', 'e-r-text', 'e-r-ref', 'e-r-consent'])
        check(f'{tag} avis : prénom, note, texte, consentement manquants', rv[0] == e['r_name'] and rv[1] == e['r_rating'] and rv[2] == e['r_short'] and rv[4] == e['r_consent'], rv)
        check(f'{tag} avis : statut', page.inner_text('#review-status') == e['incomplete'], page.inner_text('#review-status'))
        page.fill('#r-name', 'Jean')
        page.click('label[for="r-star-5"]')
        check(f'{tag} avis : libellé de la note choisie', page.inner_text('#rating-text') == e['rating_text'], page.inner_text('#rating-text'))
        page.fill('#r-text', 'Great service, quick and efficient.')
        page.fill('#r-ref', 'FF-XXXX')
        page.check('#r-consent')
        page.click('#review-submit')
        check(f'{tag} avis : numéro de dossier invalide', texts_ids(page, ['e-r-ref'])[0] == e['r_ref'], texts_ids(page, ['e-r-ref']))
        page.fill('#r-ref', 'FF-AB23CD')

        # --- formulaire d'avis : réponses du service
        M['review'] = 'fields'
        page.click('#review-submit')
        page.wait_for_function("document.getElementById('review-submit').disabled === false && document.getElementById('review-status').textContent !== ''")
        rv = texts_ids(page, ['e-r-name', 'e-r-rating', 'e-r-text', 'e-r-ref', 'e-r-consent'])
        check(f'{tag} avis : erreurs du service traduites', rv[0] == e['srv_name'] and rv[1] == e['r_rating'] and rv[2] == e['srv_text'] and rv[3] == e['r_ref'] and rv[4] == e['r_consent'], rv)
        for mode, key in (('429', 'r429'), ('500', 's500'), ('abort', 'fail_review')):
            M['review'] = mode
            page.click('#review-submit')
            page.wait_for_function("document.getElementById('review-submit').disabled === false && document.getElementById('review-status').textContent !== ''")
            st = page.inner_text('#review-status')
            expect = e['r429'] if mode == '429' else (e['s500'] if mode == '500' else e['fail'] + {'fr': ' Vous pouvez aussi nous écrire sur WhatsApp.', 'en': ' You can also write to us on WhatsApp.', 'es': ' También puede escribirnos por WhatsApp.'}[lang])
            check(f'{tag} avis : réponse « {mode} »', st == expect, st)
        check(f'{tag} avis : bouton remis à zéro', page.inner_text('#review-submit') == e['r_send'], page.inner_text('#review-submit'))
        M['review'] = 'pending'
        M['n_reviews'] = 7
        page.click('#review-submit')
        page.wait_for_function("document.getElementById('review-status').textContent === " + json.dumps(e['r_pending']))
        check(f'{tag} avis : merci (après relecture)', page.inner_text('#review-status') == e['r_pending'], page.inner_text('#review-status'))
        page.wait_for_function("document.querySelectorAll('#reviews-list figure').length === 7")
        check(f'{tag} avis : « voir l’autre avis » au singulier', page.inner_text('#reviews-more') == e['more1'], page.inner_text('#reviews-more'))
        page.fill('#r-name', 'Jean')
        page.click('label[for="r-star-4"]')
        page.fill('#r-text', 'Great service, quick and efficient.')
        page.check('#r-consent')
        M['review'] = 'published'
        page.click('#review-submit')
        page.wait_for_function("document.getElementById('review-status').textContent === " + json.dumps(e['r_pub']))
        check(f'{tag} avis : merci (publié)', page.inner_text('#review-status') == e['r_pub'])
        check(f'{tag} aucune erreur de console pendant les parcours', not errors, errors)
        ctx.close()

    # ============================================================== 5. menu mobile : libellés dans la langue
    for lang in LANGS:
        e = X[lang]
        ctx, page, errors = open_home(b, lang, viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
        check(f'[menu {lang}] libellé initial', page.get_attribute('.menu-toggle', 'aria-label') == e['menu_open'], page.get_attribute('.menu-toggle', 'aria-label'))
        page.tap('.menu-toggle')
        check(f'[menu {lang}] libellé après ouverture', page.get_attribute('.menu-toggle', 'aria-label') == e['menu_close'] and page.get_attribute('.menu-toggle', 'aria-expanded') == 'true')
        page.screenshot(path=f'{SHOTS}/mobile-menu-{lang}.png')
        page.tap('.menu-toggle')
        check(f'[menu {lang}] libellé après fermeture', page.get_attribute('.menu-toggle', 'aria-label') == e['menu_open'])
        page.evaluate('window.scrollTo(0, 0)')
        page.screenshot(path=f'{SHOTS}/mobile-top-{lang}.png')
        check(f'[menu {lang}] pas de défilement horizontal', page.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 0)
        ctx.close()

    # ============================================================== 5b. affiliation Travelpayouts : règle de chargement du script externe
    # blog = chargé une fois ; accueil (formulaires : passeport…) = jamais, sauf pour la vérification Travelpayouts (?init_marker=…) ;
    # pages légales = jamais.
    TP_SRC = build.TP_DRIVE_SRC
    VERIF = '?init_marker=805301&init_trs=600443&init_locale=en'
    for lang in LANGS:
        ctx = new_context(b, viewport={'width': 1280, 'height': 900})
        for fr_path, v in build.PATHS.items():
            if fr_path == 'index.html':
                variants = [('', 0), (VERIF, 1), ('?utm_init_marker=1', 0), ('#init_marker=805301', 0)]
            elif fr_path.startswith('flyfast-blog/'):
                variants = [('', 1), (VERIF, 1)]
            else:
                variants = [('', 0), (VERIF, 0)]
            for query, expected in variants:
                page = ctx.new_page()
                hits, errors = [], []
                page.on('request', lambda r, hits=hits: hits.append(r.url) if 'emrldco' in r.url else None)
                page.on('pageerror', lambda e, errors=errors: errors.append('pageerror: ' + str(e)))
                page.on('console', lambda m, errors=errors: errors.append(m.text) if m.type == 'error' and not noise(m.text) else None)
                page.goto(BASE + v[lang] + query, wait_until='load')
                page.wait_for_timeout(250)
                tag = f'[affiliation {v[lang]}{query}]'
                want = [TP_SRC] * expected if TP_SRC else []
                check(f'{tag} {len(want)} appel(s) à Travelpayouts', hits == want, hits)
                added = page.evaluate("[...document.head.querySelectorAll('script[src]')].map(s => ({src: s.src, async: s.async}))")
                check(f'{tag} ' + ('script ajouté dans <head>, en asynchrone' if want else 'aucun script Travelpayouts dans la page'),
                      added == [{'src': TP_SRC, 'async': True}] * len(want), added)
                check(f'{tag} aucune erreur de console', not errors, errors)
                page.close()
        ctx.close()

    # ============================================================== 6. captures pour relecture visuelle
    for lang in LANGS:
        ctx = new_context(b, viewport={'width': 1280, 'height': 900})
        page = ctx.new_page()
        for name, path in (('home', build.PATHS['index.html'][lang]), ('terms', build.PATHS['conditions-de-vente.html'][lang]), ('blog', build.PATHS['flyfast-blog/index.html'][lang])):
            page.goto(BASE + path, wait_until='load')
            page.wait_for_timeout(250)
            page.screenshot(path=f'{SHOTS}/desktop-{name}-{lang}.png', full_page=(name != 'home'))
        ctx.close()
    b.close()

failed = 0
for name, ok, detail in results:
    if not ok:
        failed += 1
        print('ÉCHEC ' + name + '  → ' + (detail if isinstance(detail, str) else json.dumps(detail, ensure_ascii=False)))
print(f'\n{len(results) - failed}/{len(results)} contrôles réussis')
sys.exit(1 if failed else 0)
