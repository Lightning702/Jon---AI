# Grundlagen der Softwarearchitektur

Ein kurzer Einstieg:  
Softwarearchitektur beschreibt die hochrangige Struktur und die Entscheidungen, die ein Softwaresystem prägen. Sie definiert, wie Komponenten, Schichten und Schnittstellen organisiert sind, um geschäftliche Anforderungen zu erfüllen und Qualitätsziele zu erreichen. Im Vergleich zu ad‑hoc Design, das ohne geplante Struktur entsteht, liefert ein bewusstes Architekturkonzept langfristige Kosteneinsparungen, bessere Wartbarkeit und gezielte Steuerung von Qualitätsmerkmalen.

## Kernaussagen
- Softwarearchitektur ist die grundlegende Strukturierung eines Softwaresystems und definiert strukturelle Elemente sowie deren Beziehungen.  
- Sie umfasst Entscheidungen über Struktur, Verantwortlichkeiten, Schnittstellen und Qualitätsmerkmale.  
- Kernprinzipien sind Trennung von Zuständigkeiten, lose Kopplung, hohe Kohäsion und die Dependency Rule.  
- Qualitätsattribute wie Performance, Sicherheit, Skalierbarkeit, Wartbarkeit und Verfügbarkeit werden maßgeblich durch die Architektur beeinflusst.  
- Architekturentscheidungen werden dokumentiert, z. B. mit Architecture Decision Records (ADRs).  
- Clean Architecture nutzt konzentrische Schichten und trennt Business‑Logik von externen Systemen, um langfristige Wartbarkeit zu sichern.  
- Ad‑hoc Design entsteht ohne strategische Planung, führt zu hohen Fehlerbehebungs‑ und Anpassungskosten und weist häufig enge Kopplungen sowie unklare Verantwortlichkeiten auf.

## Details
- **Separation of Concerns**: Jede Komponente übernimmt eine klar definierte, einzelne Aufgabe.  
- **Loose Coupling**: Schwache Kopplung zwischen Komponenten isoliert Änderungen und erhöht Flexibilität.  
- **High Cohesion**: Elemente einer Komponente gehören zusammen und verfolgen einen klaren Zweck.  
- **Dependency Rule** (Clean Architecture): Abhängigkeiten zeigen nach innen, sodass die Kernbusiness‑Logik von äußeren Technologien entkoppelt bleibt.  
- **Architecture Decision Records (ADRs)**: Dokumentieren Architekturentscheidungen, deren Kontext, Alternativen und Konsequenzen.  
- **Clean Architecture Schichten**: Frameworks & Drivers, Interface Adapters, Application Layer (Use Cases) und Domain Layer (Entities).  
- **Qualitätsmodell ISO‑25010**: Bewertet Qualitätsmerkmale wie Funktionalität, Zuverlässigkeit, Leistungsfähigkeit, Sicherheit, Wartbarkeit und Portabilität.  
- **Architektur‑Muster**: Layered, Client‑Server, Event‑Driven, Microkernel, Microservices, Pipe‑and‑Filters usw., jeweils mit eigenen Vor‑ und Nachteilen.  
- **Domain‑Driven Design (DDD)**: Nutzt fachliche Konzepte und Boundaries (Bounded Contexts), um Software an der Domäne auszurichten.  
- **Vertical Slice Architecture**: Organisiert Code um vollständige Features, ermöglicht schnelle Entwicklung, birgt jedoch Risiko von Duplizierung.

## Begriffe
**Softwarearchitektur** — Gesamtheit struktureller Elemente und ihrer Beziehungen.  
**Komponente** — Kapselt Verhalten und kommuniziert über definierte Schnittstellen.  
**Qualitätsbaum nach ISO 25010** — Strukturierte Methode zur Bewertung von Qualitätsmerkmalen.  
**Separation of Concerns** — Prinzip, dass jede Komponente eine klar definierte, einzelne Aufgabe übernimmt.  
**Loose Coupling** — Schwache Kopplung zwischen Komponenten, um Änderungen zu isolieren.  
**Cohesion** — Grad, in dem die Elemente einer Komponente zusammengehören und einen klaren Zweck haben.  
**Architecture Decision Record (ADR)** — Dokumentationsformat für Architekturentscheidungen mit Kontext, Entscheidung, Alternativen und Konsequenzen.  
**Clean Architecture** — Geschichtete Architektur, die Business‑Logik von externen Systemen trennt und die Dependency Rule nutzt.  
**Domain Layer** — Zentrale Schicht mit Unternehmens‑Entitäten und -Regeln.  
**Interface Adapters** — Konvertieren Daten zwischen äußeren Systemen und innerer Formatierung.  
**Microservices** — Architekturstil, der Anwendungen aus losem Services besteht.  
**Pipe‑and‑Filters** — Architekturmuster, bei dem Daten durch eine Kette von Transformationsschritten fließen.  
**Layered Architecture** — Strukturiert Software in unabhängige Schichten, die jeweils eine spezifische Aufgabe übernehmen.  
**Client‑Server** — Modell mit einem Server, der Ressourcen bereitstellt, und mehreren Clients, die Anfragen stellen.  
**Event‑Driven Architecture** — Architektur, bei der Aktionen (Events) Reaktionen auslösen und asynchron verarbeitet werden.  
**Microkernel** — Kernsystem mit minimalen Funktionen, das durch plug‑in Module erweitert wird.  

## Merksätze
- Architektur ist ein strategischer Plan, nicht ein ad‑hoc Ergebnis.  
- Gute Architektur reduziert langfristige Kosten für Fehlerbehebung und Anpassungen.  
- Kernprinzipien (Separation of Concerns, Loose Coupling, High Cohesion) leiten das Design.  
- Qualitätsattribute bestimmen architektonische Entscheidungen.  
- Dokumentation (z. B. ADRs) ist unverzichtbar für nachvollziehbare Entscheidungen.  

## Unsicher / strittig
- (Keine offenen Widersprüche im vorliegenden Material.)
