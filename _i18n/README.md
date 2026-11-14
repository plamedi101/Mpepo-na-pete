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
   (navigateur : formulaire, numéro de billet facultatif, limite du jour, aperçu en direct et talon de confirmation, avis, chat,
   mobile, dans les trois langues ; nécessite Playwright).

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

### Limite de 50 demandes par jour

Le service d’enregistrement (Worker Cloudflare `flyfast-api`) applique lui-même la limite annoncée sur le site :

- il compte les **réservations** (une réservation = un PNR, quel que soit le nombre de passagers) acceptées dans la journée ; la
  journée va de minuit à minuit, heure du Caire (variable `QUOTA_TZ` du Worker, `Africa/Cairo` par défaut) ;
- à partir de la 51e réservation du jour, il refuse la demande (réponse 429, code `quota`, avec l’heure de remise à zéro `resets_at`) ;
  les autres passagers d’une réservation déjà acceptée ce jour-là restent acceptés ;
- pour ne compter une réservation qu’une fois, il garde une empreinte non réversible du PNR (table `quota`), effacée au bout de
  deux jours ; la page Confidentialité le dit (ligne « Contrôle anti-abus ») ;
- `GET /api/quota` dit au site si la limite est atteinte (`{ ok, limit, full, resets_at }`) : `index.html` l’interroge au chargement,
  affiche l’avis « Limite du jour atteinte » en tête du formulaire (bloc `#form-quota`) avec l’heure de réouverture à l’heure de
  l’appareil du visiteur, et revérifie tout seul à cette heure-là. Quand le service refuse un envoi, le message apparaît sous le
  bouton, sans bouton de secours WhatsApp (la limite ne doit pas pouvoir être contournée) ;
- l’espace administrateur (`/admin` du Worker) affiche le compteur du jour.

Le nombre vient de la variable `FREE_DAILY_LIMIT` du Worker (50 si elle est absente). **À la fin de l’offre de lancement**, créer
cette variable avec la valeur `0` dans Cloudflare (Workers, `flyfast-api`, Réglages, Variables) : la limite est alors désactivée.
Retirer aussi du site les textes qui parlent des 50 demandes : bloc « Tarif » et avis `#form-quota` du formulaire, FAQ, barre de
faits, étape 2, `conditions-de-vente.html` (en bref et article sur l’offre de lancement) et la phrase ajoutée à la ligne « Contrôle
anti-abus » de `confidentialite.html`. Les textes JavaScript de l’avis sont dans `index_js.py` (table `CODE`), le message du Worker
dans la table `SERVER`.

Le numéro de billet est facultatif (beaucoup de compagnies low cost n’en fournissent pas) : le formulaire l’envoie vide, le Worker
l’accepte vide et l’espace administrateur affiche alors « non fourni ».

## Aperçu en direct et talon de confirmation (page d’accueil)

Deux effets visuels accompagnent le formulaire d’enregistrement. Tout est dans `index.html` (styles `.ticket`, `.pass`, `.stamp`,
`.takeoff` ; script « Aperçu en direct ») : aucune bibliothèque, aucune image, aucun appel réseau.

- **Aperçu en direct** (`#pass-side`) : une carte se remplit pendant la saisie. Elle ne reprend que cinq informations (table
  `PASS_FIELDS` du script) : nom, numéro de vol, référence de réservation, compagnie, date et heure. Jamais le passeport, la
  nationalité, la date de naissance, le téléphone ni le numéro de billet. Sur ordinateur, elle suit le visiteur à côté du
  formulaire ; jusqu’à 900 px de large, c’est son double (`#pass-inline`, créé par le script) qui s’affiche dans le formulaire,
  juste avant le prix. Les barres du bas sont décoratives (ce n’est pas un code-barres) et se remplissent avec le nombre de
  champs obligatoires renseignés.
- **Ce n’est pas une carte d’embarquement** : la carte porte la mention « Aperçu », sans logo de compagnie, et la phrase placée
  dessous le rappelle (la vraie carte est émise par la compagnie). Ne retirez ni la mention ni cette phrase. La carte est
  masquée aux lecteurs d’écran (`aria-hidden`), qui lisent déjà les champs.
- **Talon de confirmation** (`#done-ticket`) : quand le service accepte la demande, la confirmation prend la forme d’un talon
  avec le numéro de dossier, un tampon daté du jour et un avion qui décolle. Les textes et boutons de la confirmation sont
  inchangés ; le tampon et l’avion sont décoratifs.
- **Animations** : elles sont toutes coupées quand l’appareil du visiteur le demande (`prefers-reduced-motion`) ; la carte et
  le talon s’affichent alors directement dans leur état final.
- **Textes** : libellés de la carte et tampon dans `translations.json` ; compteur « Encore n champs à remplir » dans
  `index_js.py` (table `CODE`).

## Programme d’affiliation Travelpayouts

