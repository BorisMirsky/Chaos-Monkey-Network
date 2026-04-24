import re
import logging
from typing import Optional, Tuple, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MatchRule:
    """Правило для фильтрации пакетов"""
    target_port: Optional[int] = None      # Целевой порт (сервера)
    client_port: Optional[int] = None      # Порт клиента
    contains: Optional[str] = None         # Подстрока в данных
    regex: Optional[str] = None            # Регулярное выражение
    direction: Optional[str] = None        # "client->target" или "target->client"


class RuleEngine:
    """Движок правил для применения хаоса только к определённым пакетам"""

    def __init__(self, rules: Optional[List[MatchRule]] = None):
        self.rules = rules or []

    def add_rule(self, rule: MatchRule) -> None:
        """Добавить правило"""
        self.rules.append(rule)
        logger.debug(f"Добавлено правило: {rule}")

    def clear_rules(self) -> None:
        """Очистить все правила"""
        self.rules.clear()
        logger.debug("Все правила удалены")

    def should_apply_chaos(self, data: bytes, direction: str, 
                            target_port: int, client_port: int) -> bool:
        """
        Проверить, нужно ли применять хаос к данному пакету.
        
        Args:
            data: Данные пакета
            direction: Направление ("client->target" или "target->client")
            target_port: Порт целевого сервера
            client_port: Порт клиента
        
        Returns:
            True — хаос нужно применить, False — пропустить без изменений
        """
        # Если нет правил — применяем хаос ко всем пакетам
        if not self.rules:
            return True

        # Проверяем каждое правило (достаточно одного совпадения)
        for rule in self.rules:
            if self._match_rule(rule, data, direction, target_port, client_port):
                logger.debug(f"Пакет соответствует правилу: {rule}")
                return True

        logger.debug("Пакет не соответствует ни одному правилу — пропускаем без хаоса")
        return False

    def _match_rule(self, rule: MatchRule, data: bytes, direction: str,
                    target_port: int, client_port: int) -> bool:
        """Проверить, соответствует ли пакет одному правилу"""
        
        # Проверка направления
        if rule.direction and rule.direction != direction:
            return False

        # Проверка порта сервера
        if rule.target_port and rule.target_port != target_port:
            return False

        # Проверка порта клиента
        if rule.client_port and rule.client_port != client_port:
            return False

        # Проверка содержимого (только если данные есть)
        if data and (rule.contains or rule.regex):
            try:
                # Пробуем декодировать как текст
                text = data.decode('utf-8', errors='ignore')
                
                # Проверка на подстроку
                if rule.contains and rule.contains not in text:
                    return False
                
                # Проверка на регулярное выражение
                if rule.regex and not re.search(rule.regex, text):
                    return False
            except Exception as e:
                logger.debug(f"Ошибка при проверке содержимого: {e}")
                return False

        return True


# Предустановленные правила для удобства
class PresetRules:
    """Набор предустановленных правил для常见 сценариев"""
    
    @staticmethod
    def only_http_requests() -> List[MatchRule]:
        """Применять хаос только к HTTP запросам (GET, POST, PUT, DELETE)"""
        return [
            MatchRule(
                direction="client->target",
                regex=r"^(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)"
            )
        ]
    
    @staticmethod
    def only_sql_select() -> List[MatchRule]:
        """Применять хаос только к SELECT запросам"""
        return [
            MatchRule(
                direction="client->target",
                contains="SELECT",
                target_port=5432  # PostgreSQL по умолчанию
            )
        ]
    
    @staticmethod
    def only_target_port(port: int) -> List[MatchRule]:
        """Применять хаос только к пакетам на指定 порт"""
        return [MatchRule(target_port=port)]