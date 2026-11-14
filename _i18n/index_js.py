#!/usr/bin/env python3
"""Textes du script de la page d'accueil (formulaires, avis, messages d'erreur) en anglais et en espagnol.

patch_script(js_fr, 'en' | 'es') renvoie le script français transformé :
  - chaque chaîne française est remplacée par sa traduction (remplacements exacts, avec contrôle du nombre d'occurrences) ;
  - les messages renvoyés par le service d'enregistrement (en français) sont traduits côté navigateur
    avec le dictionnaire SERVER_TEXT et la fonction S() ; un message inconnu reste affiché tel quel.
Aucun autre comportement du script ne change.
"""
import json
import re

NB = ' '

# --- messages du service d'enregistrement (Worker flyfast-api), tels qu'il les renvoie -------------------------------
#     (français, anglais, espagnol)
SERVER = [
    ('Le service est momentanément indisponible. Réessayez dans quelques minutes.',
     'The service is temporarily unavailable. Please try again in a few minutes.',
     'El servicio no está disponible momentáneamente. Inténtelo de nuevo dentro de unos minutos.'),
    ('La vérification anti-robot a échoué. Rechargez la page et réessayez.',
     'The anti-robot check failed. Reload the page and try again.',
     'El control antirrobot ha fallado. Recargue la página e inténtelo de nuevo.'),
    ('La vérification anti-robot est momentanément indisponible. Réessayez dans un instant.',
     'The anti-robot check is temporarily unavailable. Please try again in a moment.',
     'El control antirrobot no está disponible momentáneamente. Inténtelo de nuevo dentro de un momento.'),
    ('Origine non autorisée.',
     'Origin not allowed.',
     'Origen no autorizado.'),
    ('Trop de tentatives. Réessayez un peu plus tard.',
     'Too many attempts. Please try again a little later.',
     'Demasiados intentos. Inténtelo de nuevo un poco más tarde.'),
    ('Demande illisible.',
     'The request could not be read.',
     'No se ha podido leer la solicitud.'),
    ('Format de demande non pris en charge.',
     'Request format not supported.',
     'Formato de solicitud no admitido.'),
    ('Demande trop volumineuse.',
     'Request too large.',
     'Solicitud demasiado grande.'),
    ('Complétez les champs signalés pour continuer.',
     'Complete the highlighted fields to continue.',
     'Complete los campos señalados para continuar.'),
    ('Indiquez votre nom complet, comme sur le passeport.',
     'Enter your full name, as on your passport.',
     'Indique su nombre completo, tal como figura en el pasaporte.'),
    ('Indiquez un numéro de passeport valide.',
     'Enter a valid passport number.',
     'Indique un número de pasaporte válido.'),
    ('Indiquez votre nationalité.',
     'Enter your nationality.',
     'Indique su nacionalidad.'),
    ('Indiquez votre date de naissance.',
     'Enter your date of birth.',
     'Indique su fecha de nacimiento.'),
    ('Indiquez un numéro WhatsApp valide, avec l’indicatif du pays.',
     'Enter a valid WhatsApp number, including the country code.',
     'Indique un número de WhatsApp válido, con el prefijo del país.'),
    ('Indiquez la compagnie aérienne.',
     'Enter the airline.',
     'Indique la aerolínea.'),
    ('Indiquez un numéro de vol valide, par exemple ET 704.',
     'Enter a valid flight number, for example ET 704.',
     'Indique un número de vuelo válido, por ejemplo ET 704.'),
    ('Indiquez la référence de réservation (PNR) : 5 à 8 caractères.',
     'Enter the booking reference (PNR): 5 to 8 characters.',
     'Indique el código de reserva (PNR): de 5 a 8 caracteres.'),
    ('Vérifiez le numéro de billet, ou laissez ce champ vide.',
     'Check the ticket number, or leave this field empty.',
     'Compruebe el número de billete o deje este campo vacío.'),
    ('Indiquez la date et l’heure du vol.',
     'Enter the date and time of the flight.',
     'Indique la fecha y la hora del vuelo.'),
    ('La limite quotidienne de demandes gratuites est atteinte. Votre demande n’a pas été enregistrée.',
     'The daily limit of free requests has been reached. Your request was not recorded.',
     'Se ha alcanzado el límite diario de solicitudes gratuitas. Su solicitud no se ha registrado.'),
    ('Cochez la case pour accepter les conditions.',
     'Tick the box to accept the terms.',
     'Marque la casilla para aceptar las condiciones.'),
    ('Indiquez votre prénom (lettres uniquement, 40 caractères maximum).',
     'Enter your first name (letters only, 40 characters maximum).',
     'Indique su nombre de pila (solo letras, 40 caracteres como máximo).'),
    ('Choisissez une note de 1 à 5.',
     'Choose a rating from 1 to 5.',
     'Elija una valoración de 1 a 5.'),
    ('Votre avis est trop court (10 caractères minimum).',
     'Your review is too short (10 characters minimum).',
     'Su opinión es demasiado corta (mínimo 10 caracteres).'),
    ('Votre avis est trop long (600 caractères maximum).',
     'Your review is too long (600 characters maximum).',
     'Su opinión es demasiado larga (600 caracteres como máximo).'),
    ('Les liens et adresses e-mail ne sont pas acceptés dans un avis.',
     'Links and e-mail addresses are not accepted in a review.',
     'No se aceptan enlaces ni direcciones de correo electrónico en una opinión.'),
    ('Numéro de dossier invalide. Il ressemble à FF-AB12CD.',
     'Invalid request number. It looks like FF-AB12CD.',
     'Número de solicitud no válido. Tiene este aspecto: FF-AB12CD.'),
    ('Cochez la case pour accepter la publication de votre prénom et de votre avis.',
     'Tick the box to agree to the publication of your first name and your review.',
     'Marque la casilla para aceptar la publicación de su nombre de pila y de su opinión.'),
    ('Méthode non autorisée.',
     'Method not allowed.',
     'Método no permitido.'),
    ('Introuvable.',
     'Not found.',
     'No encontrado.'),
]

