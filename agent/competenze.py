"""Confronto PRECISO tra annuncio e profilo: lo fa Python, non l'AI (zero allucinazioni)."""
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Competenza:
    nome: str                  # nome da mostrare
    alias: tuple[str, ...]     # come può comparire nel testo dell'annuncio
    la_ho: bool                # True = ce l'ho, False = non ce l'ho
    dove: str = ""             # dove l'ho usata (per scrivere esempi veri nella mail)
    maiuscole: bool = False    # True = conta maiuscole/minuscole (per parole ambigue come "Go")


COMPETENZE: list[Competenza] = [
    # ---------- Linguaggi ----------
    Competenza("Python", ("Python",), True, "Playwright e pytest in Sellogic, Django, Job Aggregator"),
    Competenza("Java", ("Java",), True, "Appium + TestNG in Sellogic, Selenium + Cucumber, Spring Boot"),
    Competenza("C#", ("C#",), True, "backend ASP.NET Core e test xUnit del mio progetto"),
    Competenza("JavaScript", ("JavaScript", "JS"), True, "Cypress in Sellogic"),
    Competenza("TypeScript", ("TypeScript",), True, "gestionale Angular del mio progetto"),
    Competenza("Dart / Flutter", ("Flutter", "Dart"), True, "app Self-Order Kiosk in Sellogic"),
    Competenza("SQL", ("SQL",), True, "database PostgreSQL dei miei progetti"),
    Competenza("Node.js", ("Node.js", "NodeJS", "Node"), True, "debug e correzioni in Sellogic"),
    # ---------- Framework ----------
    Competenza("Django", ("Django",), True, "portfolio online e Job Aggregator"),
    Competenza("Spring Boot", ("Spring Boot", "Spring"), True, "Master Epicode e JEE Academy"),
    Competenza("Hibernate / JPA", ("Hibernate", "JPA"), True, "Master Epicode e JEE Academy"),
    Competenza("Servlet / JSP", ("Servlet", "JSP"), True, "JEE Academy"),
    Competenza("ASP.NET Core", ("ASP.NET", ".NET"), True, "Web API del Restaurant Management System"),
    Competenza("Entity Framework", ("Entity Framework", "EF Core"), True, "migration del mio progetto .NET"),
    Competenza("Angular", ("Angular",), True, "gestionale Angular 20 del mio progetto"),
    Competenza("React", ("React",), True, "Master Epicode"),
    Competenza("Vue", ("Vue", "Vuetify"), True, "ho testato per mesi un gestionale Vue 3 in Sellogic"),
    Competenza("HTML / CSS", ("HTML", "CSS", "SCSS", "SASS"), True, "frontend dei miei progetti"),
    Competenza("Bootstrap", ("Bootstrap",), True, "portfolio Django"),
    # ---------- Test ----------
    Competenza("Playwright", ("Playwright", "APIRequestContext"), True, "~70 test E2E e 226 test API in Sellogic"),
    Competenza("Cypress", ("Cypress",), True, "suite E2E da zero in Sellogic"),
    Competenza("Selenium", ("Selenium", "WebDriver"), True, "53 scenari BDD sul gestionale Angular"),
    Competenza("Appium", ("Appium",), True, "25 test case su 3 app native in Sellogic"),
    Competenza("Robot Framework", ("Robot Framework",), True, "94 test E2E del mio progetto"),
    Competenza("Cucumber / BDD", ("Cucumber", "BDD", "Gherkin"), True, "scenari BDD su web e mobile"),
    Competenza("pytest", ("pytest",), True, "suite Playwright in Sellogic"),
    Competenza("JUnit / TestNG / xUnit", ("JUnit", "TestNG", "xUnit"), True, "test Java e .NET"),
    Competenza("REST Assured", ("REST Assured", "RestAssured"), True, "verifiche API nei test Cucumber"),
    Competenza("Postman", ("Postman",), True, "test API manuali"),
    Competenza("API REST", ("REST", "RESTful", "API"), True, "226 test API in Sellogic, Web API .NET"),
    Competenza("Test manuali", ("test manual", "testing manual", "collaudo"), True, "ogni modulo del gestionale Sellogic"),
    Competenza("Page Object Model", ("Page Object",), True, "tutte le mie suite"),
    # ---------- DevOps e strumenti ----------
    Competenza("Docker", ("Docker", "container"), True, "pipeline CI e Docker Compose"),
    Competenza("GitLab CI", ("GitLab",), True, "pipeline in Sellogic"),
    Competenza("GitHub Actions", ("GitHub Actions",), True, "CI del portfolio"),
    Competenza("CI/CD", ("CI/CD", "CI", "DevOps", "pipeline"), True, "GitLab CI e GitHub Actions"),
    Competenza("Git", ("Git", "GitHub", "VCS"), True, "uso quotidiano"),
    Competenza("Maven", ("Maven",), True, "progetti Selenium e Appium"),
    Competenza("Jira", ("Jira",), True, "segnalazione bug in Sellogic"),
    Competenza("Agile / Scrum", ("Agile", "Scrum"), True, "Master Epicode"),
    # ---------- Cose che NON ho ----------
    Competenza("PHP", ("PHP",), False),
    Competenza("Laravel", ("Laravel",), False),
    Competenza("Go", ("Golang", "Go"), False, maiuscole=True),
    Competenza("Kotlin", ("Kotlin",), False),
    Competenza("Swift", ("Swift",), False),
    Competenza("C++", ("C++",), False),
    Competenza("React Native", ("React Native",), False),
    Competenza("FastAPI", ("FastAPI",), False),
    Competenza("Flask", ("Flask",), False),
    Competenza("MySQL", ("MySQL",), False),
    Competenza("MongoDB", ("MongoDB", "Mongo"), False),
    Competenza("Kafka", ("Kafka",), False),
    Competenza("JMeter", ("JMeter",), False),
    Competenza("Kubernetes", ("Kubernetes", "K8s"), False),
    Competenza("Jenkins", ("Jenkins",), False),
    Competenza("Cloud (AWS / Azure / GCP)", ("AWS", "Azure", "GCP", "Google Cloud"), False),
    Competenza("SOAP", ("SOAP",), False),
    Competenza("Tomcat", ("Tomcat",), False),
    Competenza("SAP", ("SAP",), False, maiuscole=True),
    Competenza("Laurea", ("laurea", "laureato", "laureata", "degree"), False),
    Competenza("Certificazione ISTQB", ("ISTQB",), False),
    Competenza("Progetti di intelligenza artificiale", ("intelligenza artificiale", "machine learning", "deep learning"), False),
    Competenza("Data Science", ("data science", "data scientist"), False),
]


