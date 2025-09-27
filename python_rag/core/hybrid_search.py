"""
Hybrid Search Implementation for Agentic RAG
Combines vector search with BM25 keyword search for optimal retrieval
"""
import logging
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SearchResult:
    """Search result structure"""
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str  # 'vector', 'keyword', 'hybrid'
    table_name: Optional[str] = None
    column_name: Optional[str] = None

@dataclass
class SearchQuery:
    """Query structure for search operations"""
    text: str
    query_type: str  # 'schema', 'data', 'mixed'
    filters: Optional[Dict[str, Any]] = None
    top_k: int = 10

class HybridSearchEngine:
    """Advanced hybrid search combining vector and keyword search"""
    
    def __init__(self, 
                 embedding_model: str = "all-MiniLM-L6-v2",
                 chroma_persist_directory: str = "./chroma_db"):
        
        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        # Initialize ChromaDB
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Collections for different data types
        self.schema_collection = self._get_or_create_collection("schema_collection")
        self.data_collection = self._get_or_create_collection("data_collection")
        
        # BM25 indexes
        self.bm25_schema = None
        self.bm25_data = None
        self.schema_documents = []
        self.data_documents = []
        
        # Document mappings
        self.schema_doc_mapping = {}
        self.data_doc_mapping = {}
        
        logger.info(f"Hybrid search engine initialized with model: {embedding_model}")
    
    def _get_or_create_collection(self, name: str):
        """Get or create ChromaDB collection"""
        try:
            return self.chroma_client.get_collection(name=name)
        except ValueError:
            return self.chroma_client.create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}
            )
    
    def index_schema_documents(self, schemas: Dict[str, Any]):
        """Index database schemas for search"""
        logger.info("Indexing schema documents...")
        
        documents = []
        metadatas = []
        ids = []
        
        doc_id = 0
        for table_name, schema in schemas.items():
            # Create comprehensive schema document
            schema_text = self._create_schema_text(table_name, schema)
            
            documents.append(schema_text)
            metadatas.append({
                "table_name": table_name,
                "type": "schema",
                "row_count": schema.get("row_count", 0),
                "column_count": len(schema.get("columns", [])),
                "description": schema.get("description", "")
            })
            ids.append(f"schema_{doc_id}")
            
            self.schema_doc_mapping[f"schema_{doc_id}"] = {
                "table_name": table_name,
                "schema": schema,
                "text": schema_text
            }
            
            doc_id += 1
            
            # Index individual columns
            for col in schema.get("columns", []):
                col_text = self._create_column_text(table_name, col)
                documents.append(col_text)
                metadatas.append({
                    "table_name": table_name,
                    "column_name": col["name"],
                    "type": "column",
                    "data_type": col["type"],
                    "nullable": col["nullable"]
                })
                ids.append(f"column_{doc_id}")
                
                self.schema_doc_mapping[f"column_{doc_id}"] = {
                    "table_name": table_name,
                    "column": col,
                    "text": col_text
                }
                
                doc_id += 1
        
        # Add to ChromaDB
        if documents:
            self.schema_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        # Prepare for BM25
        self.schema_documents = documents
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        self.bm25_schema = BM25Okapi(tokenized_docs)
        
        logger.info(f"Indexed {len(documents)} schema documents")
    
    def index_data_documents(self, data_chunks: List[Dict[str, Any]]):
        """Index data chunks for search"""
        logger.info("Indexing data documents...")
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(data_chunks):
            # Create searchable text from data chunk
            data_text = self._create_data_text(chunk)
            
            documents.append(data_text)
            metadatas.append({
                "table_name": chunk.get("table_name"),
                "type": "data",
                "chunk_id": chunk.get("chunk_id", i),
                "row_count": len(chunk.get("rows", []))
            })
            ids.append(f"data_{i}")
            
            self.data_doc_mapping[f"data_{i}"] = {
                "chunk": chunk,
                "text": data_text
            }
        
        # Add to ChromaDB
        if documents:
            self.data_collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        # Prepare for BM25
        self.data_documents = documents
        tokenized_docs = [self._tokenize(doc) for doc in documents]
        self.bm25_data = BM25Okapi(tokenized_docs)
        
        logger.info(f"Indexed {len(documents)} data documents")
    
    def hybrid_search(self, query: SearchQuery, alpha: float = 0.5) -> List[SearchResult]:
        """Perform hybrid search combining vector and keyword search"""
        
        if query.query_type == "schema":
            return self._search_schemas(query, alpha)
        elif query.query_type == "data":
            return self._search_data(query, alpha)
        else:  # mixed
            schema_results = self._search_schemas(query, alpha)
            data_results = self._search_data(query, alpha)
            
            # Combine and re-rank
            combined_results = schema_results + data_results
            combined_results.sort(key=lambda x: x.score, reverse=True)
            
            return combined_results[:query.top_k]
    
    def _search_schemas(self, query: SearchQuery, alpha: float) -> List[SearchResult]:
        """Search schema documents"""
        results = []
        
        # Vector search
        vector_results = self._vector_search_collection(
            self.schema_collection, query.text, query.top_k
        )
        
        # Keyword search
        keyword_results = self._keyword_search(
            query.text, self.bm25_schema, self.schema_documents, 
            self.schema_doc_mapping, query.top_k
        )
        
        # Combine scores
        combined_results = self._combine_search_results(
            vector_results, keyword_results, alpha
        )
        
        return combined_results[:query.top_k]
    
    def _search_data(self, query: SearchQuery, alpha: float) -> List[SearchResult]:
        """Search data documents"""
        results = []
        
        # Vector search
        vector_results = self._vector_search_collection(
            self.data_collection, query.text, query.top_k
        )
        
        # Keyword search
        keyword_results = self._keyword_search(
            query.text, self.bm25_data, self.data_documents, 
            self.data_doc_mapping, query.top_k
        )
        
        # Combine scores
        combined_results = self._combine_search_results(
            vector_results, keyword_results, alpha
        )
        
        return combined_results[:query.top_k]
    
    def _vector_search_collection(self, collection, query_text: str, top_k: int) -> List[SearchResult]:
        """Perform vector search on ChromaDB collection"""
        try:
            results = collection.query(
                query_texts=[query_text],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            search_results = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results["documents"][0], 
                results["metadatas"][0], 
                results["distances"][0]
            )):
                # Convert distance to similarity score
                similarity_score = 1.0 - distance
                
                search_results.append(SearchResult(
                    content=doc,
                    score=similarity_score,
                    metadata=metadata,
                    source="vector",
                    table_name=metadata.get("table_name"),
                    column_name=metadata.get("column_name")
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search error: {str(e)}")
            return []
    
    def _keyword_search(self, query_text: str, bm25_index, documents: List[str], 
                       doc_mapping: Dict, top_k: int) -> List[SearchResult]:
        """Perform BM25 keyword search"""
        if not bm25_index:
            return []
        
        try:
            tokenized_query = self._tokenize(query_text)
            scores = bm25_index.get_scores(tokenized_query)
            
            # Get top results
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            search_results = []
            for idx in top_indices:
                if scores[idx] > 0:  # Only include relevant results
                    doc_id = list(doc_mapping.keys())[idx]
                    doc_info = doc_mapping[doc_id]
                    
                    search_results.append(SearchResult(
                        content=doc_info["text"],
                        score=float(scores[idx]),
                        metadata={"doc_id": doc_id, "type": "keyword"},
                        source="keyword",
                        table_name=doc_info.get("table_name"),
                        column_name=doc_info.get("column", {}).get("name")
                    ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Keyword search error: {str(e)}")
            return []
    
    def _combine_search_results(self, vector_results: List[SearchResult], 
                              keyword_results: List[SearchResult], 
                              alpha: float) -> List[SearchResult]:
        """Combine vector and keyword search results with weighted scoring"""
        
        # Normalize scores
        if vector_results:
            max_vector_score = max(result.score for result in vector_results)
            for result in vector_results:
                result.score = result.score / max_vector_score if max_vector_score > 0 else 0
        
        if keyword_results:
            max_keyword_score = max(result.score for result in keyword_results)
            for result in keyword_results:
                result.score = result.score / max_keyword_score if max_keyword_score > 0 else 0
        
        # Create combined results mapping
        combined_scores = {}
        
        # Add vector scores
        for result in vector_results:
            key = result.content[:100]  # Use content prefix as key
            combined_scores[key] = {
                "result": result,
                "vector_score": result.score,
                "keyword_score": 0.0
            }
        
        # Add keyword scores
        for result in keyword_results:
            key = result.content[:100]
            if key in combined_scores:
                combined_scores[key]["keyword_score"] = result.score
            else:
                combined_scores[key] = {
                    "result": result,
                    "vector_score": 0.0,
                    "keyword_score": result.score
                }
        
        # Calculate hybrid scores
        hybrid_results = []
        for key, scores in combined_scores.items():
            hybrid_score = alpha * scores["vector_score"] + (1 - alpha) * scores["keyword_score"]
            
            result = scores["result"]
            result.score = hybrid_score
            result.source = "hybrid"
            hybrid_results.append(result)
        
        # Sort by hybrid score
        hybrid_results.sort(key=lambda x: x.score, reverse=True)
        
        return hybrid_results
    
    def _create_schema_text(self, table_name: str, schema: Dict[str, Any]) -> str:
        """Create searchable text from schema"""
        text_parts = [
            f"Table: {table_name}",
            f"Description: {schema.get('description', '')}",
            f"Columns: {len(schema.get('columns', []))}",
            f"Rows: {schema.get('row_count', 0)}"
        ]
        
        # Add column information
        for col in schema.get("columns", []):
            col_text = f"Column {col['name']} ({col['type']}) - Examples: {', '.join(col.get('examples', []))}"
            text_parts.append(col_text)
        
        # Add relationships
        for rel in schema.get("relationships", []):
            text_parts.append(f"Relationship: {rel}")
        
        return " | ".join(text_parts)
    
    def _create_column_text(self, table_name: str, column: Dict[str, Any]) -> str:
        """Create searchable text for individual column"""
        text_parts = [
            f"Table: {table_name}",
            f"Column: {column['name']}",
            f"Type: {column['type']}",
            f"Nullable: {column['nullable']}",
            f"Primary Key: {column.get('primary_key', False)}",
            f"Examples: {', '.join(column.get('examples', []))}"
        ]
        
        if column.get('foreign_key'):
            text_parts.append(f"Foreign Key: {column['foreign_key']}")
        
        return " | ".join(text_parts)
    
    def _create_data_text(self, chunk: Dict[str, Any]) -> str:
        """Create searchable text from data chunk"""
        text_parts = [
            f"Table: {chunk.get('table_name', '')}",
            f"Rows: {len(chunk.get('rows', []))}"
        ]
        
        # Add sample data content
        for row in chunk.get("rows", [])[:3]:  # Limit to first 3 rows
            row_text = " ".join([f"{k}:{v}" for k, v in row.items() if v is not None])
            text_parts.append(row_text)
        
        return " | ".join(text_parts)
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for BM25"""
        # Convert to lowercase and split on non-alphanumeric characters
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def semantic_rerank(self, query: str, results: List[SearchResult], top_k: int = None) -> List[SearchResult]:
        """Re-rank results using semantic similarity"""
        if not results:
            return results
        
        try:
            # Generate embeddings for query and results
            query_embedding = self.embedding_model.encode([query])
            result_texts = [result.content for result in results]
            result_embeddings = self.embedding_model.encode(result_texts)
            
            # Calculate similarities
            similarities = np.dot(query_embedding, result_embeddings.T)[0]
            
            # Update scores with semantic similarity
            for i, result in enumerate(results):
                # Combine original score with semantic similarity
                result.score = 0.7 * result.score + 0.3 * similarities[i]
            
            # Re-sort
            results.sort(key=lambda x: x.score, reverse=True)
            
            return results[:top_k] if top_k else results
            
        except Exception as e:
            logger.error(f"Semantic reranking error: {str(e)}")
            return results

# Test and example usage
if __name__ == "__main__":
    # Initialize hybrid search engine
    search_engine = HybridSearchEngine()
    
    # Example schema data
    example_schemas = {
        "users": {
            "table_name": "users",
            "description": "User account information",
            "row_count": 1000,
            "columns": [
                {
                    "name": "id", "type": "INTEGER", "nullable": False,
                    "primary_key": True, "examples": ["1", "2", "3"]
                },
                {
                    "name": "email", "type": "VARCHAR", "nullable": False,
                    "primary_key": False, "examples": ["john@example.com", "jane@company.org"]
                }
            ],
            "relationships": ["orders.user_id -> users.id"]
        }
    }
    
    # Index schemas
    search_engine.index_schema_documents(example_schemas)
    
    # Test search
    query = SearchQuery(
        text="find user email information",
        query_type="schema",
        top_k=5
    )
    
    results = search_engine.hybrid_search(query)
    
    for result in results:
        print(f"Score: {result.score:.3f} | Source: {result.source}")
        print(f"Content: {result.content[:100]}...")
        print("---")