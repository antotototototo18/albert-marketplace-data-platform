from datetime import date
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import psycopg
import pyarrow.parquet as pq

from ingestion.consume_clickstream import EventBatch, consume, validate_event
from ingestion.extract_orders import CHECKPOINT, connect_with_retry, extract
from ingestion.storage import BronzeStore


def event(**changes):
    result = {
        "schema_version": 1, "event_id": "synthetic-event", "event_type": "product_viewed",
        "event_time": "2026-09-15T12:00:00Z", "emitted_at": "2026-09-15T12:01:00Z",
        "session_id": "synthetic-session", "buyer_id": "synthetic-buyer",
        "p_id": "synthetic-product", "price": 2.5,
    }
    result.update(changes)
    return result


def message(payload, offset=0, partition=0):
    return SimpleNamespace(
        value=lambda: payload, topic=lambda: "test-clickstream", partition=lambda: partition,
        offset=lambda: offset, error=lambda: None,
    )


def order(identifier):
    return {"order_id": identifier, "buyer_id": "synthetic-buyer", "discount_id": None,
            "payment_id": None, "order_date": date(2026, 9, 15)}


def connection_with_pages(*pages):
    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.__exit__.return_value = False
    results = [None] + [SimpleNamespace(fetchall=lambda rows=rows: rows) for rows in pages]
    connection.execute.side_effect = results
    return connection


class StoreTests(unittest.TestCase):
    def test_data_is_not_overwritten_and_checkpoint_rejects_stale_version(self):
        with tempfile.TemporaryDirectory() as directory:
            store = BronzeStore(directory)
            store.put_bytes("object", b"original", "text/plain")
            with self.assertRaises(FileExistsError):
                store.put_bytes("object", b"replacement", "text/plain")
            self.assertEqual((Path(directory) / "object").read_bytes(), b"original")
            version = store.put_checkpoint("state.json", {"cursor": 1}, None)
            store.put_checkpoint("state.json", {"cursor": 2}, version)
            with self.assertRaises(RuntimeError):
                store.put_checkpoint("state.json", {"cursor": 0}, version)
            self.assertEqual(store.read_checkpoint("state.json")[0], {"cursor": 2})

    def test_unsafe_object_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for key in ("../outside", "/absolute", "a/../../outside", "a\\outside"):
                with self.subTest(key=key), self.assertRaises(ValueError):
                    BronzeStore(directory).put_bytes(key, b"test", "text/plain")

    @patch("google.cloud.storage.Client")
    def test_gcs_writes_use_generation_preconditions(self, client):
        blob = client.return_value.bucket.return_value.blob.return_value
        blob.generation = 7
        store = BronzeStore("gs://test-bucket/bronze")
        version = store.put_checkpoint("state.json", {"cursor": 1}, 4)
        self.assertEqual(version, 7)
        self.assertEqual(blob.upload_from_string.call_args.kwargs["if_generation_match"], 4)
        store.put_bytes("new-object", b"test", "text/plain")
        self.assertEqual(blob.upload_from_string.call_args.kwargs["if_generation_match"], 0)


class ExtractorTests(unittest.TestCase):
    @patch("ingestion.extract_orders.psycopg.connect")
    def test_connection_retries_grow_then_stop(self, connect):
        connect.side_effect = psycopg.OperationalError()
        sleep = MagicMock()
        with self.assertRaises(psycopg.OperationalError):
            connect_with_retry("test DSN", attempts=4, initial_delay=1, sleep=sleep)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2, 4])
        self.assertEqual(connect.call_count, 4)

    @patch("ingestion.extract_orders.connect_with_retry")
    def test_restart_uses_durable_id_cursor_for_same_day_insert(self, connect):
        with tempfile.TemporaryDirectory() as directory:
            store = BronzeStore(directory)
            connect.return_value = connection_with_pages([order(1), order(2)], [])
            first = extract("postgresql://localhost/marketplace", store)
            connection = connection_with_pages([order(3)], [])
            connect.return_value = connection
            second = extract("postgresql://localhost/marketplace", BronzeStore(directory))
            self.assertEqual(first["last_order_id"], 2)
            self.assertEqual(second, {"rows_written": 1, "last_order_id": 3})
            self.assertEqual(connection.execute.call_args_list[1].args[1], (2, 5000))
            self.assertEqual(store.read_checkpoint(CHECKPOINT)[0]["last_order_id"], 3)
            files = list(Path(directory).rglob("*.parquet"))
            self.assertEqual(sum(pq.ParquetFile(file).metadata.num_rows for file in files), 3)
            self.assertEqual(pq.ParquetFile(files[0]).schema_arrow.field("discount_id").type.bit_width, 32)

    @patch("ingestion.extract_orders.connect_with_retry")
    def test_failed_object_write_does_not_advance_cursor(self, connect):
        with tempfile.TemporaryDirectory() as directory:
            store = BronzeStore(directory)
            connect.return_value = connection_with_pages([order(1)])
            with patch.object(store, "put_parquet", side_effect=OSError("storage down")):
                with self.assertRaises(OSError):
                    extract("postgresql://localhost/marketplace", store)
            self.assertIsNone(store.read_checkpoint(CHECKPOINT)[0])

    @patch("ingestion.extract_orders.connect_with_retry")
    def test_failed_checkpoint_write_leaves_objects_replayable(self, connect):
        with tempfile.TemporaryDirectory() as directory:
            store = BronzeStore(directory)
            connect.return_value = connection_with_pages([order(1)])
            with patch.object(store, "put_checkpoint", side_effect=OSError("state down")):
                with self.assertRaises(OSError):
                    extract("postgresql://localhost/marketplace", store)
            self.assertEqual(len(list(Path(directory).rglob("*.parquet"))), 1)
            self.assertIsNone(store.read_checkpoint(CHECKPOINT)[0])


