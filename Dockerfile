FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-finbert.txt ./
COPY deploy/requirements.txt deploy/requirements.txt
RUN pip install --no-cache-dir -r deploy/requirements.txt
COPY . .
# Explicit build-time asset preparation; inference never downloads missing files.
RUN python -m finscope.model_assets --prepare --acknowledge-model-licenses
EXPOSE 8501
CMD ["python","-m","streamlit","run","streamlit_app.py","--server.address=0.0.0.0","--server.port=8501"]
