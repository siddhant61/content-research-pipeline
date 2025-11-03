"""
Vector store service for persistent storage and semantic search using ChromaDB.
"""

import asyncio
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from ..config.settings import settings
from ..config.logging import get_logger
from ..data.models import ScrapedContent

logger = get_logger(__name__)


class VectorStoreService:
    """Service for managing vector database operations with ChromaDB."""
    
    def __init__(self):
        """Initialize the vector store service."""
        self.client = None
        self.collection = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize ChromaDB client and collection."""
        try:
            logger.info("Initializing ChromaDB client")
            
            # Try to connect to ChromaDB server (client/server mode)
            try:
                logger.info(f"Attempting to connect to ChromaDB server at {settings.chroma_host}:{settings.chroma_port}")
                self.client = chromadb.HttpClient(
                    host=settings.chroma_host,
                    port=settings.chroma_port
                )
                # Test connection by listing collections
                self.client.heartbeat()
                logger.info("Successfully connected to ChromaDB server")
            except Exception as e:
                logger.warning(f"Failed to connect to ChromaDB server: {e}")
                logger.info("Falling back to local ChromaDB client with persistent storage")
                # Fallback to local client with persistent storage
                self.client = chromadb.Client(
                    ChromaSettings(
                        persist_directory=settings.chroma_persist_directory,
                        anonymized_telemetry=False
                    )
                )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="research_content",
                metadata={"description": "Content research pipeline documents"}
            )
            
            logger.info(f"ChromaDB initialized with {self.collection.count()} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            raise
    
    async def add_documents(
        self,
        documents: List[ScrapedContent],
        collection_name: Optional[str] = None
    ) -> bool:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of ScrapedContent to add
            collection_name: Optional collection name (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not documents:
                logger.warning("No documents to add")
                return True
            
            logger.info(f"Adding {len(documents)} documents to vector store")
            
            # Prepare data for ChromaDB
            ids = []
            texts = []
            metadatas = []
            
            for i, doc in enumerate(documents):
                # Skip documents with errors
                if not doc.text_content or len(doc.text_content.strip()) == 0:
                    continue
                
                # Generate unique ID
                doc_id = f"{doc.url}_{doc.scraped_at.timestamp()}"
                ids.append(doc_id)
                
                # Add text content
                texts.append(doc.text_content)
                
                # Add metadata
                metadatas.append({
                    "url": str(doc.url),
                    "type": doc.type.value,
                    "scraped_at": doc.scraped_at.isoformat(),
                    "length": len(doc.text_content)
                })
            
            if not ids:
                logger.warning("No valid documents to add after filtering")
                return True
            
            # Add to collection in a thread pool
            await asyncio.to_thread(
                self.collection.add,
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Successfully added {len(ids)} documents to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}")
            return False
    
    async def retrieve_documents(
        self,
        query: str,
        n_results: int = 5,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents from the vector store using semantic search.
        
        Args:
            query: Search query
            n_results: Number of results to return
            collection_name: Optional collection name (uses default if None)
            
        Returns:
            List of documents with metadata
        """
        try:
            logger.info(f"Retrieving documents for query: {query}")
            
            # Query the collection in a thread pool
            results = await asyncio.to_thread(
                self.collection.query,
                query_texts=[query],
                n_results=n_results
            )
            
            # Format results
            documents = []
            if results and results.get('documents') and len(results['documents']) > 0:
                for i, doc_text in enumerate(results['documents'][0]):
                    doc = {
                        'text': doc_text,
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {},
                        'distance': results['distances'][0][i] if results.get('distances') else None
                    }
                    documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} documents")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            return []
    
    async def delete_collection(self, collection_name: Optional[str] = None) -> bool:
        """
        Delete a collection from the vector store.
        
        Args:
            collection_name: Collection name to delete (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Deleting collection: {collection_name or 'research_content'}")
            
            await asyncio.to_thread(
                self.client.delete_collection,
                name=collection_name or "research_content"
            )
            
            # Reinitialize the collection
            self._initialize_client()
            
            logger.info("Collection deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            return False
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = await asyncio.to_thread(self.collection.count)
            
            return {
                "name": self.collection.name,
                "count": count,
                "metadata": self.collection.metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "name": "unknown",
                "count": 0,
                "metadata": {}
            }
    
    def close(self):
        """Close the vector store connection."""
        try:
            # ChromaDB client doesn't require explicit closing
            logger.info("Vector store closed")
        except Exception as e:
            logger.error(f"Error closing vector store: {e}")


# Global vector store service instance
vector_store_service = VectorStoreService()