class EventTests(unittest.TestCase):
    def test_schema_dispatch_and_bad_payloads(self):
        valid = event()
        self.assertEqual(validate_event(json.dumps(valid).encode()), valid)
        cases = [
            b"not JSON", b"\xff", b'{"schema_version":1,"schema_version":1}',
            json.dumps(event(schema_version=2)).encode(),
            json.dumps(event(schema_version=True)).encode(),
            json.dumps(event(event_time="not a timestamp")).encode(),
            json.dumps(event(event_time="2026-02-30T00:00:00Z")).encode(),
            json.dumps(event(event_time="2026-09-15T12:00:00")).encode(),
            json.dumps(event(price=float("nan"))).encode(),
            json.dumps(event(price=10**400)).encode(),
            json.dumps(event(qty=2**70)).encode(),
            json.dumps(event(unexpected="new field")).encode(),
        ]
        for payload in cases:
            with self.subTest(payload=payload[:70]), self.assertRaises((ValueError, UnicodeError)):
                validate_event(payload)

    def test_reject_reason_names_missing_field_without_values(self):
        broken = event(buyer_id="secret-buyer")
        del broken["session_id"]
        with self.assertRaises(ValueError) as caught:
            validate_event(json.dumps(broken).encode())
        self.assertEqual(str(caught.exception), "/: missing required session_id")
        with self.assertRaises(ValueError) as caught:
            validate_event(json.dumps(event(price="secret-price")).encode())
        self.assertNotIn("secret", str(caught.exception))

    def test_each_observed_event_shape_is_accepted(self):
        for item in (
            event(), event(event_type="added_to_cart", qty=2),
            event(event_type="order_placed", order_id=1, items=[{"p_id": "p1", "qty": 1, "price": 2.5}],
                  amount=2.5, currency="EUR", payment_method="card"),
        ):
            self.assertEqual(validate_event(json.dumps(item).encode()), item)

    def test_bad_row_is_persisted_and_later_good_row_continues(self):
        with tempfile.TemporaryDirectory() as directory:
            consumer = MagicMock()
            consumer.commit.return_value = []
            raw = json.dumps(event(event_time="2026-09-15T23:30:00-02:00")).encode()
            consumer.poll.side_effect = [message(raw, 0), message(b"broken", 1), message(raw, 2)]
            result = consume(consumer, "test-clickstream", BronzeStore(directory), batch_size=3, max_messages=3)
            self.assertEqual(result, {"accepted": 2, "rejected": 1, "received": 3})
            good = list(Path(directory).glob("clickstream/v1/dt=2026-09-16/*.parquet"))
            bad = list(Path(directory).glob("_dlq/clickstream/dt=*/*.parquet"))
            self.assertEqual(pq.ParquetFile(good[0]).metadata.num_rows, 2)
            self.assertEqual(pq.ParquetFile(bad[0]).read().to_pylist()[0]["raw"], b"broken")
            self.assertEqual(consumer.commit.call_args.kwargs["offsets"][0].offset, 3)
            self.assertFalse(consumer.commit.call_args.kwargs["asynchronous"])

    def test_storage_failure_never_commits_offsets(self):
        store = MagicMock()
        store.put_parquet.side_effect = OSError("storage down")
        batch = EventBatch(store)
        batch.add(message(json.dumps(event()).encode()))
        consumer = MagicMock()
        with self.assertRaises(OSError):
            batch.flush(consumer)
        consumer.commit.assert_not_called()
        self.assertEqual(batch.size, 1)

    def test_dlq_failure_never_commits_valid_events_either(self):
        store = MagicMock()
        store.put_parquet.side_effect = [None, OSError("DLQ down")]
        batch = EventBatch(store)
        batch.add(message(json.dumps(event()).encode(), 0))
        batch.add(message(b"broken", 1))
        consumer = MagicMock()
        with self.assertRaises(OSError):
            batch.flush(consumer)
        consumer.commit.assert_not_called()

    def test_commit_failure_replays_durable_files(self):
        with tempfile.TemporaryDirectory() as directory:
            batch = EventBatch(BronzeStore(directory))
            batch.add(message(json.dumps(event()).encode()))
            consumer = MagicMock()
            consumer.commit.side_effect = [RuntimeError("broker down"), []]
            with self.assertRaises(RuntimeError):
                batch.flush(consumer)
            batch.flush(consumer)
            files = list(Path(directory).rglob("*.parquet"))
            self.assertEqual(len(files), 2)
            self.assertEqual(batch.size, 0)

    def test_offsets_are_explicit_for_each_partition(self):
        batch = EventBatch(MagicMock())
        raw = json.dumps(event()).encode()
        batch.add(message(raw, 11, 0))
        batch.add(message(raw, 6, 1))
        consumer = MagicMock()
        consumer.commit.return_value = []
        batch.flush(consumer)
        positions = consumer.commit.call_args.kwargs["offsets"]
        self.assertEqual({(p.partition, p.offset) for p in positions}, {(0, 12), (1, 7)})


if __name__ == "__main__":
    unittest.main()
