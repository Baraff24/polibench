# Sistema di Stile — SCSS + BEM

Questo documento descrive **tutto ciò che serve sapere per lavorare con il CSS di Polibench**: struttura dei file,
metodologia BEM, variabili di design, mixin disponibili, blocchi componente e regole per aggiungere nuovi stili.

---

## Struttura dei file

```
src/styles/
├── main.scss             ← entry point: importa tutto in ordine
├── abstracts/
│   ├── _variables.scss   ← token di design (colori, spaziature, tipografia…)
│   └── _mixins.scss      ← mixin riutilizzabili (card, input)
├── base/
│   ├── _reset.scss       ← reset CSS moderno
│   └── _typography.scss  ← classi helper di testo
├── components/
│   ├── _button.scss      ← .btn
│   ├── _form.scss        ← .form, .field
│   ├── _card.scss        ← .card, .card-grid
│   ├── _alert.scss       ← .alert, .toast
│   ├── _avatar.scss      ← .avatar
│   ├── _dialog.scss      ← .dialog
│   ├── _table.scss       ← .table-wrap, .table
│   ├── _badge.scss       ← .badge
│   ├── _stat-card.scss   ← .stat-card, .stat-grid
│   ├── _spinner.scss     ← .spinner
│   └── _empty-state.scss ← .empty-state
├── layout/
│   ├── _layout.scss      ← .layout, .container, .page, .page-header
│   └── _navbar.scss      ← .sidebar, .topbar, .dropdown, .sidebar-overlay
└── pages/
    ├── _home.scss        ← .hero, .how, .highlights, .stack-section
    ├── _auth.scss        ← .auth
    ├── _profile.scss     ← .profile
    ├── _users.scss       ← .users-layout, .user-list
    ├── _leaderboard.scss ← .leaderboard-filters, .leaderboard-rank, .leaderboard-chart, .leaderboard-model, .leaderboard-link
    ├── _datasets.scss    ← .dataset-card
    ├── _detail.scss      ← .detail-section, .detail-grid, .detail-field
    └── _verify-email.scss← .verify-email
```

### Regola fondamentale

`main.scss` è l'**unico** file CSS importato in `main.tsx`. Tutti gli altri file SCSS dipendono da `abstracts/`
tramite `@use`. Non esistono import CSS nei singoli componenti React.

---

## Principio BEM

BEM (Block Element Modifier) organizza i nomi di classe in tre livelli:

| Livello      | Sintassi           | Esempio                           |
|--------------|--------------------|-----------------------------------|
| **Block**    | `.block`           | `.btn`, `.card`, `.sidebar`       |
| **Element**  | `.block__element`  | `.card__title`, `.btn__icon`      |
| **Modifier** | `.block--modifier` | `.btn--primary`, `.card--compact` |

### Regole pratiche

- Il modifier si aggiunge **sempre insieme** al block: `btn btn--primary`, mai solo `btn--primary`.
- Un elemento non ha modifier diretto: `.card__title--large` è corretto, `.card__title large` no.
- Non annidare più di due livelli: `.sidebar__nav__item` è sbagliato — usare `.sidebar__item`.
- In SCSS si usa il selettore `&` per evitare ripetizioni:

```scss
.card {
  &__title {
    ...
  }

  // .card__title
  &--compact {
    ...
  }

  // .card--compact
}
```

---

## Variabili (`_variables.scss`)

### Palette colori (dark theme)

| Variabile              | Valore hex/rgba       | Uso                           |
|------------------------|-----------------------|-------------------------------|
| `$color-bg-app`        | `#0f1117`             | Sfondo app principale         |
| `$color-bg-sidebar`    | `#14171f`             | Sidebar e topbar              |
| `$color-bg-card`       | `#1a1d27`             | Card, panel, input            |
| `$color-bg-input`      | `#1a1d27`             | Sfondo input e select         |
| `$color-bg-overlay`    | `rgba(#0f1117, 0.75)` | Backdrop modale               |
| `$color-accent`        | `#564ab1`             | Colore primario (indigo)      |
| `$color-accent-light`  | `#7b72cc`             | Hover/focus dell'accent       |
| `$color-text`          | `#ced4da`             | Testo principale              |
| `$color-text-strong`   | `#e9ecef`             | Titoli e label importanti     |
| `$color-text-muted`    | `#6c757d`             | Testo secondario, label, hint |
| `$color-text-inverse`  | `#0f1117`             | Testo su sfondo chiaro        |
| `$color-border`        | `rgba(#fff, 0.07)`    | Bordo sottile standard        |
| `$color-border-strong` | `rgba(#fff, 0.12)`    | Bordo più visibile (dropdown) |

