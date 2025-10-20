# AI Receipt Processing Automation

A fully-coded, self-hosted AI receipt processing system with automated Tesseract OCR + Gemini Vision API parsing, local file storage, PostgreSQL database, and Discord bot integration for seamless receipt management.

## Features

- 📸 Receipt upload via web interface, Discord bot, or email
- 🤖 AI-powered data extraction using Gemini Vision API
- 📊 Automated OCR with Tesseract
- 💾 Local file storage for receipt images
- 🗄️ PostgreSQL database with full audit trail
- 🔐 JWT-based authentication
- ⚡ Async background processing (Redis optional)
- 📈 Admin dashboard with reporting
- 🎮 Discord bot integration with shared database

## Architecture

### System Overview

![Combined System Architecture](workflows/Combined%20System%20Architecture.png)

### Web Application Workflow

![Web App Workflow](workflows/Web%20App%20Workflow.png)

### Discord Bot Workflow

![Discord Bot Workflow](workflows/discord%20bot%20workflow.png)

## Tech Stack

### Backend
- FastAPI (Python 3.9+)
- PostgreSQL + SQLAlchemy
- Async processing (Redis optional)
- Tesseract OCR
- Google Gemini Vision API
- Local file storage

### Frontend
- React 18+
- TailwindCSS
- Axios

### Discord Bot
- discord.py 2.3.2
- aiohttp
- asyncpg
- Shared PostgreSQL database

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 12+
- Google Cloud API key (for Gemini)
- Tesseract OCR installed

### 1. Clone and Setup

```bash
cd c:\Users\USER\Desktop\WhatsApp_Invoice
```

### 2. Environment Configuration

Create `.env` file in backend:

```env
# API
SECRET_KEY=your-secret-key-change-this
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/receipts_db

# Redis (optional - will fallback to async processing if unavailable)
REDIS_URL=redis://localhost:6379/0

# Google Gemini
GOOGLE_API_KEY=your-gemini-api-key

# Storage
UPLOAD_DIR=./uploads

# Email (optional)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Setup Backend

```bash
cd backend
python -m venv venv_receipts
venv_receipts\Scripts\activate
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Create admin user
python scripts/create_admin.py

# Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Setup Frontend

```bash
cd frontend
npm install
npm start
```

Services:
- Backend API: http://localhost:8000
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432

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
venv_receipts\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd frontend
npm start
```

### Discord Bot Development

```bash
cd discord_bot
venv\Scripts\activate
python bot.py
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

1. **Upload**: User uploads receipt (web/Discord) → API validates → saves to local storage
2. **Process**: Async background task processes receipt:
   - Reads image from storage
   - Runs OCR with Tesseract
   - Sends to Gemini Vision API for structured extraction
   - Validates and normalizes data
   - Updates receipt status in PostgreSQL
3. **Review**: User can view extracted data in web interface or Discord

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

## Discord Bot Integration

This project includes a Discord bot that provides automated receipt processing directly in Discord. Upload receipt images and get instant AI-powered extraction results.

### Features
- 📸 Auto-process receipt images sent to bot
- 🤖 Gemini AI extraction with OCR
- 🔐 Secure authentication with web app credentials
- 📊 View, search, and delete receipts from Discord
- 📈 Automated weekly expense reports
- � Short number system (#1, #2, #3) for easy receipt reference
- �🔄 Real-time sync with web interface (shared database)

### Quick Setup

1. **Create Discord Bot** at [Discord Developer Portal](https://discord.com/developers/applications)
2. **Install Dependencies**
```powershell
cd discord_bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure Bot** - Create `.env`:
```ini
DISCORD_BOT_TOKEN=your_bot_token_here
API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/receipts_db
```

4. **Run Bot**
```powershell
python bot.py
```

### Available Commands

- `/login` - Authenticate with your credentials
- `/logout` - Logout from your account
- `/receipts` - List recent receipts with short numbers (#1, #2, #3)
- `/receipt <number>` - View receipt details (e.g., `/receipt 1`)
- `/search` - Search by vendor or category
- `/summary` - Get expense reports (week/month/year)
- `/delete <number>` - Delete a receipt (e.g., `/delete 1`)
- `/help` - Show all commands

**Auto-processing**: Simply send receipt images to the bot in DMs or channels!

### Complete Documentation

See [`discord_bot/README.md`](discord_bot/README.md) for detailed setup, Discord Developer Portal configuration, and usage guide.

## Extensions & Roadmap

- [x] Discord bot integration with short number system
- [x] Async processing without Redis dependency
- [x] Local file storage
- [ ] Email-to-receipt ingestion
- [ ] Multi-currency conversion
- [ ] Batch receipt import
- [ ] ML-based vendor normalization
- [ ] Tax reporting exports

## Troubleshooting

### Backend not processing receipts
- Check backend logs for errors
- Verify Gemini API key is valid
- Ensure Tesseract is installed: `tesseract --version`
- Restart backend: `uvicorn app.main:app --reload`

### Database connection issues
```powershell
psql -U postgres -d receipts_db
# Check connection and tables
```

### Discord bot not responding
- Verify bot token in `.env`
- Check backend API is running
- Run `/receipts` first before using short numbers
- See `discord_bot/README.md` for detailed troubleshooting

## License

MIT

## Support

For issues and questions, please open a GitHub issue.
