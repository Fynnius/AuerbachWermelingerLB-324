# drop

Privater Dienst für Kurzlinks und im Browser verschlüsselte Text-Drops. LB 324 (DevOps) von Fynn Auerbach und Lionel Wermelinger, IM24c.

- Idee und Spezifikation: [docs/README.md](docs/README.md)

## Lokal starten

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # danach PASSWORD und SECRET_KEY in .env setzen
flask --app drop run          # http://127.0.0.1:5000
```

Produktiv (Azure App Service): `gunicorn --bind=0.0.0.0 --timeout 600 "drop:create_app()"`.

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

## Aufgabe 4

### Laufende Applikation

**URL:** `⚠️ URL FOLGT` (Default domain der Azure Web App)

drop läuft auf **Azure App Service** (Linux, Python 3.12, Tarif Free F1) im Azure-for-Students-Abo von Lionel Wermelinger. Fynns eigenes Abo ist abgelaufen und laut IT-Helpdesk der BBB nicht reaktivierbar; zwischenzeitlich war Render geplant.

### Geheimnisse aus der `.env` auf Azure übertragen

Lokal stehen `PASSWORD` und `SECRET_KEY` in der `.env` (wird nie eingebucht, siehe `.gitignore`). Auf Azure gibt es keine `.env`; dort werden die Werte als **App Settings** gesetzt, die die App als Umgebungsvariablen liest:

1. Azure-Portal → App Services → Web App öffnen.
2. **Settings → Environment variables → App settings** → für jeden Eintrag **+ Add**, danach **Apply** und den Neustart bestätigen:

   | Name | Wert |
   |---|---|
   | `PASSWORD` | GitHub-Benutzername (Vorgabe LB), **nicht** der Wert aus der lokalen `.env` |
   | `SECRET_KEY` | langer Zufallswert, erzeugt mit `python3 -c "import secrets; print(secrets.token_hex(32))"` |
   | `DATABASE_URL` | `sqlite:////home/drop.db` (nur `/home` überlebt Neustarts und Deployments) |
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` (Azure installiert `requirements.txt` beim Deploy) |
   | `WEBSITE_WEBDEPLOY_USE_SCM` | `true` (nötig für das Publish-Profil) |

3. **Settings → Configuration → General settings** (bzw. **Stack settings**):
   - **Startup Command:** `gunicorn --bind=0.0.0.0 --timeout 600 "drop:create_app()"`
   - **SCM Basic Auth Publishing Credentials:** On, **HTTPS Only:** On → **Save**.

Prüfen: Login mit dem GitHub-Benutzernamen klappt; nach **Restart** (Overview) ist man noch eingeloggt und die Links sind noch da.

Die Werte stehen nirgends im Repository. HTTPS endet bei Azure am Load Balancer; die App erkennt das über `WEBSITE_HOSTNAME` und erzeugt trotzdem `https://`-Links (#34).

### Automatische Auslieferung

`.github/workflows/deploy.yml` läuft bei jedem Merge in `main`: zuerst pytest, danach Auslieferung mit `azure/webapps-deploy`. Einrichtung einmalig:

1. Azure-Portal → Web App → **Overview** → **Download publish profile**.
2. GitHub → Repo → **Settings → Secrets and variables → Actions**:
   - Reiter **Secrets** → **New repository secret**: `AZURE_WEBAPP_PUBLISH_PROFILE` = ganzer Inhalt der heruntergeladenen Datei.
   - Reiter **Variables** → **New repository variable**: `AZURE_WEBAPP_NAME` = Name der Web App.
3. Die heruntergeladene Datei löschen (sie ist ein Zugangsschlüssel).

Branches: Auf `main` liegt nur, was ausgeliefert ist; `dev` sammelt getestete Features (Tests bei jedem PR auf `dev`, `.github/workflows/tests.yml`); entwickelt wird auf `feature/<nr>-<slug>` ab `dev`.
