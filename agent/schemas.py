"""Schemi Pydantic: la "forma" esatta della risposta che vogliamo dal modello AI."""
from typing import Literal

from pydantic import BaseModel, Field


class Valutazione(BaseModel):
    """Valutazione di un annuncio o di un'azienda rispetto al mio profilo."""

    azienda: str = Field(description="Nome dell'azienda")
    posizione: str = Field(
        description="Titolo della posizione, oppure 'Candidatura spontanea' se non c'è un annuncio"
    )
    punteggio: int = Field(
        ge=0, le=100,  # ge = maggiore o uguale, le = minore o uguale
        description="Quanto il profilo è adatto alla posizione, da 0 a 100",
    )
    punti_forti: list[str] = Field(
        description="Requisiti dell'annuncio che il profilo soddisfa, con l'esperienza concreta collegata"
    )
    cosa_manca: list[str] = Field(
        description="Requisiti importanti dell'annuncio che il profilo NON ha"
    )
    canale: Literal["email", "form", "sconosciuto"] = Field(
        description="Come candidarsi: via email, tramite modulo sul sito, oppure non è chiaro"
    )
    email_candidatura: str | None = Field(
        default=None, description="Indirizzo email per candidarsi, se presente nel testo"
    )
    oggetto_email: str | None = Field(
        default=None, description="Oggetto dell'email, solo se il canale è email"
    )
    testo: str = Field(
        description="Testo della candidatura (email o campo del modulo), scritto seguendo le regole di stile"
    )
    note_per_me: str = Field(
        description="Note utili per me: sede, modalità di lavoro, cose da verificare"
    )