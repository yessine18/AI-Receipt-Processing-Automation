# AI Receipt Processing Automation

A fully-coded, self-hosted AI receipt processing system with automated OCR + Gemini-based parsing, secure object storage, and a PostgreSQL-backed audit trail.

## Features

- 📸 Receipt upload via web interface or email
- 🤖 AI-powered data extraction using Gemini Vision API
- 📊 Automated OCR with preprocessing (Tesseract/EasyOCR)
- 💾 Object storage (MinIO/S3) for receipt images
- 🗄️ PostgreSQL database with full audit trail
- 🔐 JWT-based authentication
- ⚡ Async processing with Redis queue
- 📈 Admin dashboard with reporting
- 🔍 Duplicate detection and data validation

## Architecture

```
Frontend (React) → Backend API (FastAPI) → Redis Queue → Worker
                         ↓                                ↓
                    PostgreSQL ←────────────────── Storage (MinIO/S3)
```

## Tech Stack

### Backend
- FastAPI (Python 3.11+)
- PostgreSQL + SQLAlchemy
- Redis + RQ (queue)
- OpenCV, Tesseract, EasyOCR
- Google Gemini API
- MinIO/S3 for object storage

### Frontend
- React 18+
- TailwindCSS
- Axios
- React Query

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+
- Google Cloud API key (for Gemini)

### 1. Clone and Setup

```bash
cd c:\Users\USER\Desktop\WhatsApp_Invoice
```

### 2. Environment Configuration

Create `.env` file in the root:

```env
# API
SECRET_KEY=your-secret-key-change-this
DATABASE_URL=postgresql://receipts_user:receipts_pass@postgres:5432/receipts_db
REDIS_URL=redis://redis:6379/0

# Storage
STORAGE_TYPE=minio
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=receipts
MINIO_SECURE=false

# Google Gemini
GOOGLE_API_KEY=your-gemini-api-key

# OCR
OCR_ENGINE=tesseract  # tesseract or easyocr

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Start Services

```bash
docker-compose up -d
```

Services:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- MinIO Console: http://localhost:9001
- PostgreSQL: localhost:5432
- Redis: localhost:6379

### 4. Initialize Database

```bash
docker-compose exec api alembic upgrade head
```

### 5. Create Admin User

```bash
docker-compose exec api python scripts/create_admin.py
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Key Endpoints

```
POST   /api/v1/auth/register       - Register new user
POST   /api/v1/auth/login          - Login (get JWT token)
POST   /api/v1/receipts/upload     - Upload receipt image
GET    /api/v1/receipts            - List receipts (paginated)
GET    /api/v1/receipts/{id}       - Get receipt details
POST   /api/v1/receipts/{id}/reprocess - Reprocess receipt
DELETE /api/v1/receipts/{id}       - Delete receipt
GET    /api/v1/receipts/export     - Export to CSV/JSON
```

## Development

### Backend Development

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Worker Development

```bash
cd backend
venv\Scripts\activate
python -m app.worker
```

### Frontend Development

```bash
cd frontend
npm install
npm start
```

## Database Schema

```sql
CREATE TABLE receipts (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP,
    processing_status VARCHAR(20),  -- pending, processing, done, error
    storage_url TEXT,
    vendor TEXT,
    date DATE,
    total_amount NUMERIC(10,2),
    currency CHAR(3),
    tax_amount NUMERIC(10,2),
    category TEXT,
    line_items JSONB,
    ocr_text TEXT,
    checksum TEXT UNIQUE,
    model_version TEXT,
    confidence JSONB,
    notes TEXT
);
```

## Processing Flow

1. **Upload**: User uploads receipt → API validates → saves to MinIO → returns job ID
2. **Queue**: Job enqueued in Redis with receipt metadata
3. **Worker**: 
   - Downloads image from storage
   - Preprocesses (deskew, denoise, crop)
   - Runs OCR (Tesseract/EasyOCR)
   - Sends to Gemini API for structured extraction
   - Validates and normalizes data
   - Saves to PostgreSQL
4. **Notification**: User receives email/in-app notification
5. **Review**: User can view, edit, or approve extracted data

## Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

## Deployment

### Production Checklist

- [ ] Change `SECRET_KEY` to a strong random value
- [ ] Use production PostgreSQL (RDS/managed)
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up monitoring (Sentry, Prometheus)
- [ ] Enable database backups
- [ ] Configure proper CORS origins
- [ ] Use production-grade object storage (AWS S3)
- [ ] Set up rate limiting
- [ ] Enable Redis persistence
- [ ] Configure email service (SendGrid/SES)

### Docker Production Build

```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Security

- JWT-based authentication with secure token storage
- HTTPS-only in production
- CORS configured for allowed origins
- Rate limiting on API endpoints
- SQL injection protection via SQLAlchemy ORM
- File type validation and size limits
- Secure object storage with signed URLs
- Environment-based secrets management

## Monitoring & Logging

- Structured JSON logging
- Sentry integration for error tracking
- Prometheus metrics endpoint: `/metrics`
- Health check: `/health`
- Worker job monitoring via RQ dashboard

## Extensions & Roadmap

- [ ] Mobile app (React Native)
- [ ] Email-to-receipt ingestion
- [ ] Multi-currency conversion
- [ ] Expense policy automation
- [ ] Batch receipt import
- [ ] ML-based vendor normalization
- [ ] Tax reporting exports
- [ ] Reimbursement workflows

## Troubleshooting

### Worker not processing jobs
```bash
docker-compose logs worker
docker-compose restart worker
```

### Database connection issues
```bash
docker-compose exec postgres psql -U receipts_user -d receipts_db
```

### Clear Redis queue
```bash
docker-compose exec redis redis-cli FLUSHALL
```

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
