#!/usr/bin/env bash
# Сбор контактов косметологов через Google Maps.
# Использование: ./scripts/collect_cosmetologists.sh [город ...]
# Без аргументов — Москва и Санкт-Петербург. Лимит мест на город: LIMIT (default 50).
set -euo pipefail
cd "$(dirname "$0")/.."
LIMIT="${LIMIT:-100}"
if [ "$#" -gt 0 ]; then CITIES=("$@"); else CITIES=("Москва" "Санкт-Петербург"); fi
for city in "${CITIES[@]}"; do
  echo "=== Сбор: косметолог / $city (limit $LIMIT) ==="
  PYTHONPATH=. .venv/bin/python scripts/collect_google_maps.py "косметолог" "$city" --limit "$LIMIT"
done