### Colori semantici

| Variabile           | Uso                              |
|---------------------|----------------------------------|
| `$color-success`    | Verde `#0ab39c` — badge/alert OK |
| `$color-success-bg` | Background `rgba` del success    |
| `$color-error`      | Rosso `#f06548` — errori, danger |
| `$color-error-bg`   | Background `rgba` dell'error     |
| `$color-warning`    | Giallo `#f7b84b` — warning       |
| `$color-warning-bg` | Background `rgba` del warning    |
| `$color-info`       | Azzurro `#4bc8ef` — info         |
| `$color-info-bg`    | Background `rgba` dell'info      |

### Tipografia

| Variabile               | Valore rem  | px equiv. |
|-------------------------|-------------|-----------|
| `$font-size-xs`         | `0.6875rem` | 11px      |
| `$font-size-sm`         | `0.8125rem` | 13px      |
| `$font-size-base`       | `0.9375rem` | 15px      |
| `$font-size-md`         | `1rem`      | 16px      |
| `$font-size-lg`         | `1.125rem`  | 18px      |
| `$font-size-xl`         | `1.375rem`  | 22px      |
| `$font-size-2xl`        | `1.75rem`   | 28px      |
| `$font-size-3xl`        | `2.25rem`   | 36px      |
| `$font-weight-regular`  | `400`       |           |
| `$font-weight-medium`   | `500`       |           |
| `$font-weight-semibold` | `600`       |           |
| `$font-weight-bold`     | `700`       |           |
| `$line-height-base`     | `1.6`       |           |
| `$line-height-tight`    | `1.25`      |           |

### Spaziatura

La scala è basata su incrementi di `0.25rem` (4px):

| Variabile   | Valore    | px |
|-------------|-----------|----|
| `$space-1`  | `0.25rem` | 4  |
| `$space-2`  | `0.5rem`  | 8  |
| `$space-3`  | `0.75rem` | 12 |
| `$space-4`  | `1rem`    | 16 |
| `$space-5`  | `1.25rem` | 20 |
| `$space-6`  | `1.5rem`  | 24 |
| `$space-8`  | `2rem`    | 32 |
| `$space-10` | `2.5rem`  | 40 |
| `$space-12` | `3rem`    | 48 |
| `$space-16` | `4rem`    | 64 |
| `$space-20` | `5rem`    | 80 |

### Border radius

| Variabile      | Valore     | Uso tipico                    |
|----------------|------------|-------------------------------|
| `$radius-sm`   | `0.25rem`  | Badge, tag                    |
| `$radius-md`   | `0.375rem` | Input, button piccolo, select |
| `$radius-lg`   | `0.5rem`   | Button standard               |
| `$radius-xl`   | `0.75rem`  | Card, dropdown, panel         |
| `$radius-full` | `9999px`   | Avatar, spinner, rank circle  |

### Layout e z-index

| Variabile           | Valore     | Uso                            |
|---------------------|------------|--------------------------------|
| `$sidebar-width`    | `15rem`    | Larghezza sidebar fissa        |
| `$topbar-height`    | `4.375rem` | Altezza topbar fissa           |
| `$container-max`    | `75rem`    | Max-width pagine standard      |
| `$container-narrow` | `45rem`    | Max-width pagine narrow (auth) |
| `$z-dropdown`       | `100`      | Dropdown menu                  |
| `$z-sidebar`        | `300`      | Sidebar                        |
| `$z-topbar`         | `300`      | Topbar                         |
| `$z-modal-bg`       | `400`      | Backdrop modale                |
| `$z-modal`          | `500`      | Modale                         |
| `$z-toast`          | `600`      | Toast/snackbar                 |

