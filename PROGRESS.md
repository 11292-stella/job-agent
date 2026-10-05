# PROGRESS – Job Application Agent

> Agente AI **locale** che mi aiuta a candidarmi: legge un'offerta o la pagina "Lavora con noi" di un'azienda, valuta quanto il mio profilo è adatto, prepara la mail o il testo per il modulo **su misura**, e prepara tutto (bozza Gmail o modulo compilato).
> **L'invio finale lo faccio sempre io.**

Repository: https://github.com/11292-stella/job-agent
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
| Modello AI | **Ollama in locale** con **`qwen2.5:3b`** | gratis, nessuna API key, i dati restano sul mio PC; il 3b sta tutto nella GPU (RTX 2050, 4 GB) |
| Modello 7b | **Scartato** | non entra nei 4 GB della GPU → troppo lento |
| Come parla con l'AI | **API di Ollama** (libreria `ollama` per Python) | niente automazione della chat web: fragile e non permessa |
| Divisione dei compiti | **Python** fa tutto ciò che deve essere esatto, **l'AI** solo scelta + 1 frase | il 3b inventava competenze, cambiava lingua e scriveva frasi arroganti |
| Frasi sulla mia esperienza | **Scritte da me** in `agent/frasi.py` | vere e umili per costruzione; l'AI non le può modificare |
| Output dell'AI | **JSON con schema** (Pydantic), con `Literal` per le scelte chiuse | l'AI può scegliere solo tra le mie competenze reali |
| Controlli di qualità | `agent/controlli.py` + **ciclo di correzione** (max 3 tentativi) | se l'AI sbaglia le rimando gli errori; se non si corregge → frase di riserva |
| Deploy | **Nessuno**: gira in locale | è un progetto da portfolio: basta codice + video demo |
| Invio mail | Solo **bozze in Gmail** (Gmail API) | l'invio automatico sembra spam e rischia di bloccare l'account |
| Moduli web | **Playwright** compila e **si ferma prima di "Invia"** | controllo umano; i captcha non si aggirano |
| LinkedIn | **Niente scraping** | vietato dalle condizioni d'uso |
| Memoria | **Database** con le aziende già contattate | evita doppioni (es. Zupit!) |
| Approccio | **Human-in-the-loop**: l'agente prepara, io approvo | qualità > quantità |

---

## 3. Architettura (attuale)

```
URL della pagina (+ nome dell'offerta, se la pagina ne ha più di una)
   │
   ▼
[Python] fetcher.py    → scarica, trova email e modulo, prende solo l'offerta scelta,
                         segue la pagina di dettaglio, pulisce il testo
   │
   ▼
ANNUNCIO (file .txt in annunci/ con righe "Azienda:", "Posizione:", "Come candidarsi:" in cima)
   │
   ▼
[Python] competenze.py → punti forti / cosa manca / punteggio      (deterministico, zero allucinazioni)
[Python] brain.py      → azienda, posizione, canale, email, oggetto
   │
   ▼
[AI qwen2.5:3b]  1) SCEGLIE le 3 competenze più rilevanti (solo da lista chiusa)
                 2) scrive UNA frase sull'azienda
   │
   ▼
[Python] controlli.py  → frasi vietate, tecnologie inventate, lunghezza
         ↺ se ci sono problemi: rimando gli errori all'AI (max 3 tentativi), poi frase di riserva
   │
   ▼
[Python] scheletro della mail + MIE frasi (frasi.py) → mail finale
   │
   ▼
(prossime fasi) bozza Gmail / modulo Playwright → tracker
```

### Esempio di risultato reale (annuncio Python Developer – BSDsoftware, 11,9 s)

```
Buongiorno,

vi scrivo per candidarmi alla posizione di Python Developer. Ho usato Python soprattutto per il testing:
in Sellogic, con Playwright e pytest, ho scritto circa 70 test E2E e 226 test API. Uso Docker e Docker
Compose nelle pipeline di test dei miei progetti. In Sellogic ho configurato le pipeline di test su GitLab CI.

Mi interessa lavorare su progetti in ambito web, AI e sviluppo software custom, e il fatto che siate
aperti allo smart working.

Sono disponibile da subito e disponibile al trasferimento. Nel mio portfolio trovate progetti, video e
report dei test: https://portfolio-loading.vercel.app/
Allego il mio CV.
...
🔁 Tentativo 1: Frase vietata: "innovativ"   ← bloccata e corretta al tentativo 2
```

### Schema chiuso per la scelta delle competenze

```python
def schema_scelta(nomi: list[str]) -> type[BaseModel]:
    NomeCompetenza = Literal[tuple(nomi)]   # es. Literal["Python", "Django", "Docker"]
    return create_model(
        "Scelta",
        competenze=(list[NomeCompetenza], Field(min_length=1, max_length=3)),
        frase_azienda=(str, Field(description="Una frase su cosa interessa dell'azienda")),
    )
```

