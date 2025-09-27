"""
Specialized Agents for Agentic RAG System
Implements Schema Agent, SQL Agent, Text Agent, and Synthesis Agent
"""
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional, Tuple
import sqlalchemy
from sqlalchemy import create_engine, text
import sqlite3

from .base_agent import BaseAgent, AgentType, AgentResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SchemaAgent(BaseAgent):
    """Agent specialized in database schema operations and exploration"""
    
    def __init__(self, hybrid_search_engine, config: Dict[str, Any] = None):
        super().__init__(AgentType.SCHEMA_AGENT, config)
        self.search_engine = hybrid_search_engine
        self.schema_cache = {}
    
    def _define_capabilities(self) -> List[str]:
        return [
            "Schema exploration and discovery",
            "Table and column information retrieval",
            "Relationship mapping",
            "Schema-based query suggestions",
            "Metadata analysis"
        ]
    
    def _define_limitations(self) -> List[str]:
        return [
            "Cannot modify database schema",
            "Cannot execute data manipulation queries",
            "Limited to read-only schema operations"
        ]
    
    def can_handle_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Check if query is schema-related"""
        schema_keywords = [
            'table', 'column', 'schema', 'structure', 'relationship',
            'foreign key', 'primary key', 'index', 'constraint',
            'describe', 'show tables', 'show columns'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in schema_keywords)
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process schema-related queries"""
        start_time = time.time()
        
        try:
            # Determine schema operation type
            operation_type = self._identify_schema_operation(query)
            
            # Execute appropriate schema operation
            if operation_type == "table_discovery":
                result = self._discover_tables(query, context)
            elif operation_type == "column_exploration":
                result = self._explore_columns(query, context)
            elif operation_type == "relationship_mapping":
                result = self._map_relationships(query, context)
            elif operation_type == "schema_overview":
                result = self._provide_schema_overview(query, context)
            else:
                result = self._general_schema_search(query, context)
            
            execution_time = time.time() - start_time
            self.update_stats(True, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                content=result,
                confidence=result.get("confidence", 0.8),
                execution_time=execution_time,
                metadata={"operation_type": operation_type}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(False, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                content=None,
                confidence=0.0,
                execution_time=execution_time,
                metadata={},
                error_message=str(e)
    
    def _identify_schema_operation(self, query: str) -> str:
        """Identify the type of schema operation needed"""
        query_lower = query.lower()
        
        if any(phrase in query_lower for phrase in ["show tables", "list tables", "what tables"]):
            return "table_discovery"
        elif any(phrase in query_lower for phrase in ["columns", "fields", "describe", "structure of"]):
            return "column_exploration"
        elif any(phrase in query_lower for phrase in ["relationship", "foreign key", "related to"]):
            return "relationship_mapping"
        elif any(phrase in query_lower for phrase in ["overview", "summary", "schema"]):
            return "schema_overview"
        else:
            return "general_search"
    
    def _discover_tables(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Discover relevant tables based on query"""
        from ..core.hybrid_search import SearchQuery
        
        # Search for table information
        search_query = SearchQuery(
            text=query,
            query_type="schema",
            top_k=10
        )
        
        search_results = self.search_engine.hybrid_search(search_query)
        
        # Extract table information
        tables_info = {}
        for result in search_results:
            if result.table_name and result.table_name not in tables_info:
                tables_info[result.table_name] = {
                    "table_name": result.table_name,
                    "relevance_score": result.score,
                    "description": result.metadata.get("description", ""),
                    "row_count": result.metadata.get("row_count", 0),
                    "column_count": result.metadata.get("column_count", 0)
                }
        
        return {
            "operation": "table_discovery",
            "query": query,
            "tables_found": len(tables_info),
            "tables": list(tables_info.values()),
            "confidence": min(0.9, len(tables_info) * 0.2)
        }
    
    def _explore_columns(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Explore column information for specified tables"""
        from ..core.hybrid_search import SearchQuery
        
        # Extract table name if mentioned in query
        table_name = self._extract_table_name(query)
        
        search_text = query
        if table_name:
            search_text = f"{query} table:{table_name}"
        
        search_query = SearchQuery(
            text=search_text,
            query_type="schema",
            top_k=15
        )
        
        search_results = self.search_engine.hybrid_search(search_query)
        
        # Group results by table
        tables_columns = {}
        for result in search_results:
            table_name = result.table_name or "unknown"
            
            if table_name not in tables_columns:
                tables_columns[table_name] = {
                    "table_name": table_name,
                    "columns": []
                }
            
            if result.column_name:
                column_info = {
                    "column_name": result.column_name,
                    "data_type": result.metadata.get("data_type", ""),
                    "nullable": result.metadata.get("nullable", True),
                    "relevance_score": result.score,
                    "content": result.content
                }
                tables_columns[table_name]["columns"].append(column_info)
        
        return {
            "operation": "column_exploration",
            "query": query,
            "target_table": table_name,
            "tables_analyzed": len(tables_columns),
            "column_details": list(tables_columns.values()),
            "confidence": min(0.9, len(tables_columns) * 0.3)
        }
    
    def _map_relationships(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Map relationships between tables"""
        from ..core.hybrid_search import SearchQuery
        
        # Search for relationship information
        relationship_query = f"{query} foreign key relationship"
        
        search_query = SearchQuery(
            text=relationship_query,
            query_type="schema",
            top_k=20
        )
        
        search_results = self.search_engine.hybrid_search(search_query)
        
        # Extract relationship information
        relationships = []
        relationship_patterns = [
            r'(\w+)\.(\w+)\s*->\s*(\w+)\.(\w+)',  # table.column -> table.column
            r'foreign key.*?(\w+).*?references.*?(\w+)',
            r'(\w+)\s+references\s+(\w+)'
        ]
        
        for result in search_results:
            content = result.content.lower()
            
            for pattern in relationship_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    if len(match.groups()) >= 2:
                        relationships.append({
                            "relationship": match.group(0),
                            "source_table": result.table_name,
                            "relevance_score": result.score,
                            "details": match.groups()
                        })
        
        # Remove duplicates
        unique_relationships = []
        seen = set()
        for rel in relationships:
            rel_key = rel["relationship"].lower()
            if rel_key not in seen:
                seen.add(rel_key)
                unique_relationships.append(rel)
        
        return {
            "operation": "relationship_mapping",
            "query": query,
            "relationships_found": len(unique_relationships),
            "relationships": unique_relationships,
            "confidence": min(0.9, len(unique_relationships) * 0.15)
        }
    
    def _provide_schema_overview(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Provide comprehensive schema overview"""
        # Get table discovery
        tables_result = self._discover_tables("show all tables", context)
        
        # Get key relationships
        relationships_result = self._map_relationships("show relationships", context)
        
        # Calculate statistics
        total_tables = tables_result["tables_found"]
        total_relationships = relationships_result["relationships_found"]
        
        # Identify key tables (highest row counts)
        key_tables = sorted(
            tables_result["tables"], 
            key=lambda x: x.get("row_count", 0), 
            reverse=True
        )[:5]
        
        return {
            "operation": "schema_overview",
            "query": query,
            "summary": {
                "total_tables": total_tables,
                "total_relationships": total_relationships,
                "key_tables": [t["table_name"] for t in key_tables],
                "largest_tables": key_tables[:3]
            },
            "detailed_info": {
                "tables": tables_result["tables"],
                "relationships": relationships_result["relationships"]
            },
            "confidence": 0.85
        }
    
    def _general_schema_search(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """General schema search for any schema-related query"""
        from ..core.hybrid_search import SearchQuery
        
        search_query = SearchQuery(
            text=query,
            query_type="schema",
            top_k=10
        )
        
        search_results = self.search_engine.hybrid_search(search_query)
        
        return {
            "operation": "general_schema_search",
            "query": query,
            "results_found": len(search_results),
            "results": [
                {
                    "table_name": result.table_name,
                    "column_name": result.column_name,
                    "relevance_score": result.score,
                    "content": result.content,
                    "metadata": result.metadata
                }
                for result in search_results
            ],
            "confidence": 0.7
        }
    
    def _extract_table_name(self, query: str) -> Optional[str]:
        """Extract table name from query if mentioned"""
        # Look for patterns like "table_name table", "from table_name", etc.
        patterns = [
            r'\bfrom\s+(\w+)',
            r'\btable\s+(\w+)',
            r'(\w+)\s+table',
            r'\b(\w+)\s+columns?'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None

class SQLAgent(BaseAgent):
    """Agent specialized in SQL query generation and execution"""
    
    def __init__(self, database_url: str, config: Dict[str, Any] = None):
        super().__init__(AgentType.SQL_AGENT, config)
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.query_templates = self._load_query_templates()
    
    def _define_capabilities(self) -> List[str]:
        return [
            "SQL query generation from natural language",
            "Query validation and syntax checking",
            "Query execution and result formatting",
            "Performance optimization suggestions",
            "Error handling and recovery"
        ]
    
    def _define_limitations(self) -> List[str]:
        return [
            "Cannot modify database schema",
            "Limited to SELECT queries by default",
            "Cannot execute dangerous operations (DROP, DELETE without WHERE)",
            "Query complexity limited by timeout constraints"
        ]
    
    def can_handle_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Check if query requires SQL execution"""
        sql_indicators = [
            'select', 'count', 'sum', 'avg', 'min', 'max',
            'group by', 'order by', 'where', 'join',
            'find records', 'get data', 'show data',
            'how many', 'list all', 'filter'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in sql_indicators)
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process SQL-related queries"""
        start_time = time.time()
        
        try:
            # Check if query is already SQL
            if self._is_sql_query(query):
                result = self._execute_sql_query(query, context)
            else:
                # Generate SQL from natural language
                result = self._generate_and_execute_sql(query, context)
            
            execution_time = time.time() - start_time
            self.update_stats(True, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                content=result,
                confidence=result.get("confidence", 0.8),
                execution_time=execution_time,
                metadata={"query_type": "sql_execution"}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(False, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                content=None,
                confidence=0.0,
                execution_time=execution_time,
                metadata={},
                error_message=str(e)
            )
    
    def _is_sql_query(self, query: str) -> bool:
        """Check if query is already in SQL format"""
        sql_keywords = ['SELECT', 'select', 'FROM', 'from', 'WHERE', 'where']
        return any(keyword in query for keyword in sql_keywords) and 'FROM' in query.upper()
    
    def _execute_sql_query(self, sql_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a SQL query safely"""
        
        # Validate query safety
        if not self._is_safe_query(sql_query):
            raise ValueError("Unsafe SQL query detected")
        
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text(sql_query))
                
                # Fetch results
                rows = result.fetchall()
                columns = list(result.keys()) if rows else []
                
                # Convert to list of dictionaries
                data = [dict(zip(columns, row)) for row in rows]
                
                return {
                    "operation": "sql_execution",
                    "query": sql_query,
                    "success": True,
                    "row_count": len(data),
                    "columns": columns,
                    "data": data[:100],  # Limit results
                    "truncated": len(data) > 100,
                    "confidence": 0.9
                }
                
        except Exception as e:
            return {
                "operation": "sql_execution",
                "query": sql_query,
                "success": False,
                "error": str(e),
                "confidence": 0.0
            }
    
    def _generate_and_execute_sql(self, natural_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL from natural language and execute"""
        
        # Simple pattern-based SQL generation
        sql_query = self._generate_sql_from_patterns(natural_query, context)
        
        if not sql_query:
            return {
                "operation": "sql_generation",
                "query": natural_query,
                "success": False,
                "error": "Could not generate SQL from natural language",
                "confidence": 0.0
            }
        
        # Execute generated SQL
        execution_result = self._execute_sql_query(sql_query, context)
        
        # Combine generation and execution results
        return {
            "operation": "nl_to_sql_execution",
            "natural_query": natural_query,
            "generated_sql": sql_query,
            "execution_result": execution_result,
            "confidence": execution_result.get("confidence", 0.0) * 0.8  # Reduced confidence for generated queries
        }
    
    def _generate_sql_from_patterns(self, query: str, context: Dict[str, Any]) -> Optional[str]:
        """Generate SQL using pattern matching (simplified approach)"""
        
        query_lower = query.lower()
        
        # Pattern 1: "Show all records from table"
        if "show all" in query_lower and "from" in query_lower:
            table_match = re.search(r'from\s+(\w+)', query_lower)
            if table_match:
                table_name = table_match.group(1)
                return f"SELECT * FROM {table_name} LIMIT 100"
        
        # Pattern 2: "Count records in table"
        if "count" in query_lower or "how many" in query_lower:
            table_match = re.search(r'(?:in|from)\s+(\w+)', query_lower)
            if table_match:
                table_name = table_match.group(1)
                return f"SELECT COUNT(*) as count FROM {table_name}"
        
        # Pattern 3: "Find records where condition"
        if "find" in query_lower and "where" in query_lower:
            # This would need more sophisticated parsing
            # For now, return a basic query structure
            return None
        
        # Pattern 4: Use context from schema agent
        if context and "step_1_result" in context:
            schema_result = context["step_1_result"]
            if "tables" in schema_result and schema_result["tables"]:
                # Use first relevant table
                table_name = schema_result["tables"][0]["table_name"]
                return f"SELECT * FROM {table_name} LIMIT 10"
        
        return None
    
    def _is_safe_query(self, query: str) -> bool:
        """Check if SQL query is safe to execute"""
        dangerous_keywords = [
            'drop', 'delete', 'update', 'insert', 'alter',
            'create', 'truncate', 'grant', 'revoke'
        ]
        
        query_upper = query.upper()
        
        # Check for dangerous keywords
        for keyword in dangerous_keywords:
            if keyword.upper() in query_upper:
                # Allow DELETE and UPDATE with WHERE clause
                if keyword in ['delete', 'update'] and 'WHERE' in query_upper:
                    continue
                return False
        
        # Additional safety checks
        if ';' in query and query.count(';') > 1:  # Multiple statements
            return False
        
        return True
    
    def _load_query_templates(self) -> Dict[str, str]:
        """Load common SQL query templates"""
        return {
            "count_all": "SELECT COUNT(*) as count FROM {table}",
            "select_all": "SELECT * FROM {table} LIMIT {limit}",
            "describe_table": "PRAGMA table_info({table})",  # SQLite specific
            "list_tables": "SELECT name FROM sqlite_master WHERE type='table'",  # SQLite specific
            "aggregate_by_column": "SELECT {column}, COUNT(*) as count FROM {table} GROUP BY {column} ORDER BY count DESC",
            "recent_records": "SELECT * FROM {table} ORDER BY {date_column} DESC LIMIT {limit}"
        }

class TextAgent(BaseAgent):
    """Agent specialized in text processing and knowledge base search"""
    
    def __init__(self, hybrid_search_engine, config: Dict[str, Any] = None):
        super().__init__(AgentType.TEXT_AGENT, config)
        self.search_engine = hybrid_search_engine
    
    def _define_capabilities(self) -> List[str]:
        return [
            "Natural language query processing",
            "Knowledge base search and retrieval",
            "Text analysis and summarization",
            "Context understanding",
            "Semantic similarity matching"
        ]
    
    def _define_limitations(self) -> List[str]:
        return [
            "Cannot execute SQL queries",
            "Cannot access live databases",
            "Limited to text-based knowledge",
            "Requires pre-indexed knowledge base"
        ]
    
    def can_handle_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Text agent can handle most general queries"""
        return True
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Process text-based queries"""
        start_time = time.time()
        
        try:
            # Search knowledge base
            result = self._search_knowledge_base(query, context)
            
            execution_time = time.time() - start_time
            self.update_stats(True, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                content=result,
                confidence=result.get("confidence", 0.7),
                execution_time=execution_time,
                metadata={"search_type": "text_knowledge_base"}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(False, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                content=None,
                confidence=0.0,
                execution_time=execution_time,
                metadata={},
                error_message=str(e)
            )
    
    def _search_knowledge_base(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Search the knowledge base using hybrid search"""
        from ..core.hybrid_search import SearchQuery
        
        # Determine search scope based on context
        query_type = context.get("query_type", "mixed") if context else "mixed"
        
        search_query = SearchQuery(
            text=query,
            query_type=query_type,
            top_k=10
        )
        
        search_results = self.search_engine.hybrid_search(search_query)
        
        # Process and format results
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "content": result.content,
                "relevance_score": result.score,
                "source": result.source,
                "table_name": result.table_name,
                "column_name": result.column_name,
                "metadata": result.metadata
            })
        
        # Generate summary
        summary = self._generate_search_summary(query, formatted_results)
        
        return {
            "operation": "knowledge_base_search",
            "query": query,
            "results_count": len(formatted_results),
            "results": formatted_results,
            "summary": summary,
            "confidence": min(0.9, len(formatted_results) * 0.1)
        }
    
    def _generate_search_summary(self, query: str, results: List[Dict]) -> str:
        """Generate a summary of search results"""
        if not results:
            return f"No relevant information found for query: {query}"
        
        # Get top results
        top_results = results[:3]
        
        summary_parts = [
            f"Found {len(results)} relevant pieces of information for: {query}",
            "",
            "Key findings:"
        ]
        
        for i, result in enumerate(top_results, 1):
            content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
            summary_parts.append(f"{i}. {content_preview} (Score: {result['relevance_score']:.3f})")
        
        return "\n".join(summary_parts)

class SynthesisAgent(BaseAgent):
    """Agent specialized in synthesizing results from multiple agents"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(AgentType.SYNTHESIS_AGENT, config)
    
    def _define_capabilities(self) -> List[str]:
        return [
            "Multi-agent result synthesis",
            "Response formatting and presentation",
            "Context integration",
            "Answer coherence validation",
            "Final response generation"
        ]
    
    def _define_limitations(self) -> List[str]:
        return [
            "Cannot generate new data",
            "Limited to combining existing results",
            "Dependent on input agent quality"
        ]
    
    def can_handle_query(self, query: str, context: Dict[str, Any] = None) -> bool:
        """Synthesis agent works on processed results from other agents"""
        return context is not None and any(
            key.startswith("step_") and key.endswith("_result") 
            for key in context.keys()
        )
    
    def process_query(self, query: str, context: Dict[str, Any] = None) -> AgentResponse:
        """Synthesize results from multiple agents"""
        start_time = time.time()
        
        try:
            # Extract results from previous steps
            step_results = self._extract_step_results(context)
            
            # Generate synthesized response
            synthesis_result = self._synthesize_results(query, step_results, context)
            
            execution_time = time.time() - start_time
            self.update_stats(True, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=True,
                content=synthesis_result,
                confidence=synthesis_result.get("confidence", 0.8),
                execution_time=execution_time,
                metadata={"synthesis_type": "multi_agent"}
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.update_stats(False, execution_time)
            
            return AgentResponse(
                agent_type=self.agent_type,
                success=False,
                content=None,
                confidence=0.0,
                execution_time=execution_time,
                metadata={},
                error_message=str(e)
            )
    
    def _extract_step_results(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract results from previous processing steps"""
        step_results = []
        
        for key, value in context.items():
            if key.startswith("step_") and key.endswith("_result"):
                step_results.append({
                    "step": key,
                    "content": value
                })
        
        return step_results
    
    def _synthesize_results(self, query: str, step_results: List[Dict], context: Dict[str, Any]) -> Dict[str, Any]:
        """Synthesize results into coherent response"""
        
        # Determine response format based on query type
        query_type = context.get("query_type", "general")
        
        if query_type == "schema_exploration":
            return self._synthesize_schema_response(query, step_results)
        elif query_type == "direct_sql" or query_type == "data_retrieval":
            return self._synthesize_data_response(query, step_results)
        elif query_type == "analytical_query":
            return self._synthesize_analytical_response(query, step_results)
        else:
            return self._synthesize_general_response(query, step_results)
    
    def _synthesize_schema_response(self, query: str, step_results: List[Dict]) -> Dict[str, Any]:
        """Synthesize schema exploration results"""
        
        # Find schema agent results
        schema_result = None
        for step in step_results:
            if "tables" in step["content"] or "columns" in step["content"]:
                schema_result = step["content"]
                break
        
        if not schema_result:
            return {
                "response_type": "schema_exploration",
                "answer": "Unable to retrieve schema information.",
                "confidence": 0.1
            }
        
        # Format schema information
        response_text = f"Here's the schema information for your query: '{query}'\n\n"
        
        if "tables" in schema_result:
            tables = schema_result["tables"]
            response_text += f"Found {len(tables)} relevant table(s):\n\n"
            
            for table in tables[:5]:  # Limit to top 5 tables
                response_text += f"**{table['table_name']}**\n"
                response_text += f"  - Description: {table.get('description', 'No description available')}\n"
                response_text += f"  - Row count: {table.get('row_count', 'Unknown'):,}\n"
                response_text += f"  - Relevance: {table.get('relevance_score', 0):.2f}\n\n"
        
        if "column_details" in schema_result:
            response_text += "Column Details:\n\n"
            for table_info in schema_result["column_details"][:3]:
                response_text += f"**{table_info['table_name']} Columns:**\n"
                for col in table_info["columns"][:10]:
                    response_text += f"  - {col['column_name']} ({col.get('data_type', 'unknown')})\n"
                response_text += "\n"
        
        return {
            "response_type": "schema_exploration",
            "answer": response_text.strip(),
            "confidence": schema_result.get("confidence", 0.8),
            "metadata": {
                "tables_found": len(schema_result.get("tables", [])),
                "operation": schema_result.get("operation", "schema_search")
            }
        }
    
    def _synthesize_data_response(self, query: str, step_results: List[Dict]) -> Dict[str, Any]:
        """Synthesize data retrieval results"""
        
        # Find SQL agent results
        sql_result = None
        for step in step_results:
            if "execution_result" in step["content"] or "data" in step["content"]:
                sql_result = step["content"]
                break
        
        if not sql_result:
            return {
                "response_type": "data_retrieval",
                "answer": "Unable to retrieve data for your query.",
                "confidence": 0.1
            }
        
        # Extract data from nested structure
        data_info = sql_result.get("execution_result", sql_result)
        
        response_text = f"Results for your query: '{query}'\n\n"
        
        if data_info.get("success"):
            row_count = data_info.get("row_count", 0)
            columns = data_info.get("columns", [])
            data = data_info.get("data", [])
            
            response_text += f"Found {row_count:,} record(s)\n"
            
            if data:
                response_text += f"Columns: {', '.join(columns)}\n\n"
                response_text += "Sample data:\n"
                
                # Format first few rows
                for i, row in enumerate(data[:5]):
                    response_text += f"Row {i+1}: {json.dumps(row, default=str)}\n"
                
                if len(data) > 5:
                    response_text += f"\n... and {len(data) - 5} more records"
            
            if "generated_sql" in sql_result:
                response_text += f"\n\nGenerated SQL: {sql_result['generated_sql']}"
        
        else:
            response_text += f"Error executing query: {data_info.get('error', 'Unknown error')}"
        
        return {
            "response_type": "data_retrieval",
            "answer": response_text.strip(),
            "confidence": data_info.get("confidence", 0.6),
            "metadata": {
                "row_count": data_info.get("row_count", 0),
                "success": data_info.get("success", False)
            }
        }
    
    def _synthesize_analytical_response(self, query: str, step_results: List[Dict]) -> Dict[str, Any]:
        """Synthesize analytical query results"""
        
        response_parts = [f"Analysis for: '{query}'\n"]
        
        # Combine insights from different agents
        schema_insights = []
        data_insights = []
        text_insights = []
        
        for step in step_results:
            content = step["content"]
            
            if "tables" in content or "relationships" in content:
                schema_insights.append(content)
            elif "data" in content or "execution_result" in content:
                data_insights.append(content)
            elif "results" in content and "summary" in content:
                text_insights.append(content)
        
        # Add schema context
        if schema_insights:
            response_parts.append("**Schema Context:**")
            for insight in schema_insights[:2]:
                if "summary" in insight:
                    summary = insight["summary"]
                    response_parts.append(f"- {summary.get('total_tables', 0)} tables analyzed")
                    if "key_tables" in summary:
                        response_parts.append(f"- Key tables: {', '.join(summary['key_tables'][:3])}")
        
        # Add data findings
        if data_insights:
            response_parts.append("\n**Data Findings:**")
            for insight in data_insights[:2]:
                if insight.get("success"):
                    row_count = insight.get("row_count", 0)
                    response_parts.append(f"- {row_count:,} records found")
        
        # Add text analysis
        if text_insights:
            response_parts.append("\n**Additional Context:**")
            for insight in text_insights[:1]:
                if "summary" in insight:
                    response_parts.append(f"- {insight['summary'][:200]}...")
        
        # Calculate overall confidence
        confidences = []
        for step in step_results:
            if "confidence" in step["content"]:
                confidences.append(step["content"]["confidence"])
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        return {
            "response_type": "analytical_query",
            "answer": "\n".join(response_parts),
            "confidence": overall_confidence,
            "metadata": {
                "components_analyzed": len(step_results),
                "schema_insights": len(schema_insights),
                "data_insights": len(data_insights),
                "text_insights": len(text_insights)
            }
        }
    
    def _synthesize_general_response(self, query: str, step_results: List[Dict]) -> Dict[str, Any]:
        """Synthesize general query results"""
        
        if not step_results:
            return {
                "response_type": "general",
                "answer": f"I couldn't find specific information for: '{query}'",
                "confidence": 0.1
            }
        
        # Combine all available information
        response_parts = [f"Here's what I found for: '{query}'\n"]
        
        for i, step in enumerate(step_results, 1):
            content = step["content"]
            
            if "summary" in content:
                response_parts.append(f"**Finding {i}:** {content['summary']}")
            elif "answer" in content:
                response_parts.append(f"**Finding {i}:** {content['answer']}")
            elif isinstance(content, str):
                response_parts.append(f"**Finding {i}:** {content[:300]}...")
        
        # Calculate confidence
        confidences = []
        for step in step_results:
            if "confidence" in step["content"]:
                confidences.append(step["content"]["confidence"])
        
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.6
        
        return {
            "response_type": "general",
            "answer": "\n\n".join(response_parts),
            "confidence": overall_confidence,
            "metadata": {
                "sources_combined": len(step_results)
            }
        }

# Example usage and testing
if __name__ == "__main__":
    # This would be used in integration with the main system
    print("Specialized agents module loaded successfully")