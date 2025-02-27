"""Functions dealing with the general_cache table of the Global DB"""
from collections.abc import Iterable
from typing import Optional, Union

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.types import (
    CacheType,
    ChecksumEvmAddress,
    GeneralCacheType,
    Timestamp,
    UniqueCacheType,
)
from rotkehlchen.utils.misc import ts_now


def compute_cache_key(key_parts: Iterable[Union[str, CacheType]]) -> str:
    """Function that computes the cache key for accessing the globaldb general or unique cache
    tables. It computes the cache key by iterating through `key_parts` and making one string
    from them. Only a tuple with the same values and the same order represents the same key."""
    cache_key = ''
    for part in key_parts:
        if isinstance(part, CacheType):
            cache_key += part.serialize()
        else:
            cache_key += part
    return cache_key


# Using any random address here, since length of all addresses is the same
BASE_POOL_TOKENS_KEY_LENGTH = len(compute_cache_key([CacheType.CURVE_POOL_TOKENS, ZERO_ADDRESS]))


def globaldb_set_general_cache_values_at_ts(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
        timestamp: Timestamp,
) -> None:
    """Function to update the general cache in globaldb. Inserts all values paired
    with the cache key. If any entry exists, overwrites it."""
    cache_key = compute_cache_key(key_parts)
    tuples = [(cache_key, value, timestamp) for value in values]
    write_cursor.executemany(
        'INSERT OR REPLACE INTO general_cache '
        '(key, value, last_queried_ts) VALUES (?, ?, ?)',
        tuples,
    )


def globaldb_set_general_cache_values(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
        values: Iterable[str],
) -> None:
    """Function to update general cache in globaldb. Inserts the value paired with the cache key.
    If any entry exists, overwrites it. The timestamp is always the current time."""
    timestamp = ts_now()
    globaldb_set_general_cache_values_at_ts(
        write_cursor=write_cursor,
        key_parts=key_parts,
        values=values,
        timestamp=timestamp,
    )


def globaldb_get_general_cache_values(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[str]:
    """Function that reads from the general cache table.
    It returns all the values that are paired with the given key."""
    cache_key = compute_cache_key(key_parts)
    cursor.execute('SELECT value FROM general_cache WHERE key=?', (cache_key,))
    return [entry[0] for entry in cursor]


def globaldb_set_unique_cache_value_at_ts(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, UniqueCacheType]],
        value: str,
        timestamp: Timestamp,
) -> None:
    """Function that updates the unique cache in globaldb. Inserts the value paired with the
    cache key. If any entry exists, overwrites it."""
    cache_key = compute_cache_key(key_parts)
    write_cursor.execute(
        'INSERT OR REPLACE INTO unique_cache '
        '(key, value, last_queried_ts) VALUES (?, ?, ?)',
        (cache_key, value, timestamp),
    )


def globaldb_set_unique_cache_value(
        write_cursor: DBCursor,
        key_parts: Iterable[Union[str, UniqueCacheType]],
        value: str,
) -> None:
    """Function that updates the unique cache in globaldb. Inserts the value paired with the
    cache key. If any entry exists, overwrites it. The timestamp is always the current time."""
    timestamp = ts_now()
    globaldb_set_unique_cache_value_at_ts(
        write_cursor=write_cursor,
        key_parts=key_parts,
        value=value,
        timestamp=timestamp,
    )


def globaldb_get_unique_cache_value(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, UniqueCacheType]],
) -> Optional[str]:
    """Function that reads from the unique cache table.
    It returns the value that is paired with the given key."""
    cache_key = compute_cache_key(key_parts)
    cursor.execute('SELECT value FROM unique_cache WHERE key=?', (cache_key,))
    result = cursor.fetchone()
    if result is None:
        return None
    return result[0]


def globaldb_get_general_cache_like(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[str]:
    """
    Function to read globaldb cache.
    Returns all values where key starts with the provided `key_parts`.

    key_parts should contain neither the "%" nor the "." symbol.
    """
    cache_key = compute_cache_key(key_parts)
    return [x[0] for x in cursor.execute(
        'SELECT value FROM general_cache WHERE key LIKE ?',
        (f'{cache_key}%',),
    )]


def globaldb_get_general_cache_keys_and_values_like(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> list[tuple[str, str]]:
    """
    Function that reads globaldb general cache.
    Returns all key-value pairs where key starts with the provided `key_parts`.

    key_parts should contain neither the "%" nor the "." symbol.
    """
    cache_key = compute_cache_key(key_parts)
    return cursor.execute(
        'SELECT key, value FROM general_cache WHERE key LIKE ?',
        (f'{cache_key}%',),
    ).fetchall()


def globaldb_get_general_cache_last_queried_ts_by_key(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, GeneralCacheType]],
) -> Timestamp:
    """
    Get the last_queried_ts of the oldest stored element by key_parts. If there is no such
    element returns Timestamp(0)
    """
    cache_key = compute_cache_key(key_parts)
    cursor.execute(
        'SELECT last_queried_ts FROM general_cache WHERE key=? '
        'ORDER BY last_queried_ts ASC',
        (cache_key,),
    )
    result = cursor.fetchone()
    if result is None:
        return Timestamp(0)
    return Timestamp(result[0])


def globaldb_get_unique_cache_last_queried_ts_by_key(
        cursor: DBCursor,
        key_parts: Iterable[Union[str, UniqueCacheType]],
) -> Timestamp:
    """
    Get the last_queried_ts of the oldest stored element by key_parts. If there is no such
    element returns Timestamp(0)
    """
    cache_key = compute_cache_key(key_parts)
    cursor.execute(
        'SELECT last_queried_ts FROM unique_cache WHERE key=? '
        'ORDER BY last_queried_ts ASC',
        (cache_key,),
    )
    result = cursor.fetchone()
    if result is None:
        return Timestamp(0)
    return Timestamp(result[0])


def read_curve_pool_tokens(
        cursor: 'DBCursor',
        pool_address: ChecksumEvmAddress,
) -> list[ChecksumEvmAddress]:
    """
    Reads tokens for a particular curve pool. Tokens are stored with their indices to make sure
    that the order of coins in pool contract and in our cache is the same. This functions reads
    and returns tokens in sorted order.
    """
    tokens_data = globaldb_get_general_cache_keys_and_values_like(
        cursor=cursor,
        key_parts=(CacheType.CURVE_POOL_TOKENS, pool_address),
    )
    found_tokens: list[tuple[int, ChecksumEvmAddress]] = []
    for key, address in tokens_data:
        index = int(key[BASE_POOL_TOKENS_KEY_LENGTH:])  # len(key) > BASE_POOL_TOKENS_KEY_LENGTH
        found_tokens.append((index, string_to_evm_address(address)))

    found_tokens.sort(key=lambda x: x[0])
    return [address for _, address in found_tokens]
