import os
from pathlib import Path

import pytest

os.environ["KARAR_OFFLINE"] = "1"  # tests never call real Google APIs unless mocked
os.environ["RATE_LIMIT_PER_MIN"] = "1000"

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def load(name: str) -> str:
    return (SAMPLES / name).read_text(encoding="utf-8")


@pytest.fixture
def one_sided() -> str:
    return load("rental_agreement_one_sided.txt")


@pytest.fixture
def balanced() -> str:
    return load("rental_agreement_balanced.txt")


@pytest.fixture
def gig() -> str:
    return load("gig_partner_agreement.txt")


@pytest.fixture
def offer() -> str:
    return load("offer_letter.txt")


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app import main

    main._cache.clear()
    main._hits.clear()
    return TestClient(main.app)
