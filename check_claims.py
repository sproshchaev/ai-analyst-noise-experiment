"""Проверка каждого «инсайта» из ответов ассистента на тех же данных.

Каждое утверждение из data/claims.csv переводится в проверку:
  trend    - ранговая корреляция метрики с номером недели;
  lastweek - насколько неделя 12 выбивается из недель 1-11;
  pair     - парный тест «сегмент A против сегмента B» по 12 неделям;
  spike    - вероятность увидеть такой максимум среди 72 ячеек,
             если доля возвратов у всех одна (параметрический бутстрап).
p-value сравнивается с порогом Бонферрони 0,05/90: столько срезов
перебирает noise_check.py, и столько же видит аналитик, который смотрит
на всю таблицу.

Запуск: python3 check_claims.py
"""
import csv
import random
from collections import defaultdict

from noise_check import corr, ranks

N_SIM = 5000
SEED = 11
FAMILY = 90
ALPHA = 0.05


def load():
    rows = list(csv.DictReader(open("data/weekly_metrics.csv", encoding="utf-8")))
    by = defaultdict(dict)
    for r in rows:
        by[r["segment"]][int(r["week"])] = r
    return rows, by


def series(rows, by, seg, metric):
    if seg == "all":
        out = []
        for w in range(1, 13):
            out.append(sum(float(r[metric]) for r in rows if int(r["week"]) == w))
        return out
    return [float(by[seg][w][metric]) for w in range(1, 13)]


def p_trend(ys, rng):
    wr = ranks(list(range(12)))
    obs = abs(corr(wr, ranks(ys)))
    pool, hits = list(ys), 0
    for _ in range(N_SIM):
        rng.shuffle(pool)
        hits += abs(corr(wr, ranks(pool))) >= obs - 1e-12
    return (hits + 1) / (N_SIM + 1)


def p_lastweek(ys, week):
    # доля недель, которые отклоняются от среднего не меньше выбранной
    mean = sum(ys) / len(ys)
    d = abs(ys[week - 1] - mean)
    return sum(1 for y in ys if abs(y - mean) >= d - 1e-12) / len(ys)


def p_pair(a, b, rng):
    diffs = [x - y for x, y in zip(a, b)]
    obs = abs(sum(diffs))
    hits = 0
    for _ in range(N_SIM):
        s = sum(d if rng.random() < 0.5 else -d for d in diffs)
        hits += abs(s) >= obs - 1e-12
    return (hits + 1) / (N_SIM + 1)


def p_spike(rows, value, rng):
    orders = [int(r["orders"]) for r in rows]
    refunds = sum(round(float(r["refunds_pct"]) * int(r["orders"]) / 100) for r in rows)
    rate = refunds / sum(orders)
    hits = 0
    for _ in range(N_SIM):
        mx = max(100.0 * sum(1 for _ in range(n) if rng.random() < rate) / n for n in orders)
        hits += round(mx, 1) >= value
    return (hits + 1) / (N_SIM + 1)


def main():
    rows, by = load()
    rng = random.Random(SEED)
    claims = list(csv.DictReader(open("data/claims.csv", encoding="utf-8")))
    cache = {}
    threshold = ALPHA / FAMILY
    survived = defaultdict(int)
    total = defaultdict(int)
    print(f"threshold (Bonferroni 0.05/{FAMILY}): {threshold:.5f}")
    for c in claims:
        key = (c["test"], c["seg_a"], c["seg_b"], c["metric"], c["week"])
        if key not in cache:
            if c["test"] == "trend":
                p = p_trend(series(rows, by, c["seg_a"], c["metric"]), rng)
            elif c["test"] == "lastweek":
                p = p_lastweek(series(rows, by, c["seg_a"], c["metric"]), int(c["week"]))
            elif c["test"] == "pair":
                p = p_pair(series(rows, by, c["seg_a"], c["metric"]),
                           series(rows, by, c["seg_b"], c["metric"]), rng)
            else:
                v = float(by[c["seg_a"]][int(c["week"])][c["metric"]])
                p = p_spike(rows, v, rng)
            cache[key] = p
        p = cache[key]
        ok = p < threshold
        total[c["run"]] += 1
        survived[c["run"]] += ok
        print(f"  {c['run']:10} {c['framing']:7} {c['test']:8} p={p:.4f} {'SURVIVES' if ok else 'noise'}")
    print("summary:")
    for run in sorted(total):
        print(f"  {run:10} claims={total[run]} survived={survived[run]}")


if __name__ == "__main__":
    main()
