# drop

Privater Dienst für Kurzlinks und im Browser verschlüsselte Text-Drops. LB 324 (DevOps) von Fynn Auerbach und Lionel Wermelinger, IM24c.

- Idee und Spezifikation: [docs/README.md](docs/README.md)
- Laufende App: <https://drop-auerbachwermelinger-dtbuh3c7bre2e7a9.switzerlandnorth-01.azurewebsites.net>

## Funktionen

- **Kurzlinks** mit QR-Code und Kopier-Knopf
- **Verschlüsselte Text-Drops:** Der Browser verschlüsselt mit AES-GCM, der Schlüssel steht nur im `#`-Teil des Links. Der Server speichert nie Klartext.
- **Ablaufzeit** (1 Stunde, 1 Tag, 7 Tage) und **Löschen nach dem ersten Lesen**
- **Dashboard** mit Klicks pro Link, 7-Tage-Verlauf und Gerätetypen (ohne IP-Adressen)
- Login mit einem Passwort aus der Umgebung (`PASSWORD`)

## Lokal starten

```bash
python3 -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # danach PASSWORD und SECRET_KEY in .env setzen
flask --app drop run          # http://127.0.0.1:5000
```

Produktiv (Azure App Service): `gunicorn --bind=0.0.0.0 --timeout 600 "drop:create_app()"`.

## Aufgabe 1

Neue Anforderungen werden über die Issue-Vorlage **«Anforderung»** (`.github/ISSUE_TEMPLATE/anforderung.yml`) erfasst. Sie fragt das Format der LB ab: **Zielsystem + Priorität (muss/soll/wird) + Systemaktivität + Ergänzungen + Funktionalität + Bedingungen** (zeitlich mit «wenn», logisch mit «falls»), dazu Akzeptanzkriterien als Given/When/Then, die später zu Testfällen werden. Fehler meldet man mit der Vorlage **«Bug»**.

Den Typ setzt man **manuell** als Label: `Funktionale Anforderung`, `Qualitätsanforderung` oder `Randanforderung`. Dazu kommen die Status-Labels aus LA 1611, die wir von Hand pflegen: neu erfasst `status: new issue`, in Arbeit `status: in progress`, zurückgestellt `status: backlog`; geschlossene Issues tragen kein Status-Label mehr. Jedes Issue hängt an einem Meilenstein nach Semantic Versioning (`0.1.0`, `0.2.0`, `0.3.0`, `0.3.1`) oder an `Backlog` für spätere Ideen.

## Aufgabe 2

### pre-commit installieren

Einmal pro Rechner, im Projektordner (macOS/Linux; unter Windows `.venv\Scripts\activate` statt `source`):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pre-commit
pre-commit install --hook-type pre-commit
pre-commit install --hook-type pre-push
pre-commit install --hook-type commit-msg
```

`pre-commit install` allein reicht auch, weil `.pre-commit-config.yaml` alle drei Hook-Typen unter `default_install_hook_types` aufführt. Die drei Befehle oben machen es ausdrücklich.

Vor dem Arbeiten immer zuerst die virtuelle Umgebung aktivieren (`source .venv/bin/activate`), sonst findet der push-Hook `python -m pytest` nicht.

### Was automatisch passiert

| Wann | Was | Wirkung |
|---|---|---|
| `git commit` | black, flake8, Datei-Checks | Code wird formatiert und geprüft. Ändert black etwas, Dateien neu `git add`-en und erneut committen. |
| `git commit` (Message) | needs-hash | Commit-Message muss ein Issue referenzieren, z. B. `#10`. |
| `git push` | pytest | Alle Tests laufen. Schlägt einer fehl, wird der Push abgebrochen. |

Alle Hooks von Hand ausführen: `pre-commit run --all-files` (commit-Stufe) und `pre-commit run --hook-stage pre-push` (Tests).

`git commit --no-verify` bzw. `git push --no-verify` ist in diesem Projekt nicht erlaubt. Weil sich lokale Hooks so umgehen lassen (LA 1640), laufen die Tests zusätzlich auf GitHub bei jedem Pull Request auf `dev`.

## Aufgabe 3

`.github/workflows/tests.yml` führt bei **jedem Pull Request auf `dev`** pytest aus und löst sonst nichts aus (kein Push-Trigger, kein Lint, keine weiteren Jobs). Das Ergebnis erscheint als Check «test» im Pull Request. So ist auch dann sichergestellt, dass nur getesteter Code auf `dev` kommt, wenn jemand die lokalen Hooks umgeht.

## Aufgabe 4

### Laufende Applikation

**URL:** <https://drop-auerbachwermelinger-dtbuh3c7bre2e7a9.switzerlandnorth-01.azurewebsites.net>

Web App `drop-auerbachwermelinger`, Region Switzerland North. Funktionstest: `/health` liefert `{"status":"ok"}`.

**Login:** Passwort ist der GitHub-Benutzername des Repo-Besitzers, `Fynnius` (Vorgabe LB).

drop läuft auf **Azure App Service** (Linux, Python 3.12, Tarif Free F1) im Azure-for-Students-Abo von Lionel Wermelinger. Fynns eigenes Abo ist abgelaufen und laut IT-Helpdesk der BBB nicht reaktivierbar; zwischenzeitlich war Render geplant.

### Geheimnisse aus der `.env` auf Azure übertragen

Lokal stehen `PASSWORD` und `SECRET_KEY` in der `.env` (wird nie eingebucht, siehe `.gitignore`). Auf Azure gibt es keine `.env`; dort werden die Werte als **App Settings** gesetzt, die die App als Umgebungsvariablen liest:

