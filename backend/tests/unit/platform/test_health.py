from prometheus_client import generate_latest

from forgeml.platform.health import (
    DependencyProbe,
    ReadinessChecker,
    check_redis_connection,
)


def test_readiness_checker_skips_dependency_probes_when_disabled() -> None:
    calls: list[str] = []
    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=False,
        probes=[DependencyProbe(name="database", check=lambda: calls.append("database"))],
    )

    report = checker.run()

    assert report.status == "ready"
    assert not report.checks_enabled
    assert report.checks == []
    assert calls == []


def test_readiness_checker_reports_passing_probes() -> None:
    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=True,
        probes=[
            DependencyProbe(name="database", check=lambda: None),
            DependencyProbe(name="redis", check=lambda: None),
        ],
    )

    report = checker.run()

    assert report.status == "ready"
    assert report.checks_enabled
    assert [check.name for check in report.checks] == ["database", "redis"]
    assert {check.status for check in report.checks} == {"pass"}


def test_readiness_checker_reports_failures_without_leaking_details() -> None:
    def fail() -> None:
        raise RuntimeError("postgresql://user:password@internal")

    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=True,
        probes=[DependencyProbe(name="database", check=fail)],
    )

    report = checker.run()

    assert report.status == "not_ready"
    assert report.checks[0].status == "fail"
    assert report.checks[0].message == "Probe raised RuntimeError."
    assert "password" not in report.model_dump_json()


def test_readiness_checker_emits_probe_metrics() -> None:
    checker = ReadinessChecker(
        service_name="forgeml-api",
        checks_enabled=True,
        probes=[DependencyProbe(name="database", check=lambda: None)],
    )

    checker.run()
    metrics = generate_latest().decode("utf-8")

    assert 'forgeml_readiness_probe_status{probe="database"} 1.0' in metrics
    assert "forgeml_readiness_probe_duration_seconds_count" in metrics


def test_redis_readiness_probe_pings_and_closes_client(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class FakeRedis:
        def ping(self) -> bool:
            calls.append(("ping", None))
            return True

        def close(self) -> None:
            calls.append(("close", None))

    def from_url(redis_url: str, **kwargs: object) -> FakeRedis:
        calls.append(("url", redis_url))
        calls.append(("timeout", kwargs["socket_connect_timeout"]))
        calls.append(("socket_timeout", kwargs["socket_timeout"]))
        return FakeRedis()

    monkeypatch.setattr("forgeml.platform.health.Redis.from_url", from_url)

    check_redis_connection("redis://redis.internal:6379/0", timeout_seconds=0.25)

    assert calls == [
        ("url", "redis://redis.internal:6379/0"),
        ("timeout", 0.25),
        ("socket_timeout", 0.25),
        ("ping", None),
        ("close", None),
    ]
