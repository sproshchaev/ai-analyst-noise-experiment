"""Проверка каждого «инсайта» из ответов ассистента на тех же данных.

Каждое утверждение из data/claims.csv переводится в одну из проверок
модуля stats.py: trend, lastweek, pair или spike.
p-value сравнивается с порогом Бонферрони 0,05/90: столько срезов
перебирает noise_check.py, и примерно столько видит аналитик,
который смотрит на всю таблицу.

Что эти же проверки ловят настоящие эффекты, показывает power_check.py.

Запуск: python3 check_claims.py
"""
import csv
import random
from collections import defaultdict

from stats import run_test

SEED = 11
FAMILY = 90
ALPHA = 0.05


def main():
    rows = list(csv.DictReader(open("data/weekly_metrics.csv", encoding="utf-8")))
    claims = list(csv.DictReader(open("data/claims.csv", encoding="utf-8")))
    rng = random.Random(SEED)
    threshold = ALPHA / FAMILY
    cache = {}
    survived, total = defaultdict(int), defaultdict(int)
    print(f"threshold (Bonferroni 0.05/{FAMILY}): {threshold:.5f}")
    for c in claims:
        key = (c["test"], c["seg_a"], c["seg_b"], c["metric"], c["week"])
        if key not in cache:
            cache[key] = run_test(rows, *key, rng)
        p = cache[key]
        ok = p < threshold
        total[c["run"]] += 1
        survived[c["run"]] += ok
        target = c["seg_a"] + (" vs " + c["seg_b"] if c["seg_b"] else "")
        print(f"  {c['run']:10} {c['test']:8} {target:30} {c['metric']:15} "
              f"p={p:.4f} {'SURVIVES' if ok else 'noise'}")
    print("summary:")
    for run in sorted(total):
        print(f"  {run:10} claims={total[run]} survived={survived[run]}")
    print(f"  total      claims={sum(total.values())} survived={sum(survived.values())}")


if __name__ == "__main__":
    main()
