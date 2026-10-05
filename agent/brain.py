"""Il "cervello" dell'agente.

- Python  → competenze, punteggio, canale, email, oggetto e SCHELETRO della mail
- AI      → scrive SOLO due paragrafi (esperienza + perché l'azienda)
- Python  → controlla i paragrafi; se ci sono problemi li rimanda all'AI da correggere
"""
import re
import sys
import time
from pathlib import Path

import ollama

from agent.competenze import confronta
from agent.controlli import FRASI_VIETATE, controlla
from agent.schemas import Paragrafi, Valutazione

MODELLO = "qwen2.5:3b"
MAX_TENTATIVI = 3
PORTFOLIO = "https://portfolio-loading.vercel.app/"

SCHELETRO = """Buongiorno,

{apertura} {esperienza}

{azienda}

Sono disponibile da subito e disponibile al trasferimento. Nel mio portfolio trovate progetti, video e report dei test: {portfolio}
Allego il mio CV.

Cordiali saluti,
Stella Marucelli
+39 378 066 2596
stella.marucelli@gmail.com"""

ISTRUZIONI = f"""Scrivi in ITALIANO due paragrafi per l'email di candidatura di Stella (prima persona, al femminile).

- "esperienza": 2-4 frasi. Collega l'annuncio alle esperienze dell'elenco ESPERIENZE.
  Cita SOLO quelle esperienze, con i dettagli esattamente come sono scritti. Non aggiungere numeri, progetti o tecnologie.
- "azienda": 1-2 frasi su cosa ti interessa di questa azienda, usando UN dettaglio vero preso dall'annuncio.

ESEMPIO di stile (per un'altra azienda: copia il TONO, non il contenuto):
- esperienza: "In Sellogic ho lavorato con GitLab CI e Jira, prima come sviluppatrice e poi come QA Automation Engineer, e con Playwright e pytest ho scritto 226 test API. Ho una formazione Java con Spring Boot e JPA, e ho sviluppato da sola un'applicazione con API REST e frontend Angular."
- azienda: "Mi interessa lavorare sulla manutenzione e sull'evoluzione di applicazioni web, e il fatto che la posizione sia completamente da remoto."

Nota: in Sellogic i test li SCRIVEVO (QA), non sviluppavo le applicazioni. Non dire mai "esperta".

Non scrivere saluti, disponibilità, link, firma.
Tono semplice, concreto e umile. Non usare mai queste espressioni: {", ".join(FRASI_VIETATE)}."""


def leggi_campo(annuncio: str, campo: str) -> str | None:
    """Legge una riga tipo 'Azienda: BSDsoftware' in cima al file dell'annuncio."""
    trovato = re.search(rf"^{campo}:\s*(.+)$", annuncio, re.MULTILINE | re.IGNORECASE)
    return trovato.group(1).strip() if trovato else None


def trova_email(annuncio: str) -> str | None:
    trovata = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", annuncio)
    return trovata.group(0) if trovata else None


def scrivi_paragrafi(annuncio: str, esperienze: str, modello: str) -> tuple[Paragrafi, list[str]]:
    """Chiede all'AI i due paragrafi e li fa correggere finché passano i controlli."""
    avvisi: list[str] = []
    messaggi = [
        {"role": "system", "content": ISTRUZIONI},
        {"role": "user", "content": f"=== ESPERIENZE ===\n{esperienze}\n\n=== ANNUNCIO ===\n{annuncio}"},
    ]
    paragrafi = Paragrafi(esperienza="", azienda="")

    for tentativo in range(1, MAX_TENTATIVI + 1):
        risposta = ollama.chat(
            model=modello,
            messages=messaggi,
            format=Paragrafi.model_json_schema(),
            options={"temperature": 0.4, "num_ctx": 4096, "num_predict": 500},
        )
        contenuto = risposta.message.content
        paragrafi = Paragrafi.model_validate_json(contenuto)

        problemi = (
            controlla(paragrafi.esperienza, min_parole=25, max_parole=110)
            + controlla(paragrafi.azienda, min_parole=10, max_parole=70)
        )
        if not problemi:
            return paragrafi, avvisi

        avvisi.append(f"Tentativo {tentativo}: " + " | ".join(problemi))
        # Ciclo di correzione: rimandiamo all'AI la sua risposta + gli errori trovati
        messaggi.append({"role": "assistant", "content": contenuto})
        messaggi.append({
            "role": "user",
            "content": "Il testo ha questi problemi:\n- " + "\n- ".join(problemi)
                       + "\nRiscrivi i due paragrafi correggendoli.",
        })

    avvisi.append("⚠ Dopo 3 tentativi ci sono ancora problemi: controlla e correggi a mano!")
    return paragrafi, avvisi


def valuta(annuncio: str, modello: str = MODELLO) -> tuple[Valutazione, list[str]]:
    # 1) Python: competenze e punteggio
    forti, manca = confronta(annuncio)
    totale = len(forti) + len(manca)
    punteggio = round(100 * len(forti) / totale) if totale else 50

    # 2) Python: dati dell'annuncio
    azienda = leggi_campo(annuncio, "Azienda") or "Azienda sconosciuta"
    posizione = leggi_campo(annuncio, "Posizione") or "Candidatura spontanea"
    email = trova_email(annuncio)
    if "modulo" in annuncio.lower():
        canale = "form"
    elif email:
        canale = "email"
    else:
        canale = "sconosciuto"

    if posizione == "Candidatura spontanea":
        oggetto = "Candidatura spontanea – QA Automation Engineer / Full Stack Developer – Stella Marucelli"
        apertura = "vi scrivo per proporvi la mia candidatura spontanea come QA Automation Engineer o sviluppatrice full stack."
    else:
        oggetto = f"Candidatura – {posizione} – Stella Marucelli"
        apertura = f"vi scrivo per candidarmi alla posizione di {posizione}."

    # 3) AI: solo i due paragrafi (con ciclo di correzione)
    esperienze = "\n".join(f"- {c.nome}: {c.dove}" for c in forti)
    paragrafi, avvisi = scrivi_paragrafi(annuncio, esperienze, modello)

    # 4) Python: monta lo scheletro
    testo = SCHELETRO.format(
        apertura=apertura,
        esperienza=paragrafi.esperienza.strip(),
        azienda=paragrafi.azienda.strip(),
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
        print(f"\n🔁 {a}")
    print(f"\n⏱  Tempo: {time.time() - inizio:.1f} secondi")