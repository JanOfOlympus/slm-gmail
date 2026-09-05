# slm-gmail

## Setup

### 1. Create python virsual env
- py -m venv .venv
- .venv\Scripts\Activate.ps1
- deactivate

### 2. Install required package
```bash
pip install -r requirements.txt
```

### 3. Gmail API access
1. Go to https://console.cloud.google.com/ and create (or pick) a project
2. Enable the **Gmail API** for that project
3. Create **OAuth 2.0 credentials** -> Application type: **Desktop app**
4. Download the JSON and save it as `credentials.json` in this folder
5. First run opens a browser to authorize; after that a `token.json` is cached, so
   you won't need to re-auth every time (useful before a live demo -- do this ahead of time).

### 4. Run
```bash
streamlit run app.py
```

## streamlit
- streamlit run app.py

## model useds
- command: ollama pull <models>
- decoding model: qwen2.5:3b
- embedding model: nomic-embed-text

## vector store
- chroma