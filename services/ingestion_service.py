"""
Ingestion Service
=================

This service is responsible for receiving external event files,
validating input, enforcing idempotency, and storing immutable
raw artifacts alongside structured metadata.

Design Principles
-----------------
• Immutable ingestion (no overwrite, append-only)
• Idempotent client request handling
• Hash-based duplicate detection
• Structured failure metadata
• Cloud-native object storage
• Explicit retry classification
• Schema version awareness

This module is intentionally domain-neutral and suitable
for event-driven ledger architectures.
"""

import os
import io
import json
import uuid
import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from google.cloud import storage


# -------------------------------------------------------------------
# Configuration (environment driven)
# -------------------------------------------------------------------

RAW_BUCKET = os.getenv("RAW_BUCKET", "event-raw-bucket")
METADATA_BUCKET = os.getenv("METADATA_BUCKET", "event-metadata-bucket")
IDEMPOTENCY_PREFIX = "idempotency/"
SERVICE_NAME = "event-ingestion-service"
API_VERSION = "v1.0"
SCHEMA_VERSION = "1.0"

storage_client = storage.Client()

app = FastAPI(
    title="Immutable Event Ingestion Service",
    version=API_VERSION,
)


# -------------------------------------------------------------------
# Canonical Status & Error Codes
# -------------------------------------------------------------------

class IngestionStatus(str, Enum):
    STORED = "stored"
    DUPLICATE = "duplicate"
    IDEMPOTENT_REPLAY = "idempotent_replay"
    FAILED = "failed"


class IngestionErrorCode(str, Enum):
    EMPTY_FILE = "EMPTY_FILE"
    INVALID_FILE = "INVALID_FILE"
    DUPLICATE_FILE = "DUPLICATE_FILE"
    IDEMPOTENT_REPLAY = "IDEMPOTENT_REPLAY"
    STORAGE_FAILURE = "STORAGE_FAILURE"
    METADATA_WRITE_FAILURE = "METADATA_WRITE_FAILURE"
    INTERNAL_ERROR = "INTERNAL_ERROR"


RETRYABLE_MAP = {
    IngestionErrorCode.EMPTY_FILE: False,
    IngestionErrorCode.INVALID_FILE: False,
    IngestionErrorCode.DUPLICATE_FILE: False,
    IngestionErrorCode.IDEMPOTENT_REPLAY: False,
    IngestionErrorCode.STORAGE_FAILURE: True,
    IngestionErrorCode.METADATA_WRITE_FAILURE: True,
    IngestionErrorCode.INTERNAL_ERROR: True,
}


class ValidationError(Exception):
    def __init__(self, error_code: IngestionErrorCode, message: str):
        self.error_code = error_code
        self.message = message


# -------------------------------------------------------------------
# Utility Functions
# -------------------------------------------------------------------

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def validate_file(file_bytes: bytes):
    if not file_bytes:
        raise ValidationError(
            IngestionErrorCode.EMPTY_FILE,
            "Uploaded file is empty"
        )

    # Minimal structural validation for demonstration purposes
    try:
        file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ValidationError(
            IngestionErrorCode.INVALID_FILE,
            "File must be UTF-8 encoded"
        )


# -------------------------------------------------------------------
# Failure Metadata Handling
# -------------------------------------------------------------------

def write_failure_metadata(
    *,
    error_code: IngestionErrorCode,
    message: str,
    client_request_id: Optional[str],
    retryable: bool,
):
    failure_id = str(uuid.uuid4())
    timestamp = utc_now()

    failure_payload = {
        "schema_version": SCHEMA_VERSION,
        "failure_id": failure_id,
        "status": IngestionStatus.FAILED,
        "error_code": error_code,
        "retryable": retryable,
        "message": message,
        "client_request_id": client_request_id,
        "timestamp": timestamp,
    }

    date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
    failure_path = f"failures/{date_path}/failure_id={failure_id}.json"

    bucket = storage_client.bucket(METADATA_BUCKET)
    blob = bucket.blob(failure_path)
    blob.upload_from_string(
        json.dumps(failure_payload, indent=2),
        content_type="application/json"
    )


# -------------------------------------------------------------------
# Health Endpoint
# -------------------------------------------------------------------

@app.get("/v1/health")
def health():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "version": API_VERSION
    }


# -------------------------------------------------------------------
# Ingestion Endpoint
# -------------------------------------------------------------------

