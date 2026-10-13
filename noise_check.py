"""Сколько «находок» даёт чистый шум, если перебрать все срезы.

Для каждого ряда сегмент x метрика считаются три проверки,
которые чаще всего стоят за фразами из отчётов:
  trend   - «метрика растёт/падает»: ранговая корреляция с номером недели,
            перестановочный тест по неделям одного сегмента;
  recent  - «в последние 4 недели просела/выросла»: последние 4 против первых 8;
  segment - «сегмент лучше/хуже остальных»: сегмент против остальных пяти.
Для долей (конверсия, возвраты) recent и segment сравнивают счётчики
(заказы и сессии, возвраты и заказы), а не проценты: у сегментов разный
трафик, и проценты по 3 500 и по 9 000 сессиям имеют разную точность.
Средний чек в segment сравнивается с учётом числа заказов.
Затем поправка Холма на все 90 проверок сразу.

Запуск: python3 noise_check.py data/weekly_metrics.csv
"""
import csv
import random
import sys

from stats import RATES, cells, corr, holm, ranks, two_props, weekly, norm_p

METRICS = ["sessions", "orders", "conversion_pct", "avg_check_rub", "revenue_rub", "refunds_pct"]
N_PERM = 5000
SEED = 7


def perm_p(stat_fn, values, rng, n_perm=N_PERM):
    observed = abs(stat_fn(values))
    hits = 0
    pool = list(values)
    for _ in range(n_perm):
        rng.shuffle(pool)
        if abs(stat_fn(pool)) >= observed - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def rate_totals(cs, metric):
    from stats import count
    num, den = RATES[metric]
    return sum(count(r, num) for r in cs), sum(count(r, den) for r in cs)


def p_check_segment(rows, seg):
    # средний чек ячейки ~ N(mu, sigma^2 / orders); sigma^2 оцениваем по всем ячейкам
    orders = [int(r["orders"]) for r in rows]
    avgs = [float(r["revenue_rub"]) / int(r["orders"]) for r in rows]
    mu = sum(float(r["revenue_rub"]) for r in rows) / sum(orders)
    sigma2 = sum(n * (a - mu) ** 2 for n, a in zip(orders, avgs)) / (len(rows) - 1)
    mine = [r for r in rows if r["segment"] == seg]
    rest = [r for r in rows if r["segment"] != seg]
    n1 = sum(int(r["orders"]) for r in mine)
    n2 = sum(int(r["orders"]) for r in rest)
    m1 = sum(float(r["revenue_rub"]) for r in mine) / n1
    m2 = sum(float(r["revenue_rub"]) for r in rest) / n2
    return m1 - m2, norm_p((m1 - m2) / (sigma2 * (1 / n1 + 1 / n2)) ** 0.5)


def run_tests(rows, rng, n_perm=N_PERM):
    segments = sorted({r["segment"] for r in rows})
    wr = ranks(list(range(12)))
    tests = []
    for seg in segments:
        for m in METRICS:
            ys = weekly(rows, seg, m)
            p_trend = perm_p(lambda v: corr(wr, ranks(v)), ys, rng, n_perm)
            tests.append(("trend", seg, m, round(corr(wr, ranks(ys)), 2), p_trend))
            diff = lambda v: sum(v[8:]) / 4 - sum(v[:8]) / 8
            if m in RATES:
                x1, n1 = rate_totals(cells(rows, seg, range(9, 13)), m)
                x2, n2 = rate_totals(cells(rows, seg, range(1, 9)), m)
                p_rec = two_props(x1, n1, x2, n2)
            else:
                p_rec = perm_p(diff, ys, rng, n_perm)
            tests.append(("recent", seg, m, round(diff(ys), 2), p_rec))
    for seg in segments:
        # объём трафика, заказов и выручки различается по построению - это не находка
        for m in ("conversion_pct", "avg_check_rub", "refunds_pct"):
            if m in RATES:
                x1, n1 = rate_totals(cells(rows, seg), m)
                rest = [r for r in rows if r["segment"] != seg]
                x2, n2 = rate_totals(rest, m)
                tests.append(("segment", seg, m, round(100 * (x1 / n1 - x2 / n2), 2),
                              two_props(x1, n1, x2, n2)))
            else:
                eff, p = p_check_segment(rows, seg)
                tests.append(("segment", seg, m, round(eff, 2), p))
    return tests


def main(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    tests = run_tests(rows, random.Random(SEED))
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