---

## 4. Stack

| Parte | Tecnologia | La conoscevo già? |
|---|---|---|
| Linguaggio | Python 3.14 | ✅ |
| Modello AI | Ollama + **qwen2.5:3b** | 🆕 imparato in questo progetto |
| Validazione JSON | Pydantic (`BaseModel`, `Field`, `create_model`, `Literal`) | 🆕 imparato in questo progetto |
| Riconoscimento competenze | `re` (regex a parola intera) + `dataclass` | ✅ |
| Lettura pagine web | requests + BeautifulSoup (`urljoin`, `find_all_next`, `dataclass`) | ✅ (Job Aggregator) |
| Moduli web | Playwright (Python) | ✅ (Sellogic) |
| Bozze email | Gmail API | ✅ (Job Aggregator) |
| Database | SQLite all'inizio, poi PostgreSQL | ✅ |
| Dashboard | Django (fase 5) | ✅ |
| Test | pytest | ✅ |
| CI | GitHub Actions | ✅ |

---

## 5. Struttura delle cartelle

```
job-agent/
├── PROGRESS.md
├── requirements.txt         # ollama, pydantic, requests, beautifulsoup4 (salvato in UTF-8!)
├── .gitignore
├── data/
│   ├── profilo.md           # il mio profilo, con la sezione "Cosa NON ho"
│   └── regole_stile.md      # tono umile, niente frasi fatte, struttura della mail
├── annunci/
│   ├── bsd_python.txt       # annuncio copiato a mano (prima prova)
│   └── bsdsoftware_python.txt  # creato dal fetcher
├── agent/
│   ├── __init__.py
│   ├── schemas.py           # Valutazione (output finale)
│   ├── competenze.py        # dizionario competenze (le ho / non le ho) + regex
│   ├── frasi.py             # le MIE frasi, una per competenza
│   ├── controlli.py         # frasi vietate, tecnologie inventate, lunghezza
│   ├── fetcher.py           # da URL a file annuncio (email, modulo, offerta, dettaglio)
│   └── brain.py             # orchestrazione: Python + AI + controlli + scheletro mail
└── tests/                   # (fase 6)
```

Comandi:
```powershell
# 1. Dalla pagina al file annuncio (il nome dell'offerta è facoltativo)
python -m agent.fetcher https://www.bsdsoftware.it/LavoraConNoi "Python"

# 2. Dal file annuncio alla mail
python -m agent.brain annunci\bsdsoftware_python.txt
```
Se il nome dell'offerta non esiste, il fetcher elenca i titoli trovati nella pagina.

---

## 6. Piano di lavoro

### Fase 0 – Preparazione ✅
- [x] Cartella `job-agent` + repo Git + GitHub
- [x] Ollama installato, modello `qwen2.5:3b` scaricato e provato
- [x] Ambiente virtuale Python + `requirements.txt` + `.gitignore`

### Fase 1 – Il cervello ✅
- [x] `data/profilo.md` e `data/regole_stile.md`
- [x] `agent/schemas.py`
- [x] `agent/competenze.py`: confronto deterministico annuncio ↔ profilo
- [x] `agent/controlli.py`: controlli di qualità sul testo
- [x] `agent/frasi.py`: le mie frasi
- [x] `agent/brain.py`: l'AI sceglie 3 competenze + scrive 1 frase, ciclo di correzione, scheletro mail
- [x] Prova con un annuncio vero (BSDsoftware) → mail vera e umile in ~12 s

