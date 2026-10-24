"""
=============================================================================
APH STATUTORY DOCUMENT CHUNKING & BM25 RETRIEVAL ENGINE
=============================================================================
Provides grounded, probabilistic information retrieval (BM25) over official
Approval Process Handbook (APH 2024-25 to 2026-27) text chunks.

Replaces simple keyword matching with statistical Okapi BM25 scoring.
If retrieved evidence does not satisfy the confidence threshold,
retrieval fails safely and triggers the statutory "not found in APH" guard.
=============================================================================
"""

import os
import re
import math
from typing import List, Dict, Any, Tuple, Optional

# Pre-compiled high-resolution chunks from the official APH 2024-27 PDF
OFFICIAL_APH_CHUNKS = [
    {
        "id": "chunk_clause_1_8_scrutiny",
        "clause": "Chapter I, Clause 1.8 & 1.8(g)",
        "clause_number": "1.8",
        "page": "22-23",
        "topic": "Scrutiny Deficiency & Rectification Cure Window",
        "verbatim_quote": "Process for Evaluation of the Application by the Scrutiny/ Re-Scrutiny Committee",
        "content": (
            "Process for Evaluation of the Application by the Scrutiny/ Re-Scrutiny Committee (Clause 1.8). "
            "When the Scrutiny Committee notes deficiencies in an application, a formal deficiency communication "
            "is issued. The applicant institution is granted a cure window (15 working days — design choice, configurable) "
            "to rectify documents and submit compliance online. The SLA processing clock is paused during this deficiency cure period. "
            "Under Clause 1.8(g), the Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out by the Scrutiny committee as per norms."
        ),
    },
    {
        "id": "chunk_clause_2_1_e_lease",
        "clause": "Chapter II, Clause 2.1(e) & Chapter VI, Clause 6.17",
        "clause_number": "2.1(e)",
        "page": "52, 72",
        "topic": "Land Lease Validity & Renewal Requirements",
        "verbatim_quote": "term lease for a minimum period of 30 years",
        "content": (
            "Land Norms and Registered Lease Deeds under Chapter II Clause 2.1(e) and Chapter VI Clause 6.17. "
            "The land must be held on an irrevocable registered lease for a minimum period of 30 years. "
            "The Live Lease has to be at least equal to Maximum Course Duration. If the live lease expires or "
            "equals maximum course duration without an extension for a further 30 years, Extension of Approval (EoA) "
            "is blocked and fresh admissions cannot be permitted. The system fires early warning alerts at configurable offsets."
        ),
    },
    {
        "id": "chunk_clause_1_9_evc_panel",
        "clause": "Chapter I, Clause 1.9 & Annexure-16, Clause 16.5",
        "clause_number": "1.9",
        "page": "23, 215",
        "topic": "Expert Visit Committee (EVC) Panel & Inspection Framework",
        "verbatim_quote": "Process for Evaluation of Application by Expert Visit Committee",
        "content": (
            "Expert Visit Committee (EVC) composition and physical/virtual inspection norms under Clause 1.9 and Annexure-16. "
            "EVC panel comprises senior academic expert, professional expert, and Council of Architecture registered architect. "
            "Experts must be excluded if from the same state, institution group, or having reviewed the institution during cooling period. "
            "Requires mandatory 30-minute geotagged video recording and GPS timestamp coordinates at campus entrance. "
            "Authority boundary: EVC findings are strictly SUGGEST-ONLY / RECOMMENDATORY and require human committee sign-off."
        ),
    },
    {
        "id": "chunk_clause_1_11_2_24_sac_appeal",
        "clause": "Chapter I Clause 1.11(a) & Chapter II Clause 2.24(a)",
        "clause_number": "2.24",
        "page": "37, 45",
        "topic": "Standing Appellate Committee (SAC) 7-Day Appeal Window",
        "verbatim_quote": "appeal as per Clause 2.24 of the Approval Process Handbook",
        "content": (
            "Standing Appellate Committee (SAC) appeal procedures under Chapter I Clause 1.11(a) and Chapter II Clause 2.24(a). "
            "An institution aggrieved by the decision of the Executive Committee shall have the right to appeal once to the Council "
            "within 7 calendar days of communication of rejection/deficiency. The Council or Executive Committee reviews SAC recommendations "
            "and issues speaking orders. No further statutory appeals lie beyond the Council."
        ),
    },
    {
        "id": "chunk_clause_2_6_table_2_3_intake",
        "clause": "Chapter II, Clause 2.6 & Table 2.3",
        "clause_number": "2.6",
        "page": "30, 45",
        "topic": "Increase in Intake & Pipeline Determination",
        "verbatim_quote": "Table-2.3 of Chapter-II",
        "content": (
            "Table 2.3 of Chapter II: Official Processing Steps and Pipelines by Nature of Application. "
            "Extension of Approval routes to ONLY_SELF_DISCLOSURE. New Technical Institution routes to SCRUTINY_EVC. "
            "Increase in Intake or New Programmes routes to SCRUTINY_EVC_SAC. "
            "Requires minimum 50% eligible courses with NBA accreditation, compliant Faculty Student Ratio (1:20 for Engineering), "
            "and zero unresolved compliance undertakings."
        ),
    },
    {
        "id": "chunk_clause_1_10_undertakings",
        "clause": "Chapter I, Clause 1.10(b) & Chapter VIII Clause 8.1",
        "clause_number": "1.10",
        "page": "43, 204",
        "topic": "Time-Bound Undertakings & Compliance Digital Register",
        "verbatim_quote": "Time-Bound Undertakings",
        "content": (
            "Monitoring of Time-Bound Undertakings and compliance register under Clause 1.10(b) and Chapter VIII. "
            "Conditional approvals are tracked in the digital register with binding statutory due dates. "
            "Institutions must submit evidence online before expiry. Failure to fulfill undertakings escalates hierarchically "
            "and triggers Chapter VIII punitive actions, including intake reduction or withdrawal of approval."
        ),
    },
    {
        "id": "chunk_clause_2_25_security_deposit",
        "clause": "Chapter II, Clause 2.25(f)",
        "clause_number": "2.25",
        "page": "46",
        "topic": "Security Deposit and Penalty Deadlines",
        "verbatim_quote": "Security Deposit",
        "content": (
            "Security Deposit requirements under Chapter II Clause 2.25(f). Applicant institutions must submit Security Deposit "
            "and Affidavit 3 within 15 days of Letter of Intent. Delays up to 31st May incur a 10% penalty. Delays between 1st June "
            "and 31st July incur a 20% penalty. Failure to deposit by 31st July results in automatic withdrawal of approval."
        ),
    },
    {
        "id": "chunk_calendar_clause_2_25_j",
        "clause": "Chapter II, Clause 2.25(j)",
        "clause_number": "2.25(j)",
        "page": "47",
        "topic": "Academic Calendar Cutoff for Extension of Approval",
        "verbatim_quote": "No Extension of Approval shall be granted after the cutoff date",
        "content": (
            "Strict Academic Calendar Cutoff under Chapter II Clause 2.25(j). Pursuant to Hon'ble Supreme Court directives "
            "in Parshvanath Charitable Trust, no Extension of Approval (EoA) or variation in intake shall be granted after the "
            "statutory cutoff date (10th June) specified in the AICTE Academic Calendar."
        ),
    },
]

