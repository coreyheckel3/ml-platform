from typing import Protocol
from uuid import UUID

from forgeml.modules.lifecycle.domain.entities import ProjectLifecycleSnapshot


class ProjectLifecycleRepository(Protocol):
    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> ProjectLifecycleSnapshot | None:
        raise NotImplementedError