# --- textes écrits directement dans le script : (extrait exact du script français, anglais, espagnol, occurrences) -----
# Les extraits incluent les guillemets lorsque c'est nécessaire pour éviter qu'une chaîne plus courte n'en touche une autre.
CODE = [
    # menu mobile
    ("'Ouvrir le menu'", "'Open menu'", "'Abrir el menú'", 2),
    ("'Fermer le menu'", "'Close menu'", "'Cerrar el menú'", 1),

    # échec d'envoi générique
    ("'L’envoi n’a pas abouti. Vérifiez votre connexion et réessayez.'",
     "'Sending failed. Check your connection and try again.'",
     "'No se pudo enviar. Compruebe su conexión e inténtelo de nuevo.'", 1),

    # anti-robot : langue du widget
    ("language: 'fr',", "language: 'en',", "language: 'es',", 1),

    # champs obligatoires (formulaire de demande)
    ("'Indiquez votre nom complet, comme sur le passeport.'", "'Enter your full name, as on your passport.'",
     "'Indique su nombre completo, tal como figura en el pasaporte.'", 1),
    ("'Indiquez votre numéro de passeport.'", "'Enter your passport number.'", "'Indique su número de pasaporte.'", 1),
    ("'Indiquez votre nationalité.'", "'Enter your nationality.'", "'Indique su nacionalidad.'", 1),
    ("'Indiquez votre date de naissance.'", "'Enter your date of birth.'", "'Indique su fecha de nacimiento.'", 1),
    ("'Indiquez votre numéro WhatsApp.'", "'Enter your WhatsApp number.'", "'Indique su número de WhatsApp.'", 1),
    ("'Indiquez la compagnie aérienne.'", "'Enter the airline.'", "'Indique la aerolínea.'", 1),
    ("'Indiquez le numéro de vol.'", "'Enter the flight number.'", "'Indique el número de vuelo.'", 1),
    ("'Indiquez la référence de réservation (PNR).'", "'Enter the booking reference (PNR).'",
     "'Indique el código de reserva (PNR).'", 1),
    ("'Indiquez la date et l’heure du vol.'", "'Enter the date and time of the flight.'",
     "'Indique la fecha y la hora del vuelo.'", 1),

    # bouton d'envoi
    ("submitBtn.textContent = on ? 'Envoi en cours…' : 'Envoyer ma demande';",
     "submitBtn.textContent = on ? 'Sending…' : 'Send my request';",
     "submitBtn.textContent = on ? 'Enviando…' : 'Enviar mi solicitud';", 1),

    # message WhatsApp de secours (demande complète)
    ('"Bonjour FlyFast, voici ma demande d\'enregistrement :"',
     '"Hello FlyFast, here is my check-in request:"',
     '"Hola FlyFast, esta es mi solicitud de check-in:"', 1),
    ("'Nom : '", "'Name: '", "'Nombre: '", 1),
    ("'Passeport : '", "'Passport: '", "'Pasaporte: '", 1),
    ("'Nationalité : '", "'Nationality: '", "'Nacionalidad: '", 1),
    ("'Date de naissance : '", "'Date of birth: '", "'Fecha de nacimiento: '", 1),
    ("'Compagnie : '", "'Airline: '", "'Aerolínea: '", 1),
    ("'Vol : '", "'Flight: '", "'Vuelo: '", 1),
    ("'PNR : '", "'PNR: '", "'PNR: '", 1),
    ("'Numéro de billet : '", "'Ticket number: '", "'Número de billete: '", 1),
    ("'non fourni'", "'not provided'", "'no facilitado'", 1),
    ("'Date/heure du vol : '", "'Flight date/time: '", "'Fecha y hora del vuelo: '", 1),
    ("'Mon WhatsApp : '", "'My WhatsApp: '", "'Mi WhatsApp: '", 1),
    ("'Je confirme avoir lu et accepté les conditions du service.'",
     "'I confirm that I have read and accepted the terms of service.'",
     "'Confirmo que he leído y aceptado las condiciones del servicio.'", 1),
    ("'WhatsApp s’ouvre avec votre demande. Appuyez sur Envoyer dans WhatsApp pour la transmettre.'",
     "'WhatsApp opens with your request. Tap Send in WhatsApp to transmit it.'",
     "'WhatsApp se abre con su solicitud. Pulse Enviar en WhatsApp para transmitirla.'", 1),

    # confirmation d'enregistrement
    ("'Demandes enregistrées' : 'Demande enregistrée'",
     "'Requests recorded' : 'Request recorded'",
     "'Solicitudes registradas' : 'Solicitud registrada'", 1),
    ("'Notez vos numéros de dossier" + NB + ":' : 'Notez votre numéro de dossier" + NB + ":'",
     "'Note your request numbers:' : 'Note your request number:'",
     "'Anote sus números de solicitud:' : 'Anote su número de solicitud:'", 1),
    ("'Bonjour FlyFast, j’ai envoyé ma demande d’enregistrement sur le site. '",
     "'Hello FlyFast, I sent my check-in request on the website. '",
     "'Hola FlyFast, he enviado mi solicitud de check-in a través del sitio web. '", 1),
    ("'Mes numéros de dossier : ' : 'Mon numéro de dossier : '",
     "'My request numbers: ' : 'My request number: '",
     "'Mis números de solicitud: ' : 'Mi número de solicitud: '", 1),

    # messages d'état
    ("'Complétez les champs signalés pour continuer.'",
     "'Complete the highlighted fields to continue.'",
     "'Complete los campos señalados para continuar.'", 4),
    ("'Cochez la case pour accepter les conditions.'", "'Tick the box to accept the terms.'",
     "'Marque la casilla para aceptar las condiciones.'", 1),
    ("'Enregistrement de votre demande…'", "'Saving your request…'", "'Registrando su solicitud…'", 1),
    ("'Trop de tentatives en peu de temps. Patientez un moment, puis réessayez.'",
     "'Too many attempts in a short time. Please wait a moment, then try again.'",
     "'Demasiados intentos en poco tiempo. Espere un momento y vuelva a intentarlo.'", 2),

    # limite du jour (offre de lancement) : moment de réouverture à l'heure de l'appareil, puis messages
    ("return 'le ' + when.toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' }) + ' à ' + when.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });",
     "return 'on ' + when.toLocaleDateString('en-GB', { day: 'numeric', month: 'long' }) + ' at ' + when.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });",
     "return 'el ' + when.toLocaleDateString('es-ES', { day: 'numeric', month: 'long' }) + ' a las ' + when.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });", 1),
    ("'Le formulaire acceptera de nouvelles réservations ' + reopening(resetsAt) + ' (heure de votre appareil).'",
     "'The form will accept new bookings again ' + reopening(resetsAt) + ' (your device’s time).'",
     "'El formulario volverá a aceptar nuevas reservas ' + reopening(resetsAt) + ' (hora de su dispositivo).'", 1),
    ("'Le formulaire acceptera de nouvelles réservations demain.'",
     "'The form will accept new bookings again tomorrow.'",
     "'El formulario volverá a aceptar nuevas reservas mañana.'", 1),
    ("'La limite quotidienne de demandes gratuites est atteinte" + NB + ": votre demande n’a pas été enregistrée. '",
     "'The daily limit of free requests has been reached: your request was not recorded. '",
     "'Se ha alcanzado el límite diario de solicitudes gratuitas: su solicitud no se ha registrado. '", 1),

    # avis : liste
    ("moreBtn.textContent = showAll ? 'Réduire la liste' : 'Voir les ' + extra + (extra > 1 ? ' autres avis' : ' autre avis');",
     "moreBtn.textContent = showAll ? 'Show fewer reviews' : 'Show ' + extra + ' more ' + (extra > 1 ? 'reviews' : 'review');",
     "moreBtn.textContent = showAll ? 'Ver menos opiniones' : 'Ver ' + extra + (extra > 1 ? ' opiniones más' : ' opinión más');", 1),
    ("d.toLocaleDateString('fr-FR',", "d.toLocaleDateString('en-GB',", "d.toLocaleDateString('es-ES',", 1),
    ("summary.textContent = 'Note moyenne" + NB + ": ' + String(data.average).replace('.', ',') + ' sur 5, d’après ' + data.count + ' avis';",
     "summary.textContent = 'Average rating: ' + String(data.average) + ' out of 5, based on ' + data.count + (data.count > 1 ? ' reviews' : ' review');",
     "summary.textContent = 'Nota media: ' + String(data.average).replace('.', ',') + ' de 5, según ' + data.count + (data.count > 1 ? ' opiniones' : ' opinión');", 1),
    ("r.rating + ' sur 5'", "r.rating + ' out of 5'", "r.rating + ' de 5'", 1),
    ("'Client vérifié'", "'Verified customer'", "'Cliente verificado'", 1),
    ("chosenRating() + ' sur 5'", "chosenRating() + ' out of 5'", "chosenRating() + ' de 5'", 1),

    # avis : formulaire
    ("'Indiquez votre prénom.'", "'Enter your first name.'", "'Indique su nombre de pila.'", 1),
    ("'Choisissez une note de 1 à 5.'", "'Choose a rating from 1 to 5.'", "'Elija una valoración de 1 a 5.'", 1),
    ("'Votre avis est trop court (10 caractères minimum).'", "'Your review is too short (10 characters minimum).'",
     "'Su opinión es demasiado corta (mínimo 10 caracteres).'", 1),
    ("'Numéro de dossier invalide. Il ressemble à FF-AB12CD.'", "'Invalid request number. It looks like FF-AB12CD.'",
     "'Número de solicitud no válido. Tiene este aspecto: FF-AB12CD.'", 1),
    ("'Cochez la case pour accepter la publication de votre prénom et de votre avis.'",
     "'Tick the box to agree to the publication of your first name and your review.'",
     "'Marque la casilla para aceptar la publicación de su nombre de pila y de su opinión.'", 1),
    ("'L’envoi d’avis est momentanément indisponible. Vous pouvez nous écrire sur WhatsApp.'",
     "'Review submission is temporarily unavailable. You can write to us on WhatsApp.'",
     "'El envío de opiniones no está disponible momentáneamente. Puede escribirnos por WhatsApp.'", 1),
    ("reviewSubmit.textContent = 'Envoi en cours…';", "reviewSubmit.textContent = 'Sending…';",
     "reviewSubmit.textContent = 'Enviando…';", 1),
    ("'Envoi de votre avis…'", "'Sending your review…'", "'Enviando su opinión…'", 1),
    ("'Merci" + NB + "! Votre avis est publié.'", "'Thank you! Your review is published.'",
     "'¡Gracias! Su opinión está publicada.'", 1),
    ("'Merci" + NB + "! Votre avis sera publié après relecture par notre équipe.'",
     "'Thank you! Your review will be published after our team has checked it.'",
     "'¡Gracias! Su opinión se publicará tras la revisión de nuestro equipo.'", 1),
    ("' Vous pouvez aussi nous écrire sur WhatsApp.'", "' You can also write to us on WhatsApp.'",
     "' También puede escribirnos por WhatsApp.'", 1),
    ("reviewSubmit.textContent = 'Envoyer mon avis';", "reviewSubmit.textContent = 'Send my review';",
     "reviewSubmit.textContent = 'Enviar mi opinión';", 1),
]

