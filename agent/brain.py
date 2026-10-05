"""Il "cervello" dell'agente.

Divisione dei compiti:
- Python  → confronto competenze, punteggio, canale, email, oggetto (preciso)
- AI      → scrive SOLO il testo della candidatura (quello che sa fare bene)
- Python  → controllo anti-allucinazione sul testo scritto dall'AI
"""
import re
import sys
import time
from pathlib import Path

import ollama

from agent.competenze import confronta, inventate
from agent.schemas import Valutazione

MODELLO = "qwen2.5:3b"
MAX_TENTATIVI = 3
CARTELLA_DATA = Path(__file__).resolve().parent.parent / "data"

ISTRUZIONI_SCRITTURA = """Scrivi in ITALIANO il corpo di un'email di candidatura per Stella Marucelli.
Regole obbligatorie:
- Scrivi SOLO in italiano, in prima persona al femminile.
- Cita SOLO le tecnologie ed esperienze dell'elenco "ESPERIENZE DA CITARE". Non nominare nessun'altra tecnologia.
- Segui le REGOLE DI STILE.
- Non scrivere l'oggetto, non scrivere istruzioni per candidarsi, non aggiungere frasi dopo la firma.
- Rispondi solo con il testo dell'email, da "Buongiorno," fino alla firma."""


def carica_file(nome: str) -> str:
    return (CARTELLA_DATA / nome).read_text(encoding="utf-8-sig")


def leggi_campo(annuncio: str, campo: str) -> str | None:
    """Legge una riga tipo 'Azienda: BSDsoftware' in cima al file dell'annuncio."""
    trovato = re.search(rf"^{campo}:\s*(.+)$", annuncio, re.MULTILINE | re.IGNORECASE)
    return trovato.group(1).strip() if trovato else None


def trova_email(annuncio: str) -> str | None:
    trovata = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", annuncio)
    return trovata.group(0) if trovata else None


def scrivi_testo(annuncio: str, esperienze: str, modello: str) -> str:
    """Chiede all'AI SOLO il testo dell'email (testo libero, niente JSON)."""
    regole = carica_file("regole_stile.md")
    messaggio = (
        f"=== ESPERIENZE DA CITARE ===\n{esperienze}\n\n"
        f"=== REGOLE DI STILE ===\n{regole}\n\n"
        f"=== ANNUNCIO (per capire posizione e azienda) ===\n{annuncio}"
    )
    risposta = ollama.chat(
        model=modello,
        messages=[
            {"role": "system", "content": ISTRUZIONI_SCRITTURA},
            {"role": "user", "content": messaggio},
        ],
        options={"temperature": 0.4, "num_ctx": 6144, "num_predict": 600},
    )
    return risposta.message.content.strip()


def valuta(annuncio: str, modello: str = MODELLO) -> tuple[Valutazione, list[str]]:
    """Restituisce la Valutazione e la lista degli avvisi."""
    avvisi: list[str] = []

    # 1) Python: confronto preciso delle competenze
    forti, manca = confronta(annuncio)
    totale = len(forti) + len(manca)
    punteggio = round(100 * len(forti) / totale) if totale else 50

    # 2) Python: dati dell'annuncio
    azienda = leggi_campo(annuncio, "Azienda") or "Azienda sconosciuta"
    posizione = leggi_campo(annuncio, "Posizione") or "Candidatura spontanea"
    email = trova_email(annuncio)
    canale = "email" if email and "modulo" not in annuncio.lower() else ("form" if "modulo" in annuncio.lower() else "sconosciuto")
    if posizione == "Candidatura spontanea":
        oggetto = "Candidatura spontanea – QA Automation Engineer / Full Stack Developer – Stella Marucelli"
    else:
        oggetto = f"Candidatura – {posizione} – Stella Marucelli"

    # 3) AI: scrive il testo, usando solo le esperienze vere
    esperienze = "\n".join(f"- {c.nome}: {c.dove}" for c in forti)
    testo = ""
    for tentativo in range(1, MAX_TENTATIVI + 1):
        testo = scrivi_testo(annuncio, esperienze, modello)
        # 4) Python: controllo anti-allucinazione
        sbagliate = inventate(testo)
        if not sbagliate:
            break
        avvisi.append(f"Tentativo {tentativo}: il testo citava tecnologie che non ho → {', '.join(sbagliate)}")
    else:
        avvisi.append("⚠ Dopo 3 tentativi il testo contiene ancora tecnologie che non ho: correggilo a mano!")

    valutazione = Valutazione(
        azienda=azienda,
        posizione=posizione,
        punteggio=punteggio,
        punti_forti=[f"{c.nome} ({c.dove})" for c in forti],
        cosa_manca=[c.nome for c in manca],
        canale=canale,
        email_candidatura=email,
        oggetto_email=oggetto,
        testo=testo,
        note_per_me=f"Mi mancano: {', '.join(c.nome for c in manca)}" if manca else "Nessun requisito mancante rilevato.",
    )
    return valutazione, avvisi


if __name__ == "__main__":
    # Uso: python -m agent.brain annunci\file.txt [modello]
    if len(sys.argv) not in (2, 3):
        print("Uso: python -m agent.brain <file_annuncio.txt> [modello]")
        sys.exit(1)

    testo_annuncio = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    modello = sys.argv[2] if len(sys.argv) == 3 else MODELLO

    inizio = time.time()
    v, avvisi = valuta(testo_annuncio, modello=modello)

    print(f"🏢 {v.azienda} – {v.posizione}")
    print(f"📊 Punteggio: {v.punteggio}/100   📨 Canale: {v.canale}   ✉ {v.email_candidatura or '-'}")
    print("\n✅ Punti forti:\n   - " + "\n   - ".join(v.punti_forti))
    print("\n❌ Cosa manca:\n   - " + ("\n   - ".join(v.cosa_manca) or "niente"))
    print(f"\n📝 Oggetto: {v.oggetto_email}\n")
    print(v.testo)
    for a in avvisi:
        print(f"\n{a}")
    print(f"\n⏱  Tempo: {time.time() - inizio:.1f} secondi")