### Transizioni

```scss
$transition: 0.15s ease; // usato per hover, focus, open/close
```

---

## Mixin (`_mixins.scss`)

### `@mixin card`

Applica lo stile base di una card (sfondo, bordo, border-radius):

```scss
@mixin card {
  background: $color-bg-card;
  border: 1px solid $color-border;
  border-radius: $radius-xl;
}
```

**Usato in**: `_card.scss`, `_table.scss` (`.table-wrap`), `_stat-card.scss`, `_datasets.scss`, `_detail.scss`.

### `@mixin input`

Applica lo stile base di un campo input (display, padding, font, colori, focus):

```scss
@mixin input {
  display: block;
  width: 100%;
  padding: $space-3 $space-4;
  font: inherit;
  color: $color-text;
  background: $color-bg-input;
  border: 1px solid $color-border;
  border-radius: $radius-lg;
  transition: border-color $transition;
  &::placeholder {
    color: $color-text-muted;
  }
  &:focus {
    outline: none;
    border-color: $color-accent;
  }
  &:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
}
```

**Usato in**: `_form.scss` (`.field__input`).

---

## Blocchi componente

### `.btn` — `_button.scss`

Pulsante base con varianti di stile e dimensione.

```scss
// Varianti di stile
.btn--primary // sfondo accent, testo bianco
.btn--outline // bordo visibile, sfondo trasparente
.btn--ghost // nessun bordo, hover sottile
.btn--danger // sfondo error
  // Varianti di dimensione
.btn--sm // padding ridotto, font-size xs
.btn--lg // padding aumentato, font-size md
.btn--full // width: 100%
  // Elemento interno
.btn__icon

// SVG 1.125rem
```

Esempio:

```tsx
<button className='btn btn--primary btn--full'>
    <svg className='btn__icon'
    …/>
    Save
</button>
```

---

### `.form` / `.field` — `_form.scss`

Struttura di un form con campi, divisore, footer e azioni.

```scss
.form
.form__title // titolo centrato
.form__subtitle // sottotitolo centrato
.form__footer // testo in fondo (link registrazione)
.form__divider // separatore "or" con linee laterali
.form__actions // wrapper per i bottoni di submit
.field
.field__label // label del campo
.field__input // input (usa @mixin input)
.field__input--error // bordo rosso in stato di errore
.field__error

// messaggio di errore sotto il campo
```

---

### `.card` / `.card-grid` — `_card.scss`

Card generica con media, corpo, footer. La griglia adatta il numero di colonne alla viewport.

```scss
.card
.card__media // immagine/header visivo (height: 8rem, object-fit: contain)
.card__body // contenuto principale (padding, flex: 1)
.card__title // titolo bold
.card__desc // descrizione muted
.card__footer // area azioni in fondo (border-top)
.card-grid

// griglia responsive: 1 col mobile, 2 col ≥768px, 3 col ≥1200px
```

---

### `.badge` — `_badge.scss`

Badge inline con varianti semantiche.

```scss
.badge // base (inline-block, padding, border-radius small)
.badge--success // verde
.badge--error // rosso
.badge--warning // giallo
.badge--info // azzurro
.badge--neutral

// grigio muted
```

Esempio:

```tsx
<span className='badge badge--success'>public</span>
```

---

### `.table-wrap` / `.table` — `_table.scss`

Tabella dati con intestazione, righe, bordi e righe cliccabili.

```scss
.table-wrap // contenitore (usa @mixin card, overflow-x: auto)
.table // <table> a larghezza piena
.table__th // intestazione: muted, uppercase, xs
.table__td // cella: padding, bordo-bottom
.table__tr--clickable

// cursore pointer + hover highlight
```

---

### `.stat-card` / `.stat-grid` — `_stat-card.scss`

Card KPI con icona, valore grande e label.

