# 🚀 Deployment Guide

## Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- Neo4j Aura instance (or local Neo4j)
- Google API Key (for Gemini)
- Tavily API Key (for web search)

### 2. Setup Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env
```

### 3. Start Development Environment
```bash
# Using Make
make dev

# Or using Docker Compose directly
docker-compose up --build
```

### 4. Access Services

- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Chainlit UI**: http://localhost:8001

### 5. Run Tests
```bash
# Using Make
make test

# Or directly
python tests/test_integration.py
```

## Production Deployment

### 1. Build Production Images
```bash
make prod
```

### 2. Configure Reverse Proxy (Nginx)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Chainlit UI
    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 3. Enable HTTPS (Certbot)
```bash
sudo certbot --nginx -d your-domain.com
```

## Monitoring

### View Logs
```bash
# All services
make logs

# Specific service
docker-compose logs -f backend
docker-compose logs -f ui
```

### Check Health
```bash
curl http://localhost:8000/health
```

## Troubleshooting

### Backend won't start
1. Check database connection
2. Verify environment variables
3. Check logs: `docker-compose logs backend`

### UI can't connect to backend
1. Verify `API_BASE_URL` in ui/.env
2. Check backend is running: `curl http://localhost:8000/health`
3. Check Docker network: `docker network inspect traffic-law-assistant_app_network`

### Database connection issues
1. Check PostgreSQL is running: `docker-compose ps`
2. Verify credentials in .env
3. Check database logs: `docker-compose logs db`

---

## 🎯 SUCCESS CHECKLIST

Sau khi deploy, kiểm tra các mục sau:

✅ **Backend API**
- [ ] Health endpoint responds: `curl http://localhost:8000/health`
- [ ] API docs accessible: http://localhost:8000/docs
- [ ] Can register new user
- [ ] Can login and get JWT token

✅ **Chat Functionality**
- [ ] Can send message and get response
- [ ] Streaming endpoint works
- [ ] Sources/citations appear correctly
- [ ] Session history saved to database

✅ **Chainlit UI**
- [ ] Can login through UI
- [ ] Welcome message displays
- [ ] Thinking steps appear during processing
- [ ] Answer streams in real-time
- [ ] Sources display at bottom

✅ **Integration**
- [ ] All integration tests pass
- [ ] Legal queries work (Neo4j retrieval)
- [ ] News queries work (Tavily search)
- [ ] Session management works

✅ **Docker**
- [ ] All containers start successfully
- [ ] No errors in logs
- [ ] Containers restart after failure
- [ ] Health checks passing


Hệ thống đã hoàn thiện! Bạn có thể bắt đầu với:

````bash
make dev
````

Sau đó truy cập http://localhost:8001 để test UI! 🎉