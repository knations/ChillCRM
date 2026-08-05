"""Database compatibility helpers for CHILLCRM.

The production app can run against local SQLite or hosted Postgres. This module
keeps that adapter logic separate from request routing.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import urllib.parse
from typing import Any


POSTGRES_ADAPTER_VALUES = {"postgres", "hosted_postgres", "supabase"}


def postgres_statement_timeout_ms() -> int:
    raw = os.environ.get("CHILLCRM_POSTGRES_STATEMENT_TIMEOUT_MS", "").strip()
    try:
        timeout_ms = int(raw) if raw else 8_000
    except ValueError:
        timeout_ms = 8_000
    return max(1_000, min(timeout_ms, 60_000))


class PostgresCompatRow(dict):
    """Small row wrapper that behaves like sqlite3.Row for current app code."""

    @staticmethod
    def normalize_value(value: Any) -> Any:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return value

    def __init__(self, columns: list[str], values: tuple[Any, ...]):
        normalized_values = tuple(self.normalize_value(value) for value in values)
        super().__init__(zip(columns, normalized_values))
        self._values = normalized_values

    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return self._values[key]
        return super().__getitem__(key)


class PostgresCompatCursor:
    def __init__(self, cursor: Any):
        self.cursor = cursor
        self.columns = [column[0] for column in (cursor.description or [])]

    def _row(self, values: tuple[Any, ...] | None) -> PostgresCompatRow | None:
        if values is None:
            return None
        return PostgresCompatRow(self.columns, values)

    def fetchone(self) -> PostgresCompatRow | None:
        return self._row(self.cursor.fetchone())

    def fetchall(self) -> list[PostgresCompatRow]:
        return [self._row(row) for row in self.cursor.fetchall()]

    def close(self) -> None:
        self.cursor.close()

    def __iter__(self) -> Any:
        for row in self.cursor:
            yield self._row(row)


class PostgresCompatConnection:
    def __init__(self, database_url: str, ssl_root_cert: str = ""):
        try:
            import pg8000.dbapi as pg
        except ImportError as exc:
            raise RuntimeError("pg8000 is required for the hosted Postgres adapter.") from exc
        parsed = urllib.parse.urlparse(database_url)
        if not parsed.hostname:
            raise ValueError("DATABASE_URL is missing a hostname.")
        database = (parsed.path or "/postgres").lstrip("/") or "postgres"
        self.conn = pg.connect(
            user=urllib.parse.unquote(parsed.username or ""),
            password=urllib.parse.unquote(parsed.password or ""),
            host=parsed.hostname,
            port=parsed.port or 5432,
            database=database,
            ssl_context=postgres_ssl_context(ssl_root_cert),
            timeout=10,
        )
        cursor = self.conn.cursor()
        try:
            cursor.execute("SET search_path TO crm, public")
            cursor.execute(f"SET statement_timeout TO {postgres_statement_timeout_ms()}")
            cursor.execute("SET idle_in_transaction_session_timeout TO 10000")
        finally:
            cursor.close()

    def execute(self, sql: str, parameters: Any = ()) -> PostgresCompatCursor:
        cursor = self.conn.cursor()
        cursor.execute(translate_sqlite_sql_for_postgres(sql), postgres_parameters_for_sql(sql, parameters))
        return PostgresCompatCursor(cursor)

    def commit(self) -> None:
        self.conn.commit()

    def rollback(self) -> None:
        self.conn.rollback()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self) -> "PostgresCompatConnection":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        try:
            if exc_type:
                self.rollback()
        finally:
            self.close()


def postgres_ssl_context(ssl_root_cert: str = "") -> ssl.SSLContext:
    return ssl.create_default_context(cafile=ssl_root_cert or None)


def hosted_postgres_adapter_enabled_from_env() -> bool:
    database_url_configured = bool(os.environ.get("DATABASE_URL", "").strip())
    adapter = os.environ.get("CHILLCRM_DATABASE_ADAPTER") or os.environ.get("CRM_DATABASE_ADAPTER") or ""
    return database_url_configured and adapter.strip().lower() in POSTGRES_ADAPTER_VALUES


def translate_sqlite_sql_for_postgres(sql: str) -> str:
    translated, _ = translate_sqlite_parameters(sql)
    translated = re.sub(r"\s+COLLATE\s+NOCASE\b", "", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bLIKE\b", "ILIKE", translated, flags=re.IGNORECASE)
    translated = re.sub(
        r"(?<!CAST\()(?P<field>\b(?:[A-Za-z_][A-Za-z0-9_]*\.)?source_json)\s+(?P<operator>NOT\s+ILIKE|ILIKE)\b",
        lambda match: f"CAST({match.group('field')} AS TEXT) {match.group('operator')}",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(r"\bifnull\s*\(", "coalesce(", translated, flags=re.IGNORECASE)
    translated = translated.replace("round(sum(d.value), 2)", "round((sum(d.value))::numeric, 2)")
    translated = translated.replace("printf('%.0f', d.value)", "to_char(d.value, 'FM999999999999990')")
    translated = translated.replace("CASE WHEN t.completed THEN", "CASE WHEN t.completed <> 0 THEN")
    translated = translated.replace("CASE WHEN completed THEN", "CASE WHEN completed <> 0 THEN")
    translated = translated.replace(
        "json_array_length(source_json, '$.associated_deal_ids')",
        "jsonb_array_length(coalesce(source_json::jsonb -> 'associated_deal_ids', '[]'::jsonb))",
    )
    translated = translated.replace(
        "group_concat(DISTINCT ta.record_type)",
        "string_agg(DISTINCT ta.record_type::text, ',')",
    )
    translated = translated.replace(
        "group_concat(DISTINCT ta.resource_type)",
        "string_agg(DISTINCT ta.resource_type::text, ',')",
    )
    translated = translated.replace(
        "group_concat(DISTINCT coalesce(t.display_name, ta.source_name, t.normalized_name))",
        "string_agg(DISTINCT coalesce(t.display_name, ta.source_name, t.normalized_name)::text, ',')",
    )
    translated = re.sub(
        r"json_extract\(([^,]+),\s*'\$\.([A-Za-z0-9_]+)'\)",
        lambda match: f"({match.group(1).strip()}::jsonb ->> '{match.group(2)}')",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"\bdate\s*\(\s*'now'\s*,\s*'\+7 days'\s*\)",
        "(CURRENT_DATE + INTERVAL '7 days')::date",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(
        r"\bdate\s*\(\s*'now'\s*,\s*'-14 days'\s*\)",
        "(CURRENT_DATE - INTERVAL '14 days')::date",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(r"\bdate\s*\(\s*'now'\s*\)", "CURRENT_DATE", translated, flags=re.IGNORECASE)
    translated = re.sub(
        r"\bdate\s*\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*\)",
        r"CAST(\1 AS date)",
        translated,
        flags=re.IGNORECASE,
    )
    translated = re.sub(r"\bdatetime\s*\(\s*'now'\s*\)", "CURRENT_TIMESTAMP", translated, flags=re.IGNORECASE)
    translated = re.sub(r"\bSELECT\s+last_insert_rowid\s*\(\s*\)", "SELECT lastval()", translated, flags=re.IGNORECASE)
    return translated


def postgres_parameters_for_sql(sql: str, parameters: Any) -> Any:
    _, named_parameter_order = translate_sqlite_parameters(sql)
    if isinstance(parameters, dict):
        return [parameters[name] for name in named_parameter_order]
    return parameters


def translate_sqlite_parameters(sql: str) -> tuple[str, list[str]]:
    result: list[str] = []
    named_parameter_order: list[str] = []
    index = 0
    quote: str | None = None
    while index < len(sql):
        char = sql[index]
        if quote:
            result.append(char)
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    result.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            result.append(char)
            index += 1
            continue
        if char == "?":
            result.append("%s")
            index += 1
            continue
        if char == ":" and (index == 0 or sql[index - 1] != ":"):
            name_match = re.match(r":([A-Za-z_][A-Za-z0-9_]*)", sql[index:])
            if name_match:
                result.append("%s")
                named_parameter_order.append(name_match.group(1))
                index += len(name_match.group(0))
                continue
        result.append(char)
        index += 1
    return "".join(result), named_parameter_order
