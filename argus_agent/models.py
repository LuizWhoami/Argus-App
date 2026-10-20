from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from .database import Base


class Scan(Base):
    __tablename__ = "scans"
    id = Column(Integer, primary_key=True)
    target = Column(String, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")


class Asset(Base):
    __tablename__ = "assets"
    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True, index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class DNSRecord(Base):
    __tablename__ = "dns_records"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)
    record_type = Column(String)
    value = Column(String)


class HTTPProbe(Base):
    __tablename__ = "http_probes"
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), index=True)
    scan_id = Column(Integer, ForeignKey("scans.id"))
    url = Column(String)
    status_code = Column(Integer)
    content_type = Column(String)
    title = Column(String)
    tech = Column(String)
    webserver = Column(String)
    location = Column(String)


class APIEndpoint(Base):
    __tablename__ = "api_endpoints"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), index=True)
    host = Column(String, index=True)
    url = Column(String, index=True)
    kind = Column(String)          # swagger | openapi | graphql | rest
    status_code = Column(Integer)
    content_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Parameter(Base):
    __tablename__ = "parameters"
    id = Column(Integer, primary_key=True)
    scan_id = Column(Integer, ForeignKey("scans.id"), index=True)
    endpoint = Column(String, index=True)
    name = Column(String, index=True)
    location = Column(String)      # query | form
    created_at = Column(DateTime, default=datetime.utcnow)
