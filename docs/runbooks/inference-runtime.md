# Local inference runtime runbook (laptop)

Decision D1: a **dedicated Docker inference service** on the laptop, separate
from the existing native Ollama service. Nothing here is deployed yet; run these
steps yourself on the laptop when you are ready. Do not stop or reconfigure the
existing Ollama service or its models.

## Prerequisites to confirm (read-only, before any change)

```bash
docker --version && docker compose version
nvidia-smi
# GPU access from containers (must print the GPU, not an error):
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi
df -h /var/lib/docker     # model weights need ~6-10 GB free
```

If the last command fails, install/configure NVIDIA Container Toolkit for the
Docker daemon first. That is a host change and needs your approval; stop here.

## 1. Start the isolated service

```bash
cd /path/to/beng-intellistore
docker compose -f compose.inference.yaml up -d
docker compose -f compose.inference.yaml ps
```

The service listens only on `127.0.0.1:11435`; it does not change the existing
Ollama service on `11434`.

## 2. Pull and pin candidates

At most two candidates are allowed. Both are permissively licensed and small
enough for an 8 GB GPU at Q4 quantization:

```bash
docker compose -f compose.inference.yaml exec inference ollama pull qwen2.5:7b-instruct
docker compose -f compose.inference.yaml exec inference ollama pull phi3.5:latest

# Record the exact digests next to this runbook (not in Git if you prefer):
docker compose -f compose.inference.yaml exec inference ollama list
```

`qwen2.5:7b-instruct` is Apache-2.0 (Hugging Face `Qwen/Qwen2.5-7B-Instruct`).
`phi3.5` is MIT (`microsoft/Phi-3.5-mini-instruct`). A mutable tag alone is not a
pin: keep the digest output with your release evidence.

## 3. Smoke a structured response

```bash
curl -s http://127.0.0.1:11435/api/generate -d '{
  "model": "qwen2.5:7b-instruct",
  "prompt": "Reply with JSON only: {\"classification\":\"spending\",\"confidence\":0.5,\"explanation\":\"x\"}",
  "format": "json",
  "stream": false
}'
```

Expect an HTTP 200 with a `response` field containing valid JSON. A running
container is not quality or fit evidence; record cold-load time and `nvidia-smi`
memory during this call.

## 4. Verify worker-container connectivity (advice still disabled)

Edit the root-owned worker environment file (created by the setup wizard), not
the checkout:

```bash
sudoedit /etc/beng-intellistore-worker/runtime.env
```

```
INFERENCE_URL=http://127.0.0.1:11435
INFERENCE_MODEL=qwen2.5:7b-instruct
INFERENCE_ENABLED=false
INFERENCE_TIMEOUT_SECONDS=10
INFERENCE_MAX_ATTEMPTS=2
INFERENCE_RETRY_DELAY_SECONDS=2
```

`INFERENCE_ENABLED=false` keeps suggestions off during ordinary processing: a URL
alone is a qualification setting, not permission to show unqualified advice. The
worker container uses host networking, so `127.0.0.1` reaches the service. Run the
explicit connectivity check:

```bash
sudo systemctl restart intellistore-worker.service
sudo docker compose --env-file /dev/null   --project-directory "$INTELLISTORE_COMPOSE_DIR" \
  -f "$INTELLISTORE_COMPOSE_DIR/compose.worker.yaml" \
  run --rm worker --check-inference
```

Expect JSON with a classification, model and prompt version. This request uses a
synthetic description and does not touch financial records. Imports and manual
review work throughout with advice disabled.

## 5. Qualify the candidate before enabling ordinary advice

Prepare at least 50 privately labelled ambiguous cases outside Git (see
`scripts/advice_benchmark.py --help`). Keep labels independent of the model. The
benchmark talks to the runtime directly; ordinary advice stays disabled.

```bash
python scripts/advice_benchmark.py \
  --cases ~/private/advice-heldout.json \
  --url http://127.0.0.1:11435 \
  --model qwen2.5:7b-instruct \
  --output ~/private/advice-report.json
```

Accept a candidate only when the script reports `meets_gates: true`
(≥90% correct among non-abstained suggestions, ≥50% coverage, ≥50 cases) and a
100-item warm run finishes within ten minutes. Otherwise keep
`INFERENCE_ENABLED=false`, use manual review and report the result for an
explicit scope decision.

## 6. Enable ordinary advice only after a recorded pass

Only after task08 is recorded as passed, set in the worker environment:

```
INFERENCE_ENABLED=true
```

Then restart only the worker and confirm a review item shows a source-linked
suggestion that changes nothing until accepted:

```bash
sudo systemctl restart intellistore-worker.service
sudo journalctl -u intellistore-worker.service -n 50 --no-pager
```

A failed attempt is retried up to `INFERENCE_MAX_ATTEMPTS` and is visible on the
review page. Advice never re-imports the statement.

## 7. Rollback

```bash
sudo sed -i 's/^INFERENCE_ENABLED=.*/INFERENCE_ENABLED=false/' \
  /etc/beng-intellistore-worker/runtime.env
sudo systemctl restart intellistore-worker.service
docker compose -f compose.inference.yaml stop
```

Stopping the inference service never affects ordinary browsing, review or
previously imported figures.
