# Versions anglaise et espagnole du site

Les pages **françaises** sont la source. Tout le reste est **généré** par `build.py` : ne modifiez pas à la main les dossiers
`en/` et `es/`, le sélecteur de langue et les balises `hreflang` des pages, `sitemap.xml` ni `flyfast-chat.js`
(vos modifications seraient écrasées à la prochaine génération).

Ce dossier commence par un tiret bas : GitHub Pages ne le publie pas.

## Modifier le site

1. Modifiez la page française (par exemple `index.html`).
2. Si un texte a été changé ou ajouté, listez les phrases qui n'ont pas encore de traduction :

   ```
   python3 _i18n/extract.py . /tmp/a_traduire.txt index.html mentions-legales.html
   ```

   Ajoutez ensuite chaque phrase (traduction anglaise et espagnole) dans `_i18n/translations.json`, sous la forme
   `"phrase française": {"en": "…", "es": "…"}`. Les balises à l'intérieur d'une phrase sont remplacées par des repères
   numérotés (`<a1>…</a1>`, `<strong1>…</strong1>`, `{svg1}`, `<br>`) qui doivent se retrouver à l'identique dans la traduction.
3. Régénérez tout (relançable à volonté, le résultat est identique) :

   ```
   python3 _i18n/build.py .
   ```

   Pour fixer la date du plan du site : `BUILD_DATE=2026-11-09 python3 _i18n/build.py .`
4. Vérifiez : `python3 _i18n/test_static.py .` (structure, liens, langues, plan du site), puis, le site étant servi en local
   (`python3 -m http.server 8766` dans le dossier du site), `python3 _i18n/test_browser.py http://127.0.0.1:8766/`
   (navigateur : formulaire, avis, chat, mobile, dans les trois langues ; nécessite Playwright).

## Où se trouvent les textes

| Quoi | Où |
| --- | --- |
| Texte des pages (éléments, `alt`, `aria-label`, descriptions, messages WhatsApp prérempli) | `translations.json` |
| Textes JavaScript de `index.html` (formulaire, avis, erreurs) | `index_js.py`, table `CODE` |
| Messages d'erreur du service d'enregistrement (écrits en français par le Worker), traduits dans le navigateur | `index_js.py`, table `SERVER` : ajoutez-y tout nouveau message du Worker |
| Bouton et fenêtre de chat | version française dans `flyfast-chat.fr.js`, textes anglais et espagnols dans `patch_chat.py` |
| Adresses des pages traduites | `build.py`, liste `_SLUGS` |
| Note « traduction de courtoisie » des pages légales | `build.py`, `NOTE_TEXT` |

Si une phrase française du script de `index.html` ou du chat change, `build.py` s'arrête avec un message : mettez alors la table
correspondante à jour.

## Ajouter une page

Ajoutez-la dans `_SLUGS` (chemin français, chemin anglais, chemin espagnol), traduisez ses textes (étape 2) puis régénérez.

## Choix de traduction

Anglais britannique ; espagnol avec « usted ». Termes : « numéro de dossier » = *request number* / *número de solicitud* ;
« enregistrement en ligne » = *online check-in* / *check-in online* ; « carte d'embarquement » = *boarding pass* / *tarjeta de embarque*.
Les pages légales traduites portent une note indiquant que la version française fait foi.
