"""NLP application services package (Fase 6.18)."""

from app.services.nlp.classification import ClassificationService
from app.services.nlp.dictionary import DictionaryService
from app.services.nlp.embeddings import EmbeddingService
from app.services.nlp.entities import EntityExtractionService
from app.services.nlp.facade import NLPService
from app.services.nlp.interfaces import (
    IClassificationService,
    IDictionaryService,
    IEmbeddingService,
    IEntityExtractionService,
    IModelManagementService,
    IPreprocessingService,
    IProductExtractionService,
    IRelevanceService,
    IReviewService,
    IRuleClassificationService,
    ISemanticSearchService,
    ITaxonomyService,
)
from app.services.nlp.model_management import ModelManagementService
from app.services.nlp.preprocessing import PreprocessingService
from app.services.nlp.products import ProductExtractionService
from app.services.nlp.relevance import RelevanceService
from app.services.nlp.review import ReviewService
from app.services.nlp.rules import RuleClassificationService
from app.services.nlp.semantic_search import SemanticSearchService
from app.services.nlp.taxonomy import TaxonomyService

__all__ = [
    "ClassificationService",
    "DictionaryService",
    "EmbeddingService",
    "EntityExtractionService",
    "IClassificationService",
    "IDictionaryService",
    "IEmbeddingService",
    "IEntityExtractionService",
    "IModelManagementService",
    "IPreprocessingService",
    "IProductExtractionService",
    "IRelevanceService",
    "IReviewService",
    "IRuleClassificationService",
    "ISemanticSearchService",
    "ITaxonomyService",
    "ModelManagementService",
    "NLPService",
    "PreprocessingService",
    "ProductExtractionService",
    "RelevanceService",
    "ReviewService",
    "RuleClassificationService",
    "SemanticSearchService",
    "TaxonomyService",
]
