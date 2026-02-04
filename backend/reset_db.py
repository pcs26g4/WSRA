#!/usr/bin/env python3
"""
Database Reset Script for WSRA
This script drops all existing tables and recreates them from the models.
"""

import sys
import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from pydantic_settings import BaseSettings
from pydantic import Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load settings directly
class Settings(BaseSettings):
    DATABASE_URL: str = Field(..., validation_alias="DATABASE_URL")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True
        extra = "ignore"

settings = Settings()

# Database setup
SQLALCHEMY_DATABASE_URL = getattr(settings, "DATABASE_URL", "").strip()

if not SQLALCHEMY_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Check your .env or environment variables.")

if SQLALCHEMY_DATABASE_URL.startswith("DATABASE_URL="):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("DATABASE_URL=", "", 1).strip()

if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False
)

Base = declarative_base()

# Import all model definitions
from sqlalchemy import (
    Column, Integer, String, DateTime, JSON, Text,
    Boolean, ForeignKey
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

# Define all models inline
class Scan(Base):
    __tablename__ = "scans"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_domain = Column(String(255), nullable=False)
    status = Column(String(50))
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

class Url(Base):
    __tablename__ = "urls"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    status_code = Column(Integer)
    depth_level = Column(Integer)

class HtmlPage(Base):
    __tablename__ = "html_pages"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    hash = Column(Text)
    html = Column(Text)
    html_analysis = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

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
    parameters = Column(JSON)

class JsFile(Base):
    __tablename__ = "js_files"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text)
    sources = Column(JSON)
    sinks = Column(JSON)

class Sitemap(Base):
    __tablename__ = "sitemaps"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    sitemap_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Form(Base):
    __tablename__ = "forms"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, nullable=False)
    method = Column(String(10))
    action = Column(Text)
    fields = Column(JSON)

class Parameter(Base):
    __tablename__ = "parameters"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(50))
    endpoints = Column(JSON)
    reflected_in_response = Column(Boolean, default=False)

class InteractionOutcome(Base):
    __tablename__ = "interaction_outcomes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    action_type = Column(String(50))
    element_selector = Column(Text)
    previous_url = Column(Text)
    new_url = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class Session_details(Base):
    __tablename__ = "session_details"
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), primary_key=True)
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_identifier = Column(String(255))
    session_data = Column(JSON)
    created_timestamp = Column(DateTime(timezone=True), server_default=func.now())
    session_status = Column(String(20), default="active")

class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    agent = Column(String(100))
    action = Column(String(255))
    details = Column(JSON)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class ScanStatistics(Base):
    __tablename__ = "scan_statistics"
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), primary_key=True)
    total_urls = Column(Integer, default=0)
    total_forms = Column(Integer, default=0)
    total_parameters = Column(Integer, default=0)
    total_js_files = Column(Integer, default=0)
    total_network_requests = Column(Integer, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now())

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

class PageSnapshot(Base):
    __tablename__ = "page_snapshots"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id = Column(UUID(as_uuid=True), ForeignKey("scans.id"), nullable=False)
    url = Column(Text, index=True)
    fingerprint = Column(Text, index=True)
    html = Column(Text)
    text = Column(Text)  # 🔥 ADD THIS LINE

def reset_database():
    """Drop all tables and recreate them"""
    try:
        logger.info("Starting database reset...")
        
        # Drop all tables
        logger.info("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
        
        # Create all tables
        logger.info("Creating all tables from models...")
        Base.metadata.create_all(bind=engine)
        logger.info("All tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            
        logger.info(f"Database reset completed. Created {len(tables)} tables:")
        for table in tables:
            logger.info(f"  - {table}")
            
        return True
        
    except Exception as e:
        logger.error(f"Database reset failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = reset_database()
    sys.exit(0 if success else 1)