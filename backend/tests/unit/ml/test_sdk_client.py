import io
import json
from urllib.error import HTTPError

import pytest
from ml.libraries.forgeml_sdk import client as sdk_client
from ml.libraries.forgeml_sdk.client import ForgeMLApiError, ForgeMLClient


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_sdk_client_sends_authorized_json_request(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_requests = []

    def fake_urlopen(api_request, timeout):
        captured_requests.append((api_request, timeout))
        return FakeResponse({"ok": True})

    monkeypatch.setattr(sdk_client.request, "urlopen", fake_urlopen)
    client = ForgeMLClient(
        base_url="http://api.test/",
        access_token="token-123",
        timeout_seconds=4.0,
    )

    result = client.create_project({"name": "Fraud Detection"})

    assert result == {"ok": True}
    api_request, timeout = captured_requests[0]
    headers = {key.lower(): value for key, value in api_request.header_items()}
    assert api_request.full_url == "http://api.test/api/v1/projects"
    assert api_request.get_method() == "POST"
    assert json.loads(api_request.data.decode("utf-8")) == {"name": "Fraud Detection"}
    assert headers["authorization"] == "Bearer token-123"
    assert headers["content-type"] == "application/json"
    assert timeout == 4.0


def test_sdk_client_maps_api_error_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_api_request, timeout):
        assert timeout == 30.0
        raise HTTPError(
            url="http://api.test/api/v1/projects",
            code=409,
            msg="conflict",
            hdrs=None,
            fp=io.BytesIO(b'{"detail":"Project already exists."}'),
        )

    monkeypatch.setattr(sdk_client.request, "urlopen", fake_urlopen)
    client = ForgeMLClient(base_url="http://api.test")

    with pytest.raises(ForgeMLApiError) as exc_info:
        client.create_project({"name": "Fraud Detection"})

    assert exc_info.value.status_code == 409
    assert str(exc_info.value) == "Project already exists."
    assert exc_info.value.payload == {"detail": "Project already exists."}


def test_sdk_client_lists_inference_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_paths = []

    def fake_get(_client: ForgeMLClient, path: str) -> dict[str, object]:
        captured_paths.append(path)
        return {"items": []}

    monkeypatch.setattr(ForgeMLClient, "get", fake_get)
    client = ForgeMLClient(base_url="http://api.test", access_token="token-123")

    assert client.list_inference_requests("endpoint-1") == {"items": []}
    assert captured_paths == ["/api/v1/inference-endpoints/endpoint-1/requests"]


def test_sdk_client_gets_model_version(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_paths = []

    def fake_get(_client: ForgeMLClient, path: str) -> dict[str, object]:
        captured_paths.append(path)
        return {"id": "model-version-1"}

    monkeypatch.setattr(ForgeMLClient, "get", fake_get)
    client = ForgeMLClient(base_url="http://api.test")

    assert client.get_model_version("model-version-1") == {"id": "model-version-1"}
    assert captured_paths == ["/api/v1/model-versions/model-version-1"]
