# Traffic Law Agent - Configuration Setup

## Quick Start

### 1. Install Dependencies

```bash
# Install pipenv if you don't have it
pip install --user pipenv

# Install project dependencies
pipenv install

# Activate virtual environment
pipenv shell
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual API keys and database credentials
nano .env  # or use your preferred editor
```

### 3. Test Configuration

```bash
# Run the main.py to test if config loads correctly
python main.py
```

You should see output like:
```
2024-02-06 10:30:00.123 | INFO     | __main__:main:23 | ============================================================
2024-02-06 10:30:00.124 | INFO     | __main__:main:24 | Traffic Law Agent Starting
2024-02-06 10:30:00.125 | INFO     | __main__:main:25 | ============================================================
```

## Configuration Modules

### `app/infrastructure/config/settings.py`

Handles all environment variables using Pydantic Settings with validation:

```python
from app.infrastructure.config import settings

# Access configuration
api_key = settings.OPENAI_API_KEY
max_docs = settings.MAX_RETRIEVAL_DOCS
is_prod = settings.is_production()
```

### `app/infrastructure/config/logger.py`

Provides structured logging with Loguru:

```python
from app.infrastructure.config import get_logger

logger = get_logger(__name__)

logger.info("Processing query", query="example", user_id=123)
logger.error("Failed to connect", error=str(e))
```

## Key Features

✅ **Validated Settings**: API keys and URIs are validated at startup  
✅ **Type Safety**: All settings have proper type hints  
✅ **Structured Logging**: JSON format for production, colored for dev  
✅ **Thread-Safe**: Loguru handles concurrent logging automatically  
✅ **Auto-Rotation**: Log files rotate at 100MB and compress after 30 days  

## Next Steps

After configuration is working:
1. Implement Domain layer (entities, state, interfaces)
2. Implement Infrastructure adapters (databases, LLM services)
3. Implement Application nodes (business logic)
4. Wire everything together in Container

## Troubleshooting

**ValidationError on startup?**
- Check that all required keys in `.env` match `.env.example`
- Verify API keys have correct prefixes (sk-, gsk-, etc.)

**Import errors?**
- Make sure you're in the pipenv shell: `pipenv shell`
- Check that `app/` directory has `__init__.py` files

**Logger not colorizing?**
- Set `json_format=False` in `setup_logger()`
- Ensure you're running in a terminal that supports ANSI colors
