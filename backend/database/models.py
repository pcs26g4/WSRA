from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Text,
    Boolean, ForeignKey, Float
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from .connection import Base

# ==============================================================================
# 1. CORE SCAN
# ==============================================================================

class Scan(Base):
    __tablename__ = "scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_domain = Column(String(255), nullable=False)
    status = Column(String(50))  # running, completed, failed
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    urls = relationship("Url", back_populates="scan", cascade="all, delete-orphan")
    html_pages = relationship("HtmlPage", back_populates="scan", cascade="all, delete-orphan")
    network_requests = relationship("NetworkRequest", back_populates="scan", cascade="all, delete-orphan")
    js_files = relationship("JsFile", back_populates="scan", cascade="all, delete-orphan")
    sitemaps = relationship("Sitemap", back_populates="scan", cascade="all, delete-orphan")
    interaction_outcomes = relationship("InteractionOutcome", back_populates="scan", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="scan", cascade="all, delete-orphan")
    exports = relationship("Export", back_populates="scan", cascade="all, delete-orphan")
    vulnerability_hints = relationship("VulnerabilityHint", back_populates="scan", cascade="all, delete-orphan")


# ==============================================================================
# 2. CRAWLER DATA
# ==============================================================================

class Url(Base):
    __tablename__ = "urls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    status_code = Column(Integer)
    depth_level = Column(Integer)

    scan = relationship("Scan", back_populates="urls")


class HtmlPage(Base):
    __tablename__ = "html_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    hash = Column(Text)
    html = Column(Text)
    html_analysis = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="html_pages")


class NetworkRequest(Base):
    __tablename__ = "network_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10))
    request_headers = Column(JSON)
    request_body = Column(Text)
    response_status = Column(Integer)
    response_body = Column(Text)
    parameters = Column(JSON)  # MUST include response_headers

    scan = relationship("Scan", back_populates="network_requests")


class JsFile(Base):
    __tablename__ = "js_files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text)
    sources = Column(JSON)
    sinks = Column(JSON)

    scan = relationship("Scan", back_populates="js_files")


# ==============================================================================
# 3. ANALYSIS & MAPPING
# ==============================================================================

class Sitemap(Base):
    __tablename__ = "sitemaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    sitemap_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    scan = relationship("Scan", back_populates="sitemaps")


class Form(Base):
    __tablename__ = "forms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10))
    action = Column(Text)
    fields = Column(JSON)

    scan = relationship("Scan")


class Parameter(Base):
    __tablename__ = "parameters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(50))  # query, body
    endpoints = Column(JSON)
    reflected_in_response = Column(Boolean, default=False)


# ==============================================================================
# 4. INTERACTION & AUTH
# ==============================================================================

class InteractionTarget(Base):
    __tablename__ = "interaction_targets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    source_url = Column(Text, nullable=False)
    element_type = Column(String(50)) # button, link, form
    element_selector = Column(Text)
    attributes_json = Column(JSON)
    visited = Column(Boolean, default=False)
    
    scan = relationship("Scan")


class InteractionOutcome(Base):
    __tablename__ = "interaction_outcomes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    action_type = Column(String(50))  # click, input
    element_selector = Column(Text)
    previous_url = Column(Text)
    new_url = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="interaction_outcomes")


class Session_details(Base):
    __tablename__ = "session_details"

    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), primary_key=True)
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_identifier = Column(String(255))
    session_data = Column(JSON)
    created_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    session_status = Column(String(20), default="active")


# ==============================================================================
# 5. AUDIT & STATS
# ==============================================================================

class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    agent = Column(String(100))
    action = Column(String(255))
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="audit_logs")


class ScanStatistics(Base):
    __tablename__ = "scan_statistics"

    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), primary_key=True)
    total_urls = Column(Integer, default=0)
    total_forms = Column(Integer, default=0)
    total_parameters = Column(Integer, default=0)
    total_js_files = Column(Integer, default=0)
    total_network_requests = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan")


class LLMRequest(Base):
    __tablename__ = "llm_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    agent_name = Column(String(100))
    url = Column(Text)
    prompt = Column(Text)
    response = Column(Text)
    tokens_used = Column(Integer, default=0)
    status = Column(String(50), default="pending")
    error = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan")


# ==============================================================================
# 6. PAGE SNAPSHOTS (DEDUP)
# ==============================================================================

class PageSnapshot(Base):
    __tablename__ = "page_snapshots"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, index=True)
    fingerprint = Column(Text, index=True)
    html = Column(Text)
    text = Column(Text)


# ==============================================================================
# 7. EXPORTS
# ==============================================================================

class Export(Base):
    __tablename__ = "exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    format = Column(String(20), nullable=False) # json, csv, xml, markdown
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="exports")


# ==============================================================================
# 8. VULNERABILITY HINTS
# ==============================================================================

class VulnerabilityHint(Base):
    __tablename__ = "vulnerability_hints"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    type = Column(String(50))
    endpoint = Column(Text)
    parameter = Column(String(255))
    location = Column(String(50))
    confidence = Column(Float)
    evidence = Column(JSON)
    manual_test = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("Scan", back_populates="vulnerability_hints")

# Update Scan relationship
Scan.vulnerability_hints = relationship("VulnerabilityHint", back_populates="scan")
