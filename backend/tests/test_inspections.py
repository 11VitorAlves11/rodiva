from datetime import date

from httpx import AsyncClient


async def test_inspection_snapshot_failure_and_generated_plan(user_client: AsyncClient) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Carro"})
    vehicle_id = vehicle.json()["id"]
    template = await user_client.post(
        "/api/inspection-templates",
        json={
            "name": "Inspeção de viagem",
            "fields": [
                {
                    "id": "lights",
                    "label": "Luzes funcionam",
                    "type": "boolean",
                    "required": True,
                    "failure_values": [False],
                    "create_plan_on_failure": True,
                },
                {"id": "comment", "label": "Observação", "type": "note"},
            ],
        },
    )
    assert template.status_code == 201
    inspection = await user_client.post(
        f"/api/vehicles/{vehicle_id}/inspections",
        json={
            "template_id": template.json()["id"],
            "recorded_on": date.today().isoformat(),
            "odometer": 20_000,
            "responses": {"lights": False},
        },
    )
    assert inspection.status_code == 201
    completed = await user_client.post(
        f"/api/vehicles/{vehicle_id}/inspections/{inspection.json()['id']}/complete"
    )
    assert completed.status_code == 200
    assert completed.json()["result"] == "failed"
    assert completed.json()["template_snapshot"]["version"] == 1
    plans = await user_client.get(f"/api/vehicles/{vehicle_id}/plans")
    assert any(item["description"] == "Inspection: Luzes funcionam" for item in plans.json())
    immutable = await user_client.patch(
        f"/api/vehicles/{vehicle_id}/inspections/{inspection.json()['id']}",
        json={"responses": {"lights": True}},
    )
    assert immutable.status_code == 409


async def test_required_inspection_answers_and_template_versioning(
    user_client: AsyncClient,
) -> None:
    vehicle = await user_client.post("/api/vehicles", json={"name": "Mota"})
    template = await user_client.post(
        "/api/inspection-templates",
        json={
            "name": "Checklist",
            "fields": [{"id": "pressure", "label": "Pressão", "type": "number", "required": True}],
        },
    )
    inspection = await user_client.post(
        f"/api/vehicles/{vehicle.json()['id']}/inspections",
        json={"template_id": template.json()["id"], "recorded_on": date.today().isoformat()},
    )
    missing = await user_client.post(
        f"/api/vehicles/{vehicle.json()['id']}/inspections/{inspection.json()['id']}/complete"
    )
    assert missing.status_code == 422
    version = await user_client.patch(
        f"/api/inspection-templates/{template.json()['id']}",
        json={
            "name": "Checklist revista",
            "fields": [{"id": "pressure", "label": "Pressão", "type": "number"}],
        },
    )
    assert version.status_code == 201
    assert version.json()["version"] == 2
    assert inspection.json()["template_snapshot"]["name"] == "Checklist"
    branching = await user_client.patch(
        f"/api/inspection-templates/{template.json()['id']}",
        json={"name": "Outra versão", "fields": version.json()["fields"]},
    )
    assert branching.status_code == 409
    duplicate = await user_client.post(
        f"/api/inspection-templates/{version.json()['id']}/duplicate"
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["version"] == 1
    assert duplicate.json()["name"] == "Checklist revista (copy)"
    invalid_update = await user_client.patch(
        f"/api/vehicles/{vehicle.json()['id']}/inspections/{inspection.json()['id']}",
        json={"responses": None},
    )
    assert invalid_update.status_code == 422
