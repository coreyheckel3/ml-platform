from typing import Protocol
from uuid import UUID

from forgeml.modules.evaluation.domain.entities import EvaluationComparisonSnapshot


class EvaluationComparisonRepository(Protocol):
    def load_snapshot(
        self,
        organization_id: UUID,
        project_id: UUID,
    ) -> EvaluationComparisonSnapshot | None:
        raise NotImplementedError
