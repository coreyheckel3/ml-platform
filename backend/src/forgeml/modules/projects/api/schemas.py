from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)
    description: str = Field(default="", max_length=2000)


class ProjectResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    slug: str
    description: str
    status: str
    owner_user_id: str


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    next_cursor: str | None = None

