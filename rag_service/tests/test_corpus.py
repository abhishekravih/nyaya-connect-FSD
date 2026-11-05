"""
NyayaConnect - Corpus Ingestion and Coverage Test Suite (Reviewer Requirement 4)
Asserts every Article 1 to 395 is present (except an explicit allowlist of repealed ones),
verifies Article 22(4) chunking, asserts chunk size constraints (<150 and >2800),
verifies dynamic schedule page numbers, and checks multi-source statutory corpus expansion.
"""

import os
import re
import json
import pytest

CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "constitution_chunks.json")

# Explicit allowlist of articles genuinely omitted or repealed by Constitutional Amendments:
# - Article 232: Omitted by 7th Amendment, 1956
# - Article 238: Repealed by 7th Amendment, 1956
# - Article 259: Repealed by 7th Amendment, 1956
# - Article 272: Repealed by 80th Amendment, 2000
REPEALED_ARTICLES_ALLOWLIST = {232, 238, 259, 272}


@pytest.fixture(scope="session")
def corpus():
    with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    return chunks


def test_article_1_to_395_coverage(corpus):
    """
    Reviewer Requirement 4:
    Asserts every Article 1 to 395 is present, except an explicit allowlist of repealed ones.
    Specifically checks that previously missing Articles 65, 174, 325, 369, 370, and 371 are present.
    """
    found_articles = set()
    for c in corpus:
        art = c.get("article_number", "")
        m = re.match(r"Article\s+(\d+[A-Z]?)", art)
        if m:
            found_articles.add(m.group(1))

    # Test previously missing articles specifically
    for critical_art in ["65", "174", "325", "369", "370", "371"]:
        assert critical_art in found_articles, f"Article {critical_art} must be present in the ingested corpus"

    # Test all 1 to 395
    missing_numbers = []
    for i in range(1, 396):
        if i not in REPEALED_ARTICLES_ALLOWLIST and str(i) not in found_articles:
            missing_numbers.append(i)

    assert len(missing_numbers) == 0, f"Missing non-repealed articles from 1-395: {missing_numbers}"


def test_article_22_clause_4_chunk(corpus):
    """
    Reviewer Requirement 4:
    Make sure Article 22(4) gets its own chunk.
    """
    clause_4_found = False
    for c in corpus:
        if c.get("article_number") == "Article 22" and ("(4)" in c.get("clause", "") or "Clause (4)" in c.get("title", "")):
            clause_4_found = True
            assert "preventive detention" in c.get("text", "").lower()
            break
    assert clause_4_found, "Article 22(4) must exist as an independent semantic chunk"


def test_chunk_size_constraints(corpus):
    """
    Reviewer Requirement 4:
    Merge chunks under about 150 characters into their parent, and split the 2,800-character ones.
    """
    for c in corpus:
        text_len = len(c["text"])
        assert text_len >= 150, f"Chunk '{c['id']}' has length {text_len} < 150 characters"
        assert text_len <= 2800, f"Chunk '{c['id']}' has length {text_len} > 2800 characters"


def test_schedule_page_numbers_not_hardcoded(corpus):
    """
    Reviewer Requirement 4:
    Compute real page numbers for schedules instead of the hardcoded 284.
    """
    schedule_chunks = [c for c in corpus if c.get("part") == "Schedules"]
    assert len(schedule_chunks) > 0, "Schedule chunks must exist"
    
    unique_pages = set(c["page_number"] for c in schedule_chunks)
    assert len(unique_pages) > 5, "Schedules must span multiple distinct pages (not hardcoded to 284)"
    assert any(c["page_number"] > 300 for c in schedule_chunks), "Later schedules should have page numbers > 300"


def test_expanded_corpus_sources(corpus):
    """
    Reviewer Requirement 5:
    Expand corpus with Consumer Protection Act 2019, BNS, BNSS, RTI Act, and Landmark Judgments.
    """
    source_types = set(c.get("source_type", "") for c in corpus)
    assert "Constitution" in source_types
    assert "Statute" in source_types
    assert "Landmark Judgment" in source_types

    cpa_chunks = [c for c in corpus if "Consumer Protection Act" in c.get("source", "")]
    assert len(cpa_chunks) >= 4, "Must contain Consumer Protection Act chunks"

    bnss_chunks = [c for c in corpus if "Bharatiya Nagarik Suraksha" in c.get("source", "")]
    assert len(bnss_chunks) >= 4, "Must contain BNSS chunks"

    bns_chunks = [c for c in corpus if "Bharatiya Nyaya Sanhita" in c.get("source", "")]
    assert len(bns_chunks) >= 2, "Must contain BNS chunks"

    rti_chunks = [c for c in corpus if "Right to Information" in c.get("source", "")]
    assert len(rti_chunks) >= 2, "Must contain RTI Act chunks"

    precedent_chunks = [c for c in corpus if c.get("source_type") == "Landmark Judgment"]
    assert len(precedent_chunks) >= 5, "Must contain landmark judgments (Maneka Gandhi, D.K. Basu, Puttaswamy, etc.)"
