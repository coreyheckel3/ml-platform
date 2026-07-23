from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from forgeml.modules.datasets.api.schemas import (
    CreateDatasetRequest,
    CreateDatasetVersionRequest,
    CreateDatasetVersionResponse,
    DatasetListResponse,
    DatasetResponse,
    DatasetSchemaResponse,
    DatasetValidationRunListResponse,
    DatasetValidationRunResponse,
    DatasetVersionListResponse,
    DatasetVersionResponse,
    FinalizeDatasetVersionRequest,
    SchemaFieldPayload,
    UploadInstructionsResponse,
)
from forgeml.modules.datasets.application.services import (
    CreateDatasetCommand,
    CreateDatasetVersionCommand,
    DatasetService,
    FinalizeDatasetVersionCommand,
)
from forgeml.modules.datasets.domain.entities import (
    Dataset,
    DatasetSchema,
    DatasetSourceType,
    DatasetValidationRun,
    DatasetVersion,
    SchemaField,
)
from forgeml.modules.datasets.infrastructure.object_storage import LocalObjectStorageGateway
from forgeml.modules.datasets.infrastructure.sqlalchemy_repositories import (
    SqlAlchemyDatasetRepository,
)
from forgeml.platform.api.dependencies import get_current_principal, get_db_session
from forgeml.platform.config import Settings, get_settings
from forgeml.platform.security.rbac import Principal

router = APIRouter(tags=["datasets"])


def get_dataset_service(
    session: Session = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> DatasetService:
    return DatasetService(
        datasets=SqlAlchemyDatasetRepository(session),
        object_storage=LocalObjectStorageGateway(
            endpoint=settings.object_storage_endpoint,
            bucket=settings.object_storage_bucket,
            signing_secret=settings.jwt_secret,
        ),
    )


@router.post(
    "/projects/{project_id}/datasets",
    response_model=DatasetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset(
    project_id: UUID,
    request: CreateDatasetRequest,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetResponse:
    dataset = service.create_dataset(
        CreateDatasetCommand(
            organization_id=UUID(principal.organization_id),
            project_id=project_id,
            name=request.name,
            description=request.description,
            source_type=DatasetSourceType(request.source_type),
        ),
        principal,
    )
    return _dataset_response(dataset)


@router.get("/projects/{project_id}/datasets", response_model=DatasetListResponse)
def list_datasets(
    project_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetListResponse:
    return DatasetListResponse(
        items=[
            _dataset_response(dataset)
            for dataset in service.list_datasets(project_id, principal)
        ]
    )


@router.get("/datasets/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetResponse:
    return _dataset_response(service.get_dataset(dataset_id, principal))


@router.post(
    "/datasets/{dataset_id}/versions",
    response_model=CreateDatasetVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dataset_version(
    dataset_id: UUID,
    request: CreateDatasetVersionRequest,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> CreateDatasetVersionResponse:
    result = service.create_version(
        CreateDatasetVersionCommand(
            dataset_id=dataset_id,
            created_by=UUID(principal.user_id),
            filename=request.filename,
            content_type=request.content_type,
        ),
        principal,
    )
    return CreateDatasetVersionResponse(
        version=_version_response(result.version),
        upload=UploadInstructionsResponse(
            upload_url=result.upload.upload_url,
            object_uri=result.upload.object_uri,
            expires_at=result.upload.expires_at,
            required_headers=result.upload.required_headers,
        ),
    )


@router.get("/datasets/{dataset_id}/versions", response_model=DatasetVersionListResponse)
def list_dataset_versions(
    dataset_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetVersionListResponse:
    return DatasetVersionListResponse(
        items=[
            _version_response(version)
            for version in service.list_versions(dataset_id, principal)
        ]
    )


@router.get("/dataset-versions/{version_id}", response_model=DatasetVersionResponse)
def get_dataset_version(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetVersionResponse:
    return _version_response(service.get_version(version_id, principal))


@router.post("/dataset-versions/{version_id}/finalize", response_model=DatasetVersionResponse)
def finalize_dataset_version(
    version_id: UUID,
    request: FinalizeDatasetVersionRequest,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetVersionResponse:
    schema_fields = (
        tuple(
            SchemaField(name=field.name, dtype=field.dtype, nullable=field.nullable)
            for field in request.schema_fields
        )
        if request.schema_fields is not None
        else None
    )
    return _version_response(
        service.finalize_version(
            FinalizeDatasetVersionCommand(
                version_id=version_id,
                object_uri=request.object_uri,
                content_hash=request.content_hash,
                size_bytes=request.size_bytes,
                row_count=request.row_count,
                schema_fields=schema_fields,
                sample_csv=request.sample_csv,
            ),
            principal,
        )
    )


@router.get("/dataset-versions/{version_id}/schema", response_model=DatasetSchemaResponse)
def get_dataset_schema(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetSchemaResponse:
    return _schema_response(service.get_schema(version_id, principal))


@router.post(
    "/dataset-versions/{version_id}/validate",
    response_model=DatasetValidationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def validate_dataset_version(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetValidationRunResponse:
    return _validation_run_response(service.validate_version(version_id, principal))


@router.get(
    "/dataset-versions/{version_id}/validation-runs",
    response_model=DatasetValidationRunListResponse,
)
def list_dataset_validation_runs(
    version_id: UUID,
    principal: Principal = Depends(get_current_principal),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetValidationRunListResponse:
    return DatasetValidationRunListResponse(
        items=[
            _validation_run_response(run)
            for run in service.list_validation_runs(version_id, principal)
        ]
    )


def _dataset_response(dataset: Dataset) -> DatasetResponse:
    return DatasetResponse(
        id=str(dataset.id),
        organization_id=str(dataset.organization_id),
        project_id=str(dataset.project_id),
        name=dataset.name,
        slug=dataset.slug,
        description=dataset.description,
        source_type=dataset.source_type.value,
        status=dataset.status.value,
    )


def _version_response(version: DatasetVersion) -> DatasetVersionResponse:
    return DatasetVersionResponse(
        id=str(version.id),
        dataset_id=str(version.dataset_id),
        version=version.version,
        object_uri=version.object_uri,
        content_hash=version.content_hash,
        row_count=version.row_count,
        size_bytes=version.size_bytes,
        status=version.status.value,
        created_by=str(version.created_by),
    )


def _schema_response(schema: DatasetSchema) -> DatasetSchemaResponse:
    return DatasetSchemaResponse(
        dataset_version_id=str(schema.dataset_version_id),
        fields=[
            SchemaFieldPayload(name=field.name, dtype=field.dtype, nullable=field.nullable)
            for field in schema.fields
        ],
        inferred=schema.inferred,
        schema_hash=schema.schema_hash,
    )


def _validation_run_response(run: DatasetValidationRun) -> DatasetValidationRunResponse:
    return DatasetValidationRunResponse(
        id=str(run.id),
        dataset_version_id=str(run.dataset_version_id),
        status=run.status.value,
        report=run.report,
        error_message=run.error_message,
    )
