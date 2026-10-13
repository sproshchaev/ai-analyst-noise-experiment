"""Калибровка тестов: как часто они дают p < 0,05 на таблицах без эффекта.

Генератор запускается со 100 новыми seed. На каждой таблице считаются
все 90 проверок noise_check.py и тесты утверждений из stats.py для
типичных утверждений ассистента. У откалиброванного теста доля p < 0,05
должна быть около 5%. Доверительный интервал на 100 таблицах широкий,
поэтому смотреть стоит на порядок: 3-8% нормально, 15% и выше - тест врёт.

Для скорости перестановок здесь 499, а симуляций максимума 199, а не 5000.

Запуск: python3 calibration.py
"""
import random
from collections import defaultdict

from generate import make_rows
from noise_check import run_tests
from stats import p_lastweek, p_pair, p_spike

TABLES = 100
FIRST_SEED = 1000


def main():
    hits, total = defaultdict(int), defaultdict(int)
    for i in range(TABLES):
        rows = make_rows(FIRST_SEED + i)
        rng = random.Random(i)
        for kind, seg, metric, _, p in run_tests(rows, rng, n_perm=499):
            key = f"sweep {kind:8} {'rate' if metric in ('conversion_pct', 'refunds_pct') else 'value'}"
            total[key] += 1
            hits[key] += p < 0.05
        claim_tests = {
            "claim lastweek rate ": p_lastweek(rows, "ios/new", "conversion_pct"),
            "claim lastweek value": p_lastweek(rows, "web/new", "revenue_rub"),
            "claim pair     rate ": p_pair(rows, "ios/returning", "web/returning", "conversion_pct", rng),
            "claim pair     rate2": p_pair(rows, "web/new", "web/returning", "refunds_pct", rng),
            # ассистент называет аномалией самую высокую ячейку таблицы
            "claim spike    max  ": p_spike(rows, max(float(r["refunds_pct"]) for r in rows), rng, n_sim=199),
        }
        for key, p in claim_tests.items():
            total[key] += 1
            hits[key] += p < 0.05
    print(f"null tables: {TABLES}, share of p<0.05 (target about 5%)")
    for key in sorted(total):
        print(f"  {key:24} tests={total[key]:5} share={100 * hits[key] / total[key]:5.1f}%")


if __name__ == "__main__":
    main()