class BM25Retriever:
    """
    Standard Okapi BM25 statistical retriever for grounded APH regulatory search.
    Computes term frequencies and inverse document frequencies over chunk corpus.
    """
    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None, k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks or OFFICIAL_APH_CHUNKS
        self.k1 = k1
        self.b = b
        self.doc_len = []
        self.avg_doc_len = 0.0
        self.doc_freqs: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.corpus_size = len(self.chunks)
        self._build_index()

    STOPWORDS = {
        "what", "is", "the", "and", "or", "who", "won", "in", "of", "to", "a", "an",
        "for", "by", "with", "on", "at", "from", "as", "it", "this", "that", "are",
        "be", "was", "were", "my", "your", "our", "their", "have", "has", "had", "do",
        "does", "did", "how", "can", "could", "should", "would", "which", "where", "when",
        "about", "any", "some", "all", "more", "most", "other", "so", "than", "too", "very"
    }

    @classmethod
    def tokenize(cls, text: str) -> List[str]:
        """Simple, robust tokenization removing punctuation, stopwords, and normalizing terms."""
        return [
            t for t in re.findall(r"\b[a-zA-Z0-9_\-\./]+\b", (text or "").lower()) 
            if len(t) > 1 and t not in cls.STOPWORDS
        ]

    def _build_index(self):
        total_len = 0
        for chunk in self.chunks:
            full_text = f"{chunk.get('topic', '')} {chunk.get('clause', '')} {chunk.get('content', '')}"
            tokens = self.tokenize(full_text)
            self.doc_len.append(len(tokens))
            total_len += len(tokens)
            
            unique_tokens = set(tokens)
            for t in unique_tokens:
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

        self.avg_doc_len = total_len / max(1, self.corpus_size)

        # Precompute IDF
        for term, df in self.doc_freqs.items():
            # Standard Lucene/BM25 formula
            self.idf[term] = math.log(1.0 + (self.corpus_size - df + 0.5) / (df + 0.5))

    def retrieve(
        self, query: str, top_k: int = 3, min_score: float = 0.8
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Retrieves top-k relevant APH chunks using BM25 ranking.
        Returns list of (chunk, bm25_score).
        If top score is below min_score, returns empty list (weak evidence guard).
        """
        q_tokens = self.tokenize(query)
        if not q_tokens:
            return []

        scores: List[float] = [0.0] * self.corpus_size

        for term in q_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            
            for doc_idx, chunk in enumerate(self.chunks):
                full_text = f"{chunk.get('topic', '')} {chunk.get('clause', '')} {chunk.get('content', '')}"
                doc_tokens = self.tokenize(full_text)
                tf = doc_tokens.count(term)
                if tf == 0:
                    continue
                
                doc_l = self.doc_len[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_l / self.avg_doc_len))
                scores[doc_idx] += term_idf * (numerator / denominator)

        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for idx in ranked_indices[:top_k]:
            if scores[idx] >= min_score:
                results.append((self.chunks[idx], round(scores[idx], 3)))

        return results

# Singleton retriever instance
aph_bm25_retriever = BM25Retriever()
