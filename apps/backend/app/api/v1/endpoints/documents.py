from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from app.api.deps.settings import Settings, get_settings
from app.api.deps.use_cases import (
    DocumentStorageUseCase,
    get_document_storage_use_case,
)
from app.schemas.documents import (
    DocumentDownloadUrlResponse,
    DocumentUploadResponse,
)

router = APIRouter()


@router.post(
    "/{object_name}",
    response_model=DocumentUploadResponse,
    tags=["Documents"],
    summary="Upload a document",
    description="Uploads a file to object storage under `object_name`. Public documents "
    "are stored in the public bucket and served without a signed URL; private documents "
    "require `GET /documents/{object_name}/download-url` to obtain a signed link.",
)
async def upload_document(
    object_name: str,
    file: UploadFile = File(..., description="The file contents to store."),
    is_public: bool = Form(False, description="Store in the public bucket instead of private."),
    settings: Settings = Depends(get_settings),
    use_case: DocumentStorageUseCase = Depends(get_document_storage_use_case),
) -> DocumentUploadResponse:
    payload = await file.read()
    stored_document = use_case.store_document(
        settings=settings,
        object_name=object_name,
        data=payload,
        content_type=file.content_type or "application/octet-stream",
        is_public=is_public,
        original_filename=file.filename,
    )
    return DocumentUploadResponse.model_validate(stored_document)


@router.get(
    "/{object_name}",
    tags=["Documents"],
    summary="Download a document",
    description="Streams the raw file bytes for a previously uploaded document.",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_document(
    object_name: str,
    settings: Settings = Depends(get_settings),
    use_case: DocumentStorageUseCase = Depends(get_document_storage_use_case),
) -> Response:
    payload = use_case.fetch_document(settings=settings, object_name=object_name)
    return Response(content=payload, media_type="application/octet-stream")


@router.get(
    "/{object_name}/download-url",
    response_model=DocumentDownloadUrlResponse,
    tags=["Documents"],
    summary="Get a document's download URL",
    description="Returns the direct URL for public documents, or a time-limited signed "
    "URL for private ones.",
)
def document_download_url(
    object_name: str,
    settings: Settings = Depends(get_settings),
    use_case: DocumentStorageUseCase = Depends(get_document_storage_use_case),
) -> DocumentDownloadUrlResponse:
    download_link = use_case.get_download_link(
        settings=settings, object_name=object_name
    )
    return DocumentDownloadUrlResponse.model_validate(download_link)
