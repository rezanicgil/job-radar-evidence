FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=7860 HOME=/home/app
RUN useradd -m -u 1000 app
WORKDIR /home/app
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.7.0 && pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app scripts/ scripts/
COPY --chown=app:app templates/ templates/
COPY --chown=app:app reports/ reports/
USER app
RUN python -c "import sys; sys.path.insert(0,'scripts'); from train_smoke import BASE, REVISION; from transformers import AutoModel, AutoTokenizer; AutoTokenizer.from_pretrained(BASE, revision=REVISION); AutoModel.from_pretrained(BASE, revision=REVISION)"
ENV HF_HUB_OFFLINE=1
EXPOSE 7860
CMD ["python", "scripts/demo.py"]