# --- endroits où un texte venu du service (en français) doit passer par S() ---------------------------------------
WRAP = [
    ('      setError(el, message);', '      setError(el, S(message));', 1),
    ('      setError(consent, errors.consent);', '      setError(consent, S(errors.consent));', 1),
    ('showFailure(res.body.message || FAIL_TEXT);', 'showFailure(S(res.body.message) || FAIL_TEXT);', 1),
    ('        setError(pair[1], errors[pair[0]]);', '        setError(pair[1], S(errors[pair[0]]));', 1),
    ('      box.textContent = errors.rating;', '      box.textContent = S(errors.rating);', 1),
    ('setReviewStatus(res.body.message || FAIL_TEXT, true);', 'setReviewStatus(S(res.body.message) || FAIL_TEXT, true);', 1),
]

FAIL_ANCHOR_RE = re.compile(r"^  var FAIL_TEXT = .*;\n", re.M)


def norm_key(s):
    return re.sub(r'\s+', ' ', s).strip()


def server_dictionary(lang):
    col = {'en': 1, 'es': 2}[lang]
    return {norm_key(row[0]): row[col] for row in SERVER}


def patch_script(js, lang):
    assert lang in ('en', 'es'), lang
    col = {'en': 1, 'es': 2}[lang]
    for row in CODE:
        old, new, count = row[0], row[col], row[3]
        n = js.count(old)
        assert n == count, f'{n} occurrence(s) au lieu de {count} : {old[:90]}'
        js = js.replace(old, new)
    for old, new, count in WRAP:
        n = js.count(old)
        assert n == count, f'{n} occurrence(s) au lieu de {count} : {old[:90]}'
        js = js.replace(old, new)
    m = FAIL_ANCHOR_RE.search(js)
    assert m, 'ligne FAIL_TEXT introuvable'
    block = (
        '\n  // Messages renvoyés par le service d’enregistrement (rédigés en français) : affichés dans la langue de la page.\n'
        '  var SERVER_TEXT = ' + json.dumps(server_dictionary(lang), ensure_ascii=False, indent=2).replace('\n', '\n  ') + ';\n'
        '  function S(message) {\n'
        '    var key = String(message || \'\').replace(/\\s+/g, \' \').trim();\n'
        '    return Object.prototype.hasOwnProperty.call(SERVER_TEXT, key) ? SERVER_TEXT[key] : message;\n'
        '  }\n'
    )
    js = js[:m.end()] + block + js[m.end():]
    return js


if __name__ == '__main__':
    # Contrôle rapide : python3 index_js.py index.html  (vérifie que chaque texte du script a bien été trouvé)
    import sys
    src = open(sys.argv[1], encoding='utf-8').read()
    a = src.index('<script>\n') + len('<script>\n')
    js = src[a:src.index('</script>', a)]
    for lang in ('en', 'es'):
        print(lang, len(js), '->', len(patch_script(js, lang)))
