"""Tests for zoning code mapper — no DB connection required (mocked session)."""
import uuid
from unittest.mock import MagicMock

import pytest

from app.adapters.zoning_mapper import resolve_zoning_district_id


def _make_jurisdiction(code_map: dict | None = None) -> MagicMock:
    j = MagicMock()
    j.id = uuid.uuid4()
    j.name = "City of Kyle, TX"
    j.gis_zoning_code_map = code_map
    return j


def _make_session(district_id: uuid.UUID | None = None) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = district_id
    session.execute.return_value = result
    return session


# ------------------------------------------------------------------

def test_none_input_returns_none():
    j = _make_jurisdiction({"R-1-2": "R-1-2"})
    session = _make_session()
    assert resolve_zoning_district_id(None, j, session) is None
    session.execute.assert_not_called()


def test_empty_string_returns_none():
    j = _make_jurisdiction({"R-1-2": "R-1-2"})
    session = _make_session()
    assert resolve_zoning_district_id("", j, session) is None
    session.execute.assert_not_called()


def test_unknown_code_returns_none_without_querying_db():
    j = _make_jurisdiction({"R-1-2": "R-1-2"})
    session = _make_session()
    result = resolve_zoning_district_id("PUDX", j, session)
    assert result is None
    session.execute.assert_not_called()


def test_known_code_resolves_to_district_id():
    district_id = uuid.uuid4()
    j = _make_jurisdiction({"R-1-2": "R-1-2"})
    session = _make_session(district_id=district_id)
    result = resolve_zoning_district_id("R-1-2", j, session)
    assert result == district_id
    session.execute.assert_called_once()


def test_alternate_format_resolves_via_map():
    district_id = uuid.uuid4()
    j = _make_jurisdiction({"R1-2": "R-1-2"})  # alternate format maps to canonical
    session = _make_session(district_id=district_id)
    result = resolve_zoning_district_id("R1-2", j, session)
    assert result == district_id


def test_code_in_map_but_no_db_row_returns_none():
    j = _make_jurisdiction({"R-1-2": "R-1-2"})
    session = _make_session(district_id=None)  # DB returns nothing
    result = resolve_zoning_district_id("R-1-2", j, session)
    assert result is None


def test_codes_are_case_sensitive():
    j = _make_jurisdiction({"R-1-2": "R-1-2"})  # uppercase only
    session = _make_session()
    result = resolve_zoning_district_id("r-1-2", j, session)
    assert result is None
    session.execute.assert_not_called()


def test_none_code_map_returns_none():
    j = _make_jurisdiction(code_map=None)
    session = _make_session()
    result = resolve_zoning_district_id("R-1-2", j, session)
    assert result is None
    session.execute.assert_not_called()
