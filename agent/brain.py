"""Il "cervello" dell'agente.

- Python → competenze, punteggio, canale, email, oggetto, scheletro della mail
- AI     → 1) SCEGLIE le 3 competenze più rilevanti (solo da una lista chiusa)
           2) scrive UNA frase sull'azienda (controllata, con ciclo di correzione)
- Python → monta il paragrafo con le MIE frasi (agent/frasi.py)
"""
import re
import sys
import time
from pathlib import Path
from typing import Literal

import ollama
from pydantic import BaseModel, Field, create_model

from agent.competenze import confronta
from agent.controlli import FRASI_VIETATE, controlla
from agent.frasi import FRASI
from agent.schemas import Valutazione

MODELLO = "qwen2.5:3b"
MAX_TENTATIVI = 3
PORTFOLIO = "https://portfolio-loading.vercel.app/"
FRASE_AZIENDA_RISERVA = "Mi piacerebbe molto entrare nel vostro team e crescere insieme a voi."

SCHELETRO = """Buongiorno,

{apertura} {esperienza}

{azienda}

Sono disponibile da subito e disponibile al trasferimento. Nel mio portfolio trovate progetti, video e report dei test: {portfolio}
Allego il mio CV.

Cordiali saluti,
Stella Marucelli
+39 378 066 2596
stella.marucelli@gmail.com"""

ISTRUZIONI = f"""Aiuti Stella a preparare una candidatura. Ricevi un ANNUNCIO e la lista delle sue COMPETENZE.

1. "competenze": scegli dalla lista le 3 competenze più importanti per questo annuncio, dalla più importante.
2. "frase_azienda": scrivi in ITALIANO UNA sola frase, in prima persona al femminile, su cosa le interessa di
   questa azienda, usando UN dettaglio concreto preso dall'annuncio (es. la modalità di lavoro, il tipo di progetti).

Esempio di frase_azienda: "Mi interessa lavorare su applicazioni web e gestionali, e il fatto che siate aperti allo smart working."
Tono semplice e umile. Non usare mai: {", ".join(FRASI_VIETATE)}."""


def leggi_campo(annuncio: str, campo: str) -> str | None:
    trovato = re.search(rf"^{campo}:\s*(.+)$", annuncio, re.MULTILINE | re.IGNORECASE)
    return trovato.group(1).strip() if trovato else None


def trova_email(annuncio: str) -> str | None:
    trovata = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", annuncio)
    return trovata.group(0) if trovata else None


def schema_scelta(nomi: list[str]) -> type[BaseModel]:
    """Crea al volo uno schema in cui 'competenze' può contenere SOLO i nomi della lista."""
    NomeCompetenza = Literal[tuple(nomi)]  # es. Literal["Python", "Django", "Docker"]
    return create_model(
        "Scelta",
        competenze=(list[NomeCompetenza], Field(min_length=1, max_length=3)),
        frase_azienda=(str, Field(description="Una frase su cosa interessa dell'azienda")),
    )


def scegli_e_scrivi(annuncio: str, candidate: list[str], modello: str) -> tuple[list[str], str, list[str]]:
    """L'AI sceglie le competenze e scrive la frase sull'azienda. Restituisce (scelte, frase, avvisi)."""
    Scelta = schema_scelta(candidate)
    avvisi: list[str] = []
    messaggi = [
        {"role": "system", "content": ISTRUZIONI},
        {"role": "user", "content": "=== COMPETENZE ===\n- " + "\n- ".join(candidate)
                                    + f"\n\n=== ANNUNCIO ===\n{annuncio}"},
    ]
    scelte = candidate[:3]

    for tentativo in range(1, MAX_TENTATIVI + 1):
        risposta = ollama.chat(
            model=modello,
            messages=messaggi,
            format=Scelta.model_json_schema(),
            options={"temperature": 0.3, "num_ctx": 4096, "num_predict": 300},
        )
        contenuto = risposta.message.content
        risultato = Scelta.model_validate_json(contenuto)
        scelte = list(dict.fromkeys(risultato.competenze))  # toglie eventuali doppioni

        problemi = controlla(risultato.frase_azienda, min_parole=8, max_parole=45)
        if not problemi:
            return scelte, risultato.frase_azienda.strip(), avvisi

        avvisi.append(f"Tentativo {tentativo}: " + " | ".join(problemi))
        messaggi.append({"role": "assistant", "content": contenuto})
        messaggi.append({"role": "user", "content": "La frase_azienda ha questi problemi:\n- "
                         + "\n- ".join(problemi) + "\nRiscrivila correggendoli."})

    avvisi.append("Frase sull'azienda non valida dopo 3 tentativi: uso la frase di riserva.")
    return scelte, FRASE_AZIENDA_RISERVA, avvisi


def componi_paragrafo(scelte: list[str]) -> str:
    """Unisce le MIE frasi: ognuna diventa una frase con la maiuscola e il punto."""
    frasi = [FRASI[nome] for nome in scelte if nome in FRASI]
    return " ".join(f[0].upper() + f[1:] + "." for f in frasi)


def valuta(annuncio: str, modello: str = MODELLO) -> tuple[Valutazione, list[str]]:
    # 1) Python: competenze e punteggio
    forti, manca = confronta(annuncio)
    totale = len(forti) + len(manca)
    punteggio = round(100 * len(forti) / totale) if totale else 50

    # 2) Python: dati dell'annuncio
    azienda = leggi_campo(annuncio, "Azienda") or "Azienda sconosciuta"
    posizione = leggi_campo(annuncio, "Posizione") or "Candidatura spontanea"
    email = trova_email(annuncio)
    canale = "form" if "modulo" in annuncio.lower() else ("email" if email else "sconosciuto")

    if posizione == "Candidatura spontanea":
        oggetto = "Candidatura spontanea – QA Automation Engineer / Full Stack Developer – Stella Marucelli"
        apertura = "vi scrivo per proporvi la mia candidatura spontanea come QA Automation Engineer o sviluppatrice full stack."
    else:
        oggetto = f"Candidatura – {posizione} – Stella Marucelli"
        apertura = f"vi scrivo per candidarmi alla posizione di {posizione}."

    # 3) AI: sceglie solo tra le competenze che HO e per cui ho scritto una frase
    candidate = [c.nome for c in forti if c.nome in FRASI]
    avvisi: list[str] = []
    if len(candidate) > 3:
        scelte, frase_azienda, avvisi = scegli_e_scrivi(annuncio, candidate, modello)
    elif candidate:
        scelte = candidate
        _, frase_azienda, avvisi = scegli_e_scrivi(annuncio, candidate, modello)
    else:
        scelte, frase_azienda = [], FRASE_AZIENDA_RISERVA
        avvisi.append("Nessuna competenza con frase trovata: completa il paragrafo a mano.")

    # 4) Python: monta la mail
    testo = SCHELETRO.format(
        apertura=apertura,
        esperienza=componi_paragrafo(scelte),
        azienda=frase_azienda,
        portfolio=PORTFOLIO,
    )

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
        print(f"\n🔁 {a}")
    print(f"\n⏱  Tempo: {time.time() - inizio:.1f} secondi")