@app.post("/v1/ingest")
async def ingest(
    client_request_id: str = Form(...),
    file: UploadFile = File(...)
):
    ingestion_id = str(uuid.uuid4())
    timestamp = utc_now()

    metadata_bucket = storage_client.bucket(METADATA_BUCKET)

    # -------------------------------------------------------------
    # Idempotency Check
    # -------------------------------------------------------------

    idempotency_key = f"{IDEMPOTENCY_PREFIX}{client_request_id}.json"
    idempotency_blob = metadata_bucket.blob(idempotency_key)

    if idempotency_blob.exists():
        record = json.loads(idempotency_blob.download_as_text())
        return JSONResponse(
            status_code=200,
            content={
                "status": IngestionStatus.IDEMPOTENT_REPLAY,
                "error_code": IngestionErrorCode.IDEMPOTENT_REPLAY,
                "retryable": False,
                "ingestion_id": record.get("ingestion_id"),
                "timestamp": record.get("timestamp"),
            }
        )

    try:
        # ---------------------------------------------------------
        # Read & Validate File
        # ---------------------------------------------------------
        file_bytes = await file.read()
        validate_file(file_bytes)
        file_hash = sha256_hash(file_bytes)

        # ---------------------------------------------------------
        # Duplicate Detection (hash-based)
        # ---------------------------------------------------------
        for blob in metadata_bucket.list_blobs(prefix="ingestions/"):
            metadata = json.loads(blob.download_as_text())
            if metadata.get("file_hash") == file_hash:
                return JSONResponse(
                    status_code=200,
                    content={
                        "status": IngestionStatus.DUPLICATE,
                        "error_code": IngestionErrorCode.DUPLICATE_FILE,
                        "retryable": False,
                        "file_hash": file_hash,
                        "timestamp": timestamp,
                    }
                )

        # ---------------------------------------------------------
        # Store Raw File (Immutable)
        # ---------------------------------------------------------
        raw_bucket = storage_client.bucket(RAW_BUCKET)
        date_path = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        raw_path = f"raw/{date_path}/ingestion_id={ingestion_id}/{file.filename}"

        raw_blob = raw_bucket.blob(raw_path)
        raw_blob.upload_from_file(
            io.BytesIO(file_bytes),
            content_type="application/octet-stream"
        )

        # ---------------------------------------------------------
        # Store Metadata
        # ---------------------------------------------------------
        metadata_payload = {
            "schema_version": SCHEMA_VERSION,
            "ingestion_id": ingestion_id,
            "client_request_id": client_request_id,
            "status": IngestionStatus.STORED,
            "file_hash": file_hash,
            "stored_at": f"gs://{RAW_BUCKET}/{raw_path}",
            "timestamp": timestamp,
        }

        metadata_path = f"ingestions/{date_path}/ingestion_id={ingestion_id}.json"
        metadata_blob = metadata_bucket.blob(metadata_path)
        metadata_blob.upload_from_string(
            json.dumps(metadata_payload, indent=2),
            content_type="application/json"
        )

        # ---------------------------------------------------------
        # Write Idempotency Record
        # ---------------------------------------------------------
        idempotency_blob.upload_from_string(
            json.dumps({
                "schema_version": SCHEMA_VERSION,
                "client_request_id": client_request_id,
                "ingestion_id": ingestion_id,
                "timestamp": timestamp
            }, indent=2),
            content_type="application/json"
        )

        return JSONResponse(
            status_code=201,
            content={
                "ingestion_id": ingestion_id,
                "status": IngestionStatus.STORED,
                "file_hash": file_hash,
                "stored_at": metadata_payload["stored_at"],
                "timestamp": timestamp
            }
        )

    except ValidationError as ve:
        write_failure_metadata(
            error_code=ve.error_code,
            message=ve.message,
            client_request_id=client_request_id,
            retryable=RETRYABLE_MAP[ve.error_code],
        )

        return JSONResponse(
            status_code=400,
            content={
                "status": IngestionStatus.FAILED,
                "error_code": ve.error_code,
                "retryable": RETRYABLE_MAP[ve.error_code],
                "message": ve.message,
            }
        )

    except Exception:
        write_failure_metadata(
            error_code=IngestionErrorCode.INTERNAL_ERROR,
            message="Unexpected internal error",
            client_request_id=client_request_id,
            retryable=True,
        )

        raise HTTPException(
            status_code=500,
            detail={
                "status": IngestionStatus.FAILED,
                "error_code": IngestionErrorCode.INTERNAL_ERROR,
                "retryable": True,
                "message": "Internal server error",
            }
        )