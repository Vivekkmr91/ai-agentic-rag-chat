import { Hono } from 'hono'
import { cors } from 'hono/cors'
import { serveStatic } from 'hono/cloudflare-workers'

type Bindings = {
  // Add Cloudflare bindings here if needed
}

const app = new Hono<{ Bindings: Bindings }>()

// Enable CORS for frontend-backend communication
app.use('/api/*', cors())

// Serve static files from public directory
app.use('/static/*', serveStatic({ root: './public' }))

// API Routes for RAG system integration

// Health check for Python RAG system
app.get('/api/health', async (c) => {
  try {
    const response = await fetch('http://localhost:8000/health')
    const data = await response.json()
    return c.json({ 
      hono_status: 'healthy',
      python_rag_status: data,
      timestamp: new Date().toISOString()
    })
  } catch (error) {
    return c.json({ 
      hono_status: 'healthy',
      python_rag_status: 'unavailable',
      error: 'Python RAG system not accessible',
      timestamp: new Date().toISOString()
    }, 503)
  }
})

// Process query through RAG system
app.post('/api/query', async (c) => {
  try {
    const body = await c.req.json()
    
    // Forward request to Python RAG system
    const response = await fetch('http://localhost:8000/query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body)
    })
    
    if (!response.ok) {
      throw new Error(`RAG system error: ${response.status}`)
    }
    
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      success: false,
      response: 'Sorry, the AI system is currently unavailable. Please try again later.',
      confidence: 0.0,
      query_type: 'error',
      execution_time: 0.0,
      metadata: {},
      error: error instanceof Error ? error.message : 'Unknown error'
    }, 503)
  }
})

// Connect to database
app.post('/api/connect-database', async (c) => {
  try {
    const body = await c.req.json()
    
    const response = await fetch('http://localhost:8000/connect-database', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body)
    })
    
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      success: false,
      tables_count: 0,
      schema_summary: {},
      extraction_time: 0.0,
      error: error instanceof Error ? error.message : 'Database connection failed'
    }, 503)
  }
})

// Get system status
app.get('/api/status', async (c) => {
  try {
    const response = await fetch('http://localhost:8000/status')
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      status: 'error',
      agents_initialized: [],
      database_connected: false,
      knowledge_base_size: 0,
      performance_metrics: {},
      error: 'Python RAG system unavailable'
    }, 503)
  }
})

// Get database tables
app.get('/api/schema/tables', async (c) => {
  try {
    const response = await fetch('http://localhost:8000/schema/tables')
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      success: false,
      tables: [],
      count: 0,
      error: error instanceof Error ? error.message : 'Failed to fetch tables'
    }, 503)
  }
})

// Get table columns
app.get('/api/schema/tables/:tableName/columns', async (c) => {
  try {
    const tableName = c.req.param('tableName')
    const response = await fetch(`http://localhost:8000/schema/tables/${tableName}/columns`)
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      success: false,
      table_name: c.req.param('tableName'),
      columns: [],
      count: 0,
      error: error instanceof Error ? error.message : 'Failed to fetch columns'
    }, 503)
  }
})

// Get performance metrics
app.get('/api/metrics', async (c) => {
  try {
    const response = await fetch('http://localhost:8000/metrics')
    const data = await response.json()
    return c.json(data)
    
  } catch (error) {
    return c.json({
      success: false,
      metrics: {},
      timestamp: Date.now(),
      error: error instanceof Error ? error.message : 'Failed to fetch metrics'
    }, 503)
  }
})

