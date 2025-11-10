# Director Verification App

A secure web portal that enables Authorised Corporate Service Providers (ACSPs) to collect Companies House director
identity verification evidence. Directors can upload required documents, submit residential history, and capture selfie
media while the ACSP reviews and exports encrypted submissions.

## Features

- Self-service registration that issues a unique director user ID and verification code.
- Guided upload workflow that enforces Companies House document rules (two Group A, or one Group A plus one Group B).
- Webcam capture overlay for selfie photos, with the option to upload a photo or video instead.
- Encrypted file storage using Fernet symmetric encryption with metadata per upload.
- Admin console for ACSP staff to review submissions and download all artefacts as a zip package.
- GDPR-friendly messaging, contact guidance, and optional link to the GOV.UK identity verification service.

## Getting started

### Prerequisites

- Python 3.11+
- A virtual environment is recommended.

### Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure secure values:

```bash
cp .env.example .env
```

Set `SECRET_KEY`, `ADMIN_PASSWORD`, and provide a 32-byte url-safe base64 `ENCRYPTION_KEY` (generate with
`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`). Adjust `DATABASE_PATH`
and `UPLOAD_FOLDER` if required.

### Running the app

```bash
flask --app app:create_app run --debug
```

The portal will be available at <http://127.0.0.1:5000>.

### Default workflow

1. ACSP creates a director profile at `/register` (or generates IDs centrally and shares them with directors).
2. Director signs in with their user ID at `/start` and completes the upload checklist.
3. Files are encrypted and stored under `storage/<user_id>` with metadata recorded in `data/app.db`.
4. ACSP logs in at `/admin` using the configured password to review submissions, confirm completeness, and download a
   zip archive for evidence retention and verification code entry.

### Security notes

- All uploads are encrypted at rest using the configured Fernet key. Keep the key secret and rotate it periodically.
- Use HTTPS in production by setting `SESSION_COOKIE_SECURE=True` and running behind a TLS terminator or platform.
- Configure access controls and logging on the host/storage location to remain compliant with GDPR and AML obligations.
- Delete director data promptly once verification is complete, unless retention is legally required.

### Optional GOV.UK Verify link

Directors can choose to verify directly through GOV.UK by using the "Go to GOV.UK Verify" button on the landing page.

## Development notes

- The SQLite database schema is created automatically when the app starts.
- Uploaded files are grouped by user ID in the storage directory with encrypted contents and recorded metadata.
- The `selfie.js` helper handles live camera capture and stores an inline PNG for secure upload.
