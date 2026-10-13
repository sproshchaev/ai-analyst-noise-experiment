"""Позитивный контроль: те же проверки и тот же порог ловят настоящие эффекты.

Без этого шага «ни одно утверждение не выжило» ничего не доказывает:
проверка могла бы быть просто слишком слабой. Здесь в копию генератора
закладываются четыре эффекта того же вида, что утверждения ассистента,
и для каждого запускается та же проверка из stats.py.

  1. lastweek: конверсия ios/new на неделе 12 падает с 3,1% до 2,0%;
  2. pair:     у ios/returning конверсия 3,7% против 3,1% у всех остальных;
  3. trend:    трафик android/new растёт на 4% в неделю;
  4. spike:    доля возвратов ios/new на неделе 11 равна 25%.

Запуск: python3 power_check.py
"""
import random

import generate as g
from stats import run_test

SEED = 20261014
THRESHOLD = 0.05 / 90


def planted_rows():
    rng = random.Random(SEED)
    rows = []
    for week in range(1, g.WEEKS + 1):
        for seg, traffic in g.SEGMENTS.items():
            if seg == "android/new":
                traffic = traffic * 1.04 ** (week - 1)
            p_order = g.P_ORDER
            if seg == "ios/new" and week == 12:
                p_order = 0.020
            if seg == "ios/returning":
                p_order = 0.037
            p_refund = 0.25 if (seg == "ios/new" and week == 11) else g.P_REFUND
            sessions = g.normal_approx_poisson(rng, traffic)
            orders = g.binomial(rng, sessions, p_order)
            checks = [max(300.0, rng.gauss(g.CHECK_LOCATION, g.CHECK_SD)) for _ in range(orders)]
            revenue = round(sum(checks))
            refunds = g.binomial(rng, orders, p_refund)
            rows.append({
                "week": str(week), "segment": seg, "sessions": str(sessions),
                "orders": str(orders),
                "conversion_pct": str(round(100.0 * orders / sessions, 2)),
                "avg_check_rub": str(round(revenue / orders)),
                "revenue_rub": str(revenue),
                "refunds_pct": str(round(100.0 * refunds / orders, 1)),
            })
    return rows


PLANTED = [
    ("lastweek", "ios/new", "", "conversion_pct", "12"),
    ("pair", "ios/returning", "web/returning", "conversion_pct", ""),
    ("trend", "android/new", "", "sessions", ""),
    ("spike", "ios/new", "", "refunds_pct", "11"),
]


def main():
    rows = planted_rows()
    rng = random.Random(3)
    print(f"threshold (Bonferroni 0.05/90): {THRESHOLD:.5f}")
    caught = 0
    for test in PLANTED:
        p = run_test(rows, *test, rng)
        ok = p < THRESHOLD
        caught += ok
        print(f"  {test[0]:8} {test[1]:14} {test[3]:15} p={p:.6f} {'CAUGHT' if ok else 'MISSED'}")
    print(f"caught {caught} of {len(PLANTED)} planted effects")


if __name__ == "__main__":
    main()
