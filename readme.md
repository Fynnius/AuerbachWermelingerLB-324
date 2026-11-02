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

Produktiv (Render): `gunicorn "drop:create_app()"`.

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
