"""Bozze Gmail: crea una bozza con il CV allegato. NON invia mai niente."""

import base64
import mimetypes
import sys
from email.message import EmailMessage
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Permesso minimo per creare bozze (non serve leggere la posta)
SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
CREDENZIALI = Path("credentials.json")   # scaricato da Google Cloud (in .gitignore)
TOKEN = Path("token.json")               # creato al primo accesso (in .gitignore)
CV = Path("data/Stella_Marucelli_CV.pdf")
MITTENTE = "stella.marucelli@gmail.com"


def servizio_gmail():
    """Accesso a Gmail: la prima volta apre il browser per il consenso, poi usa token.json."""
    creds = None
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())           # rinnovo silenzioso
        except RefreshError:
            creds = None                       # token scaduto o revocato: rifaccio il login

    if not creds or not creds.valid:
        if not CREDENZIALI.exists():
            raise FileNotFoundError("Manca credentials.json nella cartella del progetto")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENZIALI), SCOPES)
        creds = flow.run_local_server(port=0)  # si apre il browser
        TOKEN.write_text(creds.to_json(), encoding="utf-8")

    return build("gmail", "v1", credentials=creds)


def crea_messaggio(destinatario: str | None, oggetto: str, testo: str,
                   allegato: Path | None = None) -> EmailMessage:
    """Costruisce la mail. Non tocca Gmail: per questo si potrà testare con pytest."""
    messaggio = EmailMessage()
    messaggio["From"] = MITTENTE
    if destinatario:                       # per i moduli il destinatario può mancare
        messaggio["To"] = destinatario
    messaggio["Subject"] = oggetto
    messaggio.set_content(testo)

    if allegato:
        tipo, _ = mimetypes.guess_type(allegato.name)
        principale, secondario = (tipo or "application/octet-stream").split("/")
        messaggio.add_attachment(allegato.read_bytes(), maintype=principale,
                                 subtype=secondario, filename=allegato.name)
    return messaggio


def crea_bozza(destinatario: str | None, oggetto: str, testo: str,
               allegato: Path | None = CV) -> str:
    """Crea la bozza in Gmail e restituisce il suo id."""
    if allegato and not allegato.exists():
        raise FileNotFoundError(f"CV non trovato: {allegato}")

    messaggio = crea_messaggio(destinatario, oggetto, testo, allegato)
    grezzo = base64.urlsafe_b64encode(messaggio.as_bytes()).decode()
    bozza = (servizio_gmail().users().drafts()
             .create(userId="me", body={"message": {"raw": grezzo}})
             .execute())
    return bozza["id"]


if __name__ == "__main__":
    # Prova: bozza indirizzata a me stessa
    try:
        id_bozza = crea_bozza(
            destinatario=MITTENTE,
            oggetto="Prova job-agent – bozza con CV",
            testo="Buongiorno,\n\nquesta è una bozza di prova creata dal mio job-agent.\n\nStella",
        )
    except FileNotFoundError as errore:
        print(f"❌ {errore}")
        sys.exit(1)

    print(f"✅ Bozza creata (id {id_bozza})")
    print("📬 Controlla in Gmail → Bozze: https://mail.google.com/mail/#drafts")