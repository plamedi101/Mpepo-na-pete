/* FlyFast : bouton « Discuter ».
 *
 * Ouvre un petit panneau où le visiteur écrit sa question ; la conversation continue sur WhatsApp,
 * avec le message déjà rédigé. Ce script n’envoie rien à notre site ni à un tiers : rien ne part tant que
 * le visiteur n’a pas touché « Envoyer sur WhatsApp », et il relit son message dans WhatsApp avant de l’envoyer.
 * Aucun cookie, aucun stockage dans le navigateur.
 *
 * Pour que n’importe quel élément ouvre le panneau, lui ajouter l’attribut data-open-chat.
 */
(function () {
  'use strict';
  if (window.__ffChat) { return; }
  window.__ffChat = true;

  var WHATSAPP_NUMBER = '201508319385';
  var MAX_LENGTH = 400;
  var DEFAULT_TEXT = 'Bonjour FlyFast, j’ai une question.';
  var TOPICS = [
    { label: 'Comment ça marche ?', text: 'Bonjour FlyFast, comment fonctionne l’enregistrement de mon vol ?' },
    { label: 'Combien ça coûte ?', text: 'Bonjour FlyFast, combien coûte votre service ?' },
    { label: 'Mon vol part bientôt', text: 'Bonjour FlyFast, mon vol part dans moins de 10 heures. Que puis-je faire ?' },
    { label: 'Conseils de voyage', text: 'Bonjour FlyFast, j’ai une question sur mon voyage : ' }
  ];

  var script = document.currentScript;
  var base = (script && script.getAttribute('data-base')) || '';

  var CSS = [
    '.ffc{--ffc-navy:#0C2E4E;--ffc-navy-2:#154670;--ffc-sky:#3B9EE8;--ffc-gold:#F0B92E;--ffc-gold-hover:#F7CB55;--ffc-ink:#13222F;--ffc-muted:#4A5B6C;--ffc-line:#D5DFEA;--ffc-mist:#F2F6FA;--ffc-field:#6C7F92;font-family:var(--font-body,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif);font-size:1rem;line-height:1.5;color:var(--ffc-ink);}',
    '.ffc *,.ffc *::before,.ffc *::after{box-sizing:border-box;}',
    '.ffc [hidden]{display:none !important;}',
    '.ffc button,.ffc textarea{font:inherit;}',
    '.ffc-launch{position:fixed;right:20px;bottom:20px;z-index:90;display:inline-flex;align-items:center;gap:10px;min-height:52px;padding:0 22px 0 18px;border:0;border-radius:26px;background:var(--ffc-navy);color:#fff;font-weight:600;line-height:1;cursor:pointer;box-shadow:0 0 0 2px #fff,0 6px 20px rgba(12,46,78,.35);}',
    '.ffc-launch:hover{background:var(--ffc-navy-2);}',
    '.ffc-launch svg{width:22px;height:22px;flex:none;color:var(--ffc-gold);}',
    '.ffc-launch:focus-visible,.ffc-close:focus-visible{outline:3px solid #fff;outline-offset:0;box-shadow:0 0 0 6px #1D6FB8;}',
    '.ffc-panel{position:fixed;right:20px;bottom:86px;z-index:91;display:flex;flex-direction:column;width:380px;max-width:calc(100vw - 32px);max-height:calc(100vh - 110px);max-height:calc(100dvh - 110px);overflow:hidden;background:#fff;border:1px solid var(--ffc-line);border-radius:10px;box-shadow:0 18px 50px rgba(12,46,78,.32);}',
    '.ffc-stripe{flex:none;height:4px;background:linear-gradient(90deg,var(--ffc-sky) 0 58%,var(--ffc-gold) 58% 60.5%,#CE1021 60.5% 67.5%,var(--ffc-gold) 67.5% 70%,var(--ffc-sky) 70% 100%);}',
    '.ffc-head{flex:none;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;padding:14px 8px 14px 20px;background:var(--ffc-navy);color:#fff;}',
    '.ffc-title{margin:0;color:#fff;font:700 1.375rem/1.15 var(--font-head,"Barlow Semi Condensed",system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif);letter-spacing:-0.005em;}',
    '.ffc-sub{margin:6px 0 0;font-size:.9375rem;color:#C9D9E8;}',
    '.ffc-close{flex:none;display:inline-flex;align-items:center;justify-content:center;width:44px;height:44px;border:0;border-radius:6px;background:transparent;color:#fff;cursor:pointer;}',
    '.ffc-close:hover{background:rgba(255,255,255,.12);}',
    '.ffc-close svg{width:20px;height:20px;}',
    '.ffc-body{flex:1 1 auto;min-height:0;overflow:auto;padding:16px 20px 18px;}',
    '.ffc-lead{margin:0 0 12px;font-weight:500;color:var(--ffc-navy);}',
    '.ffc-chips{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 14px;padding:0;list-style:none;}',
    '.ffc-chip{min-height:40px;padding:8px 14px;border:1.5px solid var(--ffc-line);border-radius:20px;background:#fff;color:var(--ffc-navy);font-size:.9375rem;font-weight:500;line-height:1.2;cursor:pointer;}',
    '.ffc-chip:hover{border-color:var(--ffc-sky);background:var(--ffc-mist);}',
    '.ffc label.ffc-label{display:block;margin-bottom:6px;font-weight:600;color:var(--ffc-navy);}',
    '.ffc-text{display:block;width:100%;min-height:92px;padding:12px 14px;border:1.5px solid var(--ffc-field);border-radius:6px;background:#fff;color:var(--ffc-ink);line-height:1.45;resize:vertical;}',
    '.ffc-text:focus{border-color:var(--ffc-navy);outline:3px solid #1D6FB8;outline-offset:1px;}',
    '.ffc-count{margin:6px 0 0;font-size:.875rem;color:var(--ffc-muted);text-align:right;}',
    '.ffc-send{display:flex;align-items:center;justify-content:center;min-height:52px;margin-top:10px;padding:0 20px;border-radius:6px;background:var(--ffc-gold);color:var(--ffc-navy);font-weight:600;text-align:center;text-decoration:none;}',
    '.ffc-send:hover{background:var(--ffc-gold-hover);}',
    '.ffc-send:focus-visible{outline:3px solid #1D6FB8;outline-offset:3px;}',
    '.ffc-note{margin:14px 0 0;font-size:.875rem;color:var(--ffc-muted);}',
    '.ffc-note + .ffc-note{margin-top:8px;}',
    '.ffc-note a{color:#0F5A93;text-decoration:underline;text-underline-offset:3px;}',
    '.ffc-note a:focus-visible,.ffc-chip:focus-visible{outline:3px solid #1D6FB8;outline-offset:3px;}',
    '@media (prefers-reduced-motion:no-preference){.ffc-panel:not([hidden]){animation:ffc-in .18s ease-out;}@keyframes ffc-in{from{opacity:0;transform:translateY(8px);}to{opacity:1;transform:none;}}}',
    '@media (max-width:760px){.site-footer{padding-bottom:92px;}.ffc-quiet:not(.ffc-open) .ffc-launch{display:none;}}',
    '@media (max-width:560px){.ffc-launch{right:14px;bottom:14px;}.ffc-open .ffc-launch{display:none;}.ffc-panel{left:10px;right:10px;bottom:10px;width:auto;max-width:none;max-height:calc(100vh - 20px);max-height:calc(100dvh - 20px);}.ffc-head{padding:14px 6px 14px 16px;}.ffc-body{padding:14px 16px 16px;}.ffc-chips{gap:6px;margin-bottom:14px;}.ffc-chip{padding:8px 12px;font-size:.875rem;}.ffc-text{min-height:92px;}}',
    '@media print{.ffc{display:none !important;}}'
  ].join('\n');

  var BUBBLE = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M21 11.5a8.4 8.4 0 0 1-8.6 8.2 9 9 0 0 1-3.6-.7L3.5 20.5l1.6-4.5A7.9 7.9 0 0 1 3.8 11.5C3.8 6.9 7.6 3.3 12.4 3.3S21 6.9 21 11.5z"/><path d="M8.6 10.4h6.8M8.6 13.4h4.2"/></svg>';
  var CROSS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false"><path d="M6 6l12 12M18 6L6 18"/></svg>';

  function build() {
    var style = document.createElement('style');
    style.setAttribute('data-ffc', '');
    style.textContent = CSS;
    document.head.appendChild(style);

    var root = document.createElement('div');
    root.className = 'ffc';
    root.id = 'ffc-root';
    root.innerHTML =
      '<button class="ffc-launch" type="button" aria-expanded="false" aria-controls="ffc-panel">' + BUBBLE + '<span>Discuter</span></button>' +
      '<section class="ffc-panel" id="ffc-panel" role="dialog" aria-labelledby="ffc-title" hidden>' +
        '<div class="ffc-stripe" aria-hidden="true"></div>' +
        '<div class="ffc-head">' +
          '<div><h2 class="ffc-title" id="ffc-title">Une question ?</h2>' +
          '<p class="ffc-sub">Conseils gratuits sur l’enregistrement en ligne et le voyage. La conversation continue sur WhatsApp.</p></div>' +
          '<button class="ffc-close" type="button" aria-label="Fermer la fenêtre de discussion">' + CROSS + '</button>' +
        '</div>' +
        '<div class="ffc-body">' +
          '<p class="ffc-lead" id="ffc-lead">Choisissez un sujet ou écrivez votre question.</p>' +
          '<ul class="ffc-chips" aria-labelledby="ffc-lead"></ul>' +
          '<label class="ffc-label" for="ffc-text">Votre message</label>' +
          '<textarea class="ffc-text" id="ffc-text" rows="4" maxlength="' + MAX_LENGTH + '" aria-describedby="ffc-count"></textarea>' +
          '<p class="ffc-count" id="ffc-count"></p>' +
          '<a class="ffc-send" href="#" target="_blank" rel="noopener">Envoyer sur WhatsApp</a>' +
          '<p class="ffc-note">Votre message s’ouvre dans WhatsApp : vous le relisez avant de l’envoyer.</p>' +
          '<p class="ffc-note">N’écrivez ici ni numéro de passeport, ni numéro de carte bancaire. Pour une demande d’enregistrement, utilisez le <a class="ffc-formlink" href="#">formulaire sécurisé</a>.</p>' +
        '</div>' +
      '</section>';

    var launch = root.querySelector('.ffc-launch');
    var panel = root.querySelector('.ffc-panel');
    var closeBtn = root.querySelector('.ffc-close');
    var chips = root.querySelector('.ffc-chips');
    var ta = root.querySelector('.ffc-text');
    var count = root.querySelector('.ffc-count');
    var send = root.querySelector('.ffc-send');
    var formLink = root.querySelector('.ffc-formlink');

    var onPageForm = !!document.getElementById('enregistrer');
    formLink.setAttribute('href', onPageForm ? '#enregistrer' : base + 'index.html#enregistrer');

    TOPICS.forEach(function (t) {
      var li = document.createElement('li');
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'ffc-chip';
      b.textContent = t.label;
      b.addEventListener('click', function () {
        var current = ta.value.trim();
        var known = TOPICS.some(function (x) { return x.text.trim() === current; });
        ta.value = (!current || known) ? t.text : current + '\n' + t.text;
        refresh();
        ta.focus();
        ta.setSelectionRange(ta.value.length, ta.value.length);
      });
      li.appendChild(b);
      chips.appendChild(li);
    });

    function message() {
      var t = ta.value.trim();
      if (!t) { return DEFAULT_TEXT; }
      return /^bonjour/i.test(t) ? t : 'Bonjour FlyFast, ' + t;
    }
    function refresh() {
      send.setAttribute('href', 'https://wa.me/' + WHATSAPP_NUMBER + '?text=' + encodeURIComponent(message()));
      count.textContent = ta.value.length + '/' + MAX_LENGTH;
    }

    function setOpen(open) {
      panel.hidden = !open;
      launch.setAttribute('aria-expanded', open ? 'true' : 'false');
      root.classList.toggle('ffc-open', open);
      if (open) { refresh(); ta.focus(); }
    }
    function close(returnFocus) {
      var hadFocus = panel.contains(document.activeElement);
      setOpen(false);
      if (returnFocus || hadFocus) { launch.focus(); }
    }

    launch.addEventListener('click', function () { if (panel.hidden) { setOpen(true); } else { close(true); } });
    closeBtn.addEventListener('click', function () { close(true); });
    ta.addEventListener('input', refresh);
    send.addEventListener('click', function () { refresh(); });
    formLink.addEventListener('click', function () { if (onPageForm) { setOpen(false); } });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !panel.hidden) { close(true); }
    });
    document.addEventListener('click', function (e) {
      var t = e.target && e.target.closest ? e.target.closest('[data-open-chat]') : null;
      if (t) { e.preventDefault(); if (panel.hidden) { setOpen(true); } }
    });

    document.body.appendChild(root);
    refresh();

    // Sur petit écran, le bouton s’efface quand un formulaire passe dans la zone du bas de l’écran (là où il se trouve)
    // ou dès qu’on tape dans un formulaire : il ne masque ainsi jamais un champ ni un bouton d’envoi.
    var forms = document.querySelectorAll('form');
    if (forms.length) {
      var BAND = 150;
      var inBand = [];
      var typing = false;
      var io = null;
      var resizeTimer = 0;
      var updateQuiet = function () { root.classList.toggle('ffc-quiet', typing || inBand.length > 0); };
      var watch = function () {
        if (!('IntersectionObserver' in window)) { return; }
        if (io) { io.disconnect(); }
        inBand = [];
        io = new IntersectionObserver(function (entries) {
          entries.forEach(function (en) {
            var i = inBand.indexOf(en.target);
            if (en.isIntersecting && i === -1) { inBand.push(en.target); }
            if (!en.isIntersecting && i !== -1) { inBand.splice(i, 1); }
          });
          updateQuiet();
        }, { rootMargin: '-' + Math.max(0, window.innerHeight - BAND) + 'px 0px 0px 0px', threshold: 0 });
        Array.prototype.forEach.call(forms, function (f) { io.observe(f); });
      };
      document.addEventListener('focusin', function (e) {
        typing = !!(e.target && e.target.closest && e.target.closest('form'));
        updateQuiet();
      });
      document.addEventListener('focusout', function () { typing = false; updateQuiet(); });
      window.addEventListener('resize', function () {
        window.clearTimeout(resizeTimer);
        resizeTimer = window.setTimeout(watch, 200);
      });
      watch();
    }
  }

  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', build); } else { build(); }
})();
