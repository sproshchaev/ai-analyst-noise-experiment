"""Генератор недельных метрик интернет-магазина без единого эффекта.

Все шесть сегментов живут по одним и тем же параметрам: одинаковая
вероятность заказа, одинаковый средний чек, одинаковая доля возвратов.
Различается только объём трафика. Никаких трендов по неделям нет.
Любой «тренд» или «разница между сегментами» в этих данных - шум.

Запуск: python3 generate.py > data/weekly_metrics.csv
"""
import random

SEED = 20261013
WEEKS = 12
SEGMENTS = {
    # сегмент: средний трафик за неделю
    "web/new": 9000,
    "web/returning": 6000,
    "ios/new": 4000,
    "ios/returning": 5000,
    "android/new": 5000,
    "android/returning": 3500,
}
P_ORDER = 0.031        # вероятность заказа на сессию, у всех одна
CHECK_LOCATION = 3200.0    # среднее нормального распределения чека до отсечения снизу на 300 руб.;
                       # после отсечения матожидание около 3 252 руб.
CHECK_SD = 1900.0      # разброс чека одного заказа
P_REFUND = 0.06        # доля возвратов
HEADER = ["week", "segment", "sessions", "orders", "conversion_pct",
          "avg_check_rub", "revenue_rub", "refunds_pct"]


def normal_approx_poisson(rng, lam):
    # не выборка из распределения Пуассона, а его нормальное приближение:
    # для lam в тысячах разница несущественна
    return max(0, round(rng.gauss(lam, lam ** 0.5)))


def binomial(rng, n, p):
    return sum(1 for _ in range(n) if rng.random() < p)


def make_rows(seed=SEED):
    rng = random.Random(seed)
    rows = []
    for week in range(1, WEEKS + 1):
        for seg, traffic in SEGMENTS.items():
            sessions = normal_approx_poisson(rng, traffic)
            orders = binomial(rng, sessions, P_ORDER)
            checks = [max(300.0, rng.gauss(CHECK_LOCATION, CHECK_SD)) for _ in range(orders)]
            revenue = round(sum(checks))
            avg_check = round(revenue / orders) if orders else 0
            refunds = binomial(rng, orders, P_REFUND)
            conv = round(100.0 * orders / sessions, 2) if sessions else 0.0
            ref_pct = round(100.0 * refunds / orders, 1) if orders else 0.0
            rows.append({"week": str(week), "segment": seg, "sessions": str(sessions),
                         "orders": str(orders), "conversion_pct": str(conv),
                         "avg_check_rub": str(avg_check), "revenue_rub": str(revenue),
                         "refunds_pct": str(ref_pct)})
    return rows


def main():
    print(",".join(HEADER))
    for r in make_rows():
        print(",".join(r[h] for h in HEADER))


if __name__ == "__main__":
    main()