```scss
.stat-card // usa @mixin card + flex row
.stat-card__icon // contenitore icona (sfondo accent 15%, bordo-radius lg)
.stat-card__body // flex column
.stat-card__value // numero grande (font-size-xl, bold)
.stat-card__label // label uppercase muted xs
.stat-grid

// griglia: auto-fill con min 14rem per colonna
```

---

### `.spinner` — `_spinner.scss`

Spinner di caricamento animato.

```scss
.spinner // wrapper centrato con padding
.spinner__circle

// cerchio con border-top accent + animazione spin
```

---

### `.empty-state` — `_empty-state.scss`

Stato vuoto centrato con titolo e descrizione.

```scss
.empty-state
.empty-state__title // testo muted, font-weight medium
.empty-state__desc

// testo muted, font-size sm
```

---

### `.avatar` — `_avatar.scss`

Avatar circolare con varianti di dimensione.

```scss
.avatar // base circolare
.avatar--sm // 2rem
.avatar--md // 2.5rem
.avatar--lg // 3rem
.avatar--xl // 4.5rem
.avatar__img

// immagine interna
```

---

### `.alert` / `.toast` — `_alert.scss`

Messaggi inline e notifiche a scomparsa.

```scss
.alert // messaggio inline
.alert--success /error/ warning

/
info
.toast-container // fixed bottom-right, z-index toast
.toast // singola notifica
.toast--success /error/ warning

/
info
```

---

### `.dialog` — `_dialog.scss`

Modale con backdrop.

```scss
.dialog-backdrop // overlay scuro (rgba, z-index modal-bg)
.dialog // pannello centrato (z-index modal)
.dialog__header
.dialog__title
.dialog__body
.dialog__footer
```

---

## Layout

### `.layout` — `_layout.scss`

Shell principale dell'applicazione.

```scss
.layout // flex row, min-height: 100vh
.layout__main // area destra con margin-left = sidebar-width e padding-top = topbar-height
.layout--collapsed

// sidebar nascosta: margin-left: 0
```

### `.page` / `.container` / `.page-header`

```scss
.page // padding standard (space-8 space-6)
.container // max-width: 75rem, centrato
.container--narrow // max-width: 45rem (pagine auth)
.page-header // flex row, space-between, margin-bottom space-8
.page-header__title // font-size-xl, bold, text-strong
.page-header__actions

// area destra per bottoni/badge
```

---

### `.sidebar` — `_navbar.scss`

Sidebar verticale fissa a sinistra.

```scss
.sidebar // fixed left, full height, z-index sidebar
.sidebar--hidden // translateX(-100%) — nascosta
.sidebar__brand // area brand (logo + bottone chiudi)
.sidebar__brand-link // link al brand
.sidebar__brand-name // nome app
.sidebar__close // bottone X per chiudere la sidebar
.sidebar__nav // area link di navigazione
.sidebar__section-label // etichetta sezione (es. "Menu", "Admin")
.sidebar__item // link di navigazione (flex row, icona + testo)
.sidebar__item--active // stato attivo (sfondo accent 10%, testo accent-light)
.sidebar__item-icon

// SVG 1.125rem
```

### `.topbar` — `_navbar.scss`

Barra orizzontale fissa in alto.

```scss
.topbar // fixed top, left = sidebar-width, z-index topbar
.topbar--full // left: 0 (sidebar nascosta)
.topbar__toggle // bottone hamburger (visibile solo senza sidebar)
.topbar__right // area destra (avatar, dropdown)
.topbar__avatar-btn // bottone avatar con nome utente
.topbar__user-name

// nome utente (nascosto su mobile)
```

### `.dropdown` — `_navbar.scss`

Menu a tendina per l'account utente.

```scss
.dropdown // position: relative
.dropdown__menu // hidden by default (display: none)
.dropdown__menu--open // display: block
.dropdown__item // voce di menu (link o button)
.dropdown__item--danger // colore error (logout)
.dropdown__divider

// linea separatrice
```

---

## Pagine

### `.auth` — `_auth.scss`

Layout pagine login/register (centrato verticalmente, sfondo app).

