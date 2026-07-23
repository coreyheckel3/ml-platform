from typing import Protocol
from uuid import UUID

from forgeml.modules.monitoring.domain.entities import InferenceEndpointMonitoringSummary


class MonitoringRepository(Protocol):
    def list_inference_endpoint_summaries(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> list[InferenceEndpointMonitoringSummary]:
        raise NotImplementedError

    def count_active_alerts(self, organization_id: UUID, project_id: UUID) -> int:
        raise NotImplementedError
