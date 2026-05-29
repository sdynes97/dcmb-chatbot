#!/usr/bin/env python3
"""
One-time script to load schedule_seed.json into Azure Table Storage.
Usage: python scripts/seed_table.py [--clear]
Requires AZURE_STORAGE_CONNECTION_STRING and TABLE_STORAGE_TABLE_NAME env vars.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError

CONN_STR = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
TABLE_NAME = os.environ.get("TABLE_STORAGE_TABLE_NAME", "bandschedule")
SEED_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "schedule_seed.json")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--clear", action="store_true", help="Delete all existing events before seeding")
    args = parser.parse_args()

    if not CONN_STR:
        print("ERROR: AZURE_STORAGE_CONNECTION_STRING not set", file=sys.stderr)
        sys.exit(1)

    service = TableServiceClient.from_connection_string(CONN_STR)
    try:
        service.create_table(TABLE_NAME)
        print(f"Created table: {TABLE_NAME}")
    except ResourceExistsError:
        print(f"Table already exists: {TABLE_NAME}")

    client = service.get_table_client(TABLE_NAME)

    if args.clear:
        print("Clearing existing schedule events...")
        entities = list(client.query_entities("PartitionKey ne 'eta'"))
        for e in entities:
            client.delete_entity(partition_key=e["PartitionKey"], row_key=e["RowKey"])
        print(f"Deleted {len(entities)} entities.")

    with open(SEED_FILE) as f:
        events = json.load(f)

    for event in events:
        entity = {
            "PartitionKey": event["partition_key"],
            "RowKey": event["row_key"],
            **{k: v for k, v in event.items() if k not in ("partition_key", "row_key")},
        }
        client.upsert_entity(entity)
        print(f"  Upserted: {event['row_key']}")

    print(f"\nSeeded {len(events)} events into '{TABLE_NAME}'.")


if __name__ == "__main__":
    main()
