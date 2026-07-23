from ml.libraries.forgeml_sdk.inference_runtime import create_app


def test_inference_runtime_contract() -> None:
    routes = {route.path for route in create_app().routes}

    assert "/health/live" in routes
    assert "/health/ready" in routes
    assert "/predict" in routes

