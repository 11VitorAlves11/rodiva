import base64
import zipfile
from datetime import date
from io import BytesIO

from httpx import AsyncClient


async def test_report_aggregates_costs_distance_and_csv(user_client: AsyncClient) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Relatório"})).json()
    vehicle_id = vehicle["id"]
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-01-01", "reading": 1000},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/odometer-readings",
        json={"recorded_on": "2026-02-01", "reading": 1500},
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/fuel-records",
        json={
            "recorded_on": "2026-02-01",
            "volume_litres": "40",
            "total_price": "80",
            "unit_price": "2",
        },
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/work-records",
        json={
            "recorded_on": "2026-02-02",
            "kind": "maintenance",
            "description": "Revisão",
            "total_cost": "120",
        },
    )
    await user_client.post(
        f"/api/vehicles/{vehicle_id}/expenses",
        json={
            "issued_on": "2026-02-03",
            "category": "insurance",
            "amount": "300",
            "status": "paid",
        },
    )
    response = await user_client.get(
        "/api/reports/summary",
        params={"vehicle_id": vehicle_id, "date_from": "2026-01-01", "date_to": "2026-12-31"},
    )
    assert response.status_code == 200, response.text
    report = response.json()
    assert report["total_cost"] == "500.00"
    assert report["total_distance"] == 500
    assert report["vehicles"][0]["cost_per_distance"] == "1.000"
    assert report["currency"] == "EUR"
    exported = await user_client.get("/api/reports/export.csv", params={"vehicle_id": vehicle_id})
    assert exported.status_code == 200
    assert "Revisão" in exported.text
    assert "text/csv" in exported.headers["content-type"]


async def test_report_rejects_cross_household_vehicle_and_invalid_dates(
    user_client: AsyncClient, register
) -> None:
    other, _ = await register()
    foreign = (await other.post("/api/vehicles", json={"name": "Privado"})).json()
    denied = await user_client.get("/api/reports/summary", params={"vehicle_id": foreign["id"]})
    assert denied.status_code == 404
    invalid = await user_client.get(
        "/api/reports/summary",
        params={"date_from": date(2026, 2, 1).isoformat(), "date_to": date(2026, 1, 1).isoformat()},
    )
    assert invalid.status_code == 422


async def _upload_attachment(
    client: AsyncClient, vehicle_id: str, filename: str, content: bytes
) -> None:
    response = await client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": filename,
            "content_type": "application/pdf",
            "content_base64": base64.b64encode(content).decode(),
        },
    )
    assert response.status_code == 201, response.text


async def test_attachments_zip_contains_chronologically_named_entries(
    user_client: AsyncClient,
) -> None:
    vehicle = (await user_client.post("/api/vehicles", json={"name": "Relatório Zip"})).json()
    vehicle_id = vehicle["id"]
    await _upload_attachment(user_client, vehicle_id, "fatura.pdf", b"conteudo-a")
    await _upload_attachment(user_client, vehicle_id, "fatura.pdf", b"conteudo-b")

    response = await user_client.get(
        "/api/reports/attachments.zip", params={"vehicle_id": vehicle_id}
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/zip"
    assert 'filename="rodiva-attachments.zip"' in response.headers["content-disposition"]

    today = date.today().isoformat()
    with zipfile.ZipFile(BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert len(names) == 2
        folder = names[0].split("/", 1)[0]
        assert folder.startswith("Relat")
        assert all(name.startswith(f"{folder}/{today}_fatura") for name in names)
        assert all(name.endswith(".pdf") for name in names)
        # Collision between two same-named same-day attachments must be disambiguated.
        assert names[0] != names[1]
        contents = {archive.read(name) for name in names}
        assert contents == {b"conteudo-a", b"conteudo-b"}


async def test_attachments_zip_excludes_cross_household_vehicles(
    user_client: AsyncClient, register
) -> None:
    other, _ = await register()
    foreign = (await other.post("/api/vehicles", json={"name": "Privado"})).json()
    await _upload_attachment(other, foreign["id"], "segredo.pdf", b"segredo")

    denied = await user_client.get(
        "/api/reports/attachments.zip", params={"vehicle_id": foreign["id"]}
    )
    assert denied.status_code == 404

    own_vehicle = (await user_client.post("/api/vehicles", json={"name": "Meu"})).json()
    own_vehicle_id = own_vehicle["id"]
    await _upload_attachment(user_client, own_vehicle_id, "meu.pdf", b"meu-conteudo")

    scoped = await user_client.get("/api/reports/attachments.zip")
    assert scoped.status_code == 200
    with zipfile.ZipFile(BytesIO(scoped.content)) as archive:
        names = archive.namelist()
        assert any(name.endswith("meu.pdf") for name in names)
        assert not any("segredo" in name for name in names)
