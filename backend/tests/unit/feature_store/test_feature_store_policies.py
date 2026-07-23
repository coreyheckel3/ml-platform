from uuid import uuid4

import pytest

from forgeml.modules.feature_store.domain.entities import FeatureDefinition
from forgeml.modules.feature_store.domain.policies import (
    build_feature_set_slug,
    validate_entity_key,
    validate_feature_definitions,
)
from forgeml.platform.domain.errors import DomainValidationError


def test_build_feature_set_slug_normalizes_names() -> None:
    assert build_feature_set_slug(" Merchant Signals / Daily ") == "merchant-signals-daily"


def test_validate_entity_key_requires_identifier() -> None:
    with pytest.raises(DomainValidationError):
        validate_entity_key("merchant id")


def test_validate_feature_definitions_rejects_duplicate_names() -> None:
    feature_set_id = uuid4()
    with pytest.raises(DomainValidationError):
        validate_feature_definitions(
            (
                FeatureDefinition(
                    id=uuid4(),
                    feature_set_id=feature_set_id,
                    name="amount_30d",
                    dtype="float",
                    description="",
                    nullable=False,
                    constraints={},
                ),
                FeatureDefinition(
                    id=uuid4(),
                    feature_set_id=feature_set_id,
                    name="Amount_30d",
                    dtype="float",
                    description="",
                    nullable=False,
                    constraints={},
                ),
            )
        )
