#!/bin/bash

echo "🚀 Đang khởi tạo cấu trúc dự án Traffic Law Bot..."

# 1. Tạo cấu trúc thư mục (Folder Structure)
mkdir -p app/api/v1
mkdir -p app/core
mkdir -p app/domain/interfaces
mkdir -p app/domain/models
mkdir -p app/domain/schemas
mkdir -p app/infrastructure/database
mkdir -p app/infrastructure/neo4j
mkdir -p app/infrastructure/llm
mkdir -p app/infrastructure/search
mkdir -p app/modules/auth
mkdir -p app/modules/rag_engine
mkdir -p ui/public

# 2. Tạo file __init__.py cho tất cả các thư mục con trong app/
# Giúp Python import module chính xác
find app -type d -exec touch {}/__init__.py \;

# 3. Tạo các file Code trống (Empty Files)
# --- API Layer ---
touch app/api/v1/chat.py
touch app/api/v1/auth.py
touch app/api/v1/dependencies.py

# --- Core Layer ---
touch app/core/config.py
touch app/core/security.py

# --- Domain Layer ---
touch app/domain/interfaces/base_llm.py
touch app/domain/interfaces/base_search.py
touch app/domain/interfaces/base_repository.py
touch app/domain/models/user.py
touch app/domain/models/chat.py
touch app/domain/schemas/chat_dto.py
touch app/domain/schemas/common.py

# --- Infrastructure Layer ---
touch app/infrastructure/database/postgres_repo.py
touch app/infrastructure/database/session.py
touch app/infrastructure/neo4j/driver.py
touch app/infrastructure/neo4j/vector_store.py
touch app/infrastructure/neo4j/cypher_queries.py
touch app/infrastructure/llm/openai_client.py
touch app/infrastructure/llm/gemini_client.py
touch app/infrastructure/search/tavily_client.py

# --- Modules Layer ---
touch app/modules/rag_engine/graph.py
touch app/modules/rag_engine/tools.py
touch app/modules/rag_engine/chains.py
touch app/modules/rag_engine/state.py

# --- UI & Root ---
touch ui/app.py
touch main.py
touch docker-compose.yml
touch requirements.txt
touch .env

# # 4. Thêm các thư viện cần thiết vào requirements.txt
# cat <<EOT > requirements.txt
# fastapi>=0.100.0
# uvicorn>=0.20.0
# pydantic>=2.0.0
# pydantic-settings
# sqlmodel
# psycopg2-binary
# python-jose[cryptography]
# passlib[bcrypt]
# langchain
# langchain-community
# langchain-openai
# langchain-google-genai
# langgraph
# neo4j
# tavily-python
# chainlit
# python-dotenv
# httpx
# EOT

# 4. Cấp quyền thực thi cho script chính (nếu cần)
chmod +x main.py

echo "✅ Hoàn tất! Cấu trúc dự án đã được tạo thành công."
echo "👉 Chạy lệnh 'ls -R' để kiểm tra."