// Main chat interface
app.get('/', (c) => {
  return c.html(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI-Enabled Agentic RAG Chat</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <link href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.0/css/all.min.css" rel="stylesheet">
        <script>
            tailwind.config = {
                theme: {
                    extend: {
                        animation: {
                            'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                            'bounce-subtle': 'bounce 1s infinite',
                        }
                    }
                }
            }
        </script>
        <style>
            .message-animation {
                animation: slideInUp 0.3s ease-out;
            }
            @keyframes slideInUp {
                from {
                    opacity: 0;
                    transform: translateY(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(0);
                }
            }
            .typing-indicator {
                display: inline-block;
                animation: bounce-subtle 1.4s infinite;
            }
            .typing-indicator:nth-child(2) { animation-delay: 0.2s; }
            .typing-indicator:nth-child(3) { animation-delay: 0.4s; }
        </style>
    </head>
    <body class="bg-gradient-to-br from-blue-50 to-indigo-100 min-h-screen">
        <div class="container mx-auto px-4 py-6 max-w-6xl">
            <!-- Header -->
            <div class="text-center mb-8">
                <h1 class="text-4xl font-bold text-gray-800 mb-2">
                    <i class="fas fa-robot text-blue-600 mr-3"></i>
                    AI-Enabled Agentic RAG Chat
                </h1>
                <p class="text-gray-600 text-lg">Intelligent database conversations powered by multi-agent AI</p>
            </div>

            <!-- System Status -->
            <div class="bg-white rounded-lg shadow-md p-4 mb-6">
                <div class="flex items-center justify-between">
                    <div class="flex items-center space-x-4">
                        <div id="system-status" class="flex items-center">
                            <div class="w-3 h-3 bg-yellow-400 rounded-full animate-pulse mr-2"></div>
                            <span class="text-sm text-gray-600">Checking system status...</span>
                        </div>
                    </div>
                    <div class="flex space-x-2">
                        <button id="connect-db-btn" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors">
                            <i class="fas fa-database mr-2"></i>Connect Database
                        </button>
                        <button id="show-metrics-btn" class="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 transition-colors">
                            <i class="fas fa-chart-bar mr-2"></i>Metrics
                        </button>
                    </div>
                </div>
            </div>

            <!-- Main Chat Interface -->
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">
                
                <!-- Chat Panel -->
                <div class="lg:col-span-3 bg-white rounded-lg shadow-lg flex flex-col h-[600px]">
                    <!-- Chat Header -->
                    <div class="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 rounded-t-lg">
                        <h2 class="text-xl font-semibold flex items-center">
                            <i class="fas fa-comments mr-2"></i>
                            Chat with Your Database
                        </h2>
                        <p class="text-blue-100 text-sm mt-1">Ask questions about your data using natural language</p>
                    </div>
                    
                    <!-- Messages Container -->
                    <div id="messages" class="flex-1 p-4 overflow-y-auto space-y-4 bg-gray-50">
                        <div class="message-animation bg-blue-100 border-l-4 border-blue-500 p-4 rounded-r-lg">
                            <div class="flex items-start">
                                <i class="fas fa-robot text-blue-600 mr-2 mt-1"></i>
                                <div>
                                    <p class="text-gray-800">Hello! I'm your AI assistant powered by agentic RAG technology. I can help you explore and analyze your database using natural language.</p>
                                    <p class="text-gray-600 text-sm mt-2">To get started, connect a database or ask me questions like:</p>
                                    <ul class="text-gray-600 text-sm mt-1 ml-4">
                                        <li>• "Show me all tables in the database"</li>
                                        <li>• "What columns does the users table have?"</li>
                                        <li>• "Find customers who made purchases last month"</li>
                                        <li>• "Analyze sales trends by region"</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Chat Input -->
                    <div class="p-4 border-t border-gray-200 bg-white rounded-b-lg">
                        <div class="flex space-x-2">
                            <input 
                                type="text" 
                                id="message-input" 
                                placeholder="Ask a question about your database..."
                                class="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            >
                            <button 
                                id="send-btn" 
                                class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors flex items-center"
                            >
                                <i class="fas fa-paper-plane mr-2"></i>Send
                            </button>
                        </div>
                        <div class="flex items-center mt-2 space-x-4">
                            <label class="flex items-center text-sm text-gray-600">
                                <input type="checkbox" id="include-metadata" class="mr-2" checked>
                                Include technical details
                            </label>
                            <div id="typing-indicator" class="hidden text-sm text-gray-500">
                                <span class="typing-indicator">●</span>
                                <span class="typing-indicator">●</span>
                                <span class="typing-indicator">●</span>
                                <span class="ml-2">AI is thinking...</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Sidebar -->
                <div class="space-y-6">
                    
                    <!-- Database Info -->
                    <div class="bg-white rounded-lg shadow-md p-4">
                        <h3 class="font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-database text-blue-600 mr-2"></i>Database Info
                        </h3>
                        <div id="database-info" class="text-sm text-gray-600">
                            <p>No database connected</p>
                        </div>
                    </div>

                    <!-- Quick Actions -->
                    <div class="bg-white rounded-lg shadow-md p-4">
                        <h3 class="font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-lightning-bolt text-yellow-500 mr-2"></i>Quick Actions
                        </h3>
                        <div class="space-y-2">
                            <button class="w-full text-left text-sm text-blue-600 hover:bg-blue-50 p-2 rounded quick-action" 
                                    data-query="Show me all tables in the database">
                                📊 List all tables
                            </button>
                            <button class="w-full text-left text-sm text-blue-600 hover:bg-blue-50 p-2 rounded quick-action" 
                                    data-query="What is the structure of this database?">
                                🏗️ Database overview
                            </button>
                            <button class="w-full text-left text-sm text-blue-600 hover:bg-blue-50 p-2 rounded quick-action" 
                                    data-query="Show me relationships between tables">
                                🔗 Table relationships
                            </button>
                            <button class="w-full text-left text-sm text-blue-600 hover:bg-blue-50 p-2 rounded quick-action" 
                                    data-query="Give me a summary of the data">
                                📈 Data summary
                            </button>
                        </div>
                    </div>

                    <!-- Agent Status -->
                    <div class="bg-white rounded-lg shadow-md p-4">
                        <h3 class="font-semibold text-gray-800 mb-3 flex items-center">
                            <i class="fas fa-users-cog text-green-600 mr-2"></i>Agent Status
                        </h3>
                        <div id="agent-status" class="space-y-2 text-sm">
                            <div class="flex items-center justify-between">
                                <span class="text-gray-600">Query Analyzer</span>
                                <span class="text-yellow-600">●</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-gray-600">Schema Agent</span>
                                <span class="text-yellow-600">●</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-gray-600">SQL Agent</span>
                                <span class="text-yellow-600">●</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-gray-600">Text Agent</span>
                                <span class="text-yellow-600">●</span>
                            </div>
                            <div class="flex items-center justify-between">
                                <span class="text-gray-600">Synthesis Agent</span>
                                <span class="text-yellow-600">●</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Database Connection Modal -->
        <div id="db-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold mb-4">Connect to Database</h3>
                <form id="db-form">
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Database URL</label>
                        <input 
                            type="text" 
                            id="db-url" 
                            placeholder="sqlite:///example.db or postgresql://..."
                            class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            required
                        >
                    </div>
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Database Type</label>
                        <select id="db-type" class="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="sqlite">SQLite</option>
                            <option value="postgresql">PostgreSQL</option>
                            <option value="mysql">MySQL</option>
                        </select>
                    </div>
                    <div class="flex justify-end space-x-2">
                        <button type="button" id="cancel-db" class="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50">
                            Cancel
                        </button>
                        <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
                            Connect
                        </button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Metrics Modal -->
        <div id="metrics-modal" class="fixed inset-0 bg-black bg-opacity-50 hidden flex items-center justify-center z-50">
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                <div class="flex justify-between items-center mb-4">
                    <h3 class="text-lg font-semibold">System Performance Metrics</h3>
                    <button id="close-metrics" class="text-gray-400 hover:text-gray-600">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div id="metrics-content" class="text-sm">
                    Loading metrics...
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/axios@1.6.0/dist/axios.min.js"></script>
        <script src="/static/app.js"></script>
    </body>
    </html>
  `)
})

export default app
