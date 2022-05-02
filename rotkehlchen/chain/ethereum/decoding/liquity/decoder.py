from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import (
    HistoryBaseEntry,
    HistoryEventSubType,
    HistoryEventType,
    get_tx_event_type_identifier,
)
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem, TxEventSettings
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_ethereum_address
from rotkehlchen.constants.assets import A_ETH, A_LUSD
from rotkehlchen.types import ChecksumEthAddress, EthereumTransaction

if TYPE_CHECKING:
    from rotkehlchen.accounting.pot import AccountingPot

BALANCE_UPDATE = b'\xca#+Z\xbb\x98\x8cT\x0b\x95\x9f\xf6\xc3\xbf\xae>\x97\xff\xf9d\xfd\t\x8cP\x8f\x96\x13\xc0\xa6\xbf\x1a\x80'  # noqa: E501
STABILITY_POOL = string_to_ethereum_address('0xDf9Eb223bAFBE5c5271415C75aeCD68C21fE3D7F')

CPT_LIQUITY = 'liquity'


class LiquityDecoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    @staticmethod
    def _decode_trove_operations(
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], Optional[ActionItem]]:
        if tx_log.topics[0] != BALANCE_UPDATE:
            return None, None

        for event in decoded_events:
            if event.event_type == HistoryEventType.RECEIVE and event.asset == A_LUSD:
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.GENERATE_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Generate {event.balance.amount} {A_LUSD.symbol} from liquity'
            elif event.event_type == HistoryEventType.SPEND and event.asset == A_LUSD:
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.PAYBACK_DEBT
                event.counterparty = CPT_LIQUITY
                event.notes = f'Return {event.balance.amount} {A_LUSD.symbol} to liquity'
            elif event.event_type == HistoryEventType.SPEND and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Deposit {event.balance.amount} {event.asset.symbol} as collateral for liquity'  # noqa: E501
            elif event.event_type == HistoryEventType.RECEIVE and event.event_subtype == HistoryEventSubType.NONE and event.asset == A_ETH:  # noqa: E501
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.counterparty = CPT_LIQUITY
                event.notes = f'Withdraw {event.balance.amount} {event.asset.symbol} collateral from liquity'  # noqa: E501
        return None, None

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEthAddress, Tuple[Any, ...]]:
        return {
            STABILITY_POOL: (self._decode_trove_operations,),  # noqa: E501
        }

    def counterparties(self) -> List[str]:
        return [CPT_LIQUITY]

    def event_settings(self, pot: 'AccountingPot') -> Dict[str, TxEventSettings]:  # pylint: disable=unused-argument  # noqa: E501
        """Being defined at function call time is fine since this function is called only once"""
        return {
            get_tx_event_type_identifier(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET, CPT_LIQUITY): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
                multitake_treatment=None,
            ),
            get_tx_event_type_identifier(HistoryEventType.SPEND, HistoryEventSubType.PAYBACK_DEBT, CPT_LIQUITY): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='spend',
                take=1,
                multitake_treatment=None,
            ),
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.GENERATE_DEBT, CPT_LIQUITY): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            ),
            get_tx_event_type_identifier(HistoryEventType.WITHDRAWAL, HistoryEventSubType.REMOVE_ASSET, CPT_LIQUITY): TxEventSettings(  # noqa: E501
                taxable=False,
                count_entire_amount_spend=False,
                count_cost_basis_pnl=False,
                method='acquisition',
                take=1,
                multitake_treatment=None,
            ),
        }
