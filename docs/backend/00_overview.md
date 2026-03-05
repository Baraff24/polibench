# Backend — Panoramica Generale

## Cos'è Polibench

Polibench è una piattaforma web per il **benchmarking comparativo di modelli di raccomandazione**. L'obiettivo è fornire
un ambiente strutturato in cui ricercatori e team possano:

- registrare dataset di valutazione con le relative partizioni (train/test/validation)
- registrare algoritmi di raccomandazione (MLModel) con le loro caratteristiche
- sottomettere esperimenti (Experiment) che associano un algoritmo a un dataset
- registrare le metriche di valutazione prodotte da ogni esperimento
- consultare una leaderboard che mostra i risultati ordinati per metrica

Il sistema è pensato per contesti accademici e di ricerca, dove la riproducibilità e la trasparenza dei risultati sono
requisiti fondamentali.

## Perché un benchmark dedicato

Nei sistemi di raccomandazione, confrontare modelli diversi è storicamente difficile perché:

- dataset diversi portano a risultati non comparabili
- le partizioni train/test variano da paper a paper
- le implementazioni di riferimento non sempre coincidono
- le metriche (@k, split, direzione) vengono calcolate con varianti diverse

Polibench affronta questi problemi centralizzando dataset, partizioni e metriche in un unico sistema con un contratto
API ben definito.

## Struttura del backend

Il backend è un'applicazione **FastAPI** che espone una REST API. Si compone di sei strati distinti:

```
┌─────────────────────────────────────────┐
│              HTTP (FastAPI)              │  ← routers/
├─────────────────────────────────────────┤
│          Schemi API (Pydantic)           │  ← schemas/
├─────────────────────────────────────────┤
│         Service Layer (logica)           │  ← services/
├─────────────────────────────────────────┤
│          Autenticazione (JWT)            │  ← auth/
├─────────────────────────────────────────┤
│       Modelli dati (Beanie/ODM)          │  ← models/
├─────────────────────────────────────────┤
│          Database (MongoDB)              │  ← via Motor (async)
└─────────────────────────────────────────┘
```

Ogni strato ha una responsabilità precisa e non conosce i dettagli degli strati al di sotto del successivo.
I **router** sono volutamente sottili: ricevono la richiesta HTTP, delegano al **service layer** e restituiscono
la risposta. Tutta la logica (risoluzione UUID→ObjectId, denormalizzazione, query) vive nei service.

## Entità principali

Il dominio del problema si articola attorno a sei entità:

| Entità       | Descrizione                                                                |
|--------------|----------------------------------------------------------------------------|
| `User`       | Utente della piattaforma, con ruolo e metodo di autenticazione             |
| `Team`       | Gruppo di ricerca, raggruppa utenti sotto uno stesso namespace             |
| `Dataset`    | Dataset di valutazione con task, versione e partizioni                     |
| `MLModel`    | Algoritmo di raccomandazione registrato nel sistema                        |
| `Experiment` | Associazione dataset–modello con configurazione e stato                    |
| `Metric`     | Risultato numerico di un esperimento per uno split e una metrica specifica |

## File di ingresso

Il punto di ingresso dell'applicazione è `app/main.py`. Questo file:

1. definisce il **lifespan** dell'applicazione (startup/shutdown)
2. connette l'applicazione a MongoDB tramite Motor
3. inizializza Beanie con tutti i Document registrati in `DOCUMENT_MODELS`
4. crea il superutente iniziale se non esiste
5. configura il middleware CORS
6. registra il router principale (`api_router`) con prefisso `/api/v1`