def _regex(alias: str, maiuscole: bool) -> re.Pattern:
    """Cerca l'alias come parola intera: "Java" NON deve trovare "JavaScript"."""
    flag = 0 if maiuscole else re.IGNORECASE
    # (?<![\w]) e (?![\w]) = prima e dopo non ci devono essere lettere o numeri
    return re.compile(rf"(?<![\w]){re.escape(alias)}(?![\w])", flag)


def trova(testo: str) -> list[Competenza]:
    """Restituisce le competenze citate nel testo (senza doppioni, in ordine di lista)."""
    trovate = []
    for c in COMPETENZE:
        if any(_regex(a, c.maiuscole).search(testo) for a in c.alias):
            trovate.append(c)
    return trovate


def confronta(annuncio: str) -> tuple[list[Competenza], list[Competenza]]:
    """Divide le competenze dell'annuncio in (punti_forti, cosa_manca)."""
    trovate = trova(annuncio)
    punti_forti = [c for c in trovate if c.la_ho]
    cosa_manca = [c for c in trovate if not c.la_ho]
    return punti_forti, cosa_manca


def inventate(testo_generato: str) -> list[str]:
    """Controllo anti-allucinazione: tecnologie che NON ho ma che compaiono nel testo scritto dall'AI."""
    return [c.nome for c in trova(testo_generato) if not c.la_ho]


if __name__ == "__main__":
    # Uso: python -m agent.competenze annunci\bsd_python.txt
    annuncio = Path(sys.argv[1]).read_text(encoding="utf-8-sig")
    forti, manca = confronta(annuncio)

    print("✅ PUNTI FORTI")
    for c in forti:
        print(f"   - {c.nome}: {c.dove}")
    print("\n❌ COSA MANCA")
    for c in manca:
        print(f"   - {c.nome}")