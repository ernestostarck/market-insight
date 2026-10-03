from pydantic import BaseModel, ConfigDict, Field


class DocumentUploadResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "bucket": "documents-private",
                "object_name": "sample.txt",
                "uri": "s3://documents-private/sample.txt",
                "is_public": False,
            }
        },
    )

    bucket: str = Field(..., description="Object storage bucket the file was written to.")
    object_name: str = Field(..., description="Key/path of the stored object.")
    uri: str = Field(..., description="Internal storage URI (`s3://bucket/object_name`).")
    is_public: bool = Field(..., description="Whether the object is in the public bucket.")


class DocumentDownloadUrlResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "bucket": "documents-public",
                "object_name": "public.txt",
                "download_url": "http://minio:9000/documents-public/public.txt",
                "is_public": True,
            }
        },
    )

    bucket: str = Field(..., description="Object storage bucket holding the file.")
    object_name: str = Field(..., description="Key/path of the stored object.")
    download_url: str = Field(
        ..., description="Direct URL for public files, or a time-limited signed URL for private ones."
    )
    is_public: bool = Field(..., description="Whether the object is in the public bucket.")
