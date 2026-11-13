/* FlyFast : bandeau de consentement pour le script d'affiliation Travelpayouts (pages du blog).
   Fichier écrit à la main : il n'est pas généré par _i18n/build.py, qui le référence dans l'en-tête des pages du blog,
   avec l'adresse du script Travelpayouts (data-drive) et celle de la section « Liens partenaires » de la page
   Confidentialité (data-privacy).
   Le script Travelpayouts n'est chargé qu'après un clic sur « Accepter ». Le choix est gardé 6 mois dans le navigateur
   (localStorage, clé « ff-consent »). Le lien « Gérer les cookies » du pied de page rouvre le bandeau. */
(function () {
  'use strict';

  var tag = document.currentScript || document.querySelector('script[data-drive]');
  var DRIVE = tag && tag.getAttribute('data-drive');
  var PRIVACY = (tag && tag.getAttribute('data-privacy')) || '';
  if (!DRIVE) { return; }

  var KEY = 'ff-consent';
  var MAX_AGE = 183 * 24 * 60 * 60 * 1000;   // 6 mois
  var COOKIE = 'am_user_session';              // cookie de session posé par le script Travelpayouts

  var TEXTS = {
    fr: {
      title: 'Cookies et liens partenaires',
      text: 'Les pages du blog peuvent charger le script d’affiliation de Travelpayouts. Il enregistre un cookie de session, lui envoie des statistiques de visite et peut afficher des offres partenaires. Il ne se charge que si vous l’acceptez.',
      more: 'En savoir plus', accept: 'Accepter', refuse: 'Refuser', manage: 'Gérer les cookies'
    },
    en: {
      title: 'Cookies and partner links',
      text: 'The blog pages may load the Travelpayouts affiliate script. It stores a session cookie, sends visit statistics to Travelpayouts and may show partner offers. It only loads if you accept.',
      more: 'Learn more', accept: 'Accept', refuse: 'Decline', manage: 'Manage cookies'
    },
    es: {
      title: 'Cookies y enlaces a socios',
      text: 'Las páginas del blog pueden cargar el script de afiliación de Travelpayouts. Guarda una cookie de sesión, envía estadísticas de visita a Travelpayouts y puede mostrar ofertas de socios. Solo se carga si usted lo acepta.',
      more: 'Más información', accept: 'Aceptar', refuse: 'Rechazar', manage: 'Gestionar cookies'
    }
  };
  var T = TEXTS[(document.documentElement.lang || 'fr').slice(0, 2)] || TEXTS.fr;

  var CSS = [
    '.ffk{position:fixed;left:16px;bottom:16px;z-index:100;box-sizing:border-box;width:min(560px,calc(100vw - 32px));padding:18px 20px 20px;background:#fff;color:var(--ink,#13222F);border:1px solid var(--line,#D5DFEA);border-top:4px solid var(--gold,#F0B92E);border-radius:var(--radius,6px);box-shadow:0 12px 40px rgba(12,46,78,.28);font-family:var(--font-body,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif);font-size:.9375rem;line-height:1.5;}',
    '.ffk *{box-sizing:border-box;}',
    '.ffk[hidden]{display:none;}',
    '.ffk-title{margin:0 0 6px;font-family:var(--font-head,var(--font-body,system-ui,sans-serif));font-size:1.125rem;font-weight:600;line-height:1.25;color:var(--navy,#0C2E4E);}',
    '.ffk-text{margin:0;}',
    '.ffk-text a{color:var(--sky-text,#0F5A93);text-underline-offset:3px;}',
    '.ffk-actions{display:flex;gap:10px;margin-top:16px;}',
    /* « Refuser » et « Accepter » : même taille, même style */
    '.ffk-btn{flex:1 1 0;min-height:46px;padding:0 16px;border:1.5px solid var(--navy,#0C2E4E);border-radius:var(--radius,6px);background:var(--navy,#0C2E4E);color:#fff;font:inherit;font-weight:600;line-height:1.2;cursor:pointer;}',
    '.ffk-btn:hover{background:var(--navy-2,#154670);border-color:var(--navy-2,#154670);}',
    '.ffk :focus-visible{outline:3px solid #1D6FB8;outline-offset:3px;}',
    '.ffk-open{display:inline;padding:0;border:0;background:none;color:inherit;font:inherit;text-align:left;cursor:pointer;}',
    '.ffk-open:hover{color:#fff;text-decoration:underline;}',
    '.ffk-open:focus-visible{outline:3px solid #FFD36B;outline-offset:3px;}',
    '@media (max-width:560px){.ffk{left:10px;right:10px;bottom:10px;bottom:max(10px,env(safe-area-inset-bottom));width:auto;padding:16px;}}',
    '@media print{.ffk{display:none !important;}}'
  ].join('\n');

  var banner = null;
  var opener = null;
  var reopened = false;
  var driveLoaded = false;

  function el(name, cls, text) {
    var e = document.createElement(name);
    if (cls) { e.className = cls; }
    if (text) { e.textContent = text; }
    return e;
  }

  /* ------------------------------------------------------------------ choix gardé dans le navigateur */
  function readChoice() {
    try {
      var o = JSON.parse(window.localStorage.getItem(KEY));
      if (!o || (o.v !== 'yes' && o.v !== 'no') || typeof o.t !== 'number') { return null; }
      if (Date.now() - o.t > MAX_AGE || o.t > Date.now() + 60000) { return null; }
      return o.v;
    } catch (e) {
      return null;
    }
  }

  function saveChoice(v) {
    try { window.localStorage.setItem(KEY, JSON.stringify({ v: v, t: Date.now() })); } catch (e) { /* stockage indisponible : le bandeau reviendra à la page suivante */ }
  }

  /* ------------------------------------------------------------------ script Travelpayouts */
  function loadDrive() {
    if (driveLoaded) { return; }
    driveLoaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.setAttribute('data-cmp-ab', '2');
    s.src = DRIVE;
    document.head.appendChild(s);
  }

  function eraseTraces() {
    try { document.cookie = COOKIE + '=; Max-Age=0; path=/'; } catch (e) { /* ignoré */ }
    try {
      /* donnée de stockage local posée par le script : clé de 16 lettres, valeur = une couleur CSS */
      for (var i = window.localStorage.length - 1; i >= 0; i--) {
        var k = window.localStorage.key(i);
        if (k && /^[A-Za-z]{16}$/.test(k) && /^rgb/.test(String(window.localStorage.getItem(k)))) { window.localStorage.removeItem(k); }
      }
    } catch (e) { /* ignoré */ }
  }

  /* ------------------------------------------------------------------ bandeau */
  function injectStyle() {
    var style = el('style');
    style.id = 'ffk-style';
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function buildBanner() {
    banner = el('div', 'ffk');
    banner.id = 'ff-consent';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-modal', 'false');
    banner.setAttribute('aria-labelledby', 'ffk-title');
    banner.setAttribute('aria-describedby', 'ffk-text');
    banner.hidden = true;

    var title = el('p', 'ffk-title', T.title);
    title.id = 'ffk-title';
    var text = el('p', 'ffk-text', T.text + ' ');
    text.id = 'ffk-text';
    var more = el('a', '', T.more);
    more.href = PRIVACY;
    text.appendChild(more);

    var actions = el('div', 'ffk-actions');
    var no = el('button', 'ffk-btn', T.refuse);
    no.type = 'button';
    no.setAttribute('data-ffk', 'no');
    var yes = el('button', 'ffk-btn', T.accept);
    yes.type = 'button';
    yes.setAttribute('data-ffk', 'yes');
    no.addEventListener('click', function () { decide('no'); });
    yes.addEventListener('click', function () { decide('yes'); });
    actions.appendChild(no);
    actions.appendChild(yes);

    banner.appendChild(title);
    banner.appendChild(text);
    banner.appendChild(actions);
    document.body.appendChild(banner);
  }

  function show(fromOpener) {
    if (!banner) { buildBanner(); }
    reopened = !!fromOpener;
    banner.hidden = false;
    if (fromOpener) { banner.querySelector('button').focus(); }
  }

  function hide() {
    if (banner) { banner.hidden = true; }
    if (reopened && opener) { opener.focus(); }
    reopened = false;
  }

  function decide(choice) {
    saveChoice(choice);
    hide();
    if (choice === 'yes') {
      loadDrive();
    } else {
      eraseTraces();
      /* un script déjà chargé ne peut pas être déchargé : on recharge la page sans lui */
      if (driveLoaded) { window.location.reload(); }
    }
  }

  /* ------------------------------------------------------------------ lien « Gérer les cookies » du pied de page */
  function footerItem() {
    var base = PRIVACY.split('#')[0];
    var links = document.querySelectorAll('.site-footer a[href]');
    for (var i = 0; i < links.length; i++) {
      if (links[i].getAttribute('href') === base) { return links[i].parentNode; }
    }
    return null;
  }

  function addOpener() {
    var li = el('li');
    opener = el('button', 'ffk-open', T.manage);
    opener.type = 'button';
    opener.addEventListener('click', function () { show(true); });
    li.appendChild(opener);
    var after = footerItem();
    if (after && after.parentNode) {
      after.parentNode.insertBefore(li, after.nextSibling);
      return;
    }
    var lists = document.querySelectorAll('.site-footer ul');
    if (lists.length) { lists[lists.length - 1].appendChild(li); }
  }

  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Escape' || e.key === 'Esc') && banner && !banner.hidden && reopened) { hide(); }
  });

  function init() {
    injectStyle();
    addOpener();
    var choice = readChoice();
    if (choice === 'yes') { loadDrive(); }
    else if (choice === null) { show(false); }
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', init); } else { init(); }
})();