Le code « Drive » de Travelpayouts (compte Travelpayouts, projet flyfastcheckin.com, marqueur 805301) a pour adresse `TP_DRIVE_SRC`
dans `build.py`. `build.py` ajoute dans l’en-tête des pages, entre `<!--i18n:tp-->` et `<!--/i18n:tp-->`, ce que prévoit `tp_mode` :

| Pages | Chargement |
| --- | --- |
| Blog (index et articles, trois langues) | seulement après un clic sur « Accepter » dans le bandeau de consentement (`flyfast-consent.js`, voir plus bas). Les articles portent aussi des liens partenaires directs (encarts « Services partenaires »), qui, eux, ne dépendent pas de ce script |
| Accueil (formulaires de demande et d’avis : passeport, etc.) | seulement si l’adresse contient `?init_marker=…`, c’est-à-dire pour la vérification de Travelpayouts (bouton « Check Drive connection », qui ouvre la page d’accueil) ; jamais pour un visiteur ordinaire, et sans bandeau |
| Page Partenaires (`partenaires.html`) | jamais : elle ne contient que des liens directs `tpk.lu`, qui ne chargent rien avant le clic ; sans bandeau |
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
seulement), aperçus au survol, et « Targeted Offers » (une offre s’ouvre dans un onglet en arrière-plan). Les liens partenaires du site
sont déjà des liens Travelpayouts (`tpk.lu`) : Drive n’a donc rien à convertir pour eux. Tout nouveau lien partenaire suit la règle
ci-dessous (`rel="sponsored noopener"` et mention « lien partenaire » visible juste après le lien).

### Liens partenaires dans le site (page Partenaires et encarts)

Les 25 liens partenaires (un lien Travelpayouts `…tpk.lu/…` par programme, Sub ID `ff-<programme>`, générés dans le compte Travelpayouts ;
la liste, avec commissions, durées de cookie et pages de destination, est dans le tableau « Liens affiliés FlyFast ») sont placés ainsi :

| Où | Quoi |
| --- | --- |
| `partenaires.html` (en : `partners.html`, es : `socios.html`) | les 25 liens, par catégorie : eSIM et SIM voyage, vols, indemnisation d’un vol retardé ou annulé, consigne à bagages, transferts, location de voiture, location de scooter et de moto, activités et billets ; encadré « À savoir avant de cliquer » (commission, rôle de FlyFast, lien vers la section « Liens partenaires » de Confidentialité) |
| Articles du blog (avant l’appel à l’action) | encart « Services partenaires » : eSIM → article eSIM ; consigne → bagages ; transferts + indemnisation → guide d’enregistrement ; vols → jargon (GDS, PNR) ; voiture, deux-roues, activités → documents pour l’Europe |
| Pied de page de toutes les pages, liste du blog, FAQ de l’accueil | lien « Partenaires » ; entrée « Partenaires » dans la liste du blog ; question « Pourquoi le site contient-il des liens partenaires ? » |
| `confidentialite.html`, section « Liens partenaires » | liens présents sur tout le site, ce qui se passe au clic (rien n’est envoyé avant), script Drive limité au blog et soumis au bandeau |

Règle pour **chaque** lien partenaire : `target="_blank" rel="sponsored noopener"`, et, juste après le lien (sans texte entre les deux),
`<span class="p-tag">lien partenaire</span>` (traduit : *partner link* / *enlace de socio*) ; la commission est annoncée dans la même page
(encadré de la page Partenaires, phrase d’introduction de chaque encart). Les descriptions restent factuelles : FlyFast n’a pas testé ces
services et ne les « recommande » pas ; ne pas y promettre de prix, de délai ou de couverture.

Pour ajouter, retirer ou changer un lien : modifier `partenaires.html` et, s’il y est repris, l’encart de l’article ; traduire les nouvelles
phrases (les noms de marque sont traduits à l’identique) ; mettre à jour la liste `PARTNERS` (et `BOXES`) de `test_static.py`, qui contient
les adresses attendues écrites à la main ; relancer build et tests. Le test statique vérifie les 25 adresses dans les trois langues, `rel`,
`target`, la mention après chaque lien, l’annonce de la commission, l’ordre des catégories, les liens de pied de page ; le test navigateur
(section 5c) vérifie qu’aucune requête ne part vers `tpk.lu` avant un clic, que chaque clic ouvre la bonne adresse dans un nouvel onglet sans
lien avec la page d’origine, et que rien ne déborde à 320 et 390 px.

## Choix de traduction

Anglais britannique ; espagnol avec « usted ». Termes : « numéro de dossier » = *request number* / *número de solicitud* ;
« enregistrement en ligne » = *online check-in* / *check-in online* ; « carte d'embarquement » = *boarding pass* / *tarjeta de embarque*.
Les pages légales traduites portent une note indiquant que la version française fait foi.
