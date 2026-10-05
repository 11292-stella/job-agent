"""Fetcher: da un URL al testo pulito di un annuncio o di una pagina "Lavora con noi"."""

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Comment

# Mi presento come un browser normale, altrimenti alcuni siti rispondono 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}
TIMEOUT = 15  # secondi

# Parti della pagina che non contengono l'annuncio
DA_TOGLIERE = ["script", "style", "noscript", "svg", "iframe",
               "header", "footer", "nav", "aside", "form"]

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)*\.[a-z]{2,}", re.IGNORECASE)
FALSE_EMAIL = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp")  # es. logo@2x.png

TESTO_MINIMO = 300  # sotto questa lunghezza la pagina è probabilmente generata da JavaScript

# Frasi che di solito accompagnano un modulo di candidatura
PAROLE_MODULO = ["carica il cv", "carica il tuo cv", "allega il cv", "allega il tuo cv",
                 "compila il modulo", "compila il form", "upload cv", "upload your cv"]
# Servizi esterni di moduli, spesso caricati dentro un iframe
SERVIZI_MODULO = ["form", "typeform", "jotform", "docs.google.com/forms"]

TITOLI = ["h1", "h2", "h3", "h4"]


@dataclass
class Pagina:
    url: str
    azienda: str
    posizione: str
    email: list[str]
    ha_modulo: bool
    testo: str

    def come_annuncio(self) -> str:
        """Testo nel formato che brain.py sa leggere."""
        canali = []
        if self.ha_modulo:
            canali.append("modulo sul sito")
        if self.email:
            canali.append("email " + ", ".join(self.email))
        intestazione = [
            f"Azienda: {self.azienda}",
            f"Posizione: {self.posizione}",
            f"Pagina: {self.url}",
            "Come candidarsi: " + (" / ".join(canali) if canali else "da verificare"),
        ]
        return "\n".join(intestazione) + "\n\n" + self.testo + "\n"


def scarica(url: str) -> str:
    risposta = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
    risposta.raise_for_status()  # errore se 404, 403, 500...
    # Molti siti italiani non dichiarano la codifica: la faccio indovinare
    if risposta.encoding is None or risposta.encoding.lower() == "iso-8859-1":
        risposta.encoding = risposta.apparent_encoding
    return risposta.text


def trova_email(soup: BeautifulSoup) -> list[str]:
    trovate = [a["href"][7:].split("?")[0] for a in soup.select('a[href^="mailto:"]')]
    trovate += EMAIL_RE.findall(soup.get_text(" "))
    pulite: list[str] = []
    for email in trovate:
        email = email.strip().lower()
        if email and not email.endswith(FALSE_EMAIL) and email not in pulite:
            pulite.append(email)
    return pulite


def ha_modulo(soup: BeautifulSoup) -> bool:
    """C'è un modo per candidarsi dal sito? (campo file, area messaggio, iframe o frasi tipiche)"""
    # 1. Campo per caricare il CV o area messaggio, anche fuori da un <form>
    if soup.find("input", {"type": "file"}) or soup.find("textarea"):
        return True
    # 2. Modulo esterno dentro un iframe
    for iframe in soup.find_all("iframe", src=True):
        if any(servizio in iframe["src"].lower() for servizio in SERVIZI_MODULO):
            return True
    # 3. Frasi tipiche nel testo
    testo = soup.get_text(" ").lower()
    return any(frase in testo for frase in PAROLE_MODULO)


def leggi_meta(soup: BeautifulSoup, proprieta: str) -> str:
    tag = soup.find("meta", property=proprieta)
    return tag["content"].strip() if tag and tag.get("content") else ""


def trova_azienda(soup: BeautifulSoup, url: str) -> str:
    nome = leggi_meta(soup, "og:site_name")
    if nome:
        return nome
    dominio = urlparse(url).netloc.removeprefix("www.")
    return dominio.split(".")[0].capitalize()


