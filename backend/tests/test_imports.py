from httpx import AsyncClient

from tests.conftest import RegisterFn


async def test_preview_does_not_write_and_commit_is_idempotent(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Import"})).json()
    payload = {
        "vehicle_id": vehicle["id"],
        "kind": "expenses",
        "csv_text": (
            "Data;Categoria;Montante\n15/01/2026;parking;12,50\n16/01/2026;insurance;100,00"
        ),
        "mapping": {"issued_on": "Data", "category": "Categoria", "amount": "Montante"},
        "locale": "pt-PT",
    }
    preview = await user_client.post("/api/imports/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["rows"][0]["data"]["amount"] == "12.50"
    assert (await user_client.get(f"/api/vehicles/{vehicle['id']}/expenses")).json() == []
    committed = await user_client.post("/api/imports/commit", json=payload)
    assert committed.status_code == 200, committed.text
    assert committed.json()["imported"] == 2
    retry = await user_client.post("/api/imports/commit", json=payload)
    assert retry.json()["already_imported"] is True
    assert len((await user_client.get(f"/api/vehicles/{vehicle['id']}/expenses")).json()) == 2


async def test_invalid_rows_prevent_partial_import(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Import"})).json()
    payload = {
        "vehicle_id": vehicle["id"],
        "kind": "expenses",
        "csv_text": "issued_on,category,amount\n2026-01-15,parking,10\n2026-01-16,parking,-10",
        "locale": "en",
    }
    preview = (await user_client.post("/api/imports/preview", json=payload)).json()
    assert not preview["rows"][0]["errors"]
    assert preview["rows"][1]["errors"]
    assert (await user_client.post("/api/imports/commit", json=payload)).status_code == 422
    assert (await user_client.get(f"/api/vehicles/{vehicle['id']}/expenses")).json() == []


async def test_import_checks_odometer_against_existing_records(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Import"})).json()
    await user_client.post(
        f"/api/vehicles/{vehicle['id']}/odometer-readings",
        json={"recorded_on": "2026-01-01", "reading": 1000},
    )
    payload = {
        "vehicle_id": vehicle["id"],
        "kind": "fuel",
        "csv_text": "recorded_on,odometer_reading,volume_litres,total_price\n2026-01-02,900,40,65",
        "locale": "en",
    }
    preview = await user_client.post("/api/imports/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["errors"]
    assert (await user_client.post("/api/imports/commit", json=payload)).status_code == 422
    assert (await user_client.get(f"/api/vehicles/{vehicle['id']}/fuel-records")).json() == []
    readings = (await user_client.get(f"/api/vehicles/{vehicle['id']}/odometer-readings")).json()
    assert len(readings) == 1


async def test_import_cannot_cross_households(register: RegisterFn) -> None:
    owner, _ = await register()
    other, _ = await register()
    vehicle = (await owner.post("/api/vehicles", json={"name": "Private"})).json()
    payload = {
        "vehicle_id": vehicle["id"],
        "kind": "notes",
        "csv_text": "title,content\nTest,Note",
        "locale": "en",
    }
    assert (await other.post("/api/imports/commit", json=payload)).status_code == 404
    invite = (await owner.post("/api/household/invites", json={"role": "reader"})).json()
    await other.post(f"/auth/invites/{invite['token']}/accept")
    assert (await other.post("/api/imports/preview", json=payload)).status_code == 403


async def test_templates_can_be_previewed(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Import"})).json()
    for kind in ["fuel", "work", "expenses", "odometer", "notes"]:
        for locale in ["en", "pt-PT"]:
            template = await user_client.get(f"/api/imports/{kind}/template.csv?locale={locale}")
            response = await user_client.post(
                "/api/imports/preview",
                json={
                    "vehicle_id": vehicle["id"],
                    "kind": kind,
                    "csv_text": template.text,
                    "locale": locale,
                },
            )
            assert response.status_code == 200, response.text
            assert not response.json()["errors"]
            assert not response.json()["rows"][0]["errors"]


async def test_import_rejects_duplicate_headers_and_excess_rows(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Import"})).json()
    for text in ["title,title\none,two", "title,content\n" + "one,two\n" * 501]:
        assert (
            await user_client.post(
                "/api/imports/preview",
                json={"vehicle_id": vehicle["id"], "kind": "notes", "csv_text": text},
            )
        ).status_code == 422
