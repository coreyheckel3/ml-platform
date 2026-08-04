from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, Field
from redis import Redis

from forgeml.platform.config import Settings
from forgeml.platform.database.session import check_database_connection
from forgeml.platform.observability.metrics import (
    readiness_probe_duration_seconds,
    readiness_probe_status,
)

ProbeStatus = Literal["pass", "fail"]
ReadinessStatus = Literal["ready", "not_ready"]


class ReadinessProbeResult(BaseModel):
    name: str
    status: ProbeStatus
    latency_ms: float = Field(ge=0)
    message: str | None = None


class ReadinessReport(BaseModel):
    status: ReadinessStatus
    service: str
    checks_enabled: bool
    checks: list[ReadinessProbeResult] = Field(default_factory=list)


@dataclass(frozen=True)
class DependencyProbe:
    name: str
    check: Callable[[], None]


class ReadinessChecker:
    def __init__(
        self,
        *,
        service_name: str,
        checks_enabled: bool,
        probes: Sequence[DependencyProbe] = (),
    ) -> None:
        self._service_name = service_name
        self._checks_enabled = checks_enabled
        self._probes = tuple(probes)

    def run(self) -> ReadinessReport:
        if not self._checks_enabled:
            return ReadinessReport(
                status="ready",
                service=self._service_name,
                checks_enabled=False,
                checks=[],
            )

        checks = [self._run_probe(probe) for probe in self._probes]
        status: ReadinessStatus = (
            "ready" if checks and all(check.status == "pass" for check in checks) else "not_ready"
        )
        return ReadinessReport(
            status=status,
            service=self._service_name,
            checks_enabled=True,
            checks=checks,
        )

    def _run_probe(self, probe: DependencyProbe) -> ReadinessProbeResult:
        started_at = perf_counter()
        try:
            probe.check()
        except Exception as exc:
            duration_seconds = perf_counter() - started_at
            readiness_probe_status.labels(probe=probe.name).set(0)
            readiness_probe_duration_seconds.labels(probe=probe.name).observe(duration_seconds)
            return ReadinessProbeResult(
                name=probe.name,
                status="fail",
                latency_ms=round(duration_seconds * 1000, 3),
                message=f"Probe raised {exc.__class__.__name__}.",
            )

        duration_seconds = perf_counter() - started_at
        readiness_probe_status.labels(probe=probe.name).set(1)
        readiness_probe_duration_seconds.labels(probe=probe.name).observe(duration_seconds)
        return ReadinessProbeResult(
            name=probe.name,
            status="pass",
            latency_ms=round(duration_seconds * 1000, 3),
            message=None,
        )


def build_readiness_checker(settings: Settings) -> ReadinessChecker:
    probes: tuple[DependencyProbe, ...] = ()
    if settings.readiness_checks_enabled:
        probes = (
            DependencyProbe(name="database", check=check_database_connection),
            DependencyProbe(
                name="redis",
                check=lambda: check_redis_connection(
                    settings.redis_url,
                    timeout_seconds=settings.readiness_timeout_seconds,
                ),
            ),
        )
    return ReadinessChecker(
        service_name=settings.service_name,
        checks_enabled=settings.readiness_checks_enabled,
        probes=probes,
    )


def check_redis_connection(redis_url: str, *, timeout_seconds: float) -> None:
    client = Redis.from_url(
        redis_url,
        socket_connect_timeout=timeout_seconds,
        socket_timeout=timeout_seconds,
    )
    try:
        if client.ping() is not True:
            raise RuntimeError("Redis ping did not return PONG.")
    finally:
        client.close()
