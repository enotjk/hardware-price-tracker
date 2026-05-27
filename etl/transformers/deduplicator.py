"""
Deduplicator — убирает дубли перед вставкой в БД
Что делает:
- Проверяет нет ли уже записи с таким product_id + source_id за сегодня
- Убирает дубли внутри одного батча (один продукт может встретиться дважды)
- Оставляет запись с минимальной ценой если дубли есть
"""

import logging
from collections import defaultdict
from typing import Optional

log = logging.getLogger(__name__)


class Deduplicator:
    """
    Убирает дублирующиеся записи из батча перед вставкой в БД.

    Использование:
        dedup = Deduplicator()
        unique = dedup.deduplicate(normalized_records)
    """

    def deduplicate(self, records: list) -> list:
        """
        Убирает дубли внутри батча.
        Если один продукт встречается несколько раз —
        оставляет запись с минимальной ценой.

        Args:
            records: список NormalizedPrice

        Returns:
            список уникальных NormalizedPrice
        """
        if not records:
            return []

        # Группируем по ключу: product_id + source_id + date
        groups = defaultdict(list)
        for record in records:
            key = (record.product_id, record.source_id, record.date_id)
            groups[key].append(record)

        # Из каждой группы берём запись с минимальной ценой
        result = []
        duplicates = 0

        for key, group in groups.items():
            if len(group) > 1:
                duplicates += len(group) - 1
                best = min(group, key=lambda r: r.price_usd)
                log.debug(
                    f"Дубль: product={key[0][:8]}... source={key[1]} "
                    f"— оставляем цену {best.price_usd} USD из {len(group)} записей"
                )
                result.append(best)
            else:
                result.append(group[0])

        if duplicates:
            log.info(f"Дедупликация: убрано {duplicates} дублей, осталось {len(result)} записей")
        else:
            log.info(f"Дублей не найдено, {len(result)} записей готово к вставке")

        return result

    def filter_existing(self, records: list, conn) -> list:
        """
        Убирает записи которые уже есть в БД за сегодня.
        Проверяет таблицу fact_price_history.

        Args:
            records: список NormalizedPrice
            conn:    psycopg2 подключение к БД

        Returns:
            список записей которых ещё нет в БД
        """
        if not records:
            return []

        cursor = conn.cursor()

        # Получаем все product_id + source_id которые уже есть за сегодня
        cursor.execute("""
            SELECT DISTINCT product_id::text, source_id
            FROM fact_price_history
            WHERE date_id = CURRENT_DATE
        """)
        existing = {(str(row[0]), row[1]) for row in cursor.fetchall()}
        cursor.close()

        if not existing:
            log.info("В БД нет записей за сегодня — вставляем все")
            return records

        # Фильтруем — оставляем только новые
        new_records = [
            r for r in records
            if (r.product_id, r.source_id) not in existing
        ]

        skipped = len(records) - len(new_records)
        if skipped:
            log.info(f"Уже в БД за сегодня: {skipped} записей пропущено")

        return new_records