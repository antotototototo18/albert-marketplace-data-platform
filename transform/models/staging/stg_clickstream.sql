-- Removes replays: the consumer delivers at least once, so one event_id can be
-- written twice. Keeps the first copy received.
-- Casts event_time, emitted_at and _ingested_at from ISO-8601 strings to TIMESTAMP.
-- Drops raw_event: the untouched JSON keeps the original identifiers, and every
-- field it holds is already a column.
-- Drops items: order lines come from order_items, the system of record.
select
    event_id,
    event_type,
    timestamp(event_time)  as event_time,
    timestamp(emitted_at)  as emitted_at,
    session_id,
    buyer_id,
    p_id,
    price,
    qty,
    order_id,
    payment_method,
    amount,
    currency,
    timestamp(_ingested_at) as ingested_at,
    dt                      as event_date
from {{ source('bronze_stream', 'clickstream') }}
where dt >= date '{{ var("clickstream_start_date") }}'
qualify row_number() over (
    partition by event_id
    order by _ingested_at, _kafka_partition, _kafka_offset
) = 1
