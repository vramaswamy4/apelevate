#!/bin/sh
# Stores the LLM API key (copied to the clipboard) in Secret Manager and in the local .env, so
# the live demo and `make eval` both use it. The key is never printed.
# Copy the key first, then run: sh infra/set-llm-key.sh
set -eu
PROJECT="${1:-apelevate-cd6c73}"
KEY="$(pbpaste | tr -d '\n ')"
case "$KEY" in
  gsk_*) ;;
  *) echo "The clipboard doesn't hold a Groq API key (they start with gsk_). Copy it and try again." >&2; exit 1 ;;
esac
printf '%s' "$KEY" | "$HOME/google-cloud-sdk/bin/gcloud" secrets versions add llm-api-key --data-file=- --project "$PROJECT"
ENV_FILE="$(dirname "$0")/../.env"
touch "$ENV_FILE"
grep -v '^LLM_API_KEY=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
printf 'LLM_API_KEY=%s\n' "$KEY" >> "$ENV_FILE.tmp"
mv "$ENV_FILE.tmp" "$ENV_FILE"
echo "Stored in Secret Manager and in .env. (The key was not printed.)"