### Fase 2 – Lettura delle pagine ✅
- [x] `agent/fetcher.py`: da URL a testo pulito
- [x] Riconoscere email di candidatura e presenza di un modulo (anche fuori da `<form>` o in iframe)
- [x] Ricavare azienda e posizione dalla pagina (og:site_name, titolo dell'offerta)
- [x] Pagine con più offerte: argomento "nome offerta" + link alla pagina di dettaglio seguito da solo
- [x] Pulizia del titolo: "Python Developer (sia Remote che On-Site):" → "Python Developer"
- [x] Prova completa fetcher → brain su BSDsoftware: punteggio 65, mancanze vere (FastAPI, Flask, Cloud, AI), mail umile

### Fase 3 – Esecutore
- [ ] `agent/gmail_drafts.py`: bozza Gmail con CV allegato
- [ ] `agent/form_filler.py`: Playwright compila e si ferma (`page.pause()`)

### Fase 4 – Tracker e ciclo
- [ ] `agent/db.py`: tabella aziende + stato + data
- [ ] `agent/main.py`: ciclo sulle aziende, salta quelle già contattate

### Fase 5 – Dashboard (facoltativa)
- [ ] Django: lista aziende, punteggi, stati, link alla bozza

### Fase 6 – Qualità (la mia firma da QA)
- [ ] pytest su `competenze.py` (es. "Java" non deve trovare "JavaScript")
- [ ] pytest su `controlli.py` (casi negativi: frasi vietate, tecnologie inventate)
- [ ] Test sull'AI con annunci salvati: JSON valido, scelte solo dalla lista, nessuna frase vietata
- [ ] GitHub Actions per i test che non richiedono Ollama
- [ ] README con video demo per il portfolio

---

## 7. Regole che l'agente deve rispettare

1. **Mai inventare** competenze, anni di esperienza o titoli di studio.
2. Se mi manca qualcosa di richiesto, segnarlo in `cosa_manca`, non nasconderlo.
3. Tono **semplice e umile**: niente "esperta", "padronanza", "valore aggiunto", "innovativo"...
4. Per il trasferimento basta "disponibile al trasferimento".
5. Mai inviare: solo bozze e moduli compilati fermi prima dell'invio.
6. Non contattare due volte la stessa azienda senza chiedermelo.

---

## 8. Diario

| Data | Cosa ho fatto | Problemi / note |
|---|---|---|
| 05/10/2026 | Idea, decisioni e architettura | — |
| 05/10/2026 | Ollama + qwen2.5:3b, ambiente Python | `pip freeze > file` in PowerShell salva in UTF-16 → usare `Out-File -Encoding utf8` |
| 05/10/2026 | Prima versione di brain.py (tutto fatto dall'AI) | Si bloccava all'infinito → aggiunto `num_predict`; poi inventava competenze, scriveva in spagnolo, frasi arroganti |
| 05/10/2026 | Prova con qwen2.5:7b | Troppo lento (non entra nella GPU) → scartato |
| 05/10/2026 | `competenze.py` (confronto deterministico) | Python fa il confronto annuncio/profilo: zero allucinazioni |
| 05/10/2026 | `controlli.py` | Falso negativo: "sono conosciuta" non trovava "sono anche conosciuta" → controllo su "conosciuta per" |
| 05/10/2026 | Scheletro mail + ciclo di correzione + esempio few-shot | Il 3b continuava a scrivere "esperta" anche dopo 3 correzioni → limite del modello |
| 05/10/2026 | `frasi.py` + l'AI sceglie solo da lista chiusa | Mail vera e umile in ~12 s; il ciclo di correzione ha bloccato "innovativo" al 1° tentativo |
| 05/10/2026 | `fetcher.py` (prima versione) | "Modulo: no" anche se il modulo c'era: i campi non erano dentro `<form>` → controllo su tutta la pagina, iframe e frasi tipiche |
| 05/10/2026 | `fetcher.py` e pagine con più offerte | La pagina "Lavora con noi" aveva 7 offerte → punteggio sporcato da Java/C#/PHP e l'AI ha scelto Java per un annuncio Python. Risolto con la scelta dell'offerta (titoli h2-h4) |
| 05/10/2026 | `fetcher.py` e pagina di dettaglio | Con il solo riassunto (157 caratteri) → **falso 100/100**. Ora il fetcher segue il link al dettaglio: punteggio 65 e mancanze vere. Test negativo con offerta inesistente → elenca i titoli |

---

## 9. Migliorie future

- [ ] Priorità tra le competenze (es. per un annuncio Python, Django prima di Docker)
- [ ] Evitare frasi che ripetono lo stesso dato (es. "226 test API" in Python e Playwright)
- [ ] Fetcher: escludere dalla pagina di dettaglio l'elenco delle "altre posizioni aperte" (oggi aggiunge ASP.NET Core, Angular, PHP al confronto)
- [ ] Fetcher: pagine generate da JavaScript → leggerle con Playwright
- [ ] Un solo comando URL → mail (lo farà `main.py` nella fase 4)
- [ ] Aggiornare profilo, CV e portfolio con questo progetto quando sarà finito

---

## 10. Cosa racconterò ai colloqui

- Ho usato un modello AI **piccolo e locale** e ne ho scoperto i limiti facendo QA sui suoi output.
- Ho **spostato la logica critica in Python** (confronto competenze) e lasciato all'AI solo i compiti in cui è affidabile.
- Ho costruito **controlli automatici** e un **ciclo di correzione**, e testandoli ho trovato un falso negativo.
- Nel fetcher ho trovato un **falso 100/100**: il programma leggeva solo il riassunto dell'offerta. Un numero "troppo bello" è un segnale da indagare, non un successo.
- Risultato: mail **vere, umili e verificabili**, l'invio resta sempre una decisione umana.
