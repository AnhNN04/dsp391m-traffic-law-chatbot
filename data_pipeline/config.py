# config.py
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / Path("data")
MD_RAW_DIR = DATA_DIR / "preprocess" / "markdown_raw"
MD_FIXED_DIR = DATA_DIR / "preprocess" / "markdown_fixed"
CHUNK_DIR = DATA_DIR / "process" / "chunking"
EMBED_DIR = DATA_DIR / "process" / "embedding"

EMBED_OUTPUT = EMBED_DIR / "laws_embedded.json"

FIX_VERSION = "fixV1"
CHUNK_VERSION = "chunkV1"

# Embedding
MODEL_NAME = "intfloat/multilingual-e5-small"
BATCH_SIZE = 32
NORMALIZE = True
TOP_K = 5

