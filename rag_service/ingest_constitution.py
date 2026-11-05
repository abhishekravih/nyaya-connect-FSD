"""
NyayaConnect - Constitutional Semantic Chunking & Ingestion Pipeline
Extracts Articles 1-395, Preamble, and Schedules 1-12 from the official
Constitution of India PDF with legal clause boundary preservation.
"""

import os
import re
import json
import fitz  # PyMuPDF
from typing import List, Dict, Any

PDF_PATH = os.path.join(os.path.dirname(__file__), "data", "constitution_of_india.pdf")
OUTPUT_CHUNKS_PATH = os.path.join(os.path.dirname(__file__), "data", "constitution_chunks.json")

# Mapping of Roman Numerals to Part Names for clean metadata
ROMAN_PARTS = {
    "I": "The Union and its Territory",
    "II": "Citizenship",
    "III": "Fundamental Rights",
    "IV": "Directive Principles of State Policy",
    "IVA": "Fundamental Duties",
    "V": "The Union",
    "VI": "The States",
    "VIII": "The Union Territories",
    "IX": "The Panchayats",
    "IXA": "The Municipalities",
    "IXB": "The Co-operative Societies",
    "X": "The Scheduled and Tribal Areas",
    "XI": "Relations between the Union and the States",
    "XII": "Finance, Property, Contracts and Suits",
    "XIII": "Trade, Commerce and Intercourse within the Territory of India",
    "XIV": "Services under the Union and the States",
    "XIVA": "Tribunals",
    "XV": "Elections",
    "XVI": "Special Provisions relating to Certain Classes",
    "XVII": "Official Language",
    "XVIII": "Emergency Provisions",
    "XIX": "Miscellaneous",
    "XX": "Amendment of the Constitution",
    "XXI": "Temporary, Transitional and Special Provisions",
    "XXII": "Short Title, Commencement, Authoritative Text in Hindi and Repeals"
}


