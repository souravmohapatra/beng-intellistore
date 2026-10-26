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

At most two candidates are allowed. These are candidates, not qualified models:
license identity is recorded below, but memory fit, throughput and structured
response quality must be measured on the laptop before enablement.

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
INFERENCE_PROMPT_VERSION=v1
INFERENCE_ENABLED=false
INFERENCE_TIMEOUT_SECONDS=10
INFERENCE_MAX_ATTEMPTS=2
INFERENCE_RETRY_DELAY_SECONDS=2
ADVICE_MAX_ROWS=25
```

`INFERENCE_ENABLED=false` keeps suggestions off during ordinary processing: a URL
alone is a qualification setting, not permission to show unqualified advice. The
worker container uses host networking, so `127.0.0.1` reaches the service. Run the
explicit connectivity check:

```bash
sudo bash -c '
  set -a; . /etc/beng-intellistore-worker/runtime.env; set +a
  exec docker --host="$DOCKER_HOST" compose --env-file /dev/null \
    --project-directory "$INTELLISTORE_COMPOSE_DIR" \
    -f "$INTELLISTORE_COMPOSE_DIR/compose.worker.yaml" \
    run --rm worker --check-inference
'
```

Expect JSON with a classification, model and prompt version. This request uses a
synthetic description and does not touch financial records. Imports and manual
review work throughout with advice disabled.

## 5. Qualify the candidate before enabling ordinary advice

Prepare at least 50 privately labelled ambiguous cases outside Git (see
`scripts/advice_benchmark.py --help`). Keep labels independent of the model. The
benchmark talks to the runtime directly; ordinary advice stays disabled.

The quality and timing gates are reported separately, and the command exits
non-zero until both pass. Timing needs its own warm workload of at least 100
unresolved items (`--warm-cases`), so a cold model load or the labelled quality
run is never counted as warm throughput. Load the model first (step 3) before
starting the warm run.

```bash
# Replace /path/to/private-evaluation with the private label/report directory.
# It must be accessible and writable by the configured worker uid/gid.
sudo bash -c '
  set -a; . /etc/beng-intellistore-worker/runtime.env; set +a
  exec docker --host="$DOCKER_HOST" compose --env-file /dev/null \
    --project-directory "$INTELLISTORE_COMPOSE_DIR" \
    -f "$INTELLISTORE_COMPOSE_DIR/compose.worker.yaml" \
    run --rm --entrypoint python \
    --volume /path/to/private-evaluation:/evaluation worker \
    scripts/advice_benchmark.py \
    --cases /evaluation/advice-heldout.json \
    --warm-cases /evaluation/advice-warm-100.json \
    --url http://127.0.0.1:11435 \
    --model qwen2.5:7b-instruct \
    --prompt-version v1 \
    --output /evaluation/advice-report.json
'
```

`--prompt-version` defaults to `INFERENCE_PROMPT_VERSION`, so the benchmark
matches the version production suggestions will record; pass it explicitly to
evaluate a different prompt. Accept a candidate only when the script reports
`meets_gates: true`, meaning
`meets_quality_gate: true` (≥90% correct among non-abstained suggestions, ≥50%
coverage, ≥50 cases) **and** `meets_time_gate: true` (≥100 warm items actually
processed with no failures within ten minutes; failed items are not counted as
throughput). The process exit code is 0 only when both gates pass. Otherwise keep
`INFERENCE_ENABLED=false`, use manual review and report the result for an
explicit scope decision.

## 6. Enable ordinary advice only after a recorded pass

Only after task08 is recorded as passed, set the flag on **both machines**:
`/etc/beng-intellistore/runtime.env` on the mini-PC and
`/etc/beng-intellistore-worker/runtime.env` on the laptop. Use `sudoedit`; never
print the files because they contain credentials.

```
INFERENCE_ENABLED=true
```

Restart each service on its own machine, so Compose recreates the containers
with the updated environment. The app enables the request UI; the worker enables
inference. Enabling only one is not a complete cutover.

```bash
# On beng-mini-pc:
sudo systemctl restart intellistore-app.service
# On beng-laptop:
sudo systemctl restart intellistore-worker.service
sudo journalctl -u intellistore-worker.service -n 50 --no-pager
```

Then request advice on an unresolved review item and verify the source-linked
suggestion changes nothing until explicitly accepted.

A failed attempt is retried up to `INFERENCE_MAX_ATTEMPTS` (hard-capped at 2)
and is visible on the review page. Every attempt renews the job lease before
calling the model, and the request timeout is capped by the remaining lease
(and by `INFERENCE_TIMEOUT_SECONDS`, whichever is smaller); a retry delay that
cannot fit the remaining lease is skipped, and `INFERENCE_RETRY_DELAY_SECONDS`
is capped at 10 s. Independent advice requests use their own claim lease the
same way. A slow or timing-out row therefore cannot outlive the lease, and at
most `ADVICE_MAX_ROWS` unresolved rows are advised per import. Advice never
re-imports the statement.

## 7. Rollback

Set `INFERENCE_ENABLED=false` using `sudoedit` in **both** runtime files, then
restart the corresponding services on their respective machines:

```bash
# On beng-mini-pc:
sudo systemctl restart intellistore-app.service
# On beng-laptop:
sudo systemctl restart intellistore-worker.service
docker compose -f compose.inference.yaml stop
```

Stopping the inference service never affects ordinary browsing, review or
previously imported figures.
