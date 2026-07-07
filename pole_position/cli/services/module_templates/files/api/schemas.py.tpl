from pydantic import BaseModel, ConfigDict, Field


class {{class_name}}Create(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class {{class_name}}Read(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
