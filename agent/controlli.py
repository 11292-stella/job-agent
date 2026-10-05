"""Controlli di qualità sul testo scritto dall'AI: la mia parte da QA nel progetto."""
from agent.competenze import inventate

# Frasi arroganti o da brochure che non voglio mai nelle mie candidature
FRASI_VIETATE = [
    "conosciuta per",
    "padronanza",
    "valore aggiunto",
    "sono certa",
    "persona giusta",
    "fare la differenza",
    "innovativ",       # innovativo, innovativa, innovative...
    "appassionat",     # appassionata, appassionato...
    "proattiv",
    "dinamic",
    "al passo con",
    "disponibile al trasferimento",  # la scrive già lo scheletro: l'AI non deve ripeterla
    "disponibile da subito",
    "esperta",
    "elenco",                    # prompt leak: "come nel mio elenco ESPERIENZE"
    "mi rende particolarmente",
    "come candidata",
]


def controlla(testo: str, min_parole: int, max_parole: int) -> list[str]:
    """Restituisce la lista dei problemi trovati. Lista vuota = testo OK."""
    problemi: list[str] = []
    minuscolo = testo.lower()

    # 1) Tecnologie che non ho (dal dizionario di competenze.py)
    sbagliate = inventate(testo)
    if sbagliate:
        problemi.append(f"Cita cose che non ho: {', '.join(sbagliate)}")

    # 2) Frasi vietate
    for frase in FRASI_VIETATE:
        if frase in minuscolo:
            problemi.append(f'Frase vietata: "{frase}"')

    # 3) Lunghezza
    parole = len(testo.split())
    if not min_parole <= parole <= max_parole:
        problemi.append(f"Lunghezza {parole} parole (accettate: {min_parole}-{max_parole})")

    return problemi


if __name__ == "__main__":
    # Prova veloce con una frase "cattiva" presa dall'ultimo output
    esempio = (
        "Sono anche conosciuta per la mia padronanza di React e ho lavorato "
        "in progetti di intelligenza artificiale. Sono disponibile da subito."
    )
    for p in controlla(esempio, min_parole=40, max_parole=110):
        print("❌", p)