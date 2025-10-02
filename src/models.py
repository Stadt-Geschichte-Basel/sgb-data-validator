"""Pydantic models for Omeka S data validation"""

from typing import Any

from pydantic import BaseModel, Field, field_validator


class OmekaProperty(BaseModel):
    """Base model for Omeka properties"""

    type: str
    property_id: int
    property_label: str
    is_public: bool
    value: str | None = Field(None, alias="@value")
    id: str | None = Field(None, alias="@id")
    language: str | None = Field(None, alias="@language")
    label: str | None = Field(None, alias="o:label")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @field_validator("value")
    @classmethod
    def value_not_empty(cls, v: str | None) -> str | None:
        """Ensure value is not empty if present"""
        if v is not None and isinstance(v, str) and v.strip() == "":
            raise ValueError("Value cannot be empty")
        return v


class DateTimeValue(BaseModel):
    """Datetime value from Omeka"""

    value: str = Field(alias="@value")
    type: str = Field(alias="@type")

    model_config = {"populate_by_name": True}


class ResourceRef(BaseModel):
    """Reference to another Omeka resource"""

    id: str = Field(alias="@id")
    o_id: int = Field(alias="o:id")

    model_config = {"populate_by_name": True, "extra": "allow"}


class Item(BaseModel):
    """Omeka S Item model"""

    context: str = Field(alias="@context")
    id: str = Field(alias="@id")
    type: str = Field(alias="@type")
    o_id: int = Field(alias="o:id")
    o_is_public: bool = Field(alias="o:is_public")
    o_owner: ResourceRef | None = Field(None, alias="o:owner")
    o_resource_class: ResourceRef | None = Field(None, alias="o:resource_class")
    o_resource_template: ResourceRef | None = Field(None, alias="o:resource_template")
    o_thumbnail: Any | None = Field(None, alias="o:thumbnail")
    o_title: str = Field(alias="o:title")
    thumbnail_display_urls: dict[str, str] | None = Field(
        None, alias="thumbnail_display_urls"
    )
    o_created: DateTimeValue = Field(alias="o:created")
    o_modified: DateTimeValue = Field(alias="o:modified")
    o_media: list[ResourceRef] = Field(default_factory=list, alias="o:media")
    o_item_set: list[ResourceRef] = Field(default_factory=list, alias="o:item_set")
    o_site: list[Any] = Field(default_factory=list, alias="o:site")

    # Dublin Core Terms
    dcterms_identifier: list[OmekaProperty] | None = Field(
        None, alias="dcterms:identifier"
    )
    dcterms_title: list[OmekaProperty] = Field(alias="dcterms:title")
    dcterms_subject: list[OmekaProperty] | None = Field(None, alias="dcterms:subject")
    dcterms_description: list[OmekaProperty] | None = Field(
        None, alias="dcterms:description"
    )
    dcterms_temporal: list[OmekaProperty] | None = Field(None, alias="dcterms:temporal")
    dcterms_language: list[OmekaProperty] | None = Field(None, alias="dcterms:language")
    dcterms_isPartOf: list[OmekaProperty] | None = Field(None, alias="dcterms:isPartOf")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @field_validator("o_title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty"""
        if not v or v.strip() == "":
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("dcterms_title")
    @classmethod
    def dcterms_title_not_empty(cls, v: list[OmekaProperty]) -> list[OmekaProperty]:
        """Ensure dcterms:title is not empty"""
        if not v:
            raise ValueError("dcterms:title is required")
        if v[0].value and v[0].value.strip() == "":
            raise ValueError("dcterms:title value cannot be empty")
        return v


class Media(BaseModel):
    """Omeka S Media model"""

    context: str = Field(alias="@context")
    id: str = Field(alias="@id")
    type: str = Field(alias="@type")
    o_id: int = Field(alias="o:id")
    o_is_public: bool = Field(alias="o:is_public")
    o_owner: ResourceRef | None = Field(None, alias="o:owner")
    o_resource_class: ResourceRef | None = Field(None, alias="o:resource_class")
    o_resource_template: ResourceRef | None = Field(None, alias="o:resource_template")
    o_thumbnail: Any | None = Field(None, alias="o:thumbnail")
    o_title: str = Field(alias="o:title")
    thumbnail_display_urls: dict[str, str] | None = Field(
        None, alias="thumbnail_display_urls"
    )
    o_created: DateTimeValue = Field(alias="o:created")
    o_modified: DateTimeValue = Field(alias="o:modified")
    o_ingester: str = Field(alias="o:ingester")
    o_renderer: str = Field(alias="o:renderer")
    o_item: ResourceRef = Field(alias="o:item")
    o_source: str | None = Field(None, alias="o:source")
    o_media_type: str = Field(alias="o:media_type")
    o_sha256: str | None = Field(None, alias="o:sha256")
    o_size: int | None = Field(None, alias="o:size")
    o_filename: str | None = Field(None, alias="o:filename")
    o_lang: str | None = Field(None, alias="o:lang")
    o_alt_text: str | None = Field(None, alias="o:alt_text")
    o_original_url: str | None = Field(None, alias="o:original_url")
    o_thumbnail_urls: dict[str, str] | None = Field(None, alias="o:thumbnail_urls")
    data: list[Any] = Field(default_factory=list)

    # Dublin Core Terms
    dcterms_identifier: list[OmekaProperty] | None = Field(
        None, alias="dcterms:identifier"
    )
    dcterms_title: list[OmekaProperty] = Field(alias="dcterms:title")
    dcterms_subject: list[OmekaProperty] | None = Field(None, alias="dcterms:subject")
    dcterms_description: list[OmekaProperty] | None = Field(
        None, alias="dcterms:description"
    )
    dcterms_creator: list[OmekaProperty] | None = Field(None, alias="dcterms:creator")
    dcterms_publisher: list[OmekaProperty] | None = Field(
        None, alias="dcterms:publisher"
    )
    dcterms_date: list[OmekaProperty] | None = Field(None, alias="dcterms:date")
    dcterms_temporal: list[OmekaProperty] | None = Field(None, alias="dcterms:temporal")
    dcterms_type: list[OmekaProperty] | None = Field(None, alias="dcterms:type")
    dcterms_format: list[OmekaProperty] | None = Field(None, alias="dcterms:format")
    dcterms_extent: list[OmekaProperty] | None = Field(None, alias="dcterms:extent")
    dcterms_source: list[OmekaProperty] | None = Field(None, alias="dcterms:source")
    dcterms_language: list[OmekaProperty] | None = Field(None, alias="dcterms:language")
    dcterms_relation: list[OmekaProperty] | None = Field(None, alias="dcterms:relation")
    dcterms_rights: list[OmekaProperty] | None = Field(None, alias="dcterms:rights")
    dcterms_license: list[OmekaProperty] | None = Field(None, alias="dcterms:license")

    model_config = {"populate_by_name": True, "extra": "allow"}

    @field_validator("o_title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty"""
        if not v or v.strip() == "":
            raise ValueError("Title cannot be empty")
        return v

    @field_validator("o_media_type")
    @classmethod
    def media_type_not_empty(cls, v: str) -> str:
        """Ensure media type is not empty"""
        if not v or v.strip() == "":
            raise ValueError("Media type cannot be empty")
        return v

    @field_validator("dcterms_title")
    @classmethod
    def dcterms_title_not_empty(cls, v: list[OmekaProperty]) -> list[OmekaProperty]:
        """Ensure dcterms:title is not empty"""
        if not v:
            raise ValueError("dcterms:title is required")
        if v[0].value and v[0].value.strip() == "":
            raise ValueError("dcterms:title value cannot be empty")
        return v

    @field_validator("o_original_url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        """Validate URL format"""
        if v and not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v
