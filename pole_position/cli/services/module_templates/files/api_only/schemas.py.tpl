from pydantic import BaseModel, Field


class {{class_name}}Request(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class {{class_name}}Response(BaseModel):
    name: str
    message: str
