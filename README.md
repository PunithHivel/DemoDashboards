# DemoDashboards

## Running the API

Activate your virtual environment (if needed), install dependencies, then start the FastAPI server:

```bash
uvicorn main:app --reload
```

The API will be available at `http://127.0.0.1:8000/`.

## Metrics Editor UI

Run the Streamlit app in a separate terminal:

```bash
streamlit run ui/metric_editor_app.py
```

The UI expects the API at `http://localhost:8000`. Override with `METRICS_EDITOR_API_URL` if needed.
