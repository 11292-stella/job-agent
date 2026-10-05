"""Il "cervello" dell'agente: manda annuncio + profilo a Ollama e riceve una Valutazione."""
import sys
import time
from pathlib import Path

import ollama

from agent.schemas import Valutazione

MODELLO = "qwen2.5:3b"
CARTELLA_DATA = Path(__file__).resolve().parent.parent / "data"

ISTRUZIONI = """Sei l'assistente di Stella, che cerca lavoro come QA Automation Engineer o sviluppatrice full stack.
Ricevi il suo PROFILO, le sue REGOLE DI STILE e il testo di un ANNUNCIO o della pagina "Lavora con noi" di un'azienda.

Devi:
1. Confrontare l'annuncio con il profilo e dare un punteggio onesto da 0 a 100.
2. Elencare i punti forti (requisiti che lei ha davvero) e cosa manca (requisiti che non ha).
3. Capire come candidarsi: email (se nel testo c'è un indirizzo) oppure modulo sul sito.
4. Scrivere il testo della candidatura in italiano, seguendo ESATTAMENTE le regole di stile.

Regole fondamentali:
- Usa SOLO le informazioni del profilo. Non inventare mai competenze, anni di esperienza o titoli di studio.
- Se un requisito è nella sezione "Cosa NON ho" del profilo, mettilo in cosa_manca.
- Rispondi solo con il JSON richiesto, senza spazi o righe vuote inutili."""


def carica_file(nome: str) -> str:
    """Legge un file della cartella data/ (utf-8-sig ignora l'eventuale BOM di Windows)."""
    return (CARTELLA_DATA / nome).read_text(encoding="utf-8-sig")


def valuta(annuncio: str, modello: str = MODELLO, mostra_progresso: bool = False) -> Valutazione:
    """Valuta un annuncio rispetto al profilo e restituisce una Valutazione validata."""
    profilo = carica_file("profilo.md")
    regole = carica_file("regole_stile.md")

    messaggio = (
        f"=== PROFILO ===\n{profilo}\n\n"
        f"=== REGOLE DI STILE ===\n{regole}\n\n"
        f"=== ANNUNCIO ===\n{annuncio}"
    )

    flusso = ollama.chat(
        model=modello,
        messages=[
            {"role": "system", "content": ISTRUZIONI},
            {"role": "user", "content": messaggio},
        ],
        format=Valutazione.model_json_schema(),  # obbliga il modello a seguire lo schema
        options={
            "temperature": 0.2,   # bassa = risposte più precise e meno "creative"
            "num_ctx": 6144,      # memoria di contesto: profilo + regole + annuncio
            "num_predict": 1200,  # LIMITE di token in uscita: evita che il modello si incastri
        },
        stream=True,  # riceviamo la risposta a pezzi, man mano che viene scritta
    )

    testo_json = ""
    for pezzo in flusso:
        testo_json += pezzo.message.content
        if mostra_progresso:
            print(f"\r✍  Caratteri ricevuti: {len(testo_json)}", end="", flush=True)
    if mostra_progresso:
        print()  # va a capo dopo il contatore

    # Pydantic controlla che il JSON rispetti lo schema (tipi, campi obbligatori, 0-100...)
    return Valutazione.model_validate_json(testo_json)


if __name__ == "__main__":
    # Uso: python -m agent.brain percorso\annuncio.txt
    if len(sys.argv) != 2:
        print("Uso: python -m agent.brain <file_annuncio.txt>")
        sys.exit(1)

    testo_annuncio = Path(sys.argv[1]).read_text(encoding="utf-8-sig")

    inizio = time.time()
    valutazione = valuta(testo_annuncio, mostra_progresso=True)
    print(valutazione.model_dump_json(indent=2))
    print(f"\n⏱  Tempo: {time.time() - inizio:.1f} secondi")