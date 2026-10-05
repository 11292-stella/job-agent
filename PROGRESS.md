# PROGRESS – Job Application Agent

> Agente AI **locale** che mi aiuta a candidarmi: legge un'offerta o la pagina "Lavora con noi" di un'azienda, valuta quanto il mio profilo è adatto, scrive la mail o il testo per il modulo **su misura**, e prepara tutto (bozza Gmail o modulo compilato).
> **L'invio finale lo faccio sempre io.**

Ultimo aggiornamento: 5 ottobre 2026

---

## 1. Perché questo progetto

Da settembre cerco lavoro candidandomi **direttamente alle aziende** (email e moduli sui loro siti): funziona molto meglio delle candidature semplici su Indeed, LinkedIn e Glassdoor.
Il problema è il tempo: per ogni azienda devo
1. trovare la pagina giusta e capire come candidarmi (email o modulo);
2. confrontare l'annuncio con il mio profilo;
3. scrivere un testo su misura;
4. compilare il modulo o preparare la mail con il CV allegato;
5. segnarmi a chi ho già scritto, per non ripetermi.

L'obiettivo è **automatizzare i punti 1-5**, tenendo per me solo il controllo finale.
È anche un progetto da portfolio: **agente AI + automazione + test**.

---

## 2. Decisioni prese

| Tema | Decisione | Motivo |
|---|---|---|
| Modello AI | **Ollama in locale** | gratis, nessuna API key, i dati restano sul mio PC |
| Come parla con l'AI | **API HTTP di Ollama** (libreria `ollama` per Python) | niente automazione della chat web: è fragile e non permessa |
| Output dell'AI | **JSON strutturato** (con uno schema) | il programma lo legge senza interpretare testo libero |
| Deploy | **Nessuno**: gira in locale | è un progetto da portfolio, basta il codice + video demo |
| Invio mail | Solo **bozze in Gmail** (Gmail API) | l'invio automatico sembra spam e rischia di bloccare l'account |
| Moduli web | **Playwright** compila i campi e **si ferma prima di "Invia"** | controllo umano; i captcha non si aggirano |
| LinkedIn | **Niente scraping** | vietato dalle condizioni d'uso |
| Memoria | **Database** con le aziende già contattate | evita doppioni (es. Zupit!) |
| Approccio | **Human-in-the-loop**: l'agente prepara, io approvo | qualità > quantità |

---

## 3. Architettura

```
┌──────────────────────────┐
│ [1] ORCHESTRATORE        │  Python: prende la prossima azienda dal DB
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ [2] CERVELLO AI (Ollama) │  input: testo annuncio/pagina + profilo + regole
│                          │  output: JSON { punteggio, canale, testo, ... }
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ [3] ESECUTORE            │  email → bozza Gmail
│                          │  form  → Playwright compila e SI FERMA
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│ [4] TRACKER              │  DB + (più avanti) dashboard Django
│                          │  stato: trovata → valutata → pronta → inviata → risposta
└──────────────────────────┘
        ↺ ricomincia con l'azienda successiva
```

### Esempio di output del cervello AI

```json
{
  "azienda": "BSDsoftware",
  "posizione": "Python Developer",
  "punteggio": 78,
  "punti_forti": ["Python con Playwright e pytest", "Django", "Docker", "React"],
  "cosa_manca": ["FastAPI"],
  "canale": "form",
  "oggetto_email": null,
  "testo": "Buongiorno, vi scrivo per la posizione di Python Developer...",
  "note_per_me": "Smart working completo possibile. Il modulo chiede 'profilo di interesse'."
}
```

### Esempio di chiamata a Ollama (anteprima)

```python
import ollama

risposta = ollama.chat(
    model="qwen2.5:7b",
    messages=[
        {"role": "system", "content": "Sei un assistente che valuta offerte di lavoro..."},
        {"role": "user", "content": f"PROFILO:\n{profilo}\n\nANNUNCIO:\n{annuncio}"},
    ],
    format=SchemaValutazione.model_json_schema(),  # forza l'output in JSON valido
)
valutazione = SchemaValutazione.model_validate_json(risposta.message.content)
```

---

## 4. Stack

