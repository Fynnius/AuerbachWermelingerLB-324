# drop – Projektidee LB 324

**Team:** Fynn Auerbach, Lionel Wermelinger (IM24c)
**Modul:** 324 DevOps, Leistungsbeurteilung (Partnerarbeit)
**Status:** Idee. Die Umsetzung folgt später.

## Idee in einem Satz

drop ist ein privater Dienst, den wir selbst auf Render betreiben: Er macht aus Links, Texten und Dateien einen Kurzlink, verschlüsselt geteilte Inhalte schon im Browser und zeigt live, wann ein Link geöffnet wurde.

## Warum

- Wir wollen Sachen schnell vom Handy auf den PC oder an Kollegen schicken, ohne WhatsApp, Mail oder einen fremden Dienst.
- Lange Links wollen wir kurz und als QR-Code teilen.
- Wir wollen sehen, ob ein geteilter Link schon geöffnet wurde.

## Funktionen

### Kurzlinks
- Aus einer langen URL wird `…/x7k2Qa`. Wer den Kurzlink öffnet, wird weitergeleitet.
- Zu jedem Link gibt es einen QR-Code.

### Verschlüsselter Drop (Text, später auch Dateien)
- Der Browser verschlüsselt den Inhalt mit der Web Crypto API (AES-GCM).
- Der Schlüssel steht nur im `#`-Teil des Links. Dieser Teil wird nie an den Server geschickt.
- **Der Server speichert also nur Datensalat.** Weder wir noch Render können den Inhalt lesen.
- Optionen pro Drop:
  - Ablaufzeit: 1 Stunde, 1 Tag oder 7 Tage
  - Löschen nach dem ersten Öffnen («burn after reading»)

### Live-Dashboard
- Pro Link sehen wir, wie oft und wann er geöffnet wurde, über welches Gerät und aus welchem Land, als Zeitverlauf.
- Das Dashboard aktualisiert sich live ohne Neuladen (Server-Sent Events).
- **Das Dashboard weiss, *dass* etwas geöffnet wurde, aber nie, *was* drin ist.** Diese Trennung zeigen wir in der Präsentation.

### Zugriff
- Erstellen und Dashboard sind durch das `PASSWORD` aus der `.env` geschützt (Vorgabe der LB).
- Öffnen geht ohne Login, nur mit dem Link.

## Technik (geplant)

| Teil | Wahl | Begründung |
|---|---|---|
| Backend | Python / Flask | Wie im Modul, damit unsere CI/CD-Vorlagen passen |
| Datenbank | SQLite, später evtl. Postgres bei Neon | Für das MVP reicht SQLite. Auf Render geht die Datei bei jeder Auslieferung verloren (siehe Hosting) |
| Verschlüsselung | Web Crypto API im Browser | Keine Bibliothek nötig, der Server sieht nie Klartext |
| Live-Updates | Server-Sent Events | Einfacher als WebSockets, läuft mit Flask |
| QR-Code | Python-Paket `qrcode` | |
| Tests | pytest | |
| Formatierung / Linting | black, flake8 via pre-commit | |
| Auslieferung | Render (Web Service) via GitHub Action und Deploy Hook | Azure ist nicht verfügbar (siehe Hosting) |

## Hosting: Render statt Azure