### `.hero` / `.features` — `_home.scss`

Homepage: sezione hero con titolo grande e sezione features con griglia di card tecnologia.

### `.profile` — `_profile.scss`

Layout pagina profilo: header avatar + sezioni form.

### `.users-layout` / `.user-list` — `_users.scss`

Layout admin users: due pannelli affiancati (lista a sinistra, dettaglio a destra).

### `.leaderboard-filters` / `.leaderboard-rank` — `_leaderboard.scss`

```scss
.leaderboard-filters // flex wrap con gap
.leaderboard-filters__field // colonna (label + controllo)
.leaderboard-filters__label // label uppercase xs muted
.leaderboard-filters__select // select stilizzata dark
.leaderboard-filters__input // input testuale stilizzato dark
.leaderboard-rank // cerchio numerato per posizione
.leaderboard-rank--gold // #1 — sfondo/testo dorato
.leaderboard-rank--silver // #2 — sfondo/testo argentato
.leaderboard-rank--bronze

// #3 — sfondo/testo bronzo
```

### `.dataset-card` — `_datasets.scss`

Card cliccabile per la lista dataset.

```scss
.dataset-card // usa @mixin card + cursor pointer + hover border accent
.dataset-card__header // flex row space-between (nome + badge visibilità)
.dataset-card__name // nome dataset, semibold
.dataset-card__meta

// versione + task, xs muted
```

### `.detail-section` / `.detail-grid` / `.detail-field` — `_detail.scss`

Layout generico per le pagine dettaglio (dataset, model, experiment).

```scss
.detail-section // usa @mixin card + padding + margin-bottom
.detail-section__title // titolo sezione, semibold
.detail-grid // griglia auto-fill, min 12rem per colonna
.detail-field // singolo campo chiave-valore
.detail-field__label // chiave: uppercase, xs, muted
.detail-field__value

// valore: sm, text normale
```

---

## Come aggiungere nuovi stili

### Aggiungere un nuovo componente UI

1. Crea `src/styles/components/_nome.scss`
2. Inizia con il commento di intestazione e importa le variabili:
   ```scss
   // Component: NomeComponente  (BEM: .nome)
   @use '../abstracts/variables' as *;
   @use '../abstracts/mixins' as *;  // solo se usi @mixin card o @mixin input
   ```
3. Aggiungi il `@use` in `main.scss` nella sezione `// 4. Components`
4. Scrivi il blocco BEM rispettando la convenzione `&__element` e `&--modifier`

### Aggiungere stili per una nuova pagina

1. Crea `src/styles/pages/_nomepagina.scss`
2. Importa solo le variabili necessarie: `@use '../abstracts/variables' as *;`
3. Aggiungi il `@use` in `main.scss` nella sezione `// 5. Pages`
4. Usa classi specifiche della pagina — non ridefinire componenti generici

### Aggiungere una variabile

1. Apri `src/styles/abstracts/_variables.scss`
2. Aggiungi la variabile nella sezione logica appropriata (colori, spaziatura, ecc.)
3. Documentala in questo file (`03_scss.md`) nella tabella della sezione corrispondente

### Aggiungere un mixin

1. Apri `src/styles/abstracts/_mixins.scss`
2. Il mixin deve importare `variables` internamente se ne ha bisogno (`@use 'variables' as *`)
3. Documenta il mixin in questo file nella sezione "Mixin"

### Regole da rispettare

- **Non usare mai `px`**: usa sempre le variabili `$space-*`, `$font-size-*`, `$radius-*`
- **Non usare mai colori hardcodati**: usa sempre le variabili `$color-*`
- **Non usare `!important`**: se serve, è un segnale che la struttura BEM va rivista
- **Non nidificare più di 2 livelli** di selettori SCSS (es. `.card .body .title` è sbagliato)
- **Non scrivere stili inline** nei componenti React
- **Non importare SCSS nei componenti React**: tutti gli stili passano per `main.scss`
- Il modifier `--active` e `--error` vanno sempre aggiunti **insieme** al block/element: mai da soli

