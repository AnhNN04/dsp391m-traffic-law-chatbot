from langchain_community.vectorstores import Neo4jVector
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings

def get_vector_store(index_name: str = "traffic_law_index"):
    """
    Khởi tạo kết nối tới Neo4j Vector Index.
    Hàm này KHÔNG tạo index mới mà kết nối tới index đã có (hoặc sẽ được tạo bởi script ingestion).
    """
    
    # Sử dụng OpenAI Embeddings (text-embedding-3-small là model mới, giá rẻ và tốt)
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=settings.OPENAI_API_KEY
    )

    # Kết nối Neo4jVector
    # retrieval_query: Cypher query tùy chỉnh để lấy thêm thông tin khi search (Optional)
    vector_store = Neo4jVector.from_existing_graph(
        embedding=embeddings,
        url=settings.NEO4J_URI,
        username=settings.NEO4J_USERNAME,
        password=settings.NEO4J_PASSWORD,
        index_name=index_name,
        node_label="LawChunk",  # Label của node chứa nội dung văn bản
        text_node_property="text", # Property chứa text để embed
        embedding_node_property="embedding", # Property chứa vector
    )
    
    return vector_store