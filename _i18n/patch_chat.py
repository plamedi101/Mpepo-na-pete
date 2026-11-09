#!/usr/bin/env python3
"""Rend flyfast-chat.js multilingue (fr / en / es) à partir de la version française d'origine.

Usage : python3 patch_chat.py <entrée.js> <sortie.js>
Le français reste la langue par défaut ; la langue est lue dans <html lang="…"> de la page.
"""
import sys

NEW_CONSTS = r"""
  // Textes du panneau, par langue. La langue est celle de la page (<html lang>) ; le français est la langue par défaut.
  var STRINGS = {
    fr: {
      launch: 'Discuter',
      title: 'Une question ?',
      sub: 'Conseils gratuits sur l’enregistrement en ligne et le voyage. La conversation continue sur WhatsApp.',
      close: 'Fermer la fenêtre de discussion',
      lead: 'Choisissez un sujet ou écrivez votre question.',
      label: 'Votre message',
      send: 'Envoyer sur WhatsApp',
      note1: 'Votre message s’ouvre dans WhatsApp : vous le relisez avant de l’envoyer.',
      note2a: 'N’écrivez ici ni numéro de passeport, ni numéro de carte bancaire. Pour une demande d’enregistrement, utilisez le ',
      note2b: 'formulaire sécurisé',
      note2c: '.',
      greeting: /^bonjour/i,
      hello: 'Bonjour FlyFast, ',
      defaultText: 'Bonjour FlyFast, j’ai une question.',
      topics: [
        { label: 'Comment ça marche ?', text: 'Bonjour FlyFast, comment fonctionne l’enregistrement de mon vol ?' },
        { label: 'Combien ça coûte ?', text: 'Bonjour FlyFast, combien coûte votre service ?' },
        { label: 'Mon vol part bientôt', text: 'Bonjour FlyFast, mon vol part dans moins de 10 heures. Que puis-je faire ?' },
        { label: 'Conseils de voyage', text: 'Bonjour FlyFast, j’ai une question sur mon voyage : ' }
      ]
    },
    en: {
      launch: 'Chat',
      title: 'A question?',
      sub: 'Free advice on online check-in and travel. The conversation continues on WhatsApp.',
      close: 'Close the chat window',
      lead: 'Choose a topic or write your question.',
      label: 'Your message',
      send: 'Send on WhatsApp',
      note1: 'Your message opens in WhatsApp: you read it again before sending it.',
      note2a: 'Do not write a passport number or a bank card number here. For a check-in request, use the ',
      note2b: 'secure form',
      note2c: '.',
      greeting: /^(hello|hi|hey|good\s+(morning|afternoon|evening))\b/i,
      hello: 'Hello FlyFast, ',
      defaultText: 'Hello FlyFast, I have a question.',
      topics: [
        { label: 'How does it work?', text: 'Hello FlyFast, how does the check-in of my flight work?' },
        { label: 'How much does it cost?', text: 'Hello FlyFast, how much does your service cost?' },
        { label: 'My flight leaves soon', text: 'Hello FlyFast, my flight leaves in less than 10 hours. What can I do?' },
        { label: 'Travel advice', text: 'Hello FlyFast, I have a question about my trip: ' }
      ]
    },
    es: {
      launch: 'Chatear',
      title: '¿Tiene una pregunta?',
      sub: 'Consejos gratuitos sobre el check-in online y el viaje. La conversación continúa en WhatsApp.',
      close: 'Cerrar la ventana de chat',
      lead: 'Elija un tema o escriba su pregunta.',
      label: 'Su mensaje',
      send: 'Enviar por WhatsApp',
      note1: 'Su mensaje se abre en WhatsApp: lo revisa antes de enviarlo.',
      note2a: 'No escriba aquí ni el número de pasaporte ni el de su tarjeta bancaria. Para una solicitud de check-in, utilice el ',
      note2b: 'formulario seguro',
      note2c: '.',
      greeting: /^(hola|buen[oa]s)/i,
      hello: 'Hola FlyFast, ',
      defaultText: 'Hola FlyFast, tengo una pregunta.',
      topics: [
        { label: '¿Cómo funciona?', text: 'Hola FlyFast, ¿cómo funciona el check-in de mi vuelo?' },
        { label: '¿Cuánto cuesta?', text: 'Hola FlyFast, ¿cuánto cuesta su servicio?' },
        { label: 'Mi vuelo sale pronto', text: 'Hola FlyFast, mi vuelo sale en menos de 10 horas. ¿Qué puedo hacer?' },
        { label: 'Consejos de viaje', text: 'Hola FlyFast, tengo una pregunta sobre mi viaje: ' }
      ]
    }
  };
  var pageLang = String(document.documentElement.getAttribute('lang') || 'fr').slice(0, 2).toLowerCase();
  var T = STRINGS[pageLang] || STRINGS.fr;
  var DEFAULT_TEXT = T.defaultText;
  var TOPICS = T.topics;

"""


