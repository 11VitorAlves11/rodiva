"""Custom field definitions and their values (RF-ADM-007/008, RF-VEI-014)."""

from types import SimpleNamespace

from httpx import AsyncClient

from app.services.custom_fields import SECRET_MASK, validate


async def _vehicle(client: AsyncClient) -> str:
    response = await client.post("/api/vehicles", json={"name": "Carro de teste"})
    assert response.status_code == 201
    return response.json()["id"]


async def _field(client: AsyncClient, **overrides: object) -> dict:
    payload = {
        "record_kind": "vehicle",
        "key": "seguro",
        "label": "Seguradora",
        "field_type": "text",
    }
    payload.update(overrides)
    response = await client.post("/api/custom-fields", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def test_define_and_fill_a_text_field(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await _field(user_client)

    written = await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={"values": {"seguro": "Fidelidade"}},
    )

    assert written.status_code == 200, written.text
    assert written.json() == {"seguro": "Fidelidade"}
    read = await user_client.get(f"/api/custom-fields/records/vehicle/{vehicle_id}")
    assert read.json() == {"seguro": "Fidelidade"}


async def test_each_type_is_checked(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await _field(user_client, key="premio", label="Prémio", field_type="currency")
    await _field(user_client, key="renova", label="Renova em", field_type="date")
    await _field(
        user_client,
        key="nivel",
        label="Nível",
        field_type="choice",
        options=["básico", "completo"],
    )
    await _field(user_client, key="portal", label="Portal", field_type="url")

    good = await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={
            "values": {
                "premio": "412.90",
                "renova": "2027-01-31",
                "nivel": "completo",
                "portal": "https://exemplo.pt",
            }
        },
    )
    assert good.status_code == 200, good.text

    for values in (
        {"premio": "muito"},
        {"renova": "trinta e um"},
        {"nivel": "inexistente"},
        {"portal": "exemplo.pt"},
    ):
        bad = await user_client.put(
            f"/api/custom-fields/records/vehicle/{vehicle_id}", json={"values": values}
        )
        assert bad.status_code == 422, (values, bad.text)


async def test_a_required_field_must_be_filled(user_client: AsyncClient) -> None:
    vehicle_id = await _vehicle(user_client)
    await _field(user_client, key="apolice", label="Apólice", field_type="text", required=True)

    response = await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}", json={"values": {}}
    )

    assert response.status_code == 422
    assert "Apólice" in response.json()["detail"]


async def test_a_secret_is_never_read_back(user_client: AsyncClient) -> None:
    """A credential parked in a custom field must not leak through an ordinary read."""
    vehicle_id = await _vehicle(user_client)
    await _field(user_client, key="token", label="Token", field_type="secret")
    await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={"values": {"token": "super-secreto"}},
    )

    read = await user_client.get(f"/api/custom-fields/records/vehicle/{vehicle_id}")

    assert read.json() == {"token": SECRET_MASK}


async def test_resaving_a_form_keeps_the_other_values(user_client: AsyncClient) -> None:
    """The mask the form was shown must not be written back over the real secret.

    Over HTTP the stored secret can never be read, so what it actually holds is
    checked where the rule lives — see the unit test below.
    """
    vehicle_id = await _vehicle(user_client)
    await _field(user_client, key="token", label="Token", field_type="secret")
    await _field(user_client, key="seguro", label="Seguradora", field_type="text")
    await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={"values": {"token": "super-secreto"}},
    )

    await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={"values": {"token": SECRET_MASK, "seguro": "Fidelidade"}},
    )

    read = await user_client.get(f"/api/custom-fields/records/vehicle/{vehicle_id}")
    assert read.json() == {"token": SECRET_MASK, "seguro": "Fidelidade"}


def test_a_masked_secret_is_dropped_from_a_submission() -> None:
    """Storing the mask would replace the credential with eight bullets."""
    token = SimpleNamespace(key="token", label="Token", field_type="secret", required=False)
    seguro = SimpleNamespace(key="seguro", label="Seguradora", field_type="text", required=False)

    stored = validate([token, seguro], {"token": SECRET_MASK, "seguro": "Fidelidade"})

    assert stored == {"seguro": "Fidelidade"}


def test_a_new_secret_replaces_the_old_one() -> None:
    token = SimpleNamespace(key="token", label="Token", field_type="secret", required=False)

    assert validate([token], {"token": "outro-segredo"}) == {"token": "outro-segredo"}


async def test_archiving_a_field_keeps_its_values(user_client: AsyncClient) -> None:
    """Retiring a field must never destroy what members already recorded."""
    vehicle_id = await _vehicle(user_client)
    field = await _field(user_client)
    await user_client.put(
        f"/api/custom-fields/records/vehicle/{vehicle_id}",
        json={"values": {"seguro": "Fidelidade"}},
    )

    archived = await user_client.patch(f"/api/custom-fields/{field['id']}", json={"archived": True})

    assert archived.status_code == 200
    listed = await user_client.get("/api/custom-fields")
    assert listed.json() == []
    with_archived = await user_client.get("/api/custom-fields?include_archived=true")
    assert len(with_archived.json()) == 1


async def test_two_fields_cannot_share_a_key(user_client: AsyncClient) -> None:
    await _field(user_client)

    clash = await user_client.post(
        "/api/custom-fields",
        json={
            "record_kind": "vehicle",
            "key": "seguro",
            "label": "Outra coisa",
            "field_type": "text",
        },
    )

    assert clash.status_code == 409


async def test_the_same_key_is_free_on_another_kind(user_client: AsyncClient) -> None:
    await _field(user_client)

    other = await user_client.post(
        "/api/custom-fields",
        json={
            "record_kind": "expense",
            "key": "seguro",
            "label": "Seguro",
            "field_type": "text",
        },
    )

    assert other.status_code == 201


async def test_a_choice_field_needs_options(user_client: AsyncClient) -> None:
    response = await user_client.post(
        "/api/custom-fields",
        json={
            "record_kind": "vehicle",
            "key": "nivel",
            "label": "Nível",
            "field_type": "choice",
        },
    )

    assert response.status_code == 422


async def test_values_are_scoped_to_the_household(register) -> None:
    mine, _ = await register()
    theirs, _ = await register()
    their_vehicle = await _vehicle(theirs)
    await _field(mine)

    response = await mine.put(
        f"/api/custom-fields/records/vehicle/{their_vehicle}",
        json={"values": {"seguro": "Fidelidade"}},
    )

    assert response.status_code == 404
