from typing import Protocol
from uuid import UUID

from forgeml.modules.alerting.domain.entities import (
    AlertEvent,
    AlertRule,
    EndpointMetricSnapshotReference,
)


class AlertingRepository(Protocol):
    def add_rule(self, rule: AlertRule) -> AlertRule:
        raise NotImplementedError

    def get_rule(self, rule_id: UUID) -> AlertRule | None:
        raise NotImplementedError

    def list_rules(self, organization_id: UUID, project_id: UUID) -> list[AlertRule]:
        raise NotImplementedError

    def rule_slug_exists(
        self,
        organization_id: UUID,
        project_id: UUID,
        slug: str,
    ) -> bool:
        raise NotImplementedError

    def add_event(self, event: AlertEvent) -> AlertEvent:
        raise NotImplementedError

    def get_event(self, event_id: UUID) -> AlertEvent | None:
        raise NotImplementedError

    def get_open_event(self, rule_id: UUID, endpoint_id: UUID) -> AlertEvent | None:
        raise NotImplementedError

    def list_events(self, organization_id: UUID, project_id: UUID) -> list[AlertEvent]:
        raise NotImplementedError

    def update_event(self, event: AlertEvent) -> AlertEvent:
        raise NotImplementedError

    def get_endpoint_snapshot_reference(
        self,
        endpoint_id: UUID,
    ) -> EndpointMetricSnapshotReference | None:
        raise NotImplementedError