def trova_posizione(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return " ".join(h1.get_text().split())
    titolo = leggi_meta(soup, "og:title") or (soup.title.string if soup.title else "")
    return " ".join((titolo or "da verificare").split())


def pulisci_titolo(titolo: str) -> str:
    """'Python Developer (sia Remote che On-Site):' → 'Python Developer'"""
    titolo = re.sub(r"\s*\(.*?\)", "", titolo)   # tolgo le parentesi
    return titolo.strip(" :-–")                  # tolgo due punti e trattini finali


def estrai_testo(soup: BeautifulSoup) -> str:
    for tag in soup(DA_TOGLIERE):
        tag.decompose()  # tolgo menu, script, footer...

    contenitore = soup.find("main") or soup.find("article") or soup.body or soup
    testo = _righe_pulite(contenitore)
    # Se <main> è quasi vuoto, riprovo con tutto il body
    if len(testo) < TESTO_MINIMO and soup.body and contenitore is not soup.body:
        testo = _righe_pulite(soup.body)
    return testo


def _righe_pulite(elemento) -> str:
    righe: list[str] = []
    for riga in elemento.get_text("\n").splitlines():
        riga = " ".join(riga.split())          # spazi multipli → uno
        if riga and riga not in righe[-1:]:    # salto righe vuote e doppioni consecutivi
            righe.append(riga)
    return "\n".join(righe)


def elenca_titoli(soup: BeautifulSoup) -> list[str]:
    """Titoli h2-h4 della pagina: servono per scegliere l'offerta."""
    return [" ".join(t.get_text().split()) for t in soup.find_all(["h2", "h3", "h4"])
            if t.get_text(strip=True)]


def estrai_sezione(soup: BeautifulSoup, offerta: str) -> tuple[str, str, list[str]] | None:
    """Trova il titolo che contiene `offerta` e prende testo e link
    fino al titolo successivo dello stesso livello (o più importante)."""
    for tag in soup(DA_TOGLIERE):
        tag.decompose()

    cerca = offerta.lower()
    for titolo in soup.find_all(TITOLI):
        nome = " ".join(titolo.get_text().split())
        if cerca not in nome.lower():
            continue

        livello = int(titolo.name[1])          # "h3" → 3
        righe = [nome]
        link: list[str] = []
        for testo in titolo.find_all_next(string=True):
            if isinstance(testo, Comment):
                continue
            genitore = testo.find_parent(TITOLI)
            if genitore is not None and genitore is not titolo and int(genitore.name[1]) <= livello:
                break                          # inizia l'offerta successiva: mi fermo
            a = testo.find_parent("a", href=True)
            if a and a["href"] not in link:    # raccolgo i link (es. "scopri di più")
                link.append(a["href"])
            if genitore is titolo:             # è il testo del titolo stesso
                continue
            riga = " ".join(testo.split())
            if riga and riga not in righe[-1:]:
                righe.append(riga)
        return nome, "\n".join(righe), link
    return None


def trova_dettaglio(url: str, link: list[str]) -> str | None:
    """Primo link della sezione che porta a un'altra pagina dello stesso sito."""
    dominio = urlparse(url).netloc
    for href in link:
        assoluto = urljoin(url, href).split("#")[0]
        if (assoluto.startswith("http")
                and urlparse(assoluto).netloc == dominio
                and assoluto.rstrip("/") != url.rstrip("/")):
            return assoluto
    return None


def leggi(url: str, offerta: str | None = None) -> Pagina:
    soup = BeautifulSoup(scarica(url), "html.parser")
    # Prima raccolgo email, modulo, azienda e posizione (il footer e i form servono ancora)
    email = trova_email(soup)
    modulo = ha_modulo(soup)
    azienda = trova_azienda(soup, url)
    posizione = trova_posizione(soup)
    pagina_usata = url

    if offerta:
        sezione = estrai_sezione(soup, offerta)
        if sezione is None:
            raise ValueError(f'Offerta "{offerta}" non trovata nella pagina')
        titolo, testo, link = sezione
        posizione = pulisci_titolo(titolo)

        # Se l'offerta ha una pagina di dettaglio, la leggo e aggiungo il suo testo
        dettaglio = trova_dettaglio(url, link)
        if dettaglio:
            soup_dettaglio = BeautifulSoup(scarica(dettaglio), "html.parser")
            email += [e for e in trova_email(soup_dettaglio) if e not in email]
            modulo = modulo or ha_modulo(soup_dettaglio)
            testo += "\n\n" + estrai_testo(soup_dettaglio)
            pagina_usata = dettaglio
    else:
        testo = estrai_testo(soup)
    return Pagina(pagina_usata, azienda, posizione, email, modulo, testo)


def nome_file(url: str, offerta: str | None = None) -> str:
    parti = urlparse(url)
    dominio = parti.netloc.removeprefix("www.").split(".")[0]
    pezzi = [p for p in parti.path.split("/") if p]
    ultimo = offerta or (pezzi[-1] if pezzi else "home")
    slug = re.sub(r"[^a-z0-9]+", "_", f"{dominio}_{ultimo}".lower()).strip("_")
    return slug[:60] + ".txt"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python -m agent.fetcher <url> ["nome offerta"]')
        sys.exit(1)

    url = sys.argv[1]
    offerta = sys.argv[2] if len(sys.argv) > 2 else None
    try:
        pagina = leggi(url, offerta)
    except requests.RequestException as errore:
        print(f"❌ Non riesco a scaricare la pagina: {errore}")
        sys.exit(1)
    except ValueError as errore:
        print(f"❌ {errore}. Titoli trovati:")
        for titolo in elenca_titoli(BeautifulSoup(scarica(url), "html.parser")):
            print(f"   - {titolo}")
        sys.exit(1)

    percorso = Path("annunci") / nome_file(url, offerta)
    percorso.write_text(pagina.come_annuncio(), encoding="utf-8")

    print(f"Azienda:   {pagina.azienda}")
    print(f"Posizione: {pagina.posizione}")
    print(f"Pagina:    {pagina.url}")
    print(f"Email:     {', '.join(pagina.email) or '—'}")
    print(f"Modulo:    {'sì' if pagina.ha_modulo else 'no'}")
    print(f"Testo:     {len(pagina.testo)} caratteri")
    print(f"💾 Salvato in {percorso}")
    if not offerta:
        print("ℹ️  Se la pagina ha più offerte, rilancia con il nome: "
              'python -m agent.fetcher <url> "Python"')
    if len(pagina.testo) < TESTO_MINIMO and not offerta:
        print("⚠️  Testo molto corto: la pagina forse è generata con JavaScript (servirà Playwright).")