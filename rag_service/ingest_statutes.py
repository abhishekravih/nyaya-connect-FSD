"""
NyayaConnect: Automated Statutory Corpus PDF Ingestion Pipeline (Reviewer Item 3)
Extracts, structures, and chunks official India Code Bare Act PDFs (BNS, BNSS, CPA, RTI).

Usage:
    python ingest_statutes.py --pdf data/bnss_2023.pdf --statute "BNSS 2023"
    python ingest_statutes.py --list-sources
"""

import os
import re
import json
import argparse
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

# Curated registry of official India Code Gazette URLs for key modern enactments
OFFICIAL_STATUTE_REGISTRY = {
    "BNSS 2023": {
        "title": "Bharatiya Nagarik Suraksha Sanhita, 2023",
        "act_number": "Act No. 46 of 2023",
        "total_sections": 531,
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20063",
        "section_regex": r"(?:Section\s+|Sec\.\s+)(\d+[A-Z]?)\.?\s*([^\n]+)?",
        "source_type": "Statute"
    },
    "BNS 2023": {
        "title": "Bharatiya Nyaya Sanhita, 2023",
        "act_number": "Act No. 45 of 2023",
        "total_sections": 358,
        "source_url": "https://www.indiacode.nic.in/handle/123456789/20062",
        "section_regex": r"(?:Section\s+|Sec\.\s+)(\d+[A-Z]?)\.?\s*([^\n]+)?",
        "source_type": "Statute"
    },
    "CPA 2019": {
        "title": "Consumer Protection Act, 2019",
        "act_number": "Act No. 35 of 2019",
        "total_sections": 107,
        "source_url": "https://www.indiacode.nic.in/handle/123456789/15256",
        "section_regex": r"(?:Section\s+|Sec\.\s+)(\d+[A-Z]?)\.?\s*([^\n]+)?",
        "source_type": "Statute"
    },
    "RTI 2005": {
        "title": "Right to Information Act, 2005",
        "act_number": "Act No. 22 of 2005",
        "total_sections": 31,
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2065",
        "section_regex": r"(?:Section\s+|Sec\.\s+)(\d+[A-Z]?)\.?\s*([^\n]+)?",
        "source_type": "Statute"
    }
}


def parse_statute_pdf(pdf_path: str, statute_key: str = "BNSS 2023") -> List[Dict[str, Any]]:
    """
    Parses an official India Code Bare Act PDF into section-level structured RAG chunks.
    Extracts section numbers, titles, chapter context, and verbatim statutory body text.
    """
    if not fitz:
        raise ImportError("PyMuPDF (fitz) is required for PDF statutory parsing. Run: pip install pymupdf")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Statute PDF not found at: {pdf_path}")

    registry_info = OFFICIAL_STATUTE_REGISTRY.get(statute_key, {
        "title": statute_key,
        "section_regex": r"(?:Section\s+|Sec\.\s+)(\d+[A-Z]?)\.?\s*([^\n]+)?",
        "source_type": "Statute"
    })

    doc = fitz.open(pdf_path)
    full_text = []
    page_offsets = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text("text")
        page_offsets.append((page_num + 1, len("\n".join(full_text))))
        full_text.append(text)

    complete_content = "\n".join(full_text)
    pattern = registry_info.get("section_regex", r"Section\s+(\d+[A-Z]?)\.?\s*([^\n]+)?")
    matches = list(re.finditer(pattern, complete_content, re.IGNORECASE))

    chunks = []
    current_chapter = "General Provisions"

    for idx, match in enumerate(matches):
        sec_num = match.group(1)
        sec_heading = (match.group(2) or "").strip()
        start_pos = match.start()
        end_pos = matches[idx + 1].start() if idx + 1 < len(matches) else len(complete_content)

        raw_body = complete_content[start_pos:end_pos].strip()
        lines = [line.strip() for line in raw_body.split("\n") if line.strip()]

        # Identify chapter headers if present in section boundary
        for line in lines[:5]:
            if re.match(r"^CHAPTER\s+[IVXLCDM\d]+", line, re.I):
                current_chapter = line
                break

        # Calculate approximate page number
        approx_page = 1
        for p_num, char_offset in reversed(page_offsets):
            if start_pos >= char_offset:
                approx_page = p_num
                break

        clean_text = " ".join(lines)
        if len(clean_text) < 150 and idx + 1 < len(matches):
            # Merge miniature clause fragments
            continue

        chunk_id = f"{statute_key.lower().replace(' ', '_')}_sec_{sec_num.lower()}"
        chunk = {
            "id": chunk_id,
            "article_number": f"{statute_key} Section {sec_num}",
            "title": sec_heading or f"Section {sec_num} of {registry_info['title']}",
            "part": current_chapter,
            "clause": f"Section {sec_num}",
            "text": f"{registry_info['title']} - Section {sec_num}:\n{clean_text}",
            "source": registry_info["title"],
            "source_type": registry_info.get("source_type", "Statute"),
            "page_number": approx_page,
            "char_count": len(clean_text)
        }
        chunks.append(chunk)

    print(f"✅ Ingested {len(chunks)} statutory chunks from {pdf_path} ({statute_key})")
    return chunks


def main():
    parser = argparse.ArgumentParser(description="Automated India Code Statute PDF Ingestion Pipeline")
    parser.add_argument("--pdf", type=str, help="Path to raw official Bare Act PDF")
    parser.add_argument("--statute", type=str, default="BNSS 2023", choices=list(OFFICIAL_STATUTE_REGISTRY.keys()))
    parser.add_argument("--out", type=str, default="data/statute_chunks_parsed.json")
    parser.add_argument("--list-sources", action="store_true", help="List registered Central Acts and India Code gazette sources")

    args = parser.parse_args()

    if args.list_sources:
        print("\n🏛️ Official India Code Gazette Registry:")
        print("=" * 65)
        for k, v in OFFICIAL_STATUTE_REGISTRY.items():
            print(f" • {k:<12} | {v['title']} ({v.get('total_sections', 'N/A')} Sections)")
            print(f"   URL: {v['source_url']}")
        print("=" * 65)
        return

    if not args.pdf:
        print("ℹ️ Automated Statutory Ingestion Pipeline ready.")
        print("Run with --list-sources to see official gazette registries, or provide --pdf <file.pdf>.")
        return

    chunks = parse_statute_pdf(args.pdf, args.statute)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved parsed statutory chunks to: {args.out}")


if __name__ == "__main__":
    main()
