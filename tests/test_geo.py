import httpx
import pytest
import respx

from paperbytes import geo


def test_flag_emoji():
    assert geo.flag_emoji("GB") == "🇬🇧"
    assert geo.flag_emoji("us") == "🇺🇸"
    assert geo.flag_emoji("X") == "🏳"  # invalid -> white flag


def test_is_private_ip():
    assert geo.is_private_ip("127.0.0.1")
    assert geo.is_private_ip("192.168.1.5")
    assert geo.is_private_ip("::1")
    assert geo.is_private_ip("not-an-ip")
    assert not geo.is_private_ip("8.8.8.8")


def test_client_ip_prefers_forwarded_for():
    assert geo.client_ip("1.2.3.4, 5.6.7.8", "9.9.9.9") == "1.2.3.4"
    assert geo.client_ip(None, "9.9.9.9") == "9.9.9.9"
    assert geo.client_ip(None, None) == ""


def test_ad_policy():
    assert geo.ad_policy("GB") == "uk"
    assert geo.ad_policy("gb") == "uk"
    assert geo.ad_policy("US") == "generic"


@pytest.mark.asyncio
async def test_lookup_private_ip_defaults_to_uk():
    async with httpx.AsyncClient() as client:
        assert await geo.lookup_country("127.0.0.1", client=client) == ("GB", "United Kingdom")


@pytest.mark.asyncio
async def test_lookup_success():
    async with respx.mock() as mock:
        mock.get("http://ip-api.com/json/8.8.8.8").respond(
            200, json={"status": "success", "country": "United States", "countryCode": "US"}
        )
        async with httpx.AsyncClient() as client:
            assert await geo.lookup_country("8.8.8.8", client=client) == ("US", "United States")


@pytest.mark.asyncio
async def test_lookup_failure_falls_back_to_default():
    async with respx.mock() as mock:
        mock.get("http://ip-api.com/json/8.8.8.8").respond(500)
        async with httpx.AsyncClient() as client:
            assert await geo.lookup_country("8.8.8.8", client=client) == ("GB", "United Kingdom")


@pytest.mark.asyncio
async def test_lookup_error_status_falls_back():
    async with respx.mock() as mock:
        # Public IP so the network is hit; a "fail" status must fall back to default.
        mock.get("http://ip-api.com/json/8.8.4.4").respond(
            200, json={"status": "fail", "message": "reserved range"}
        )
        async with httpx.AsyncClient() as client:
            assert await geo.lookup_country("8.8.4.4", client=client) == ("GB", "United Kingdom")
