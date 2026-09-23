#!/bin/sh
# Stores the Neon connection string (copied to the clipboard) in Secret Manager without
# printing it. Copy the string in Neon first, then run: sh infra/set-database-url.sh
set -eu
PROJECT="${1:-apelevate-cd6c73}"
URL="$(pbpaste | tr -d '\n')"
case "$URL" in
  postgresql://*|postgres://*) ;;
  *) echo "The clipboard doesn't hold a postgresql:// URL. Copy the connection string in Neon and try again." >&2; exit 1 ;;
esac
printf '%s' "$URL" | "$HOME/google-cloud-sdk/bin/gcloud" secrets versions add database-url --data-file=- --project "$PROJECT"
echo "Stored. (The value was not printed.)"
