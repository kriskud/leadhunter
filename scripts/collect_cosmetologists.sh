#!/usr/bin/env bash
# Сбор контактов косметологов: 2GIS (если задан DGIS_API_KEY) + Google Maps.
# Использование: ./scripts/collect_cosmetologists.sh [город ...]
# Без аргументов — Москва и Санкт-Петербург. Лимит мест на город: LIMIT (default 100).
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT="${LIMIT:-100}"
if [ "$#" -gt 0 ]; then CITIES=("$@"); else CITIES=("Москва" "Санкт-Петербург"); fi
HAS_DGIS_KEY="$(grep -E '^DGIS_API_KEY=.+' .env || true)"
for city in "${CITIES[@]}"; do
  echo "=== Сбор: косметолог / $city (limit $LIMIT) ==="
  PYTHONPATH=. .venv/bin/python scripts/collect_google_maps.py "косметолог" "$city" --limit "$LIMIT"
  if [ -n "$HAS_DGIS_KEY" ]; then
    PYTHONPATH=. .venv/bin/python scripts/collect_dgis.py "косметолог" "$city" --limit "$LIMIT"
  else
    echo "(2GIS пропущен: DGIS_API_KEY не задан в .env)"
  fi
done
