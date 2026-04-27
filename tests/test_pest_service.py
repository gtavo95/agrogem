from __future__ import annotations

from domain.pest.schema import PestMatch
from domain.pest.service import (
    QUERY_CONTENT_TYPE,
    QUERY_PREFIX,
    generate_pest_upload_url,
    identify_pest,
)
from tests.conftest import FakePestEmbedder, FakePestRepository, FakePestStorage


def test_generate_upload_url_produces_unique_path():
    storage = FakePestStorage()

    first = generate_pest_upload_url(storage)
    second = generate_pest_upload_url(storage)

    assert first.object_path != second.object_path
    assert first.object_path.startswith(QUERY_PREFIX)
    assert first.content_type == QUERY_CONTENT_TYPE
    assert first.expires_in_seconds == 15 * 60
    assert "https://fake.storage" in first.signed_url


async def test_identify_pest_no_matches_returns_empty_response():
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=[])

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    assert result.top_match is None
    assert result.alternatives == []
    assert result.votes == {}


async def test_identify_pest_dominant_match_above_threshold():
    # All 5 neighbors are the same class with high similarity
    matches = [PestMatch(pest_name="aphid", similarity=0.9) for _ in range(5)]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    assert result.top_match is not None
    assert result.top_match.pest_name == "aphid"
    # ratio = 4.5/4.5 = 1.0 -> "high"
    assert result.top_match.confidence == "high"
    assert len(result.alternatives) == 5


async def test_identify_pest_below_threshold_returns_no_top_match():
    # Highly ambiguous: 3 classes with similar weight -> ratio below MIN_CONFIDENCE_RATIO (0.827)
    matches = [
        PestMatch(pest_name="aphid", similarity=0.5),
        PestMatch(pest_name="whitefly", similarity=0.5),
        PestMatch(pest_name="thrip", similarity=0.5),
    ]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    assert result.top_match is None
    # But alternatives and votes are still reported
    assert len(result.alternatives) == 3
    assert len(result.votes) == 3


async def test_identify_pest_negative_similarity_does_not_contribute():
    """Similarities below 0 are clamped to 0 in the weighted vote."""
    matches = [
        PestMatch(pest_name="aphid", similarity=0.9),
        PestMatch(pest_name="aphid", similarity=0.8),
        PestMatch(pest_name="whitefly", similarity=-0.2),
    ]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    # whitefly contributes 0 weight, so aphid dominates with ratio 1.0
    assert result.top_match is not None
    assert result.top_match.pest_name == "aphid"
    assert result.votes["whitefly"] == 0.0


async def test_identify_pest_k_parameter_is_forwarded():
    matches = [PestMatch(pest_name="aphid", similarity=0.9) for _ in range(10)]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    await identify_pest(embedder, storage, repo, "queries/abc.jpg", k=3)

    assert repo.received_k == 3


async def test_identify_pest_just_below_min_ratio_returns_no_top_match():
    # ratio = 0.8 / 1.0 = 0.8 < MIN (0.827) -> descartado
    matches = [
        PestMatch(pest_name="aphid", similarity=0.8),
        PestMatch(pest_name="whitefly", similarity=0.2),
    ]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    assert result.top_match is None


async def test_identify_pest_medium_confidence_between_min_and_high():
    # ratio = 0.9 / 1.0 = 0.9 -> >= MIN (0.827), < HIGH (0.95) -> "medium"
    matches = [
        PestMatch(pest_name="aphid", similarity=0.9),
        PestMatch(pest_name="whitefly", similarity=0.1),
    ]
    embedder = FakePestEmbedder()
    storage = FakePestStorage(data={"queries/abc.jpg": b"img"})
    repo = FakePestRepository(matches=matches)

    result = await identify_pest(embedder, storage, repo, "queries/abc.jpg")

    assert result.top_match is not None
    assert result.top_match.pest_name == "aphid"
    assert result.top_match.confidence == "medium"
