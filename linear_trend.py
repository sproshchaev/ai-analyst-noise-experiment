"""Линейный тренд конверсии: t-тест наклона регрессии по 12 неделям.

Это та же проверка, которую ассистент выполнил в скептических прогонах
(«линейный тренд конверсии статистически незначим»), повторённая независимо.
Она не участвует в вердикте по утверждениям: в check_claims.py тренды
проверяются ранговой корреляцией, без предположения о линейности.

Запуск: python3 linear_trend.py
"""
import csv
import math

from stats import t_p, weekly


def slope_p(ys):
    n = len(ys)
    xs = list(range(1, n + 1))
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    res = [y - (my + b * (x - mx)) for x, y in zip(xs, ys)]
    s2 = sum(r * r for r in res) / (n - 2)
    return b, t_p(b / math.sqrt(s2 / sxx), n - 2)


def main():
    rows = list(csv.DictReader(open("data/weekly_metrics.csv", encoding="utf-8")))
    for seg in ["all"] + sorted({r["segment"] for r in rows}):
        b, p = slope_p(weekly(rows, seg, "conversion_pct"))
        print(f"  {seg:18} slope={b:+.4f} p.p./week p={p:.3f}")


if __name__ == "__main__":
    main()
