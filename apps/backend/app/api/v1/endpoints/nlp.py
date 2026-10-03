"""Synchronous entry points for deterministic NLP processing."""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_nlp_service
from app.nlp.taxonomy import load_initial_taxonomy
from app.schemas.nlp import NLPPreprocessRequest, NLPPreprocessResponse, RuleClassificationResponse
from app.services.nlp import NLPService
from app.nlp.contracts import ArtifactVersions, NLPJobRequest
from app.schemas.nlp import NLPJobAccepted, NLPJobCreate, TaxonomyResponse

router = APIRouter()


@router.get(
    "/taxonomy",
    response_model=TaxonomyResponse,
    summary="List the sector/rubro taxonomy",
    description="Full category -> subcategory -> concept tree used to classify tenders "
    "(includes every rubro, e.g. health, construction, apparel).",
)
def get_taxonomy() -> TaxonomyResponse:
    taxonomy = load_initial_taxonomy()
    return TaxonomyResponse.model_validate(taxonomy, from_attributes=True)


@router.post("/preprocess", response_model=NLPPreprocessResponse, summary="Normalize tender text")
def preprocess(request: NLPPreprocessRequest, service: NLPService = Depends(get_nlp_service)) -> NLPPreprocessResponse:
    return service.preprocess(request.text)


@router.post("/classify", response_model=RuleClassificationResponse, summary="Classify clear cases with rules")
def classify(request: NLPPreprocessRequest, service: NLPService = Depends(get_nlp_service)) -> RuleClassificationResponse:
    return service.classify_by_rules(request.text)


@router.post("/jobs", response_model=NLPJobAccepted, status_code=202, summary="Queue an NLP pipeline job")
def create_job(request: NLPJobCreate, service: NLPService = Depends(get_nlp_service)) -> NLPJobAccepted:
    task_id = service.submit(NLPJobRequest(
        licitacion_id=request.licitacion_id,
        text_hash=request.text_hash,
        versions=ArtifactVersions(
            taxonomy=request.taxonomy_version,
            semantic_dictionary=request.dictionary_version,
            model=request.model_version,
            embedding_model=request.embedding_model_version,
        ),
    ))
    return NLPJobAccepted(task_id=task_id)
