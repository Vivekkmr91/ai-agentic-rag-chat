"""
Simplified FastAPI Server for Agentic RAG System Demo
Provides basic REST API endpoints without heavy dependencies
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import json
import time
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(level=logging.INFO)
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
    database_type: str = "sqlite"

class SchemaResponse(BaseModel):
    success: bool
    tables_count: int
    schema_summary: Dict[str, Any]
    extraction_time: float
    error: Optional[str] = None

# FastAPI app
app = FastAPI(
    title="Simple Agentic RAG System API",
    description="AI-powered chat system with database knowledge (Demo Version)",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
connected_db = None
schema_info = {}
system_initialized = True

class SimpleQueryProcessor:
    """Simplified query processor with basic pattern matching"""
    
    def __init__(self):
        self.query_patterns = {
            'table_list': ['show tables', 'list tables', 'what tables', 'tables in'],
            'schema_info': ['describe', 'structure', 'columns', 'schema'],
            'count_query': ['how many', 'count', 'number of'],
            'data_query': ['show', 'select', 'find', 'get', 'list']
        }
    
    def classify_query(self, query: str) -> str:
        """Classify query type based on patterns"""
        query_lower = query.lower()
        
        for query_type, patterns in self.query_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                return query_type
        
        return 'general'
    
    def process_query(self, query: str, context: Dict = None) -> Dict:
        """Process query and return response"""
        start_time = time.time()
        
        query_type = self.classify_query(query)
        
        try:
            if query_type == 'table_list':
                response = self.handle_table_list(query)
            elif query_type == 'schema_info':
                response = self.handle_schema_info(query)
            elif query_type == 'count_query':
                response = self.handle_count_query(query)
            elif query_type == 'data_query':
                response = self.handle_data_query(query)
            else:
                response = self.handle_general_query(query)
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'response': response,
                'confidence': 0.8,
                'query_type': query_type,
                'execution_time': execution_time,
                'metadata': {
                    'processing_method': 'simple_pattern_matching',
                    'database_connected': connected_db is not None
                }
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'response': f"I encountered an error processing your query: {str(e)}",
                'confidence': 0.0,
                'query_type': 'error',
                'execution_time': execution_time,
                'metadata': {},
                'error': str(e)
            }
    
    def handle_table_list(self, query: str) -> str:
        """Handle table listing queries"""
        if not connected_db:
            return "No database is currently connected. Please connect to a database first using the 'Connect Database' button."
        
        try:
            conn = sqlite3.connect(connected_db)
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()
            
            if not tables:
                return "No tables found in the database."
            
            response = f"Found {len(tables)} table(s) in the database:\n\n"
            for i, table in enumerate(tables, 1):
                response += f"{i}. **{table}**\n"
            
            return response
            
        except Exception as e:
            return f"Error retrieving tables: {str(e)}"
    
    def handle_schema_info(self, query: str) -> str:
        """Handle schema information queries"""
        if not connected_db:
            return "No database is currently connected. Please connect to a database first."
        
        # Extract table name from query
        table_name = None
        words = query.lower().split()
        for i, word in enumerate(words):
            if word in ['table', 'of'] and i + 1 < len(words):
                table_name = words[i + 1]
                break
        
        if not table_name and schema_info:
            # Show general schema info
            tables = list(schema_info.keys())
            response = f"Database contains {len(tables)} tables:\n\n"
            for table in tables[:5]:  # Show first 5 tables
                info = schema_info[table]
                response += f"**{table}**: {info.get('row_count', 0)} records, {len(info.get('columns', []))} columns\n"
            
            if len(tables) > 5:
                response += f"\n... and {len(tables) - 5} more tables."
            
            return response
        
        if table_name and table_name in schema_info:
            info = schema_info[table_name]
            response = f"**{table_name}** table structure:\n\n"
            response += f"- Records: {info.get('row_count', 0):,}\n"
            response += f"- Columns: {len(info.get('columns', []))}\n\n"
            
            if 'columns' in info:
                response += "**Columns:**\n"
                for col in info['columns'][:10]:  # Show first 10 columns
                    response += f"- {col['name']} ({col['type']})\n"
            
            return response
        
        return "Please specify a table name or connect to a database first."
    
    def handle_count_query(self, query: str) -> str:
        """Handle counting queries"""
        if not connected_db:
            return "No database is currently connected. Please connect to a database first."
        
        try:
            conn = sqlite3.connect(connected_db)
            
            # Simple pattern to extract table name
            words = query.lower().split()
            table_name = None
            
            for word in words:
                if word in schema_info:
                    table_name = word
                    break
            
            if not table_name:
                # Return total count of all records
                cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                total_records = 0
                table_counts = []
                
                for table in tables:
                    try:
                        count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                        count = count_cursor.fetchone()[0]
                        total_records += count
                        table_counts.append((table, count))
                    except:
                        continue
                
                conn.close()
                
                response = f"Total records across all tables: {total_records:,}\n\n"
                response += "**Records by table:**\n"
                for table, count in sorted(table_counts, key=lambda x: x[1], reverse=True)[:5]:
                    response += f"- {table}: {count:,} records\n"
                
                return response
            
            else:
                # Count records in specific table
                cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                conn.close()
                
                return f"The **{table_name}** table contains {count:,} records."
                
        except Exception as e:
            return f"Error counting records: {str(e)}"
    
    def handle_data_query(self, query: str) -> str:
        """Handle data retrieval queries"""
        if not connected_db:
            return "No database is currently connected. Please connect to a database first."
        
        try:
            conn = sqlite3.connect(connected_db)
            
            # Very basic SQL generation
            if 'select' in query.lower():
                # User provided SQL query
                try:
                    cursor = conn.execute(query)
                    results = cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    conn.close()
                    
                    if not results:
                        return "Query executed successfully but returned no results."
                    
                    response = f"Query returned {len(results)} record(s):\n\n"
                    response += f"**Columns:** {', '.join(columns)}\n\n"
                    
                    # Show first few results
                    for i, row in enumerate(results[:5]):
                        response += f"**Row {i+1}:** {dict(zip(columns, row))}\n"
                    
                    if len(results) > 5:
                        response += f"\n... and {len(results) - 5} more records."
                    
                    return response
                    
                except Exception as e:
                    return f"SQL execution error: {str(e)}"
            
            else:
                # Generate simple SELECT query
                words = query.lower().split()
                table_name = None
                
                for word in words:
                    if word in schema_info:
                        table_name = word
                        break
                
                if not table_name and schema_info:
                    # Use first table
                    table_name = list(schema_info.keys())[0]
                
                if table_name:
                    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 5")
                    results = cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    conn.close()
                    
                    response = f"Sample data from **{table_name}** table:\n\n"
                    response += f"**Columns:** {', '.join(columns)}\n\n"
                    
                    for i, row in enumerate(results):
                        response += f"**Row {i+1}:** {dict(zip(columns, row))}\n"
                    
                    return response
                
                return "Please specify a table name in your query."
                
        except Exception as e:
            return f"Error retrieving data: {str(e)}"
    
    def handle_general_query(self, query: str) -> str:
        """Handle general queries"""
        if not connected_db:
            return "I can help you explore and query your database, but no database is currently connected. Please use the 'Connect Database' button to connect to a database first."
        
        response = f"I understand you're asking: '{query}'\n\n"
        response += "I can help you with:\n"
        response += "- Listing tables: 'Show me all tables'\n"
        response += "- Table structure: 'Describe the users table'\n"
        response += "- Counting records: 'How many users are there?'\n"
        response += "- Viewing data: 'Show me data from orders table'\n"
        response += "- SQL queries: 'SELECT * FROM products LIMIT 10'\n\n"
        
        if schema_info:
            tables = list(schema_info.keys())
            response += f"Available tables: {', '.join(tables[:5])}"
            if len(tables) > 5:
                response += f" and {len(tables) - 5} more."
        
        return response

# Initialize query processor
query_processor = SimpleQueryProcessor()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {
            "query_processor": True,
            "database": connected_db is not None
        }
    }

@app.get("/status")
async def get_system_status():
    """Get system status"""
    return {
        "status": "ready",
        "agents_initialized": ["query_analyzer", "text_agent", "synthesis_agent"],
        "database_connected": connected_db is not None,
        "knowledge_base_size": len(schema_info),
        "performance_metrics": {
            "system_type": "simplified_demo",
            "capabilities": ["basic_sql", "schema_exploration", "pattern_matching"]
        }
    }

@app.post("/connect-database", response_model=SchemaResponse)
async def connect_database(request: DatabaseConnectionRequest):
    """Connect to database and extract basic schema"""
    global connected_db, schema_info
    
    start_time = time.time()
    
    try:
        database_url = request.database_url
        
        # Simple SQLite connection for demo
        if not database_url.startswith('sqlite:'):
            return SchemaResponse(
                success=False,
                tables_count=0,
                schema_summary={},
                extraction_time=time.time() - start_time,
                error="This demo version only supports SQLite databases"
            )
        
        # Extract file path from sqlite URL
        db_path = database_url.replace('sqlite:///', '').replace('sqlite://', '')
        
        if not os.path.exists(db_path):
            return SchemaResponse(
                success=False,
                tables_count=0,
                schema_summary={},
                extraction_time=time.time() - start_time,
                error=f"Database file not found: {db_path}"
            )
        
        # Connect and extract basic schema
        conn = sqlite3.connect(db_path)
        
        # Get tables
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = {}
        total_rows = 0
        
        for table_name in tables:
            try:
                # Get column info
                table_cursor = conn.execute(f"PRAGMA table_info({table_name})")
                columns = []
                for row in table_cursor.fetchall():
                    columns.append({
                        'name': row[1],
                        'type': row[2],
                        'nullable': not row[3],
                        'primary_key': bool(row[5])
                    })
                
                # Get row count
                count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
                row_count = count_cursor.fetchone()[0]
                total_rows += row_count
                
                schema_info[table_name] = {
                    'columns': columns,
                    'row_count': row_count
                }
                
            except Exception as e:
                logger.warning(f"Error processing table {table_name}: {e}")
                continue
        
        conn.close()
        
        connected_db = db_path
        
        schema_summary = {
            "total_tables": len(tables),
            "total_columns": sum(len(info['columns']) for info in schema_info.values()),
            "total_rows": total_rows,
            "largest_tables": sorted(
                [(name, info['row_count']) for name, info in schema_info.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }
        
        execution_time = time.time() - start_time
        
        logger.info(f"Connected to database: {db_path}")
        
        return SchemaResponse(
            success=True,
            tables_count=len(tables),
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

@app.post("/query", response_model=QueryResponse)
async def process_query(request: QueryRequest):
    """Process a query using simplified processing"""
    
    try:
        result = query_processor.process_query(request.query, request.context)
        
        return QueryResponse(
            success=result['success'],
            response=result['response'],
            confidence=result['confidence'],
            query_type=result['query_type'],
            execution_time=result['execution_time'],
            metadata=result['metadata'],
            error=result.get('error')
        )
        
    except Exception as e:
        return QueryResponse(
            success=False,
            response=f"I apologize, but I encountered an unexpected error: {str(e)}",
            confidence=0.0,
            query_type="error",
            execution_time=0.0,
            metadata={},
            error=str(e)
        )

@app.get("/schema/tables")
async def get_tables():
    """Get list of all tables"""
    if not connected_db:
        raise HTTPException(status_code=503, detail="No database connected")
    
    try:
        tables = []
        for name, info in schema_info.items():
            tables.append({
                "name": name,
                "row_count": info.get("row_count", 0),
                "column_count": len(info.get("columns", []))
            })
        
        return {
            "success": True,
            "tables": tables,
            "count": len(tables)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tables: {str(e)}")

@app.get("/schema/tables/{table_name}/columns")
async def get_table_columns(table_name: str):
    """Get columns for a specific table"""
    if not connected_db:
        raise HTTPException(status_code=503, detail="No database connected")
    
    if table_name not in schema_info:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")
    
    try:
        columns = schema_info[table_name].get("columns", [])
        
        return {
            "success": True,
            "table_name": table_name,
            "columns": columns,
            "count": len(columns)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving columns: {str(e)}")

@app.get("/metrics")
async def get_metrics():
    """Get system performance metrics"""
    return {
        "success": True,
        "metrics": {
            "system_type": "simplified_demo",
            "database_connected": connected_db is not None,
            "tables_indexed": len(schema_info),
            "query_processor": "pattern_matching",
            "features": [
                "basic_sql_execution",
                "schema_exploration", 
                "table_listing",
                "simple_pattern_matching"
            ]
        },
        "timestamp": time.time()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)