import hashlib
import hmac
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import httpx
from httpx import AsyncClient

from tests.conftest import RegisterFn


def _response(status_code: int) -> httpx.Response:
    request = httpx.Request("POST", "https://example.invalid/hook")
    return httpx.Response(status_code, request=request)


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/v1/vehicles", json={"name": "Golf", "distance_unit": "km"})
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


async def _hook(client: AsyncClient, **extra: object) -> dict:
    response = await client.post(
        "/api/v1/webhooks",
        json={"description": "n8n", "url": "https://example.invalid/hook", **extra},
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


async def test_the_secret_is_shown_once_and_signs_the_body(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client)
    secret = hook["secret"]
    assert secret

    # It is not handed out again.
    listed = (await client.get("/api/v1/webhooks")).json()
    assert "secret" not in listed[0]

    with patch("app.services.events.httpx.AsyncClient") as fake:
        post = AsyncMock(return_value=_response(200))
        fake.return_value.__aenter__.return_value.post = post
        await client.post(f"/api/v1/webhooks/{hook['id']}/test")

    body = post.await_args.kwargs["content"]
    headers = post.await_args.kwargs["headers"]
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert headers["X-Rodiva-Signature"] == expected
    assert headers["X-Rodiva-Event"] == "webhook.test"
    # The envelope carries what RF-API-008 asks for.
    payload = json.loads(body)
    assert payload["version"] == 1
    assert payload["resource"] == "webhook"
    assert payload["household_id"]
    assert payload["occurred_at"]


async def test_a_change_queues_an_event_for_the_endpoint(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client)
    vehicle_id = await _vehicle(client)

    deliveries = (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json()
    assert [row["event"] for row in deliveries] == ["vehicle.created"]
    assert deliveries[0]["payload"]["data"]["name"] == "Golf"
    assert deliveries[0]["payload"]["vehicle_id"] == vehicle_id


async def test_only_subscribed_events_are_queued(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client, events=["reminder.due"])
    await _vehicle(client)

    deliveries = (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json()
    assert deliveries == []


async def test_a_failing_endpoint_backs_off_and_is_recorded(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client)

    with patch("app.services.events.httpx.AsyncClient") as fake:
        fake.return_value.__aenter__.return_value.post = AsyncMock(return_value=_response(500))
        await client.post(f"/api/v1/webhooks/{hook['id']}/test")

    delivery = (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json()[0]
    assert delivery["status"] == "pending"  # still to be retried
    assert delivery["attempts"] == 1
    assert delivery["response_status"] == 500
    assert delivery["last_error"]

    # The endpoint itself carries the last failure, so it is visible in the UI.
    assert (await client.get("/api/v1/webhooks")).json()[0]["last_error"]

    # A retry that succeeds clears it.
    with patch("app.services.events.httpx.AsyncClient") as fake:
        fake.return_value.__aenter__.return_value.post = AsyncMock(return_value=_response(204))
        retried = await client.post(
            f"/api/v1/webhooks/{hook['id']}/deliveries/{delivery['id']}/retry"
        )
    assert retried.status_code == 200
    assert retried.json()["status"] == "sent"
    assert retried.json()["delivered_at"]


async def test_delivery_failure_never_fails_the_change_behind_it(register: RegisterFn) -> None:
    client, _ = await register()
    await _hook(client)

    with patch("app.services.events.httpx.AsyncClient") as fake:
        fake.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.ConnectError("refused")
        )
        vehicle = await client.post("/api/v1/vehicles", json={"name": "Berlingo"})
        # The vehicle is created regardless of what the receiver does (RF-NOT-008).
        assert vehicle.status_code == 201
    assert len((await client.get("/api/v1/vehicles")).json()) == 1


async def test_a_reminder_coming_due_emits_an_event(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client, events=["reminder.due"])
    vehicle_id = await _vehicle(client)
    await client.post(
        f"/api/v1/vehicles/{vehicle_id}/reminders",
        json={"title": "Inspeção", "due_date": (date.today() + timedelta(days=3)).isoformat()},
    )

    with patch("app.services.events.httpx.AsyncClient") as fake:
        fake.return_value.__aenter__.return_value.post = AsyncMock(return_value=_response(200))
        await client.post("/api/v1/notifications/run")

    deliveries = (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json()
    assert [row["event"] for row in deliveries] == ["reminder.due"]
    assert deliveries[0]["payload"]["data"]["urgency"] == "very_urgent"  # 3 days out
    assert deliveries[0]["status"] == "sent"


async def test_deleting_a_record_emits_and_restoring_emits_too(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client, events=["record.deleted", "record.restored"])
    vehicle_id = await _vehicle(client)
    note = (
        await client.post(
            f"/api/v1/vehicles/{vehicle_id}/notes", json={"title": "Chave", "content": "Gaveta"}
        )
    ).json()

    await client.delete(f"/api/v1/vehicles/{vehicle_id}/notes/{note['id']}")
    await client.post(f"/api/v1/trash/note/{note['id']}/restore")

    deliveries = (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json()
    assert {row["event"] for row in deliveries} == {"record.deleted", "record.restored"}


async def test_webhooks_belong_to_their_household_and_owner(register: RegisterFn) -> None:
    owner, _ = await register()
    member, _ = await register()
    other, _ = await register()
    invite = (await owner.post("/api/household/invites", json={"role": "manager"})).json()
    await member.post(f"/auth/invites/{invite['token']}/accept")
    hook = await _hook(owner)

    # A manager is not an owner: endpoints receive the household's data.
    assert (await member.get("/api/v1/webhooks")).status_code == 403
    assert (await other.get("/api/v1/webhooks")).json() == []
    assert (await other.delete(f"/api/v1/webhooks/{hook['id']}")).status_code == 404
    assert (await owner.delete(f"/api/v1/webhooks/{hook['id']}")).status_code == 204


async def test_switching_an_endpoint_off_stops_the_events(register: RegisterFn) -> None:
    client, _ = await register()
    hook = await _hook(client)
    await client.patch(f"/api/v1/webhooks/{hook['id']}", json={"active": False})
    await _vehicle(client)
    assert (await client.get(f"/api/v1/webhooks/{hook['id']}/deliveries")).json() == []
