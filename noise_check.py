"""Сколько «находок» даёт чистый шум, если перебрать все срезы.

Для каждого ряда сегмент x метрика считаются три проверки,
которые чаще всего стоят за фразами из отчётов:
  trend  - «метрика растёт/падает»: ранговая корреляция с номером недели;
  recent - «в последние 4 недели просела/выросла»: последние 4 против первых 8;
  segment - «сегмент лучше/хуже остальных»: среднее сегмента против остальных.
p-value - перестановочным тестом, затем поправка Холма на все проверки сразу.

Запуск: python3 noise_check.py data/weekly_metrics.csv
"""
import csv
import random
import sys

METRICS = ["sessions", "orders", "conversion_pct", "avg_check_rub", "revenue_rub", "refunds_pct"]
N_PERM = 5000
SEED = 7


def ranks(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2.0
        i = j + 1
    return r


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a) ** 0.5
    vb = sum((y - mb) ** 2 for y in b) ** 0.5
    return cov / (va * vb) if va and vb else 0.0


def perm_p(stat_fn, values, rng):
    observed = abs(stat_fn(values))
    hits = 0
    pool = list(values)
    for _ in range(N_PERM):
        rng.shuffle(pool)
        if abs(stat_fn(pool)) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (N_PERM + 1)


def holm(pvals):
    m = len(pvals)
    idx = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(idx):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    segments = sorted({r["segment"] for r in rows})
    rng = random.Random(SEED)
    tests = []
    for seg in segments:
        sr = sorted((r for r in rows if r["segment"] == seg), key=lambda r: int(r["week"]))
        weeks = [float(r["week"]) for r in sr]
        wr = ranks(weeks)
        for m in METRICS:
            ys = [float(r[m]) for r in sr]
            p_trend = perm_p(lambda v: corr(wr, ranks(v)), ys, rng)
            tests.append(("trend", seg, m, round(corr(wr, ranks(ys)), 2), p_trend))
            diff = lambda v: sum(v[8:]) / 4 - sum(v[:8]) / 8
            p_rec = perm_p(diff, ys, rng)
            tests.append(("recent", seg, m, round(diff(ys), 2), p_rec))
    for seg in segments:
        for m in METRICS:
            mine = [float(r[m]) for r in rows if r["segment"] == seg]
            other = [float(r[m]) for r in rows if r["segment"] != seg]
            k = len(mine)
            allv = mine + other
            d = lambda v: sum(v[:k]) / k - sum(v[k:]) / (len(v) - k)
            # объём трафика различается по построению - это не находка
            if m in ("sessions", "orders", "revenue_rub"):
                continue
            tests.append(("segment", seg, m, round(d(allv), 2), perm_p(d, allv, rng)))
    adj = holm([t[4] for t in tests])
    raw_hits = [t for t in tests if t[4] < 0.05]
    holm_hits = [t for t, a in zip(tests, adj) if a < 0.05]
    print(f"tests: {len(tests)}")
    print(f"raw p<0.05: {len(raw_hits)}")
    print(f"expected by chance: {0.05 * len(tests):.1f}")
    print(f"after Holm p<0.05: {len(holm_hits)}")
    for t in sorted(raw_hits, key=lambda t: t[4]):
        print(f"  {t[0]:7} {t[1]:18} {t[2]:15} effect={t[3]:>9} p={t[4]:.4f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/weekly_metrics.csv")