**Entscheid:** Wir liefern drop auf [Render](https://render.com) aus, nicht auf Azure.

**Warum:**
- Fynns Azure-for-Students-Abo ist abgelaufen. Der IT-Helpdesk der BBB hat am 28.08.2026 bestätigt, dass es wegen der Regelung der Bildungsinstitution nicht neu aktiviert werden kann.
- Die Lehrperson hat erlaubt, eine andere Plattform zu verwenden.
- Render ist gratis, braucht keine Kreditkarte, und man meldet sich mit dem GitHub-Konto an.

**So setzen wir es auf:**
1. Auf Render einen *Web Service* aus dem GitHub-Repo erstellen, Branch `main`, Plan *Free*.
2. Build-Befehl: `pip install -r requirements.txt`
3. Start-Befehl: `gunicorn app:app`
4. Unter *Environment* `PASSWORD` setzen (Wert = GitHub-Username, Vorgabe LB).
5. *Auto-Deploy* ausschalten und unter *Settings* die *Deploy Hook*-URL kopieren.
6. Diese URL im GitHub-Repo als Secret `RENDER_DEPLOY_HOOK` speichern.
7. Workflow `.github/workflows/deploy.yml`: bei jedem push auf `main` die Hook-URL aufrufen (`curl -X POST`).

**Einschränkungen des Gratis-Plans:**
- Die App schläft nach etwa 15 Minuten ohne Besucher. Der erste Aufruf danach dauert rund 30 Sekunden.
- Die Festplatte ist nicht dauerhaft: Bei jeder Auslieferung geht die SQLite-Datei verloren. Für die LB und die Demo ist das in Ordnung. Wenn Daten bleiben sollen, wechseln wir auf eine Gratis-Postgres-Datenbank bei Neon; deren Verbindungs-URL wird dann ein zweites Secret.

## Umfang

**Erste Version (MVP):**
1. Link kürzen und weiterleiten
2. Verschlüsselter Text-Drop mit Ablaufzeit
3. Löschen nach dem Lesen
4. QR-Code pro Link
5. Dashboard mit Klickzahlen (zuerst ohne Live-Updates)

**Wenn Zeit bleibt:**
6. Live-Updates im Dashboard
7. Datei-Drops
8. Weltkarte und Geräte-Statistik

**Bewusst nicht dabei:** mehrere Benutzerkonten, eigene Domain, mobile App.

## Bezug zur LB 324

Bewertet wird der Umgang mit den CI/CD-Werkzeugen, nicht der Umfang der App. So decken wir die Kriterien ab:

| Krit. | Wie wir es in drop umsetzen |
|---|---|
| 0 | Öffentliches Repo nach Vorgabe benennen, URL auf Moodle abgeben, Archiv am Schluss hochladen |
| 1-1 | Issue-Vorlage im Format *Zielsystem + muss/soll/wird + Systemaktivität + Ergänzung + Funktionalität + Bedingung* sowie die Labels *Funktionale Anforderung*, *Qualitätsanforderung* und *Randanforderung* |
| 2-1 | pre-commit formatiert bei jedem **commit** (black) |
| 2-2 | pre-commit testet bei jedem **push** (pytest, `stages: [pre-push]`) |
| 2-3 | readme.md erklärt die Installation, inklusive `pre-commit install --hook-type pre-push` |
| 3-1 | GitHub Action: pytest bei jedem Pull Request auf `dev`, **sonst nichts** |
| 4-1 | drop läuft auf Render, die URL steht in der readme.md |
| 4-2 | `PASSWORD` (= GitHub-Username) als Environment Variable auf Render, Schritte in der readme.md. Die Deploy-Hook-URL liegt als GitHub-Secret im Repo. |
| 4-3 | GitHub Action: ruft bei jedem merge auf `main` den Deploy Hook von Render auf. Auto-Deploy in Render ist ausgeschaltet, damit die Auslieferung sichtbar über unseren Workflow läuft. |
| 5-1 | Eigenes Feature mit eigenem Test über den GitHub Flow (von der Lehrperson erlaubt), z. B. «Löschen nach dem Lesen». Den Branch danach **nicht löschen**. |

### Branch-Modell (Vorgabe LB)
- `main`: nur was ausgeliefert wird. Ausgelieferte Version = `main`.
- `dev`: abgeschlossene und getestete Features.
- `feature/…`: eine Aufgabe pro Branch, immer ab `dev`.

Ablauf: Issue → `feature/…` ab `dev` → PR auf `dev` (Tests laufen) → Review durch den anderen → zum Ausliefern PR von `dev` auf `main`.

## Zusammenarbeit

- Ein gemeinsames Repo, beide als Collaborators. `main` und `dev` sind geschützt.
- Jede Aufgabe ist ein Issue mit Assignee. Der andere liest den Diff vor dem Merge.
- **Aufteilung nach Dateien**, damit es nicht wieder zu Konflikten wie in LA 1632 kommt. Vorschlag:
  - Person A: Backend, Datenbank, Verschlüsselungs-Logik, Tests
  - Person B: Frontend, Dashboard, QR-Code, Live-Updates
  - Gemeinsam: pre-commit, Workflows, Render, readme.md
- PRs früh als Draft öffnen.
- KI-Regeln aus unserer Präsentation gelten weiter: Wer KI-Code einbucht, muss ihn erklären können, und Secrets (`.env`, Deploy-Hook-URL) kommen nie in einen Prompt.

## Noch offen

- [x] Repo-Name: `AuerbachWermelingerLB-324`
- [ ] Wem gehört das Repo, wer ist Collaborator?
- [ ] Wer übernimmt Person A, wer Person B?
- [ ] Name des Render-Services (bestimmt die URL `<name>.onrender.com`)
- [ ] Welches Feature genau für Kriterium 5-1?
