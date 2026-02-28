# Docker Infrastructure Setup Guide

## Quick Start

### 1. Start Services

```bash
# Start all services (MongoDB + ChromaDB)
docker-compose up -d
```

### 2. Check Health

```bash
# Check if services are running
make health

# Or manually
docker ps --filter "name=traffic_law"
```

Expected output:
```
NAMES                      STATUS                   PORTS
traffic_law_chromadb       Up 10 seconds (healthy)  0.0.0.0:8000->8000/tcp
traffic_law_mongodb        Up 10 seconds (healthy)  0.0.0.0:27017->27017/tcp
```

### 3. Test Connections

```bash
# Test MongoDB
make test-mongo

# Test ChromaDB
make test-chroma

# Test all
make test
```

## Service Details

### MongoDB

**Purpose:** Stores chat history for LangGraph checkpointing  
**Port:** 27017  
**Credentials:**
- Username: `admin`
- Password: `password123`
- Database: `traffic_law_bot`

**Connection String:**
```
mongodb://admin:password123@localhost:27017
```

**Access MongoDB Shell:**
```bash
make shell-mongo
# Or
docker exec -it traffic_law_mongodb mongosh -u admin -p password123
```

**Sample Commands:**
```javascript
// Show databases
show dbs

// Switch to traffic_law_bot database
use traffic_law_bot

// Show collections
show collections

// Query chat history
db.chat_history.find().limit(5)
```

### ChromaDB

**Purpose:** Vector similarity search for legal documents  
**Port:** 8000  
**API Endpoint:** http://localhost:8000  

**Test ChromaDB:**
```bash
curl http://localhost:8000/api/v1/heartbeat
```

**Python Client Example:**
```python
import chromadb

# Connect to ChromaDB
client = chromadb.HttpClient(host="localhost", port=8000)

# Create collection
collection = client.get_or_create_collection(name="legal_documents")

# Add documents
collection.add(
    documents=["Sample legal text"],
    metadatas=[{"source": "law_123"}],
    ids=["doc1"]
)
```

## Data Persistence

All data is stored in Docker volumes:

```bash
# List volumes
docker volume ls | grep traffic_law

# Output:
# traffic_law_mongodb_data
# traffic_law_mongodb_config
# traffic_law_chromadb_data
```

**Backup MongoDB:**
```bash
make backup
# Creates: ./backups/mongo_backup_YYYYMMDD_HHMMSS
```

**Restore MongoDB:**
```bash
docker exec -i traffic_law_mongodb mongorestore \
  -u admin -p password123 --authenticationDatabase admin \
  --drop /path/to/backup
```

## Common Operations

### View Logs

```bash
# All services
make logs

# MongoDB only
make logs-mongo

# ChromaDB only
make logs-chroma
```

### Restart Services

```bash
make restart
```

### Stop Services

```bash
make down
```

### Clean Everything (⚠️ DESTRUCTIVE)

```bash
# Removes containers AND volumes (all data lost!)
make clean
```

## Troubleshooting

### MongoDB won't start

**Issue:** Port 27017 already in use

```bash
# Check what's using the port
lsof -i :27017

# Stop local MongoDB if running
sudo systemctl stop mongod
```

### ChromaDB connection refused

**Issue:** ChromaDB not ready yet

```bash
# Wait 10-15 seconds after starting
sleep 15
make test-chroma
```

### Permission errors on volumes

```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./data
```

### Health check failing

```bash
# View detailed logs
docker logs traffic_law_mongodb
docker logs traffic_law_chromadb
```

## Optional: Mongo Express (Web UI)

Uncomment the `mongo-express` service in `docker-compose.yml` to enable:

```yaml
mongo-express:
  image: mongo-express:latest
  # ... (uncomment the section)
```

Then access at: http://localhost:8081
- Username: `admin`
- Password: `admin`

## Production Considerations

For production deployment:

1. **Change default passwords**
   ```yaml
   MONGO_INITDB_ROOT_PASSWORD: ${MONGO_PASSWORD}
   ```

2. **Enable ChromaDB authentication**
   ```yaml
   CHROMA_SERVER_AUTH_CREDENTIALS: "user:strong_password"
   CHROMA_SERVER_AUTH_PROVIDER: "chromadb.auth.basic.BasicAuthServerProvider"
   ```

3. **Use secrets management**
   ```bash
   docker secret create mongo_password ./mongo_password.txt
   ```

4. **Enable SSL/TLS**
   ```yaml
   volumes:
     - ./certs:/certs:ro
   ```

5. **Set resource limits**
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

## Integration with Application

Update your `.env` file to match Docker services:

```bash
# MongoDB (matches docker-compose.yml)
MONGO_URI=mongodb://admin:password123@localhost:27017

# ChromaDB
CHROMA_PERSIST_DIR=http://localhost:8000
```

Then in your Python code:

```python
from app.infrastructure.config import settings

# MongoDB connection (for LangGraph checkpointer)
from pymongo import MongoClient
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB_NAME]

# ChromaDB connection (for vector store)
import chromadb
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
```

## Monitoring

### Check resource usage

```bash
docker stats traffic_law_mongodb traffic_law_chromadb
```

### View networks

```bash
docker network inspect traffic_law_network
```

### Check volume sizes

```bash
docker system df -v | grep traffic_law
```

---

**Need help?** Run `make help` to see all available commands.
