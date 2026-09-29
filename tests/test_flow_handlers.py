"""Tests for options flow handlers (from_join form and media player form)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.crestron.flow_handlers.entities.media_player import MediaPlayerEntityHandler
from custom_components.crestron.flow_handlers.joins import JoinSyncHandler


def _flow(editing=None):
    flow = MagicMock()
    flow._editing_join = editing
    flow.config_entry.data = {"from_joins": [], "media_players": []}
    flow._async_reload_integration = AsyncMock()
    flow.async_step_init = AsyncMock(return_value={"type": "menu"})
    flow.async_show_form = MagicMock(side_effect=lambda **kw: kw)
    return flow


def _default(schema, key):
    for marker in schema.schema:
        if marker == key:
            return marker.default() if callable(marker.default) else marker.default
    raise KeyError(key)


class TestFromJoinForm:
    async def test_saves_target_and_data(self):
        flow = _flow()
        target = {"area_id": ["cinema"]}
        data = {"brightness_pct": 100, "transition": 4}
        await JoinSyncHandler(flow).async_step_add_from_join(
            {"join": "d1301", "service": "light.turn_on", "target": target, "data": data}
        )
        saved = flow.hass.config_entries.async_update_entry.call_args.kwargs["data"]["from_joins"]
        assert saved == [{"join": "d1301", "script": [{"service": "light.turn_on", "target": target, "data": data}]}]

    async def test_error_keeps_user_input(self):
        flow = _flow()
        result = await JoinSyncHandler(flow).async_step_add_from_join({"join": "bad", "service": "light.toggle"})
        assert result["errors"]["join"] == "invalid_join_format"
        assert _default(result["data_schema"], "service") == "light.toggle"


class TestMediaPlayerForm:
    async def test_error_keeps_user_input(self):
        flow = _flow()
        result = await MediaPlayerEntityHandler(flow).async_step_add_media_player(
            {"name": "Kitchen", "source_number_join": "a10", "sources": "Streaming"}
        )
        assert result["errors"]["sources"] == "invalid_source_format"
        assert _default(result["data_schema"], "name") == "Kitchen"
        assert _default(result["data_schema"], "sources") == "Streaming"

    async def test_valid_sources_saved(self):
        flow = _flow()
        await MediaPlayerEntityHandler(flow).async_step_add_media_player(
            {"name": "Kitchen", "source_number_join": "a10", "sources": "1: Streaming"}
        )
        saved = flow.hass.config_entries.async_update_entry.call_args.kwargs["data"]["media_players"]
        assert saved[0]["sources"] == {1: "Streaming"}
