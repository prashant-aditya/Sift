FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim

WORKDIR /app

RUN addgroup --system sift && \
    adduser --system --ingroup sift --home /home/sift sift

# Ensure SentenceTransformer / huggingface_hub can cache model files
# when running as the non-root 'sift' user.
ENV HOME=/home/sift \
    HF_HOME=/home/sift/.cache/huggingface \
    HF_HUB_CACHE=/home/sift/.cache/huggingface/hub \
    TRANSFORMERS_CACHE=/home/sift/.cache/huggingface/transformers

COPY --from=builder /install /usr/local

COPY . .

RUN mkdir -p /app/chroma_data /home/sift/.cache/huggingface && \
    chown -R sift:sift /app /home/sift

USER sift

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
