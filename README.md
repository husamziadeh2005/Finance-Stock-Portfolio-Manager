# Finora

A responsive Flask + SQLite stock portfolio simulator.

## Features
- Responsive portfolio dashboard
- Live stock quote lookup
- Buy and sell simulation
- Portfolio allocation view
- Recent activity and searchable transaction history
- Add-cash workflow with quick amounts
- Responsive navigation
- Light/dark theme toggle saved in the browser
- Account registration/login with hashed passwords
- SQLite persistence

## Run in VS Code

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open `http://127.0.0.1:5000`.

For a custom session secret:

```bash
export SECRET_KEY="your-random-secret"
python3 app.py
```
