"""
Generates the rag_responses_contract.json handoff file for Person 1 (UI) and Person 2.
"""

import json
from rag_chain import ask_constitutional_rag

QUERIES = [
    "A citizen was detained by the police for 48 hours without being presented before a magistrate. What are their constitutional rights?",
    "Can a state university deny admission to a qualified applicant solely because of their religion or caste?",
    "Does unauthorized state tapping of a citizen's mobile phone violate Article 21?",
    "What are the direct remedies available in the Supreme Court for the enforcement of fundamental rights?",
    "Can the state prohibit peaceful, unarmed assembly of citizens protesting a local grievance?",
    "A consumer bought a brand new washing machine that malfunctioned immediately, and the dealer refused a refund or repair.",
    "A 12-year-old child is being forced to work 10 hours a day in a firecracker manufacturing unit.",
    "What does the Preamble of the Constitution of India declare regarding justice, liberty, and equality?",
    "Can an individual approach the High Court under Article 226 if their civil rights are violated by a government municipal body?",
    "A school refused to admit an 8-year-old child living in a nearby slum, citing lack of birth certificate."
]

def main():
    print("Generating official rag_responses_contract.json for Person 1 / Person 2 handoff...")
    contract_responses = []

    for q in QUERIES:
        resp = ask_constitutional_rag(q)
        contract_responses.append(resp.model_dump())
        print(f" • Processed: {q[:55]}... -> [{resp.recommended_case_category} / {resp.urgency_level}]")

    output_path = "rag_responses_contract.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(contract_responses, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Generated {len(contract_responses)} contract responses saved to '{output_path}'.")

if __name__ == "__main__":
    main()