1. Azure-Portal → App Services → Web App öffnen.
2. **Settings → Environment variables → App settings** → für jeden Eintrag **+ Add**, danach **Apply** und den Neustart bestätigen:

   | Name | Wert |
   |---|---|
   | `PASSWORD` | `Fynnius`, der GitHub-Benutzername des Repo-Besitzers (Vorgabe LB), **nicht** der Wert aus der lokalen `.env` |
   | `SECRET_KEY` | langer Zufallswert, erzeugt mit `python3 -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | `sqlite:////home/drop.db` (nur `/home` überlebt Neustarts und Deployments) |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (Azure installiert `requirements.txt` beim Deploy) |
   | `WEBSITE_WEBDEPLOY_USE_SCM` | `true` (nötig für das Publish-Profil) |

3. **Settings → Configuration → General settings** (bzw. **Stack settings**):
   - **Startup Command:** `gunicorn --bind=0.0.0.0 --timeout 600 "drop:create_app()"`
   - **SCM Basic Auth Publishing Credentials:** On, **HTTPS Only:** On → **Save**.

Prüfen: Login mit `Fynnius` klappt; nach **Restart** (Overview) ist man noch eingeloggt und die Links sind noch da.

Die Werte stehen nirgends im Repository. HTTPS endet bei Azure am Load Balancer; die App erkennt das über `WEBSITE_HOSTNAME` und erzeugt trotzdem `https://`-Links (#34).

### Automatische Auslieferung

`.github/workflows/deploy.yml` läuft bei jedem Merge in `main`: zuerst pytest, danach Auslieferung mit `azure/webapps-deploy`. Einrichtung einmalig:

1. Azure-Portal → Web App → **Overview** → **Download publish profile**.
2. GitHub → Repo → **Settings → Secrets and variables → Actions**:
   - Reiter **Secrets** → **New repository secret**: `AZURE_WEBAPP_PUBLISH_PROFILE` = ganzer Inhalt der heruntergeladenen Datei.
   - Reiter **Variables** → **New repository variable**: `AZURE_WEBAPP_NAME` = Name der Web App.
3. Die heruntergeladene Datei löschen (sie ist ein Zugangsschlüssel).

## Aufgabe 5

Eigenes Feature (von der Lehrperson erlaubt): **«Löschen nach dem Lesen»** für Drops, umgesetzt nach GitHub Flow:

1. Issue [#20](https://github.com/Fynnius/AuerbachWermelingerLB-324/issues/20) im LB-Format, Label `Funktionale Anforderung`
2. Branch `feature/20-burn-after-read` direkt aus dem Issue erstellt (`gh issue develop 20 --base dev`)
3. Commits: zuerst der Test (`tests/test_burn.py`), dann Backend, dann Oberfläche
4. Pull Request [#58](https://github.com/Fynnius/AuerbachWermelingerLB-324/pull/58) auf `dev` mit Beschreibung und Testnachweis; der Workflow «Tests» lief grün
5. Merge per Rebase; **der Branch `feature/20-burn-after-read` bleibt bestehen**
6. Ausgeliefert auf Azure mit Release 0.3.0: Pull Request [#60](https://github.com/Fynnius/AuerbachWermelingerLB-324/pull/60) `dev → main`, danach lief der Workflow «Deploy» grün

## Arbeitsweise

- **Branches:** Auf `main` liegt nur, was ausgeliefert ist; `dev` sammelt getestete Features; entwickelt wird auf `feature/<issue-nr>-<slug>` ab `dev`. Feature-Branches werden nicht gelöscht.
- **Ablauf pro Änderung:** Issue → Branch ab `dev` → atomare Commits mit `#nr` → Pull Request auf `dev` → Tests grün → Review durch den anderen → Merge per Rebase. `main` und `dev` sind geschützt; Änderungen gehen nur über Pull Requests.
- **Release:** Pull Request `dev → main` (Merge-Commit) → Workflow «Deploy» → Tag und GitHub Release nach Semantic Versioning (`0.2.0`, `0.3.0`, `0.3.1`).

## KI-Nutzung

Die Lehrperson hat KI für dieses Projekt erlaubt. Wir haben **Claude** (Anthropic) eingesetzt für:

- Ideenfindung, Planung der Issues und der Reihenfolge
- Programmcode, Tests und Dokumentation (Vorschläge, die wir gelesen und übernommen haben)
- Recherche zur Einrichtung von Azure App Service und GitHub Actions
- das Öffnen und Mergen der Pull Requests per GitHub CLI, jeweils erst nach grünem Test-Workflow

Die Commits sind unter unseren Git-Identitäten entstanden; Claude hat die Git-Befehle ausgeführt, wir haben jeden Schritt geprüft und freigegeben. Entscheidungen (Projektidee, Plattform, Ablauf) haben wir getroffen. Passwörter, `SECRET_KEY` und das Publish-Profil haben wir selbst eingetragen und nie an die KI weitergegeben. Wer Code einbucht, muss ihn erklären können.

## Team

Fynn Auerbach und Lionel Wermelinger, IM24c, Berufsfachschule BBB. Partnerarbeit: Commits von beiden, gemeinsam am selben Rechner und im selben Repository. Ab [#61](https://github.com/Fynnius/AuerbachWermelingerLB-324/issues/61) prüft der jeweils andere jeden Pull Request zusätzlich als Review auf GitHub.
