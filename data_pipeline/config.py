# config.py
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / Path("data")
CHUNK_DIR = DATA_DIR / "process" / "chunking"
EMBED_DIR = DATA_DIR / "process" / "embedding"

EMBED_OUTPUT = EMBED_DIR / "laws_embedded.json"

# Embedding
MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH_SIZE = 32
NORMALIZE = True
TOP_K = 5

