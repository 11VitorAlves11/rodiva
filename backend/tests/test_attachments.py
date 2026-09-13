import base64
import hashlib

from httpx import AsyncClient


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def test_upload_and_download_attachment(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    content = b"%PDF-1.4 fake receipt"
    uploaded = await user_client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": "fatura.pdf",
            "content_type": "application/pdf",
            "content_base64": base64.b64encode(content).decode(),
        },
    )
    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["filename"] == "fatura.pdf"
    assert body["size"] == len(content)
    assert body["checksum"] == hashlib.sha256(content).hexdigest()

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/attachments")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    downloaded = await user_client.get(
        f"/api/vehicles/{vehicle_id}/attachments/{body['id']}/download"
    )
    assert downloaded.status_code == 200
    assert downloaded.content == content


async def test_delete_attachment_removes_it(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    uploaded = await user_client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": "fatura.pdf",
            "content_type": "application/pdf",
            "content_base64": base64.b64encode(b"conteudo").decode(),
        },
    )
    attachment_id = uploaded.json()["id"]

    deleted = await user_client.delete(f"/api/vehicles/{vehicle_id}/attachments/{attachment_id}")
    assert deleted.status_code == 204

    listed = await user_client.get(f"/api/vehicles/{vehicle_id}/attachments")
    assert listed.json() == []

    downloaded = await user_client.get(
        f"/api/vehicles/{vehicle_id}/attachments/{attachment_id}/download"
    )
    assert downloaded.status_code == 404


async def test_rejects_unsupported_content_type(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": "script.sh",
            "content_type": "application/x-sh",
            "content_base64": base64.b64encode(b"echo hi").decode(),
        },
    )
    assert response.status_code == 422


async def test_rejects_invalid_base64_payload(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    response = await user_client.post(
        f"/api/vehicles/{vehicle_id}/attachments",
        json={
            "filename": "fatura.pdf",
            "content_type": "application/pdf",
            "content_base64": "not-valid-base64!!",
        },
    )
    assert response.status_code == 422
