#!/usr/bin/env bash
# Собирает всё с нуля и сверяет вывод с эталоном expected.txt.
# Код выхода 1, если данные или результаты разошлись.
set -euo pipefail
cd "$(dirname "$0")"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

python3 generate.py > "$tmp/weekly_metrics.csv"
if ! cmp -s "$tmp/weekly_metrics.csv" data/weekly_metrics.csv; then
  echo "data/weekly_metrics.csv не совпадает с генератором" >&2
  exit 1
fi

{
  echo "== noise_check.py =="
  python3 noise_check.py data/weekly_metrics.csv
  echo "== check_claims.py =="
  python3 check_claims.py
  echo "== linear_trend.py =="
  python3 linear_trend.py
  echo "== power_check.py =="
  python3 power_check.py
  echo "== calibration.py =="
  python3 calibration.py
} > "$tmp/actual.txt"

if diff -u expected.txt "$tmp/actual.txt"; then
  echo "OK: результаты совпадают с expected.txt"
else
  echo "Результаты разошлись с expected.txt" >&2
  exit 1
fi