| Parte | Tecnologia | La conosco già? |
|---|---|---|
| Linguaggio | Python 3 | ✅ |
| Modello AI | Ollama + modello `qwen2.5:7b` (o `llama3.1:8b`) | 🆕 da imparare |
| Validazione JSON | Pydantic | 🆕 semplice |
| Lettura pagine web | requests + BeautifulSoup | ✅ (Job Aggregator) |
| Moduli web | Playwright (Python) | ✅ (Sellogic) |
| Bozze email | Gmail API | ✅ (Job Aggregator) |
| Database | SQLite all'inizio, poi PostgreSQL | ✅ |
| Dashboard | Django (fase 5) | ✅ |
| Test | pytest | ✅ |
| CI | GitHub Actions | ✅ |

> Nota hardware: un modello da 7-8 miliardi di parametri richiede circa **8 GB di RAM libera**. Se il PC fatica, si può usare un modello più piccolo (es. `qwen2.5:3b`).

---

## 5. Struttura delle cartelle (prevista)

```
job-agent/
├── PROGRESS.md
├── README.md
├── requirements.txt
├── .env.example
├── data/
│   ├── profilo.md          # il mio profilo in testo semplice (dal CV)
│   └── regole_stile.md     # come voglio che scriva: tono umile, niente competenze inventate...
├── agent/
│   ├── __init__.py
│   ├── schemas.py          # modelli Pydantic dell'output AI
│   ├── brain.py            # [2] chiamate a Ollama
│   ├── fetcher.py          # scarica e pulisce il testo di una pagina
│   ├── gmail_drafts.py     # [3] crea bozze Gmail
│   ├── form_filler.py      # [3] Playwright: compila e si ferma
│   ├── db.py               # [4] tracker
│   └── main.py             # [1] orchestratore
└── tests/
    ├── test_schemas.py
    ├── test_brain.py
    └── fixtures/           # annunci di esempio salvati in locale
```

---

## 6. Piano di lavoro (un pezzo alla volta)

### Fase 0 – Preparazione
- [ ] Creare la cartella `job-agent` e il repo Git
- [ ] Installare Ollama e scaricare il modello
- [ ] Primo test: far rispondere il modello da terminale
- [ ] Ambiente virtuale Python + `requirements.txt`

### Fase 1 – Il cervello (cuore del progetto)
- [ ] `data/profilo.md` e `data/regole_stile.md`
- [ ] `agent/schemas.py`: schema Pydantic della valutazione
- [ ] `agent/brain.py`: funzione `valuta(annuncio) -> Valutazione`
- [ ] Prova a mano con 3 annunci veri (es. BSDsoftware, Vanguard, CGM)
- [ ] **Già utile così**: incollo un annuncio e ottengo punteggio + testo

### Fase 2 – Lettura delle pagine
- [ ] `agent/fetcher.py`: da URL a testo pulito
- [ ] Riconoscere email di candidatura e presenza di un modulo

### Fase 3 – Esecutore
- [ ] `agent/gmail_drafts.py`: bozza Gmail con CV allegato
- [ ] `agent/form_filler.py`: Playwright compila e si ferma (`page.pause()`)

### Fase 4 – Tracker e ciclo
- [ ] `agent/db.py`: tabella aziende + stato + data
- [ ] `agent/main.py`: ciclo sulle aziende, salta quelle già contattate

### Fase 5 – Dashboard (facoltativa)
- [ ] Django: lista aziende, punteggi, stati, link alla bozza

### Fase 6 – Qualità (la mia firma da QA)
- [ ] Test pytest su schemi e parsing
- [ ] Test sull'AI con annunci salvati: il JSON è valido? Il testo **non inventa competenze** che non ho? Rispetta le regole di stile?
- [ ] GitHub Actions per i test che non richiedono Ollama
- [ ] README con video demo per il portfolio

---

## 7. Regole che l'agente deve rispettare

1. **Mai inventare** competenze, anni di esperienza o titoli di studio.
2. Se mi manca qualcosa di richiesto, dirlo nel campo `cosa_manca`, non nasconderlo.
3. Tono **semplice e umile**, niente frasi arroganti.
4. Per il trasferimento basta "disponibile al trasferimento".
5. Mai inviare: solo bozze e moduli compilati fermi prima dell'invio.
6. Non contattare due volte la stessa azienda senza chiedermelo.

---

## 8. Diario

| Data | Cosa ho fatto | Problemi / note |
|---|---|---|
| 05/10/2026 | Idea, decisioni e architettura (questo file) | — |
