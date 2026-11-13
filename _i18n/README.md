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

## Offre de lancement (gratuit jusqu’à la mi-décembre 2026)

Le bandeau doré en haut de toutes les pages est généré par `build.py` (table `PROMO`, textes fr/en/es) : pour le retirer,
mettre `PROMO = None` puis relancer le build. Les textes de prix, eux, sont écrits dans les pages françaises (puis traduits
dans `translations.json`) ; à la fin de l’offre, il faut les remettre au tarif de 2 € par réservation :
`index.html` (descriptions, barre de faits, étape 2, bloc « Tarif », prix du formulaire, message de confirmation, FAQ),
`conditions-de-vente.html` (en bref, articles 3, 4, 5 et 8), `remboursement.html` (introduction) et
`flyfast-blog/enregistrement-en-ligne-guide-complet.html` (bouton). Les anciennes phrases et leurs traductions restent dans
`translations.json`. « mi‑décembre » s’écrit avec un tiret insécable (`&#8209;`) pour ne pas être coupé en fin de ligne.
Le quota de 50 demandes par jour (une demande = une réservation) est annoncé sur le site ; le formulaire ne l’applique pas.

## Programme d’affiliation Travelpayouts

Le code « Drive » de Travelpayouts (compte Travelpayouts, projet flyfastcheckin.com, marqueur 805301) a pour adresse `TP_DRIVE_SRC`
dans `build.py`. `build.py` ajoute dans l’en-tête des pages, entre `<!--i18n:tp-->` et `<!--/i18n:tp-->`, ce que prévoit `tp_mode` :

| Pages | Chargement |
| --- | --- |
| Blog (index et articles, trois langues) | seulement après un clic sur « Accepter » dans le bandeau de consentement (`flyfast-consent.js`, voir plus bas) : c’est là que se trouveront les liens vers les partenaires |
| Accueil (formulaires de demande et d’avis : passeport, etc.) | seulement si l’adresse contient `?init_marker=…`, c’est-à-dire pour la vérification de Travelpayouts (bouton « Check Drive connection », qui ouvre la page d’accueil) ; jamais pour un visiteur ordinaire, et sans bandeau |
| Pages légales | jamais (aucun lien partenaire), sans bandeau |

Pour le retirer partout : `TP_DRIVE_SRC = None`, puis relancer le build (les pages du blog n’ont alors plus ni Drive ni bandeau ni lien
« Gérer les cookies » ; `flyfast-consent.js` n’est plus utilisé, et la section « Liens partenaires » de la page Confidentialité est à revoir).
Pour le charger sur une autre page, modifier `tp_mode` (et le test dans `test_static.py`) ; ne jamais le charger sur une page à formulaire.
La page `flyfast-blog/documents-visa-rdc-europe.html` n’est pas dans la construction (page orpheline) : elle ne reçoit pas le code.

### Bandeau de consentement (pages du blog)

Les pages du blog ne portent pas le code Drive lui-même : `build.py` y met la balise
`<script src="…/flyfast-consent.js?v=…" data-drive="<adresse Drive>" data-privacy="<page Confidentialité>#liens-partenaires" defer>`.
Le fichier `flyfast-consent.js`, à la racine du site, est **écrit à la main** (il n’est pas généré) :

- à la première visite, il affiche un bandeau dans la langue de la page (`<html lang>` ; textes fr/en/es dans le fichier) avec « Refuser » et
  « Accepter », aussi visibles l’un que l’autre, et un lien « En savoir plus » vers la section « Liens partenaires » de la page Confidentialité ;
- il ne charge Drive qu’après « Accepter ». Le choix est gardé 6 mois dans le stockage local du navigateur (clé `ff-consent`,
  valeur `{"v":"yes"|"no","t":<date en ms>}`), puis le bandeau revient ; si le stockage est bloqué, le bandeau revient à chaque page ;
- il ajoute dans le pied de page du blog, après « Confidentialité », le lien « Gérer les cookies », qui rouvre le bandeau (Échap le referme
  sans changer le choix). Refuser après avoir accepté efface le cookie `am_user_session` et la donnée de stockage local de Drive (clé de 16 lettres,
  valeur de la forme `rgb(…)`), puis recharge la page : un script déjà chargé ne peut pas être déchargé.

Pour changer un texte du bandeau : modifier `flyfast-consent.js`, puis la section « Liens partenaires » de `confidentialite.html` (le test
statique vérifie que le titre du bandeau et « Gérer les cookies » y figurent à l’identique dans chaque langue, ainsi que la durée de 6 mois).
À chaque modification de `flyfast-consent.js`, augmenter `CONSENT_VERSION` dans `build.py` (sinon les navigateurs gardent l’ancienne version en
cache) et relancer le build. Les tests du navigateur (`test_browser.py`, section 5b) déroulent les parcours : refus, acceptation, retrait,
changement d’avis, durée du choix, stockage bloqué, mobile.

Ce que fait le script (constaté le 13 novembre 2026 sur le site en ligne ; il est distant et Travelpayouts peut le modifier) : il charge une
vingtaine de morceaux de code depuis emrldco.com ; il pose un cookie de session de 30 minutes `am_user_session` (sur flyfastcheckin.com) et une
donnée de stockage local ; il envoie à `emrldco.com/collect` un identifiant de session, l’adresse de la page, la taille de la fenêtre, la position
de défilement, une détection de robot et de navigation privée ; il envoie à `emrldco.com/link-switch/v1/convert` la liste des liens de la page ;
il appelle `www.travelpayouts.com/check_auth` ; il ajoute un conteneur d’aperçus (`tp-tooltip-container`). La section « Liens partenaires » de la
page Confidentialité (fr/en/es) décrit ces points : la mettre à jour si le script ou la règle de chargement change.

Réglages Drive (compte Travelpayouts, projet Flyfastcheckin, « Advanced settings ») : par défaut tout est activé (« Monetization boost :
Maximum ») : conversion des liens vers des marques de voyage, liens sur des mots-clés et blocs de recommandations (pages en anglais
seulement), aperçus au survol, et « Targeted Offers » (une offre s’ouvre dans un onglet en arrière-plan). Tant que le site ne contient pas de
lien partenaire, rien n’est converti. Quand on ajoute un lien partenaire (par exemple dans l’article sur l’eSIM), indiquer près du lien que
c’est un lien partenaire (`rel="sponsored"` et une mention visible).

## Choix de traduction

Anglais britannique ; espagnol avec « usted ». Termes : « numéro de dossier » = *request number* / *número de solicitud* ;
« enregistrement en ligne » = *online check-in* / *check-in online* ; « carte d'embarquement » = *boarding pass* / *tarjeta de embarque*.
Les pages légales traduites portent une note indiquant que la version française fait foi.
