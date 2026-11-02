# HR Quiz App

A simple Flask quiz app for deployment on Render.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open: http://localhost:5000

## Deploy on Render

1. Create a new Web Service in Render.
2. Connect this repository.
3. Keep the default root directory as the repo root.
4. Set the start command to:

```bash
gunicorn app:app
```

5. Add environment variable if needed:
   - `PORT` is automatically provided by Render.

## Files

- `app.py` – Flask app and submission logic
- `templates/index.html` – quiz page
- `results.json` – created automatically on first submit
