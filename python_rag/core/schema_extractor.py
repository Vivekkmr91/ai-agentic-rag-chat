"""
Database Schema Extraction Module for Agentic RAG
Implements advanced schema extraction with metadata and relationship mapping
"""
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from sqlalchemy import create_engine, text, MetaData, Table, inspect
from sqlalchemy.engine import Engine
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ColumnInfo:
    """Column information structure"""
    name: str
    type: str
    nullable: bool
    default: Optional[str]
    primary_key: bool
    foreign_key: Optional[str]
    examples: List[str]

@dataclass
class TableSchema:
    """Enhanced table schema structure"""
    table_name: str
    columns: List[ColumnInfo]
    relationships: List[str]
    sample_data: List[Dict[str, Any]]
    row_count: int
    description: str
    indexes: List[str]
    constraints: List[str]

class SchemaExtractor:
    """Advanced schema extraction with intelligent sampling and metadata"""
    
    def __init__(self, database_url: str, sample_size: int = 5):
        self.database_url = database_url
        self.sample_size = sample_size
        self.engine = create_engine(database_url)
        self.metadata = MetaData()
        self.inspector = inspect(self.engine)
        
    def extract_complete_schema(self) -> Dict[str, TableSchema]:
        """Extract complete database schema with all metadata"""
        try:
            logger.info("Starting complete schema extraction...")
            
            # Get all table names
            table_names = self.inspector.get_table_names()
            logger.info(f"Found {len(table_names)} tables: {table_names}")
            
            schemas = {}
            for table_name in table_names:
                try:
                    schema = self._extract_table_schema(table_name)
                    schemas[table_name] = schema
                    logger.info(f"Successfully extracted schema for table: {table_name}")
                except Exception as e:
                    logger.error(f"Error extracting schema for table {table_name}: {str(e)}")
                    continue
                    
            return schemas
            
        except Exception as e:
            logger.error(f"Error in schema extraction: {str(e)}")
            raise
    
    def _extract_table_schema(self, table_name: str) -> TableSchema:
        """Extract detailed schema for a specific table"""
        
        # Get column information
        columns_info = self._get_columns_info(table_name)
        
        # Get relationships
        relationships = self._get_relationships(table_name)
        
        # Get sample data with examples
        sample_data, examples_by_column = self._get_sample_data_with_examples(
            table_name, columns_info
        )
        
        # Get row count
        row_count = self._get_row_count(table_name)
        
        # Get indexes
        indexes = self._get_indexes(table_name)
        
        # Get constraints
        constraints = self._get_constraints(table_name)
        
        # Generate natural language description
        description = self._generate_table_description(
            table_name, columns_info, relationships, row_count
        )
        
        # Update columns with examples
        for col_info in columns_info:
            col_info.examples = examples_by_column.get(col_info.name, [])
        
        return TableSchema(
            table_name=table_name,
            columns=columns_info,
            relationships=relationships,
            sample_data=sample_data,
            row_count=row_count,
            description=description,
            indexes=indexes,
            constraints=constraints
        )
    
    def _get_columns_info(self, table_name: str) -> List[ColumnInfo]:
        """Extract detailed column information"""
        columns = self.inspector.get_columns(table_name)
        primary_keys = self.inspector.get_primary_keys(table_name)
        foreign_keys = {fk['constrained_columns'][0]: fk['referred_table'] + '.' + fk['referred_columns'][0] 
                       for fk in self.inspector.get_foreign_keys(table_name)}
        
        columns_info = []
        for col in columns:
            col_info = ColumnInfo(
                name=col['name'],
                type=str(col['type']),
                nullable=col['nullable'],
                default=str(col['default']) if col['default'] is not None else None,
                primary_key=col['name'] in primary_keys,
                foreign_key=foreign_keys.get(col['name']),
                examples=[]  # Will be filled later
            )
            columns_info.append(col_info)
        
        return columns_info
    
    def _get_relationships(self, table_name: str) -> List[str]:
        """Extract table relationships"""
        relationships = []
        
        # Foreign keys from this table
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        for fk in foreign_keys:
            rel = f"{table_name}.{fk['constrained_columns'][0]} -> {fk['referred_table']}.{fk['referred_columns'][0]}"
            relationships.append(rel)
        
        # Foreign keys to this table (reverse relationships)
        all_tables = self.inspector.get_table_names()
        for other_table in all_tables:
            if other_table == table_name:
                continue
            try:
                other_fks = self.inspector.get_foreign_keys(other_table)
                for fk in other_fks:
                    if fk['referred_table'] == table_name:
                        rel = f"{other_table}.{fk['constrained_columns'][0]} -> {table_name}.{fk['referred_columns'][0]}"
                        relationships.append(rel)
            except Exception:
                continue
        
        return relationships
    
    def _get_sample_data_with_examples(self, table_name: str, columns_info: List[ColumnInfo]) -> Tuple[List[Dict], Dict[str, List[str]]]:
        """Get sample data and column examples"""
        try:
            query = f"SELECT * FROM {table_name} LIMIT {self.sample_size}"
            
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                rows = result.fetchall()
                columns = result.keys()
                
                # Convert to list of dictionaries
                sample_data = [dict(zip(columns, row)) for row in rows]
                
                # Extract examples for each column
                examples_by_column = {}
                for col_info in columns_info:
                    col_name = col_info.name
                    examples = []
                    for row_dict in sample_data:
                        value = row_dict.get(col_name)
                        if value is not None and str(value).strip():
                            examples.append(str(value))
                    
                    # Keep unique examples, limit to 3
                    unique_examples = list(dict.fromkeys(examples))[:3]
                    examples_by_column[col_name] = unique_examples
                
                return sample_data, examples_by_column
                
        except Exception as e:
            logger.warning(f"Could not get sample data for {table_name}: {str(e)}")
            return [], {}
    
    def _get_row_count(self, table_name: str) -> int:
        """Get approximate row count"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                return result.scalar()
        except Exception as e:
            logger.warning(f"Could not get row count for {table_name}: {str(e)}")
            return 0
    
    def _get_indexes(self, table_name: str) -> List[str]:
        """Get table indexes"""
        try:
            indexes = self.inspector.get_indexes(table_name)
            return [f"{idx['name']}: {', '.join(idx['column_names'])}" for idx in indexes]
        except Exception as e:
            logger.warning(f"Could not get indexes for {table_name}: {str(e)}")
            return []
    
    def _get_constraints(self, table_name: str) -> List[str]:
        """Get table constraints"""
        constraints = []
        try:
            # Primary keys
            pk = self.inspector.get_primary_keys(table_name)
            if pk:
                constraints.append(f"PRIMARY KEY: {', '.join(pk)}")
            
            # Foreign keys
            fks = self.inspector.get_foreign_keys(table_name)
            for fk in fks:
                constraints.append(f"FOREIGN KEY: {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}")
            
            # Unique constraints
            unique_constraints = self.inspector.get_unique_constraints(table_name)
            for uc in unique_constraints:
                constraints.append(f"UNIQUE: {', '.join(uc['column_names'])}")
                
        except Exception as e:
            logger.warning(f"Could not get constraints for {table_name}: {str(e)}")
        
        return constraints
    
    def _generate_table_description(self, table_name: str, columns_info: List[ColumnInfo], 
                                  relationships: List[str], row_count: int) -> str:
        """Generate natural language description of table"""
        
        # Basic info
        description = f"Table '{table_name}' contains {row_count} records with {len(columns_info)} columns."
        
        # Primary key info
        pk_cols = [col.name for col in columns_info if col.primary_key]
        if pk_cols:
            description += f" Primary key: {', '.join(pk_cols)}."
        
        # Key columns (likely important based on name patterns)
        key_patterns = ['id', 'name', 'title', 'email', 'date', 'created', 'updated']
        key_cols = [col.name for col in columns_info 
                   if any(pattern in col.name.lower() for pattern in key_patterns)]
        if key_cols:
            description += f" Key columns: {', '.join(key_cols)}."
        
        # Relationships
        if relationships:
            description += f" Related to {len(set([rel.split(' -> ')[1].split('.')[0] for rel in relationships]))} other tables."
        
        return description
    
    def export_schema_to_json(self, schemas: Dict[str, TableSchema], output_file: str):
        """Export schemas to JSON file"""
        try:
            serializable_schemas = {}
            for table_name, schema in schemas.items():
                serializable_schemas[table_name] = asdict(schema)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(serializable_schemas, f, indent=2, default=str, ensure_ascii=False)
            
            logger.info(f"Schema exported to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting schema: {str(e)}")
            raise
    
    def create_markdown_schema(self, schemas: Dict[str, TableSchema]) -> str:
        """Create markdown representation of schemas for RAG knowledge base"""
        
        markdown_content = "# Database Schema Documentation\n\n"
        
        for table_name, schema in schemas.items():
            markdown_content += f"## Table: {table_name}\n\n"
            markdown_content += f"**Description:** {schema.description}\n\n"
            markdown_content += f"**Row Count:** {schema.row_count:,}\n\n"
            
            # Columns table
            markdown_content += "### Columns\n\n"
            markdown_content += "| Column | Type | Nullable | Primary Key | Foreign Key | Examples |\n"
            markdown_content += "|--------|------|----------|-------------|-------------|----------|\n"
            
            for col in schema.columns:
                fk_info = col.foreign_key if col.foreign_key else ""
                examples = ", ".join(col.examples[:2]) if col.examples else ""
                markdown_content += f"| {col.name} | {col.type} | {col.nullable} | {col.primary_key} | {fk_info} | {examples} |\n"
            
            # Relationships
            if schema.relationships:
                markdown_content += "\n### Relationships\n\n"
                for rel in schema.relationships:
                    markdown_content += f"- {rel}\n"
            
            # Sample data
            if schema.sample_data:
                markdown_content += "\n### Sample Data\n\n"
                markdown_content += "```json\n"
                markdown_content += json.dumps(schema.sample_data[:2], indent=2, default=str)
                markdown_content += "\n```\n"
            
            markdown_content += "\n---\n\n"
        
        return markdown_content

# Example usage and testing
if __name__ == "__main__":
    # Test with SQLite database
    test_db_url = "sqlite:///test_database.db"
    
    try:
        extractor = SchemaExtractor(test_db_url)
        schemas = extractor.extract_complete_schema()
        
        # Export to JSON
        extractor.export_schema_to_json(schemas, "database_schema.json")
        
        # Create markdown
        markdown_schema = extractor.create_markdown_schema(schemas)
        with open("database_schema.md", "w") as f:
            f.write(markdown_schema)
            
        print(f"Successfully extracted schema for {len(schemas)} tables")
        
    except Exception as e:
        print(f"Error: {e}")