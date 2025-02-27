import csv
import logging
from itertools import count
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.base import HistoryEvent
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.converters import LOCATION_TO_ASSET_MAPPING
from rotkehlchen.assets.utils import symbol_to_asset_or_token
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_USD
from rotkehlchen.data_import.importers.constants import COINTRACKING_EVENT_PREFIX
from rotkehlchen.data_import.utils import BaseExchangeImporter, UnsupportedCSVEntry
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import AssetMovement, Trade
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_asset_amount_force_positive,
    deserialize_asset_movement_category,
    deserialize_fee,
    deserialize_timestamp_from_date,
)
from rotkehlchen.types import AssetAmount, AssetMovementCategory, Fee, Location, Price, TradeType
from rotkehlchen.utils.misc import ts_sec_to_ms

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def remap_header(fieldnames: list[str]) -> list[str]:
    cur_count = count(1)
    mapping = {1: 'Buy', 2: 'Sell', 3: 'Fee'}
    return [f'Cur.{mapping[next(cur_count)]}' if f.startswith('Cur.') else f for f in fieldnames]


def exchange_row_to_location(entry: str) -> Location:
    """Takes the exchange row entry of Cointracking exported trades list and returns a location"""
    if entry == 'no exchange':
        return Location.EXTERNAL
    if entry == 'Kraken':
        return Location.KRAKEN
    if entry == 'Poloniex':
        return Location.POLONIEX
    if entry == 'Bittrex':
        return Location.BITTREX
    if entry == 'Binance':
        return Location.BINANCE
    if entry == 'Bitmex':
        return Location.BITMEX
    if entry == 'Coinbase':
        return Location.COINBASE
    if entry in {'CoinbasePro', 'GDAX'}:
        return Location.COINBASEPRO
    if entry == 'Gemini':
        return Location.GEMINI
    if entry == 'Bitstamp':
        return Location.BITSTAMP
    if entry == 'Bitfinex':
        return Location.BITFINEX
    if entry == 'KuCoin':
        return Location.KUCOIN
    if entry == 'ETH Transaction':
        raise UnsupportedCSVEntry(
            'Not importing ETH Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your ethereum accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    if entry == 'BTC Transaction':
        raise UnsupportedCSVEntry(
            'Not importing BTC Transactions from Cointracking. Cointracking does not '
            'export enough data for them. Simply enter your BTC accounts and all '
            'your transactions will be auto imported directly from the chain',
        )
    return Location.EXTERNAL


class CointrackingImporter(BaseExchangeImporter):

    def __init__(self, db: 'DBHandler') -> None:
        super().__init__(db=db)
        self.usd = A_USD.resolve_to_asset_with_oracles()

    def _consume_cointracking_entry(
            self,
            write_cursor: DBCursor,
            csv_row: dict[str, Any],
            timestamp_format: str = '%d.%m.%Y %H:%M:%S',
    ) -> None:
        """Consumes a cointracking entry row from the CSV and adds it into the database
        Can raise:
            - DeserializationError if something is wrong with the format of the expected values
            - UnsupportedCSVEntry if importing of this entry is not supported.
            - IndexError if the CSV file is corrupt
            - KeyError if the an expected CSV key is missing
            - UnknownAsset if one of the assets founds in the entry are not supported
        """
        row_type = csv_row['Type']
        timestamp = deserialize_timestamp_from_date(
            date=csv_row['Date'],
            formatstr=timestamp_format,
            location='cointracking.info',
        )
        location = exchange_row_to_location(csv_row['Exchange'])
        asset_resolver = LOCATION_TO_ASSET_MAPPING.get(location, symbol_to_asset_or_token)
        notes = csv_row['Comment']
        if location == Location.EXTERNAL:
            notes += f'. Data from -{csv_row["Exchange"]}- not known by rotki.'

        fee = Fee(ZERO)
        # whatever (used only if there is no fee)
        fee_currency: AssetWithOracles = self.usd
        if csv_row['Fee'] != '':
            fee = deserialize_fee(csv_row['Fee'])
            fee_currency = asset_resolver(csv_row['Cur.Fee'])

        if row_type in {'Gift/Tip', 'Trade', 'Income'}:
            base_asset = asset_resolver(csv_row['Cur.Buy'])
            quote_asset = None if csv_row['Cur.Sell'] == '' else asset_resolver(csv_row['Cur.Sell'])  # noqa: E501
            if quote_asset is None and row_type not in {'Gift/Tip', 'Income'}:
                raise DeserializationError('Got a trade entry with an empty quote asset')

            if quote_asset is None:
                # Really makes no difference as this is just a gift and the amount is zero
                quote_asset = self.usd
            base_amount_bought = deserialize_asset_amount(csv_row['Buy'])
            if base_amount_bought == ZERO:
                raise DeserializationError('Bought amount in trade is zero')

            if csv_row['Sell'] != '-':
                quote_amount_sold = deserialize_asset_amount(csv_row['Sell'])
            else:
                quote_amount_sold = AssetAmount(ZERO)
            rate = Price(quote_amount_sold / base_amount_bought)

            trade = Trade(
                timestamp=timestamp,
                location=location,
                base_asset=base_asset,
                quote_asset=quote_asset,
                trade_type=TradeType.BUY,  # It's always a buy during cointracking import
                amount=base_amount_bought,
                rate=rate,
                fee=fee,
                fee_currency=fee_currency,
                link='',
                notes=notes,
            )
            self.add_trade(write_cursor, trade)
        elif row_type in {'Deposit', 'Withdrawal'}:
            category = deserialize_asset_movement_category(row_type.lower())
            if category == AssetMovementCategory.DEPOSIT:
                amount = deserialize_asset_amount(csv_row['Buy'])
                asset = asset_resolver(csv_row['Cur.Buy'])
            else:
                amount = deserialize_asset_amount_force_positive(csv_row['Sell'])
                asset = asset_resolver(csv_row['Cur.Sell'])

            asset_movement = AssetMovement(
                location=location,
                category=category,
                address=None,
                transaction_id=None,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                fee=fee,
                fee_asset=fee_currency,
                link='',
            )
            self.add_asset_movement(write_cursor, asset_movement)
        elif row_type == 'Staking':  # TODO: Not like the way duplication is checked here
            # We probably need to work on standardizing this and improving performance
            self.flush_all(write_cursor)  # flush so that the DB check later can work and not miss unwritten events  # noqa: E501
            amount = deserialize_asset_amount(csv_row['Buy'])
            asset = asset_resolver(csv_row['Cur.Buy'])
            timestamp_ms = ts_sec_to_ms(timestamp)
            event_type = HistoryEventType.STAKING
            event_subtype = HistoryEventSubType.REWARD
            with self.db.conn.read_ctx() as read_cursor:
                read_cursor.execute(
                    f"SELECT COUNT(*) FROM history_events WHERE "
                    f"event_identifier LIKE '{COINTRACKING_EVENT_PREFIX}%' "
                    "AND asset=? AND amount=? AND timestamp=? AND location=? "
                    "AND type=? AND subtype=?",
                    (asset.identifier, str(amount), timestamp_ms, location.serialize_for_db(),
                     event_type.serialize(), event_subtype.serialize()),
                )
                if read_cursor.fetchone()[0] != 0:
                    log.warning(f'Cointracking staking event for {asset} at {timestamp} already exists in the DB')  # noqa: E501
                    return

            event = HistoryEvent(
                event_identifier=f'{COINTRACKING_EVENT_PREFIX}_{uuid4().hex}',
                sequence_index=0,
                timestamp=timestamp_ms,
                location=location,
                event_type=event_type,
                event_subtype=event_subtype,
                asset=asset,
                balance=Balance(amount, ZERO),
                notes=f'Stake reward of {amount} {asset.symbol} in {location!s}',
            )
            self.add_history_events(write_cursor, [event])
        else:
            raise UnsupportedCSVEntry(
                f'Unknown entry type "{row_type}" encountered during cointracking '
                f'data import. Ignoring entry',
            )

    def _import_csv(
            self,
            write_cursor: DBCursor,
            filepath: Path,
            **kwargs: Any,
    ) -> None:
        """May raise:
        - InputError if one of the rows is malformed
        """
        with open(filepath, encoding='utf-8-sig') as csvfile:
            data = csv.reader(csvfile, delimiter=',', quotechar='"')
            header = remap_header(next(data))
            for row in data:
                try:
                    self._consume_cointracking_entry(write_cursor, dict(zip(header, row)), **kwargs)  # noqa: E501
                except UnknownAsset as e:
                    self.db.msg_aggregator.add_warning(
                        f'During cointracking CSV import found action with unknown '
                        f'asset {e.identifier}. Ignoring entry',
                    )
                    continue
                except IndexError:
                    self.db.msg_aggregator.add_warning(
                        'During cointracking CSV import found entry with '
                        'unexpected number of columns',
                    )
                    continue
                except DeserializationError as e:
                    self.db.msg_aggregator.add_warning(
                        f'Error during cointracking CSV import deserialization. '
                        f'Error was {e!s}. Ignoring entry',
                    )
                    continue
                except UnsupportedCSVEntry as e:
                    self.db.msg_aggregator.add_warning(str(e))
                    continue
                except KeyError as e:
                    raise InputError(f'Could not find key {e!s} in csv row {row!s}') from e