def patch_chat(src):
    def rep(old, new, count=1):
        nonlocal src
        assert src.count(old) == count, (src.count(old), old[:70])
        src = src.replace(old, new)


    # ---- 1. constantes de texte -> dictionnaire par langue
    old_consts = src[src.index("  var DEFAULT_TEXT = "):src.index("  var script = document.currentScript;")]
    assert "TOPICS" in old_consts and old_consts.count('\n') >= 8, old_consts

    src = src.replace(old_consts, NEW_CONSTS)

    # ---- 2. gabarit HTML du panneau
    rep("""'<span>Discuter</span></button>' +""", """'<span>' + T.launch + '</span></button>' +""")
    rep("""'<div><h2 class="ffc-title" id="ffc-title">Une question ?</h2>' +""",
        """'<div><h2 class="ffc-title" id="ffc-title">' + T.title + '</h2>' +""")
    rep("""'<p class="ffc-sub">Conseils gratuits sur l’enregistrement en ligne et le voyage. La conversation continue sur WhatsApp.</p></div>' +""",
        """'<p class="ffc-sub">' + T.sub + '</p></div>' +""")
    rep("""'<button class="ffc-close" type="button" aria-label="Fermer la fenêtre de discussion">' + CROSS + '</button>' +""",
        """'<button class="ffc-close" type="button" aria-label="' + T.close + '">' + CROSS + '</button>' +""")
    rep("""'<p class="ffc-lead" id="ffc-lead">Choisissez un sujet ou écrivez votre question.</p>' +""",
        """'<p class="ffc-lead" id="ffc-lead">' + T.lead + '</p>' +""")
    rep("""'<label class="ffc-label" for="ffc-text">Votre message</label>' +""",
        """'<label class="ffc-label" for="ffc-text">' + T.label + '</label>' +""")
    rep("""'<a class="ffc-send" href="#" target="_blank" rel="noopener">Envoyer sur WhatsApp</a>' +""",
        """'<a class="ffc-send" href="#" target="_blank" rel="noopener">' + T.send + '</a>' +""")
    rep("""'<p class="ffc-note">Votre message s’ouvre dans WhatsApp : vous le relisez avant de l’envoyer.</p>' +""",
        """'<p class="ffc-note">' + T.note1 + '</p>' +""")
    rep("""'<p class="ffc-note">N’écrivez ici ni numéro de passeport, ni numéro de carte bancaire. Pour une demande d’enregistrement, utilisez le <a class="ffc-formlink" href="#">formulaire sécurisé</a>.</p>' +""",
        """'<p class="ffc-note">' + T.note2a + '<a class="ffc-formlink" href="#">' + T.note2b + '</a>' + T.note2c + '</p>' +""")

    # ---- 3. salutation du message prérempli
    rep("""return /^bonjour/i.test(t) ? t : 'Bonjour FlyFast, ' + t;""",
        """return T.greeting.test(t) ? t : T.hello + t;""")

    return src


if __name__ == '__main__':
    out = patch_chat(open(sys.argv[1], encoding='utf-8').read())
    open(sys.argv[2], 'w', encoding='utf-8').write(out)
    print('flyfast-chat.js multilingue écrit :', len(out), 'octets')