def clean_page_text(text: str) -> str:
    """Removes running headers and isolated page numbers."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip bare page numbers or gazette top-running header
        if stripped.isdigit() and len(stripped) <= 3:
            continue
        if stripped == "THE CONSTITUTION OF INDIA":
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def extract_preamble(doc: fitz.Document) -> Dict[str, Any]:
    """Extracts the Preamble from Page 31 (0-indexed)."""
    text = doc[31].get_text()
    match = re.search(r"PREAMBLE\s*\n+(.*?)(?=PART I|\Z)", text, re.DOTALL)
    preamble_body = match.group(1).strip() if match else text.strip()
    
    # Clean bracketed footnotes e.g. 1[SOVEREIGN ... ]
    cleaned_preamble = re.sub(r"\d+\[", "", preamble_body).replace("]", "")
    # Format nicely
    cleaned_preamble = " ".join(cleaned_preamble.split())

    return {
        "id": "art_preamble",
        "article_number": "Preamble",
        "title": "Preamble to the Constitution of India",
        "part": "Preamble",
        "clause": "Full",
        "text": f"PREAMBLE TO THE CONSTITUTION OF INDIA\n\n{cleaned_preamble}",
        "source": "Constitution of India (Official Gazetted Edition)",
        "page_number": 32,
        "char_count": len(cleaned_preamble)
    }


def chunk_article(article_num: str, title: str, part: str, full_body: str, page_num: int, art_idx: int) -> List[Dict[str, Any]]:
    """
    Chunks an article. If article has multiple clauses (1), (2), (3) and is > 1000 chars,
    splits cleanly by clause boundary while preserving header context.
    """
    clean_body = re.sub(r"\d+\[", "", full_body).replace("]", "")
    clean_title = " ".join(title.split()).rstrip("—–. ")

    # Check for clause markers (1), (2), (3)...
    clause_splits = list(re.finditer(r"(?:^|\n)\s*(\(\d+\))\s+", clean_body))
    
    if len(clean_body) <= 1200 or len(clause_splits) <= 1:
        # Keep entire article as a single cohesive semantic unit
        text_content = f"Article {article_num}: {clean_title}\nPart: {part}\n\n{clean_body.strip()}"
        return [{
            "id": f"art_{article_num.lower()}_{art_idx}",
            "article_number": f"Article {article_num}",
            "title": clean_title,
            "part": part,
            "clause": "Full",
            "text": text_content,
            "source": "Constitution of India",
            "page_number": page_num,
            "char_count": len(text_content)
        }]

    # Split by clause boundaries
    chunks = []
    for i, match in enumerate(clause_splits):
        clause_id = match.group(1)
        start_idx = match.start()
        end_idx = clause_splits[i + 1].start() if i + 1 < len(clause_splits) else len(clean_body)
        clause_text = clean_body[start_idx:end_idx].strip()
        
        # Build contextualized text
        chunk_text = (
            f"Article {article_num}: {clean_title}\n"
            f"Part: {part}\n"
            f"Clause {clause_id}: {clause_text}"
        )
        clause_num_clean = clause_id.strip("()")
        chunks.append({
            "id": f"art_{article_num.lower()}_{art_idx}_c{clause_num_clean}_{i+1}",
            "article_number": f"Article {article_num}",
            "title": f"{clean_title} - Clause {clause_id}",
            "part": part,
            "clause": clause_id,
            "text": chunk_text,
            "source": "Constitution of India",
            "page_number": page_num,
            "char_count": len(chunk_text)
        })

    return chunks


def extract_articles_and_schedules(doc: fitz.Document) -> List[Dict[str, Any]]:
    """
    Iterates through Constitution pages 32 to end, tracking Part changes,
    Article headers, and Schedules.
    """
    all_chunks = []
    
    # 1. Preamble
    preamble = extract_preamble(doc)
    all_chunks.append(preamble)

    # Combine text from page 32 to page 282 (Articles 1 to 395)
    articles_stream = []
    for pno in range(32, 283):
        raw_text = clean_page_text(doc[pno].get_text())
        articles_stream.append((pno + 1, raw_text))

    # Regex for PART headings
    part_pattern = re.compile(r"(?:^|\n)\s*PART\s+([IVXLCDMA-Z]+)\s*\n+([A-Z\s,–—]+)", re.MULTILINE)
    
    # Regex for Article headings: e.g. "21. Protection of life and personal liberty.—"
    # Also handles footnote prefix e.g. "1[21A. Right to education.—"
    article_pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+\[)?(\d+[A-Z]?)\.\s+([^\n—–]+(?:\n[^\n—–]+)?)\s*[—–]\s*",
        re.MULTILINE
    )

    # Process all article pages as a contiguous legal document with page-offset index
    full_text = ""
    page_offsets = [] # (start_char_idx, page_number)
    
    for page_num, page_txt in articles_stream:
        start_idx = len(full_text)
        page_offsets.append((start_idx, page_num))
        full_text += page_txt + "\n"

    def get_page_for_idx(char_idx: int) -> int:
        for offset, pno in reversed(page_offsets):
            if char_idx >= offset:
                return pno
        return 33

    # Find all Part transitions
    parts = []
    for m in part_pattern.finditer(full_text):
        part_num = m.group(1).strip()
        part_title = " ".join(m.group(2).split()).title()
        if part_num in ROMAN_PARTS:
            part_title = ROMAN_PARTS[part_num]
        parts.append((m.start(), f"Part {part_num} - {part_title}"))

    def get_part_for_idx(char_idx: int) -> str:
        current_part = "Part I - The Union and its Territory"
        for offset, p_name in parts:
            if char_idx >= offset:
                current_part = p_name
            else:
                break
        return current_part

    # Find all Articles
    article_matches = list(article_pattern.finditer(full_text))
    print(f"Detected {len(article_matches)} Constitutional Article sections in text stream.")

    for i, match in enumerate(article_matches):
        art_num = match.group(1)
        raw_title = match.group(2)
        start_pos = match.end()
        end_pos = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(full_text)

        body = full_text[start_pos:end_pos].strip()
        page_num = get_page_for_idx(match.start())
        part_name = get_part_for_idx(match.start())

        chunks = chunk_article(art_num, raw_title, part_name, body, page_num, i)
        all_chunks.extend(chunks)

    # Process Schedules (Pages 283 to end)
    print("Processing Schedules 1 to 12...")
    sched_text = ""
    sched_offsets = []
    for pno in range(283, len(doc)):
        start_idx = len(sched_text)
        sched_offsets.append((start_idx, pno + 1))
        sched_text += clean_page_text(doc[pno].get_text()) + "\n"

    schedule_pattern = re.compile(
        r"(?:^|\n)\s*(?:\d+\[)?(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+SCHEDULE",
        re.IGNORECASE
    )

    sched_matches = list(schedule_pattern.finditer(sched_text))
    for i, sm in enumerate(sched_matches):
        sched_name = sm.group(1).title() + " Schedule"
        s_start = sm.end()
        s_end = sched_matches[i + 1].start() if i + 1 < len(sched_matches) else len(sched_text)
        s_body = sched_text[s_start:s_end].strip()
        
        # Sub-chunk schedule if very large (e.g. Seventh Schedule: Union, State, Concurrent lists)
        if len(s_body) > 2000:
            sub_chunks = [s_body[j:j+1800] for j in range(0, len(s_body), 1500)]
            for sub_idx, sc in enumerate(sub_chunks):
                all_chunks.append({
                    "id": f"sched_{sched_name.lower().replace(' ', '_')}_part_{sub_idx+1}",
                    "article_number": sched_name,
                    "title": f"{sched_name} (Part {sub_idx+1})",
                    "part": "Schedules",
                    "clause": f"Section {sub_idx+1}",
                    "text": f"{sched_name} - Part {sub_idx+1}\n\n{sc.strip()}",
                    "source": "Constitution of India",
                    "page_number": 284,
                    "char_count": len(sc)
                })
        else:
            all_chunks.append({
                "id": f"sched_{sched_name.lower().replace(' ', '_')}",
                "article_number": sched_name,
                "title": sched_name,
                "part": "Schedules",
                "clause": "Full",
                "text": f"{sched_name}\n\n{s_body}",
                "source": "Constitution of India",
                "page_number": 284,
                "char_count": len(s_body)
            })

    # Ensure strictly unique IDs across all chunks
    seen_ids = set()
    for idx, c in enumerate(all_chunks):
        base_id = c["id"]
        unique_id = base_id
        counter = 1
        while unique_id in seen_ids:
            unique_id = f"{base_id}_{counter}"
            counter += 1
        seen_ids.add(unique_id)
        c["id"] = unique_id

    return all_chunks


def main():
    print("=" * 70)
    print("🇮🇳 NyayaConnect - Constitutional Ingestion Pipeline")
    print(f"Reading document: {PDF_PATH}")
    print("=" * 70)

    if not os.path.exists(PDF_PATH):
        raise FileNotFoundError(f"PDF not found at {PDF_PATH}")

    doc = fitz.open(PDF_PATH)
    print(f"Loaded {len(doc)} pages.")

    chunks = extract_articles_and_schedules(doc)
    doc.close()

    os.makedirs(os.path.dirname(OUTPUT_CHUNKS_PATH), exist_ok=True)
    with open(OUTPUT_CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("✅ Ingestion & Semantic Chunking Summary:")
    print(f" • Total chunks created: {len(chunks)}")
    avg_chars = sum(c["char_count"] for c in chunks) // len(chunks) if chunks else 0
    print(f" • Average chunk length: {avg_chars} characters")
    print(f" • Saved structured chunks to: {OUTPUT_CHUNKS_PATH}")
    print("=" * 70)


if __name__ == "__main__":
    main()
