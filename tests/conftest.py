import pytest

from evidence_aware_rag.config import Settings
from evidence_aware_rag.corpus import Corpus


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def corpus(settings) -> Corpus:
    return Corpus.load(settings.data_dir)
