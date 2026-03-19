from neo4j import GraphDatabase
from app.core.config import settings

class Neo4jConnector:
    _driver = None

    @classmethod
    def get_driver(cls):
        """Singleton pattern để lấy driver Neo4j"""
        if cls._driver is None:
            cls._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD)
            )
        return cls._driver

    @classmethod
    def close_driver(cls):
        if cls._driver:
            cls._driver.close()
            cls._driver = None

def get_neo4j_driver():
    """Dependency injection function"""
    return Neo4jConnector.get_driver()