# Limiti Attuali e Sviluppi Futuri

Questo documento descrive onestamente i limiti dell'implementazione corrente di Polibench e le direzioni di
sviluppo future. È utile sia per la stesura della tesi (sezione "Limiti e Lavori Futuri") sia per orientare le
prossime fasi di sviluppo.

---

## Limiti attuali

### 1. Autenticazione e permessi essenziali

Il sistema di autenticazione attuale supporta:

- JWT con email/password
- Google OAuth2 (SSO)
- Verifica email con token JWT e invio SMTP
- Ruoli utente: `admin`, `researcher`, `viewer`
- Flag `is_superuser` per operazioni amministrative

**Cosa manca**:

- Non esiste un sistema di permessi granulare per risorsa (es. "solo il team che ha creato un Dataset può
  sottomettere Experiment su quel Dataset").
- Non esiste una distinzione tra Dataset `public` e `private` a livello di enforcement negli endpoint (il campo
  `visibility` è dichiarato nel modello ma non filtrato nei query).
- Non esiste un meccanismo di invito o approvazione per i team.
- `is_verified` non è ancora usato come gate obbligatorio per operazioni sensibili (submission di experiment).
  Attualmente è informativo.

**Impatto attuale**: in un contesto accademico controllato con pochi utenti fidati, questo non è un problema
operativo. Diventa rilevante se la piattaforma venisse aperta a utenti esterni non verificati.

---

### 2. Nessun caching della leaderboard

La query di leaderboard viene eseguita ad ogni richiesta HTTP. Con gli indici MongoDB ottimali, questo è veloce
per volumi piccoli/medi, ma non scala a:

- migliaia di metriche per dataset molto popolari
- richieste concorrenti frequenti (es. durante una conferenza)

**Soluzione futura**: materializzare la leaderboard in Redis (o equivalente) con invalidazione quando arrivano nuove
submission. Non implementato nell'MVP per semplicità.

---

### 3. Nessun job runner per esecuzioni automatizzate

Il campo `status` in `Experiment` prevede `queued | running | finished | failed`, ma non esiste un sistema che
esegua automaticamente gli esperimenti. Il workflow attuale è:

1. Il ricercatore esegue l'algoritmo localmente
2. Sottomette i risultati via API (`POST /experiments` + `POST /metrics`)

**Cosa manca**: un job runner che riceva la submission, istanzi un container con il codice dell'algoritmo,
esegua il training/test e sottometta automaticamente le metriche. Questo porterebbe Polibench da sistema di
*registrazione* dei risultati a sistema di *esecuzione verificata*, come fa BARS.

**Impatto**: senza esecuzione verificata, i risultati dipendono dalla correttezza del codice del ricercatore.
Per un sistema accademico in fase MVP, questo è accettabile. Per un benchmark con claim di riproducibilità forte,
diventa una limitazione.

---

### 4. Nessun versioning avanzato delle metriche

Non esiste un meccanismo per gestire multiple "run" della stessa coppia (Dataset, MLModel) con versioni esplicite.
Due Experiment con gli stessi `dataset_id` e `model_id` sono semplicemente due run distinte, senza un concetto di
"versione ufficiale" o "miglior run".

**Comportamento attuale**: la leaderboard mostra tutte le run. Se un team ha sottomesso lo stesso modello più volte,
appare più volte. Non c'è aggregazione per "miglior risultato per team/modello".

**Soluzione futura**: aggiungere una query leaderboard con `GROUP BY (model_id, team_id)` e `MAX(value)`, o un campo
`is_official: bool` sugli Experiment per distinguere le run da mostrare in leaderboard.

---

### 5. Team model volutamente semplice

Il modello `Team` attuale ha: `uuid`, `name`, `description`, `owner_user_uuid`. Non gestisce:

- membership multipla verificata (un utente ha `team_uuid` in `User`, ma non c'è una lista di membri nel Team)
- ruoli all'interno del team (es. team-admin vs team-member)
- richieste di join con approvazione

Questa scelta è stata deliberata per mantenere il modello semplice nell'MVP. Il
documento [10_decisions.md](./10_decisions.md)
non include questa come ADR esplicita perché è più una "feature non ancora implementata" che una scelta architetturale.

---

### 6. Paginazione senza metadati

Gli endpoint di listing (`GET /datasets`, `GET /ml-models`, `GET /experiments`) supportano `limit` e `offset` ma non
restituiscono il conteggio totale degli elementi. Il frontend non sa quante pagine esistono.

**Impatto**: per ora il frontend può mostrare un pulsante "Carica altri" (infinito scroll) ma non può mostrare
"Pagina 3 di 7". Soluzione banale: aggiungere `GET /datasets/count` o includere `total` nella response.

---

### 7. Nessuna validazione del formato delle metriche

`POST /experiments/{uuid}/metrics` accetta qualsiasi stringa come nome metrica (es. `"ndcg@10"`, `"recall@20"`).
Non esiste una lista di metriche valide per task. Un ricercatore potrebbe sottomettere `"accuracy"` per un task
di ranking, e il sistema non segnalerebbe l'incoerenza.

**Soluzione futura**: aggiungere una collezione `MetricDefinition` (o un enum per task) che definisce le metriche
valide per ogni `TaskType`, e validare in `services/metrics.py`.

---

### 8. Nessun supporto per benchmark multi-task

Il campo `task` in `Dataset` prevede `ranking | rating_prediction`. In sistemi più avanzati (es. BARS-CTR), i dataset
possono avere task aggiuntivi (click-through rate prediction, session-based recommendation). L'enum `TaskType` è
estensibile, ma l'aggiunta di nuovi task richiederebbe potenzialmente nuove metriche e nuove logiche di validazione.

---

## Sviluppi futuri prioritari

### Priorità alta

| Feature                           | Motivazione                                                     |
|-----------------------------------|-----------------------------------------------------------------|
| Enforcement visibilità Dataset    | Completare la feature `public/private` già modellata            |
| Aggregazione leaderboard per team | Mostrare "miglior risultato per modello/team" nella leaderboard |
| CLI di submission                 | Permettere a script esterni di sottomettere risultati via API   |
| Metadati di paginazione           | `total` nelle response di listing                               |

### Priorità media

| Feature                           | Motivazione                                          |
|-----------------------------------|------------------------------------------------------|
| Caching leaderboard (Redis)       | Performance su dataset popolari                      |
| Validazione nome metrica per task | Coerenza dei dati di benchmark                       |
| Team membership strutturata       | Necessario per accesso multi-utente al team          |
| Export risultati (CSV/JSON)       | Utilità per ricercatori che vogliono analisi offline |

### Priorità bassa (lungo termine)

| Feature                                | Motivazione                                               |
|----------------------------------------|-----------------------------------------------------------|
| Job runner per esecuzione verificata   | Riproducibilità forte in stile BARS                       |
| Versioning dataset                     | Gestire aggiornamenti del dataset senza rompere la storia |
| API pubblica con authn per terze parti | Integrazioni con tool di benchmark esterni                |
| Supporto task aggiuntivi               | Estendere oltre ranking e rating prediction               |

---

## Confronto con sistemi simili

### BARS (Benchmark and Reproducibility System)

BARS è il sistema di riferimento accademico che ha ispirato il design di Polibench. Le differenze principali:

| Aspetto                  | BARS                                     | Polibench (MVP)                           |
|--------------------------|------------------------------------------|-------------------------------------------|
| Esecuzione esperimenti   | Automatizzata (job runner)               | Manuale (ricercatore esegue e sottomette) |
| Verifica riproducibilità | Esecuzione su infrastruttura controllata | Fiducia nel ricercatore                   |
| Scope                    | Benchmark specifici (CTR)                | Generalizzabile a più task                |
| Interfaccia              | API + web UI                             | API + web UI (in sviluppo)                |
| Identità pubblica        | UUID/slug                                | UUID                                      |

### OpenBenchmark

OpenBenchmark è un altro sistema di riferimento per benchmark aperti. Polibench ne adotta il principio
"UUID-first API" e la separazione tra algoritmo (MLModel) e run (Experiment).

---

## Note per la tesi

I limiti sopra elencati non sono debolezze del progetto: sono scelte consapevoli di scope per un MVP accademico.
La distinzione importante da comunicare nella tesi è:

> "Il sistema è progettato per essere esteso. Le limitazioni attuali sono note, documentate e risolvibili
> senza stravolgere l'architettura, perché le decisioni progettuali fondamentali (UUID-first, service layer,
> denormalizzazione) sono già orientate alla scalabilità."

