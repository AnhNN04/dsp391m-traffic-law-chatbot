"""
Domain Entities - Traffic Law Agent

Core business entities representing legal documents and violations.
Pure data structures with zero framework dependencies (no LangChain, no FastAPI).

Follows Clean Architecture: Domain Layer is the innermost ring.
These classes are consumed by:
  - Application Nodes (RetrievalNode, GradeNode, GenerateNode)
  - Infrastructure Adapters (ChromaRepo, Neo4jRepo) for conversion
  - AgentState (documents: List[LegalDocument])

Author: AnhNN217-FHN
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from enum import Enum


# ---------------------------------------------------------------------------
# ENUMERATIONS
# ---------------------------------------------------------------------------

class VehicleType(str, Enum):
    """
    Vehicle types used in Vietnamese traffic law context.
    """
    
    MOTORCYCLE = "motorcycle"   # Xe máy, mô tô, xe gắn máy
    CAR = "car"                 # Ô tô con
    TRUCK = "truck"             # Xe tải, xe container
    BUS = "bus"                 # Xe khách, xe buýt
    BICYCLE = "bicycle"         # Xe đạp, xe đạp điện
    OTHER = "other"

    @classmethod
    def from_vietnamese(cls, text: str) -> "VehicleType":
        """
        Infer vehicle type from Vietnamese text (user query or doc metadata).

        Used by RetrievalNode when extracting vehicle entity from rewritten_query.

        Args:
            text: Vietnamese text containing vehicle reference.

        Returns:
            Matched VehicleType, defaults to OTHER.
        """
        t = text.lower()
        if any(k in t for k in ("xe máy", "mô tô", "moto", "xe gắn máy", "xe số", "xe tay ga")):
            return cls.MOTORCYCLE
        if any(k in t for k in ("ô tô", "xe hơi", "xe con", "xe 4 bánh", "xe 4 chỗ", "xe 7 chỗ")):
            return cls.CAR
        if any(k in t for k in ("xe tải", "xe container", "xe đầu kéo", "xe ben")):
            return cls.TRUCK
        if any(k in t for k in ("xe khách", "xe buýt", "xe bus", "xe giường nằm")):
            return cls.BUS
        if any(k in t for k in ("xe đạp", "xe đạp điện")):
            return cls.BICYCLE
        return cls.OTHER


class ViolationType(str, Enum):
    """
    Categories of traffic violations.

    Used primarily for Neo4j graph queries and statistical grouping.
    NOT used for strict filtering in retrieval — the actual violation
    content lives in LegalDocument.content.
    """
    SPEEDING = "speeding"           # Quá tốc độ
    RED_LIGHT = "red_light"         # Vượt đèn đỏ / đèn vàng
    WRONG_LANE = "wrong_lane"       # Sai làn đường, lấn tuyến
    NO_HELMET = "no_helmet"         # Không đội mũ bảo hiểm
    DRUNK_DRIVING = "drunk_driving" # Nồng độ cồn
    NO_LICENSE = "no_license"       # Không có GPLX, giấy tờ xe
    PHONE_USAGE = "phone_usage"     # Sử dụng điện thoại khi lái xe
    PARKING = "parking"             # Đỗ xe sai quy định
    OVERLOAD = "overload"           # Chở quá số người / hàng hoá
    SIGNAL = "signal"               # Vi phạm hiệu lệnh CSGT, biển báo
    OTHER = "other"

    @classmethod
    def from_vietnamese(cls, text: str) -> "ViolationType":
        """
        Infer violation type from Vietnamese text including common slang.

        Covers formal terms AND street slang as required by ETL pipeline
        (chatbot-flow.md Section 3 - LLM Enrichment: keywords, tiếng lóng).

        Args:
            text: Vietnamese text describing the violation.

        Returns:
            Best-matching ViolationType, defaults to OTHER.
        """
        t = text.lower()

        # Drunk driving — check first (high priority, distinct keywords)
        if any(k in t for k in ("nồng độ cồn", "rượu", "bia", "say xỉn", "ma tuý", "ma túy")):
            return cls.DRUNK_DRIVING

        # Red light (includes yellow light and traffic signals)
        if any(k in t for k in ("đèn đỏ", "đèn vàng", "vượt đèn", "tín hiệu đèn")):
            return cls.RED_LIGHT

        # Speeding
        if any(k in t for k in ("tốc độ", "quá tốc", "chạy nhanh", "phóng nhanh")):
            return cls.SPEEDING

        # No helmet
        if any(k in t for k in ("mũ bảo hiểm", "không đội mũ", "thiếu mũ")):
            return cls.NO_HELMET

        # No license / documents
        if any(k in t for k in ("bằng lái", "giấy phép lái xe", "gplx", "giấy đăng ký",
                                  "không có giấy", "giấy tờ xe")):
            return cls.NO_LICENSE

        # Phone usage
        if any(k in t for k in ("điện thoại", "nghe gọi", "nhắn tin", "dùng điện thoại")):
            return cls.PHONE_USAGE

        # Wrong lane — including slang
        if any(k in t for k in ("làn đường", "sai làn", "lấn tuyến", "lấn đường",
                                  "tạt đầu", "lạng lách", "đánh võng", "vượt ẩu")):
            return cls.WRONG_LANE

        # Overload — carrying too many passengers (kẹp 3, kẹp 4...)
        if any(k in t for k in ("chở quá", "kẹp 3", "kẹp ba", "kẹp 4", "quá tải",
                                  "chở người", "chở hàng quá")):
            return cls.OVERLOAD

        # Parking
        if any(k in t for k in ("đỗ xe", "đậu xe", "dừng xe", "đỗ sai")):
            return cls.PARKING

        # Traffic signal / officer command
        if any(k in t for k in ("hiệu lệnh", "biển báo", "không chấp hành", "bỏ chạy",
                                  "chống người thi hành")):
            return cls.SIGNAL

        return cls.OTHER


class DocumentSource(str, Enum):
    """
    Source of a LegalDocument — aligns with AgentState.data_source values
    and Node routing logic (chatbot-pipeline.md Section 3).

    NODE 7 (GenerateNode) uses this to decide disclaimer wording:
      - DATABASE / GRAPH → cite article directly ("Theo Điều X...")
      - WEB_SEARCH → add disclaimer ("Thông tin tham khảo từ Internet")
    """
    VECTOR_STORE = "vector_store"           # ChromaDB semantic search
    GRAPH_STORE = "graph_store"             # Neo4j exact penalty lookup
    WEB_SEARCH = "web_search"               # Tavily fallback (internet)


# ---------------------------------------------------------------------------
# CORE ENTITIES
# ---------------------------------------------------------------------------

@dataclass
class LegalDocument:
    """
    A single unit of legal knowledge retrieved from the knowledge base.

    Represents one "Đơn vị Vi phạm" (Atomic Violation Unit) as described
    in chatbot-flow.md Section 2. Can originate from:
      - ChromaDB (semantic search hit)
      - Neo4j (exact graph query result)
      - Tavily (web search fallback)

    Used in AgentState as: `documents: List[LegalDocument]`

    Key design decisions:
      - `article_id` and `law_name` are first-class fields (not buried in
        metadata) because GenerateNode MUST cite them in every answer.
      - `node_id` links back to Neo4j for graph traversal (REFERS_TO edges).
      - No `created_at` — Python object timestamp has no domain meaning here.
      - `score` is None for graph/web results (exact match, no ranking needed).

    Attributes:
        content:    Full text of the legal clause or enriched virtual doc.
        source:     Where this was retrieved from (drives GenerateNode behavior).
        article_id: Human-readable article reference e.g. "Điều 5 Khoản 3 Điểm a".
        law_name:   Law/decree name e.g. "Nghị định 168/2024/NĐ-CP".
        node_id:    Neo4j / ChromaDB node ID e.g. "ND168_D5_K3_Pa" for cross-DB linking.
        vehicle:    Vehicle type filter (from ChromaDB metadata or graph property).
        score:      Cosine similarity score from vector search (None for graph/web).
        metadata:   Additional raw metadata from the DB (fine_range, chapter, etc.).

    Example:
        >>> doc = LegalDocument(
        ...     content="Điểm a Khoản 3 Điều 5: Vượt đèn tín hiệu đỏ...",
        ...     source=DocumentSource.GRAPH_STORE,
        ...     article_id="Điều 5 Khoản 3 Điểm a",
        ...     law_name="Nghị định 168/2024/NĐ-CP",
        ...     node_id="ND168_D5_K3_Pa",
        ...     vehicle=VehicleType.MOTORCYCLE,
        ... )
        >>> doc.get_citation()
        'Theo Điều 5 Khoản 3 Điểm a - Nghị định 168/2024/NĐ-CP'
    """

    content: str
    source: DocumentSource

    # Citation fields — used directly by GenerateNode prompt
    article_id: Optional[str] = None
    law_name: Optional[str] = None

    # Cross-database linking
    node_id: Optional[str] = None

    # Retrieval metadata
    vehicle: Optional[VehicleType] = None
    score: Optional[float] = None

    # Raw passthrough from DB (fine_range, chapter, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("LegalDocument.content cannot be empty.")
        if self.score is not None and not (0.0 <= self.score <= 1.0):
            raise ValueError(f"score must be in [0.0, 1.0], got {self.score}.")

    def __repr__(self) -> str:
        score_str = f", score={self.score:.2f}" if self.score is not None else ""
        return (
            f"LegalDocument(source={self.source.value!r}, "
            f"node_id={self.node_id!r}{score_str}, "
            f"content={self.content[:60]!r}...)"
        )

    # ------------------------------------------------------------------
    # Domain Methods
    # ------------------------------------------------------------------

    def get_citation(self) -> str:
        """
        Build a Vietnamese legal citation string for use in GenerateNode prompt.

        NODE 7 system prompt requires: "BẮT BUỘC trích dẫn điều khoản".

        Returns:
            Citation string, e.g. "Theo Điều 5 Khoản 3 - Nghị định 168/2024/NĐ-CP"
            or fallback "Theo văn bản pháp luật" if no metadata available.

        Example:
            >>> doc.get_citation()
            'Theo Điều 5 Khoản 3 Điểm a - Nghị định 168/2024/NĐ-CP'
        """
        parts = []
        if self.article_id:
            parts.append(self.article_id)
        if self.law_name:
            parts.append(self.law_name)

        if not parts:
            return "Theo văn bản pháp luật"

        return "Theo " + " - ".join(parts)

    def to_context_string(self) -> str:
        """
        Format document as a context block for injection into LLM prompts.

        Used by GenerateNode and GradeNode when building the `context`
        section of their prompts. Includes citation so the LLM can
        reference the source without extra logic.

        Returns:
            Multi-line string ready for f-string prompt injection.

        Example output:
            [Nguồn: Theo Điều 5 - Nghị định 168/2024/NĐ-CP | vector_store]
            Điểm a Khoản 3 Điều 5: Vượt đèn tín hiệu đỏ bị phạt từ 4.000.000đ...
        """
        source_label = "internet" if self.source == DocumentSource.WEB_SEARCH else "cơ sở dữ liệu"
        citation = self.get_citation()
        return f"[Nguồn: {citation} | {source_label}]\n{self.content.strip()}"

    def is_from_database(self) -> bool:
        """True if document comes from internal knowledge base (not web)."""
        return self.source in (DocumentSource.VECTOR_STORE, DocumentSource.GRAPH_STORE)

    def is_relevant(self, threshold: float = 0.65) -> bool:
        """
        Check if a vector search result meets the relevance threshold.

        Logic:
          - Graph / web documents have no score (exact match or curated) → always relevant.
          - Vector documents are scored by cosine similarity → apply threshold.

        Args:
            threshold: Minimum cosine similarity score (default 0.65 for
                       Google text-embedding-004 with legal Vietnamese text).

        Returns:
            True if relevant.
        """
        if self.source != DocumentSource.VECTOR_STORE:
            return True  # Graph/web docs are always intentional results
        if self.score is None:
            return True
        return self.score >= threshold

    # ------------------------------------------------------------------
    # Serialization — for MongoDB checkpointing & LangGraph state
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-safe dict for MongoDB / LangGraph persistence."""
        return {
            "content": self.content,
            "source": self.source.value,
            "article_id": self.article_id,
            "law_name": self.law_name,
            "node_id": self.node_id,
            "vehicle": self.vehicle.value if self.vehicle else None,
            "score": self.score,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LegalDocument":
        """
        Deserialize from dict (MongoDB document or LangGraph checkpoint).

        Robust against extra keys (e.g. MongoDB `_id`) and missing optional fields.

        Args:
            data: Raw dictionary from storage.

        Returns:
            Hydrated LegalDocument instance.
        """
        known_fields = {
            "content", "source", "article_id", "law_name",
            "node_id", "vehicle", "score", "metadata",
        }
        clean = {k: v for k, v in data.items() if k in known_fields}

        if "source" in clean:
            clean["source"] = DocumentSource(clean["source"])
        if clean.get("vehicle"):
            clean["vehicle"] = VehicleType(clean["vehicle"])

        return cls(**clean)


@dataclass
class Violation:
    """
    A structured traffic violation record with penalty details.

    Primarily populated from Neo4j graph queries (GraphStore) and used
    by RetrievalNode to build LegalDocument objects for the agent state.

    Corresponds to Neo4j node schema (DATABASE_INFRASTRUCTURE.md):
        (Violation {name, penalty_min, penalty_max, description, keywords})

    Attributes:
        violation_name:      Display name e.g. "Vượt đèn đỏ".
        violation_type:      Category enum for grouping/filtering.
        penalty_min:         Minimum fine in VND (integer, no decimals).
        penalty_max:         Maximum fine in VND.
        law_article:         Full article citation e.g. "Điều 5 Khoản 3 Điểm a".
        law_name:            Decree/law name e.g. "Nghị định 168/2024/NĐ-CP".
        node_id:             Neo4j node identifier e.g. "ND168_D5_K3_Pa".
        vehicle_type:        Applicable vehicle (None = applies to all).
        additional_penalties: License suspension, vehicle confiscation, etc.
        description:         Detailed behavior description from the law text.

    Example:
        >>> v = Violation(
        ...     violation_name="Vượt đèn đỏ",
        ...     violation_type=ViolationType.RED_LIGHT,
        ...     penalty_min=4_000_000,
        ...     penalty_max=6_000_000,
        ...     law_article="Điều 5 Khoản 3 Điểm a",
        ...     law_name="Nghị định 168/2024/NĐ-CP",
        ...     vehicle_type=VehicleType.MOTORCYCLE,
        ... )
        >>> v.get_penalty_range()
        '4.000.000 - 6.000.000 VNĐ'
        >>> v.to_legal_document()
        LegalDocument(source='graph_store', ...)
    """

    violation_name: str
    violation_type: ViolationType
    penalty_min: int        # VND
    penalty_max: int        # VND
    law_article: str        # e.g. "Điều 5 Khoản 3 Điểm a"
    law_name: str           # e.g. "Nghị định 168/2024/NĐ-CP"

    node_id: Optional[str] = None
    vehicle_type: Optional[VehicleType] = None
    additional_penalties: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.violation_name.strip():
            raise ValueError("Violation.violation_name cannot be empty.")
        if self.penalty_min < 0:
            raise ValueError("Violation.penalty_min cannot be negative.")
        if self.penalty_max < self.penalty_min:
            raise ValueError("penalty_max must be >= penalty_min.")
        if not self.law_article.strip():
            raise ValueError("Violation.law_article cannot be empty.")
        if not self.law_name.strip():
            raise ValueError("Violation.law_name cannot be empty.")

    def __repr__(self) -> str:
        return (
            f"Violation({self.violation_name!r}, "
            f"vehicle={self.vehicle_type.value if self.vehicle_type else 'all'!r}, "
            f"penalty={self.get_penalty_range()}, "
            f"ref={self.law_article!r})"
        )

    # ------------------------------------------------------------------
    # Domain Methods
    # ------------------------------------------------------------------

    def get_penalty_range(self) -> str:
        """
        Human-readable penalty range in Vietnamese format.

        Returns:
            e.g. "4.000.000 - 6.000.000 VNĐ" or "4.000.000 VNĐ" (fixed fine).
        """
        lo = _fmt_vnd(self.penalty_min)
        hi = _fmt_vnd(self.penalty_max)
        if self.penalty_min == self.penalty_max:
            return f"{lo} VNĐ"
        return f"{lo} - {hi} VNĐ"

    def is_severe(self, threshold: int = 5_000_000) -> bool:
        """
        True if this violation carries a minimum fine >= threshold.

        Default threshold 5M VNĐ covers most felony-level traffic offenses
        (drunk driving, serious accidents) under Nghị định 168.

        Args:
            threshold: VND amount (default 5_000_000).
        """
        return self.penalty_min >= threshold

    def to_legal_document(self) -> LegalDocument:
        """
        Convert this Violation into a LegalDocument for injection into AgentState.

        RetrievalNode uses this to unify graph results with vector results
        into a single `documents: List[LegalDocument]` list.

        Returns:
            LegalDocument with GRAPH_STORE source and structured content.
        """
        content = self._build_content()
        return LegalDocument(
            content=content,
            source=DocumentSource.GRAPH_STORE,
            article_id=self.law_article,
            law_name=self.law_name,
            node_id=self.node_id,
            vehicle=self.vehicle_type,
            score=None,  # Graph results are exact — no similarity score
        )

    def _build_content(self) -> str:
        """Build structured content string for LLM context."""
        lines = [f"Lỗi vi phạm: {self.violation_name}"]

        if self.vehicle_type:
            lines.append(f"Loại phương tiện: {self.vehicle_type.value}")

        lines.append(f"Mức phạt tiền: {self.get_penalty_range()}")

        if self.additional_penalties:
            lines.append(f"Hình thức phạt bổ sung: {self.additional_penalties}")

        lines.append(f"Căn cứ pháp lý: {self.law_article} - {self.law_name}")

        if self.description:
            lines.append(f"Nội dung hành vi: {self.description}")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for Neo4j ingestion scripts or JSON export."""
        return {
            "violation_name": self.violation_name,
            "violation_type": self.violation_type.value,
            "penalty_min": self.penalty_min,
            "penalty_max": self.penalty_max,
            "law_article": self.law_article,
            "law_name": self.law_name,
            "node_id": self.node_id,
            "vehicle_type": self.vehicle_type.value if self.vehicle_type else None,
            "additional_penalties": self.additional_penalties,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Violation":
        """
        Deserialize from dict (Neo4j driver result or seed script data).

        Robust against extra keys from Neo4j driver response.
        """
        known_fields = {
            "violation_name", "violation_type", "penalty_min", "penalty_max",
            "law_article", "law_name", "node_id", "vehicle_type",
            "additional_penalties", "description",
        }
        clean = {k: v for k, v in data.items() if k in known_fields}

        if "violation_type" in clean:
            clean["violation_type"] = ViolationType(clean["violation_type"])
        if clean.get("vehicle_type"):
            clean["vehicle_type"] = VehicleType(clean["vehicle_type"])

        return cls(**clean)


# ---------------------------------------------------------------------------
# FACTORY FUNCTION
# ---------------------------------------------------------------------------

def create_violation(
    violation_name: str,
    penalty_min: int,
    penalty_max: int,
    law_article: str,
    law_name: str,
    **kwargs: Any,
) -> Violation:
    """
    Factory function for Violation with automatic type inference.

    Simplifies ETL scripts and seed data (scripts/seed_data.py) by
    inferring `violation_type` from the violation name when not supplied.

    Args:
        violation_name: Display name of the violation.
        penalty_min:    Minimum fine in VND.
        penalty_max:    Maximum fine in VND.
        law_article:    Article reference string.
        law_name:       Decree/law name string.
        **kwargs:       Any other Violation fields (node_id, vehicle_type, etc.)

    Returns:
        Initialized Violation instance.

    Example:
        >>> v = create_violation(
        ...     "Kẹp 3 không đội mũ bảo hiểm",
        ...     penalty_min=100_000,
        ...     penalty_max=200_000,
        ...     law_article="Điều 11 Khoản 2",
        ...     law_name="Nghị định 168/2024/NĐ-CP",
        ... )
        >>> v.violation_type
        <ViolationType.NO_HELMET: 'no_helmet'>
    """
    if "violation_type" not in kwargs:
        kwargs["violation_type"] = ViolationType.from_vietnamese(violation_name)

    return Violation(
        violation_name=violation_name,
        penalty_min=penalty_min,
        penalty_max=penalty_max,
        law_article=law_article,
        law_name=law_name,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# UTILITY HELPERS (module-private)
# ---------------------------------------------------------------------------

def _fmt_vnd(amount: int) -> str:
    """Format integer VND amount with Vietnamese dot separator."""
    return f"{amount:,}".replace(",", ".")


def merge_documents(
    graph_docs: List[LegalDocument],
    vector_docs: List[LegalDocument],
) -> List[LegalDocument]:
    """
    Merge graph and vector results with deduplication.

    Implements the RetrievalNode fusion strategy:
      - Graph results have priority (exact match, higher accuracy).
      - Vector results fill in when graph returns nothing or for context.
      - Deduplication by node_id (if available) to avoid repetition.

    Args:
        graph_docs: Documents from Neo4j (GRAPH_STORE source).
        vector_docs: Documents from ChromaDB (VECTOR_STORE source).

    Returns:
        Merged and deduplicated list, graph docs first.

    Example:
        >>> merged = merge_documents(graph_docs, vector_docs)
        >>> merged[0].source  # Graph results come first
        <DocumentSource.GRAPH_STORE: 'graph_store'>
    """
    seen_ids: set = set()
    result: List[LegalDocument] = []

    for doc in graph_docs + vector_docs:
        if doc.node_id:
            if doc.node_id in seen_ids:
                continue
            seen_ids.add(doc.node_id)
        result.append(doc)

    return result