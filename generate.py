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
CHECK_MEAN = 3200.0    # средний чек, руб.
CHECK_SD = 1900.0      # разброс чека одного заказа
P_REFUND = 0.06        # доля возвратов


def poisson(rng, lam):
    # нормальное приближение достаточно для lam в тысячах
    return max(0, round(rng.gauss(lam, lam ** 0.5)))


def binomial(rng, n, p):
    return sum(1 for _ in range(n) if rng.random() < p)


def main():
    rng = random.Random(SEED)
    print("week,segment,sessions,orders,conversion_pct,avg_check_rub,revenue_rub,refunds_pct")
    for week in range(1, WEEKS + 1):
        for seg, traffic in SEGMENTS.items():
            sessions = poisson(rng, traffic)
            orders = binomial(rng, sessions, P_ORDER)
            checks = [max(300.0, rng.gauss(CHECK_MEAN, CHECK_SD)) for _ in range(orders)]
            revenue = round(sum(checks))
            avg_check = round(revenue / orders) if orders else 0
            refunds = binomial(rng, orders, P_REFUND)
            conv = round(100.0 * orders / sessions, 2) if sessions else 0.0
            ref_pct = round(100.0 * refunds / orders, 1) if orders else 0.0
            print(f"{week},{seg},{sessions},{orders},{conv},{avg_check},{revenue},{ref_pct}")


if __name__ == "__main__":
    main()
