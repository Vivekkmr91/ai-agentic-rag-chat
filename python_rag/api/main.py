"""
FastAPI Server for Agentic RAG System
Provides REST API endpoints for the AI-enabled chat application
"""
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional
from pydantic import BaseModel
import uvicorn
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.schema_extractor import SchemaExtractor
from core.hybrid_search import HybridSearchEngine, SearchQuery
from agents.base_agent import AgentCoordinator, QueryAnalyzerAgent
from agents.specialized_agents import SchemaAgent, SQLAgent, TextAgent, SynthesisAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('rag_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class QueryRequest(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None
    include_metadata: bool = True

class QueryResponse(BaseModel):
    success: bool
    response: str
    confidence: float
    query_type: str
    execution_time: float
    metadata: Dict[str, Any]
    error: Optional[str] = None

class DatabaseConnectionRequest(BaseModel):
    database_url: str
    database_type: str = "sqlite"  # sqlite, postgresql, mysql

class SchemaResponse(BaseModel):
    success: bool
    tables_count: int
    schema_summary: Dict[str, Any]
    extraction_time: float
    error: Optional[str] = None

class SystemStatus(BaseModel):
    status: str
    agents_initialized: List[str]
    database_connected: bool
    knowledge_base_size: int
    performance_metrics: Dict[str, Any]

# Global system components
app = FastAPI(
    title="Agentic RAG System API",
    description="AI-powered chat system with database knowledge",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for system components
search_engine: Optional[HybridSearchEngine] = None
coordinator: Optional[AgentCoordinator] = None
database_url: Optional[str] = None
system_initialized = False

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "connected_at": time.time(),
            "queries_processed": 0
        }
        logger.info(f"New WebSocket connection established. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            self.connection_data.pop(websocket, None)
        logger.info(f"WebSocket connection closed. Remaining: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

manager = ConnectionManager()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize system components on startup"""
    global search_engine, coordinator, system_initialized
    
    logger.info("Starting Agentic RAG system...")
    
    try:
        # Initialize hybrid search engine
        search_engine = HybridSearchEngine(
            embedding_model="all-MiniLM-L6-v2",
            chroma_persist_directory="./chroma_db"
        )
        
        # Initialize agent coordinator
        coordinator = AgentCoordinator()
        
        # Register agents
        query_analyzer = QueryAnalyzerAgent()
        coordinator.register_agent(query_analyzer)
        
        # Text agent (works without database)
        text_agent = TextAgent(search_engine)
        coordinator.register_agent(text_agent)
        
        # Synthesis agent
        synthesis_agent = SynthesisAgent()
        coordinator.register_agent(synthesis_agent)
        
        logger.info("Basic system components initialized successfully")
        system_initialized = True
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy" if system_initialized else "initializing",
        "timestamp": time.time(),
        "components": {
            "search_engine": search_engine is not None,
            "coordinator": coordinator is not None,
            "database": database_url is not None
        }
    }

# System status endpoint
@app.get("/status", response_model=SystemStatus)
async def get_system_status():
    """Get comprehensive system status"""
    
    if not system_initialized:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    # Get agent information
    agents_initialized = []
    performance_metrics = {}
    
    if coordinator:
        for agent_type, agent in coordinator.agents.items():
            agents_initialized.append(agent_type.value)
        
        performance_metrics = coordinator.get_system_performance()
    
    # Calculate knowledge base size
    knowledge_base_size = 0
    if search_engine:
        try:
            schema_count = search_engine.schema_collection.count()
            data_count = search_engine.data_collection.count()
            knowledge_base_size = schema_count + data_count
        except:
            knowledge_base_size = 0
    
    return SystemStatus(
        status="ready" if system_initialized else "initializing",
        agents_initialized=agents_initialized,
        database_connected=database_url is not None,
        knowledge_base_size=knowledge_base_size,
        performance_metrics=performance_metrics
    )

# Database connection endpoint
@app.post("/connect-database", response_model=SchemaResponse)
async def connect_database(request: DatabaseConnectionRequest):
    """Connect to database and extract schema"""
    global database_url, search_engine, coordinator
    
    if not system_initialized:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    start_time = time.time()
    
    try:
        # Validate database URL
        database_url = request.database_url
        
        # Extract database schema
        logger.info(f"Extracting schema from database: {database_url}")
        extractor = SchemaExtractor(database_url, sample_size=5)
        schemas = extractor.extract_complete_schema()
        
        # Index schemas in search engine
        search_engine.index_schema_documents(schemas)
        
        # Initialize database-dependent agents
        schema_agent = SchemaAgent(search_engine)
        coordinator.register_agent(schema_agent)
        
        sql_agent = SQLAgent(database_url)
        coordinator.register_agent(sql_agent)
        
        # Create schema summary
        total_tables = len(schemas)
        total_columns = sum(len(schema.columns) for schema in schemas.values())
        total_rows = sum(schema.row_count for schema in schemas.values())
        
        schema_summary = {
            "total_tables": total_tables,
            "total_columns": total_columns,
            "total_rows": total_rows,
            "largest_tables": sorted(
                [(name, schema.row_count) for name, schema in schemas.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
        
        execution_time = time.time() - start_time
        
        logger.info(f"Database schema extracted successfully in {execution_time:.2f}s")
        
        return SchemaResponse(
            success=True,
            tables_count=total_tables,
            schema_summary=schema_summary,
            extraction_time=execution_time
        )
        
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"Error connecting to database: {str(e)}"
        logger.error(error_msg)
        
        return SchemaResponse(
            success=False,
            tables_count=0,
            schema_summary={},
            extraction_time=execution_time,
            error=error_msg
        )

# Main query endpoint
@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query using the agentic RAG system"""
    
    if not system_initialized:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    if not coordinator:
        raise HTTPException(status_code=503, detail="Agent coordinator not available")
    
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # Process query through agent coordinator
        result = coordinator.process_query(request.query, request.context)
        
        execution_time = time.time() - start_time
        
        # Format response
        if result["success"]:
            # Extract the final answer from synthesis agent or other agents
            response_text = ""
            confidence = result["confidence"]
            
            # Try to get synthesized response first
            if "synthesis_agent_output" in result["content"]:
                synthesis_output = result["content"]["synthesis_agent_output"]
                response_text = synthesis_output.get("answer", "Response generated successfully.")
                confidence = synthesis_output.get("confidence", confidence)
            else:
                # Fallback to combining available outputs
                for key, value in result["content"].items():
                    if isinstance(value, dict) and "answer" in value:
                        response_text += f"{value['answer']}\n\n"
                
                if not response_text:
                    response_text = "Query processed successfully, but no detailed response available."
            
            metadata = result.get("metadata", {})
            if request.include_metadata:
                metadata.update({
                    "execution_summary": result.get("execution_summary", {}),
                    "step_details": result.get("step_details", [])
                })
            
            return QueryResponse(
                success=True,
                response=response_text.strip(),
                confidence=confidence,
                query_type=result.get("query_type", "unknown"),
                execution_time=execution_time,
                metadata=metadata
            )
        
        else:
            error_msg = result.get("error", "Unknown error occurred")
            return QueryResponse(
                success=False,
                response=f"I apologize, but I encountered an error processing your query: {error_msg}",
                confidence=0.0,
                query_type="error",
                execution_time=execution_time,
                metadata={"error_details": result},
                error=error_msg
            )
    
    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = str(e)
        logger.error(f"Error processing query: {error_msg}")
        
        return QueryResponse(
            success=False,
            response=f"I apologize, but I encountered an unexpected error: {error_msg}",
            confidence=0.0,
            query_type="error",
            execution_time=execution_time,
            metadata={},
            error=error_msg
        )

# WebSocket endpoint for real-time chat
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    await manager.connect(websocket)
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "system",
            "message": "Connected to Agentic RAG system. You can now ask questions about your database!",
            "timestamp": time.time()
        }
        await manager.send_personal_message(json.dumps(welcome_message), websocket)
        
        while True:
            # Wait for message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            query = message_data.get("query", "")
            context = message_data.get("context", {})
            
            if not query:
                error_response = {
                    "type": "error",
                    "message": "Empty query received",
                    "timestamp": time.time()
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
                continue
            
            # Update connection stats
            manager.connection_data[websocket]["queries_processed"] += 1
            
            # Send typing indicator
            typing_response = {
                "type": "typing",
                "message": "Processing your query...",
                "timestamp": time.time()
            }
            await manager.send_personal_message(json.dumps(typing_response), websocket)
            
            # Process query
            try:
                request = QueryRequest(query=query, context=context)
                response = await process_query(request)
                
                # Send response
                chat_response = {
                    "type": "response",
                    "query": query,
                    "message": response.response,
                    "confidence": response.confidence,
                    "query_type": response.query_type,
                    "execution_time": response.execution_time,
                    "success": response.success,
                    "timestamp": time.time()
                }
                
                if response.error:
                    chat_response["error"] = response.error
                
                await manager.send_personal_message(json.dumps(chat_response), websocket)
                
            except Exception as e:
                error_response = {
                    "type": "error",
                    "message": f"Error processing query: {str(e)}",
                    "timestamp": time.time()
                }
                await manager.send_personal_message(json.dumps(error_response), websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Schema exploration endpoints
@app.get("/schema/tables")
async def get_tables():
    """Get list of all tables"""
    
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    
    try:
        # Search for all tables
        search_query = SearchQuery(
            text="show all tables",
            query_type="schema",
            top_k=50
        )
        
        results = search_engine.hybrid_search(search_query)
        
        # Extract unique tables
        tables = {}
        for result in results:
            if result.table_name:
                tables[result.table_name] = {
                    "name": result.table_name,
                    "description": result.metadata.get("description", ""),
                    "row_count": result.metadata.get("row_count", 0),
                    "column_count": result.metadata.get("column_count", 0)
                }
        
        return {
            "success": True,
            "tables": list(tables.values()),
            "count": len(tables)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tables: {str(e)}")

@app.get("/schema/tables/{table_name}/columns")
async def get_table_columns(table_name: str):
    """Get columns for a specific table"""
    
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    
    try:
        # Search for table columns
        search_query = SearchQuery(
            text=f"columns in table {table_name}",
            query_type="schema",
            top_k=50
        )
        
        results = search_engine.hybrid_search(search_query)
        
        # Extract columns for the specific table
        columns = []
        for result in results:
            if result.table_name == table_name and result.column_name:
                columns.append({
                    "name": result.column_name,
                    "type": result.metadata.get("data_type", ""),
                    "nullable": result.metadata.get("nullable", True),
                    "description": result.content
                })
        
        return {
            "success": True,
            "table_name": table_name,
            "columns": columns,
            "count": len(columns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving columns: {str(e)}")

# Performance metrics endpoint
@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""
    
    if not coordinator:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    try:
        metrics = coordinator.get_system_performance()
        
        # Add WebSocket metrics
        metrics["websocket"] = {
            "active_connections": len(manager.active_connections),
            "total_connections": len(manager.connection_data),
            "connection_details": [
                {
                    "connected_at": data["connected_at"],
                    "queries_processed": data["queries_processed"]
                }
                for data in manager.connection_data.values()
            ]
        }
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": time.time()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving metrics: {str(e)}")

# File upload for database schema
@app.post("/upload-schema")
async def upload_schema_file(file: UploadFile = File(...)):
    """Upload database schema file (SQL, JSON, etc.)"""
    
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")
    
    try:
        # Read file content
        content = await file.read()
        
        if file.filename.endswith('.sql'):
            # Parse SQL schema file
            # This would need proper SQL parsing logic
            return {"message": "SQL schema parsing not yet implemented"}
        
        elif file.filename.endswith('.json'):
            # Parse JSON schema
            schema_data = json.loads(content)
            search_engine.index_schema_documents(schema_data)
            
            return {
                "success": True,
                "message": f"Schema uploaded successfully from {file.filename}",
                "tables_indexed": len(schema_data)
            }
        
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading schema: {str(e)}")

# Development and testing endpoints
@app.post("/test-query")
async def test_query_processing(query: str):
    """Test query processing without full pipeline (for development)"""
    
    if not system_initialized:
        return {"error": "System not initialized"}
    
    try:
        # Simple test query processing
        test_result = {
            "query": query,
            "classification": "test",
            "timestamp": time.time(),
            "system_status": "operational"
        }
        
        return test_result
        
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Run the server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )