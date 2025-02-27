from typing import TYPE_CHECKING, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry, get_event_type_identifier
from rotkehlchen.accounting.structures.evm_event import EvmEvent
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, EventsAccountantCallback
from rotkehlchen.db.accounting_rules import DBAccountingRules
from rotkehlchen.db.filtering import AccountingRulesFilterQuery

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
    from rotkehlchen.db.dbhandler import DBHandler


class AccountingRulesManager:
    """Handle the query of accounting rules for history events"""

    def __init__(
            self,
            database: 'DBHandler',
            evm_aggregators: 'EVMAccountingAggregators',
            pot: 'AccountingPot',
    ):
        self.database = database
        self.aggregators = evm_aggregators
        self.pot = pot
        self.event_settings: dict[int, BaseEventSettings] = {}
        self.event_callbacks: dict[int, EventsAccountantCallback] = {}

    def _query_db_rules(self) -> None:
        """Query the accounting rules in the db and update event_settings with them"""
        rules_info, _ = DBAccountingRules(self.database).query_rules(
            filter_query=AccountingRulesFilterQuery.make(),
        )
        for rule_info in rules_info:
            key = get_event_type_identifier(
                event_type=rule_info.event_key[0],
                event_subtype=rule_info.event_key[1],
                counterparty=rule_info.event_key[2],
            )
            self.event_settings[key] = rule_info.rule

    def get_event_settings(
            self,
            event: HistoryBaseEntry,
    ) -> tuple[Optional[BaseEventSettings], Optional[EventsAccountantCallback]]:
        """
        Return a matching rule for the event if it exists and an optional callback defined for
        the rule that should be executed
        """
        event_identifier = event.get_type_identifier()
        rule = self.event_settings.get(event_identifier, None)
        if isinstance(event, EvmEvent) is False or rule is not None:
            return rule, self.event_callbacks.get(event_identifier)

        event_identifier = event.get_type_identifier(include_counterparty=False)
        return (
            self.event_settings.get(event_identifier),
            self.event_callbacks.get(event_identifier),
        )

    def reset(self) -> None:
        self.aggregators.reset()
        self._query_db_rules()
        self.event_callbacks = self.aggregators.get_accounting_callbacks()

    def clean_rules(self) -> None:
        """
        Remove the rules from memory. Should be done after finishing with the accounting process
        to avoid having many dynamic objects in memory since the rules come from the database
        """
        self.event_settings.clear()
        self.event_callbacks.clear()
