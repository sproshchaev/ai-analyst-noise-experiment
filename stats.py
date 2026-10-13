"""Проверки, общие для check_claims.py и power_check.py.

Каждая функция принимает строки таблицы (список словарей из CSV)
и возвращает p-value двустороннего теста.
  trend    - ранговая корреляция метрики с номером недели, перестановочный тест;
  lastweek - выбивается ли неделя 12 из недель 1-11:
             для долей (конверсия, возвраты) - сравнение двух долей по счётчикам,
             для остальных метрик - t-интервал предсказания по неделям 1-11;
  pair     - сегмент A против сегмента B за 12 недель:
             для долей - сравнение двух долей по суммарным счётчикам,
             для остальных метрик - парный перестановочный тест по неделям;
  spike    - вероятность увидеть такой максимум доли возвратов среди всех ячеек,
             если доля возвратов у всех одна (параметрический бутстрап).
"""
import math
import random

from noise_check import corr, ranks

N_SIM = 5000
RATES = {
    # метрика: (числитель, знаменатель)
    "conversion_pct": ("orders", "sessions"),
    "refunds_pct": ("refunds", "orders"),
}


def refunds(r):
    return round(float(r["refunds_pct"]) * int(r["orders"]) / 100)


def count(r, name):
    return refunds(r) if name == "refunds" else int(r[name])


def cells(rows, seg, weeks=range(1, 13)):
    ws = set(weeks)
    return [r for r in rows if int(r["week"]) in ws and (seg == "all" or r["segment"] == seg)]


def weekly(rows, seg, metric):
    out = []
    for w in range(1, 13):
        cs = cells(rows, seg, [w])
        if metric in RATES:
            num, den = RATES[metric]
            out.append(100.0 * sum(count(r, num) for r in cs) / sum(count(r, den) for r in cs))
        elif metric == "avg_check_rub" and seg == "all":
            out.append(sum(float(r["revenue_rub"]) for r in cs) / sum(int(r["orders"]) for r in cs))
        elif seg == "all" or metric in ("sessions", "orders", "revenue_rub"):
            out.append(sum(float(r[metric]) for r in cs))
        else:
            out.append(float(cs[0][metric]))
    return out


def norm_p(z):
    return math.erfc(abs(z) / math.sqrt(2))


def t_p(t, df):
    # двусторонний p для t-распределения численным интегрированием плотности
    c = math.gamma((df + 1) / 2) / (math.sqrt(df * math.pi) * math.gamma(df / 2))
    steps, top = 20000, abs(t)
    h = top / steps
    area = sum(c * (1 + ((i + 0.5) * h) ** 2 / df) ** (-(df + 1) / 2) for i in range(steps)) * h
    return max(0.0, 2 * (0.5 - area))


def two_props(x1, n1, x2, n2):
    p = (x1 + x2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return norm_p((x1 / n1 - x2 / n2) / se) if se else 1.0


def totals(cs, metric):
    num, den = RATES[metric]
    return sum(count(r, num) for r in cs), sum(count(r, den) for r in cs)


def p_trend(rows, seg, metric, rng):
    ys = weekly(rows, seg, metric)
    wr = ranks(list(range(12)))
    obs = abs(corr(wr, ranks(ys)))
    pool, hits = list(ys), 0
    for _ in range(N_SIM):
        rng.shuffle(pool)
        hits += abs(corr(wr, ranks(pool))) >= obs - 1e-12
    return (hits + 1) / (N_SIM + 1)


def p_lastweek(rows, seg, metric, week=12):
    if metric in RATES:
        x1, n1 = totals(cells(rows, seg, [week]), metric)
        x2, n2 = totals(cells(rows, seg, [w for w in range(1, 13) if w != week]), metric)
        return two_props(x1, n1, x2, n2)
    ys = weekly(rows, seg, metric)
    rest = [y for i, y in enumerate(ys, 1) if i != week]
    m = sum(rest) / len(rest)
    sd = math.sqrt(sum((y - m) ** 2 for y in rest) / (len(rest) - 1))
    return t_p((ys[week - 1] - m) / (sd * math.sqrt(1 + 1 / len(rest))), len(rest) - 1)


def p_pair(rows, seg_a, seg_b, metric, rng):
    if metric in RATES:
        x1, n1 = totals(cells(rows, seg_a), metric)
        x2, n2 = totals(cells(rows, seg_b), metric)
        return two_props(x1, n1, x2, n2)
    diffs = [a - b for a, b in zip(weekly(rows, seg_a, metric), weekly(rows, seg_b, metric))]
    obs, hits = abs(sum(diffs)), 0
    for _ in range(N_SIM):
        hits += abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= obs - 1e-12
    return (hits + 1) / (N_SIM + 1)


def p_spike(rows, value, rng):
    orders = [int(r["orders"]) for r in rows]
    rate = sum(refunds(r) for r in rows) / sum(orders)
    hits = 0
    for _ in range(N_SIM):
        mx = max(100.0 * sum(1 for _ in range(n) if rng.random() < rate) / n for n in orders)
        hits += round(mx, 1) >= value
    return (hits + 1) / (N_SIM + 1)


def run_test(rows, test, seg_a, seg_b, metric, week, rng):
    if test == "trend":
        return p_trend(rows, seg_a, metric, rng)
    if test == "lastweek":
        return p_lastweek(rows, seg_a, metric, int(week))
    if test == "pair":
        return p_pair(rows, seg_a, seg_b, metric, rng)
    cell = cells(rows, seg_a, [int(week)])[0]
    return p_spike(rows, float(cell[metric]), rng)
