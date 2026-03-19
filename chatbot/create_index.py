import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(r"c:\law_chatbot\dsp391m-traffic-law-chatbot-chatbot-anhnnhe182323\chatbot")
sys.path.insert(0, str(project_root))

from app.infrastructure.persistence.neo4j_repo import Neo4jRepo
from app.infrastructure.config import settings

def create_fulltext_index():
    repo = Neo4jRepo(settings.NEO4J_URI, settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
    print("Creating FULLTEXT index 'clause_fulltext'...")
    
    # We create a fulltext index on the `content` property of `Clause` and `Article`
    cypher = """
    CREATE FULLTEXT INDEX clause_fulltext IF NOT EXISTS
    FOR (n:Clause|Article) ON EACH [n.content, n.embed_content]
    """
    try:
        with repo.driver.session() as session:
            session.run(cypher)
        print("Successfully created fulltext index.")
        
        # Test fulltext query
        query = '("bên trái" AND "đường") OR "1 chiều" OR "nữa"'
        print(f"Testing fulltext index with query: {query}")
        result = session.run("CALL db.index.fulltext.queryNodes('clause_fulltext', $q, {limit: 5}) YIELD node, score RETURN coalesce(node.article_id, '') AS aid, score, node.content AS txt", {"q": query})
        for r in result:
            print(f"Found AID: {r['aid']} Score: {r['score']}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    create_fulltext_index()
