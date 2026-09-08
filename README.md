# Ragled

## Avvio locale

Installa le dipendenze del bridge Python e avvia il backend:

```bash
./venv/bin/pip install -r requirements.txt
./venv/bin/python api_server.py
```

In un secondo terminale avvia Next.js:

```bash
npm run dev
```

La Home invia le domande a `POST http://127.0.0.1:8000/api/chat`, che usa lo stesso `run_pipeline` eseguito dai test. Per lavorare senza backend si può impostare `NEXT_PUBLIC_USE_MOCK_DATA=true`.