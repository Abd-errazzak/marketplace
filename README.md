# Online Marketplace - Jumia-like Platform

A full-featured online marketplace with multi-user support, admin dashboard, integrated payments, AI assistance, and real-time chat.

## Features

- **Multi-user Support**: Buyers, sellers, and admin roles
- **Product Management**: CRUD operations, categories, search, image gallery
- **Payment Integration**: Stripe and PayPal with marketplace split payments
- **Real-time Chat**: Buyer-seller messaging with WebSocket
- **AI Assistant**: Product recommendations, auto-tagging, customer support
- **Analytics**: Seller dashboards with CSV export
- **Notifications**: Email, in-app, and push notifications
- **Admin Panel**: User management, platform metrics, financial reports

## Tech Stack

- **Backend**: Python (FastAPI), Node.js (Socket.IO for real-time)
- **Frontend**: React with Tailwind CSS
- **Database**: MySQL/MariaDB
- **Payments**: Stripe, PayPal
- **AI**: Python FastAPI with embeddings (FAISS)
- **Storage**: S3-compatible for images
- **Deployment**: Docker, Docker Compose

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+
- Python 3.9+

### Development Setup

1. **Clone and setup**:
```bash
git clone <repository>
cd online-store
```

2. **Environment setup**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Start with Docker**:
```bash
docker-compose up -d
```

4. **Or start individual services**:
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm start

# AI Service
cd ai-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```

### XAMPP Setup (Alternative)

1. Start XAMPP (Apache + MySQL)
2. Import database schema from `database/schema.sql`
3. Configure PHP modules in `php-modules/`
4. Update environment variables for local MySQL

## API Documentation

- Backend API: http://localhost:8000/docs
- AI Service API: http://localhost:8001/docs

## Project Structure

```
online-store/
├── backend/                 # FastAPI backend
├── frontend/               # React frontend
├── ai-service/            # AI microservice
├── database/              # Database schemas and migrations
├── docker-compose.yml     # Docker orchestration
├── nginx/                 # Nginx configuration
└── docs/                  # Documentation
```

## Environment Variables

See `.env.example` for required environment variables including:
- Database credentials
- Stripe/PayPal API keys
- JWT secrets
- SMTP settings
- AI service configuration

## Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# E2E tests
npm run test:e2e
```

## Deployment

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License
