/**
 * AI-Enabled Agentic RAG Chat Application
 * Frontend JavaScript for real-time chat interface
 */

class RAGChatApp {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.messageHistory = [];
        this.isTyping = false;
        
        this.initializeElements();
        this.bindEvents();
        this.checkSystemHealth();
        this.setupWebSocket();
    }

    initializeElements() {
        // Main elements
        this.messagesContainer = document.getElementById('messages');
        this.messageInput = document.getElementById('message-input');
        this.sendBtn = document.getElementById('send-btn');
        this.typingIndicator = document.getElementById('typing-indicator');
        this.includeMetadata = document.getElementById('include-metadata');

        // Status elements
        this.systemStatus = document.getElementById('system-status');
        this.databaseInfo = document.getElementById('database-info');
        this.agentStatus = document.getElementById('agent-status');

        // Modal elements
        this.dbModal = document.getElementById('db-modal');
        this.dbForm = document.getElementById('db-form');
        this.dbUrl = document.getElementById('db-url');
        this.dbType = document.getElementById('db-type');
        this.metricsModal = document.getElementById('metrics-modal');
        this.metricsContent = document.getElementById('metrics-content');

        // Buttons
        this.connectDbBtn = document.getElementById('connect-db-btn');
        this.showMetricsBtn = document.getElementById('show-metrics-btn');
        this.cancelDbBtn = document.getElementById('cancel-db');
        this.closeMetricsBtn = document.getElementById('close-metrics');

        // Quick actions
        this.quickActions = document.querySelectorAll('.quick-action');
    }

    bindEvents() {
        // Chat events
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Database connection events
        this.connectDbBtn.addEventListener('click', () => this.showDatabaseModal());
        this.dbForm.addEventListener('submit', (e) => this.handleDatabaseConnection(e));
        this.cancelDbBtn.addEventListener('click', () => this.hideDatabaseModal());

        // Metrics events
        this.showMetricsBtn.addEventListener('click', () => this.showMetrics());
        this.closeMetricsBtn.addEventListener('click', () => this.hideMetrics());

        // Quick actions
        this.quickActions.forEach(action => {
            action.addEventListener('click', (e) => {
                const query = e.target.getAttribute('data-query');
                this.messageInput.value = query;
                this.sendMessage();
            });
        });

        // Modal close on outside click
        this.dbModal.addEventListener('click', (e) => {
            if (e.target === this.dbModal) this.hideDatabaseModal();
        });
        this.metricsModal.addEventListener('click', (e) => {
            if (e.target === this.metricsModal) this.hideMetrics();
        });
    }

    async checkSystemHealth() {
        try {
            const response = await axios.get('/api/health');
            const data = response.data;

            this.updateSystemStatus(data);
            
            // Check if Python RAG system is available
            if (data.python_rag_status && data.python_rag_status !== 'unavailable') {
                this.getSystemStatus();
            }

        } catch (error) {
            console.error('Health check failed:', error);
            this.updateSystemStatus({
                hono_status: 'error',
                python_rag_status: 'unavailable',
                error: error.message
            });
        }
    }

    async getSystemStatus() {
        try {
            const response = await axios.get('/api/status');
            const data = response.data;

            this.updateAgentStatus(data.agents_initialized);
            this.updateDatabaseStatus(data.database_connected, data.knowledge_base_size);

        } catch (error) {
            console.error('Status check failed:', error);
        }
    }

    setupWebSocket() {
        // For now, we'll use HTTP polling instead of WebSocket since Cloudflare Pages doesn't support WebSocket servers
        // In a production environment, you'd implement proper WebSocket handling
        console.log('WebSocket setup skipped - using HTTP API instead');
    }

    updateSystemStatus(healthData) {
        const statusElement = this.systemStatus;
        const isHealthy = healthData.hono_status === 'healthy' && 
                         healthData.python_rag_status !== 'unavailable';

        if (isHealthy) {
            statusElement.innerHTML = `
                <div class="w-3 h-3 bg-green-400 rounded-full mr-2"></div>
                <span class="text-sm text-green-600">System operational</span>
            `;
        } else {
            statusElement.innerHTML = `
                <div class="w-3 h-3 bg-red-400 rounded-full mr-2"></div>
                <span class="text-sm text-red-600">System issues detected</span>
            `;
        }
    }

    updateAgentStatus(agents) {
        const agentElements = {
            'query_analyzer': 0,
            'schema_agent': 1,
            'sql_agent': 2,
            'text_agent': 3,
            'synthesis_agent': 4
        };

        const statusElements = this.agentStatus.querySelectorAll('span:last-child');
        
        // Reset all to offline
        statusElements.forEach(el => {
            el.textContent = '●';
            el.className = 'text-red-600';
        });

        // Update active agents
        agents.forEach(agent => {
            const index = agentElements[agent];
            if (index !== undefined && statusElements[index]) {
                statusElements[index].textContent = '●';
                statusElements[index].className = 'text-green-600';
            }
        });
    }

    updateDatabaseStatus(connected, knowledgeBaseSize) {
        if (connected) {
            this.databaseInfo.innerHTML = `
                <div class="text-green-600 mb-2">
                    <i class="fas fa-check-circle mr-1"></i>Connected
                </div>
                <div class="text-gray-600">
                    Knowledge base: ${knowledgeBaseSize.toLocaleString()} items
                </div>
            `;
        } else {
            this.databaseInfo.innerHTML = '<p class="text-gray-500">No database connected</p>';
        }
    }

    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isTyping) return;

        // Add user message
        this.addMessage(message, 'user');
        this.messageInput.value = '';
        
        // Show typing indicator
        this.setTyping(true);

        try {
            const requestData = {
                query: message,
                context: {},
                include_metadata: this.includeMetadata.checked
            };

            const response = await axios.post('/api/query', requestData);
            const data = response.data;

            // Add AI response
            this.addMessage(data.response, 'assistant', {
                confidence: data.confidence,
                queryType: data.query_type,
                executionTime: data.execution_time,
                success: data.success,
                metadata: data.metadata,
                error: data.error
            });

            // Store in history
            this.messageHistory.push({
                query: message,
                response: data,
                timestamp: new Date()
            });

        } catch (error) {
            console.error('Query failed:', error);
            
            let errorMessage = 'Sorry, I encountered an error processing your request.';
            if (error.response && error.response.data && error.response.data.response) {
                errorMessage = error.response.data.response;
            }
            
            this.addMessage(errorMessage, 'assistant', {
                success: false,
                error: error.message
            });
        }

        this.setTyping(false);
    }

    addMessage(content, sender, metadata = {}) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message-animation';

        if (sender === 'user') {
            messageDiv.innerHTML = `
                <div class="bg-blue-600 text-white p-4 rounded-l-lg rounded-tr-lg ml-12 relative">
                    <div class="flex items-start">
                        <div class="flex-1">
                            <p class="whitespace-pre-wrap">${this.escapeHtml(content)}</p>
                        </div>
                        <i class="fas fa-user ml-2 mt-1"></i>
                    </div>
                    <div class="text-xs text-blue-100 mt-2">
                        ${new Date().toLocaleTimeString()}
                    </div>
                </div>
            `;
        } else {
            const confidenceColor = this.getConfidenceColor(metadata.confidence || 0);
            const executionTime = metadata.executionTime ? `${metadata.executionTime.toFixed(2)}s` : 'N/A';
            
            let metadataHtml = '';
            if (this.includeMetadata.checked && metadata.success !== false) {
                metadataHtml = `
                    <div class="mt-3 pt-3 border-t border-gray-200 text-xs text-gray-500">
                        <div class="flex flex-wrap gap-4">
                            <span>Confidence: <span class="${confidenceColor}">${(metadata.confidence * 100 || 0).toFixed(1)}%</span></span>
                            <span>Type: ${metadata.queryType || 'unknown'}</span>
                            <span>Time: ${executionTime}</span>
                        </div>
                    </div>
                `;
            }

            let errorHtml = '';
            if (metadata.error) {
                errorHtml = `
                    <div class="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
                        <i class="fas fa-exclamation-triangle mr-1"></i>
                        ${this.escapeHtml(metadata.error)}
                    </div>
                `;
            }

            messageDiv.innerHTML = `
                <div class="bg-gray-100 border-l-4 ${metadata.success === false ? 'border-red-500' : 'border-green-500'} p-4 rounded-r-lg mr-12 relative">
                    <div class="flex items-start">
                        <i class="fas fa-robot ${metadata.success === false ? 'text-red-600' : 'text-green-600'} mr-2 mt-1"></i>
                        <div class="flex-1">
                            <div class="prose prose-sm max-w-none">
                                ${this.formatResponse(content)}
                            </div>
                            ${errorHtml}
                            ${metadataHtml}
                        </div>
                    </div>
                    <div class="text-xs text-gray-400 mt-2">
                        ${new Date().toLocaleTimeString()}
                    </div>
                </div>
            `;
        }

        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatResponse(content) {
        // Convert markdown-like formatting to HTML
        let formatted = this.escapeHtml(content);
        
        // Bold text
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        
        // Code blocks
        formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre class="bg-gray-100 p-2 rounded mt-2 mb-2 text-sm overflow-x-auto"><code>$1</code></pre>');
        
        // Inline code
        formatted = formatted.replace(/`([^`]*)`/g, '<code class="bg-gray-200 px-1 rounded text-sm">$1</code>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        // Lists
        formatted = formatted.replace(/^• (.+)$/gm, '<li class="ml-4">$1</li>');
        formatted = formatted.replace(/(<li.*<\/li>)/s, '<ul class="list-disc list-inside">$1</ul>');
        
        return formatted;
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    getConfidenceColor(confidence) {
        if (confidence >= 0.8) return 'text-green-600';
        if (confidence >= 0.6) return 'text-yellow-600';
        return 'text-red-600';
    }

    setTyping(isTyping) {
        this.isTyping = isTyping;
        this.sendBtn.disabled = isTyping;
        
        if (isTyping) {
            this.typingIndicator.classList.remove('hidden');
            this.sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Thinking...';
        } else {
            this.typingIndicator.classList.add('hidden');
            this.sendBtn.innerHTML = '<i class="fas fa-paper-plane mr-2"></i>Send';
        }
    }

    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }

    // Database connection methods
    showDatabaseModal() {
        this.dbModal.classList.remove('hidden');
        this.dbUrl.focus();
    }

    hideDatabaseModal() {
        this.dbModal.classList.add('hidden');
        this.dbForm.reset();
    }

    async handleDatabaseConnection(event) {
        event.preventDefault();
        
        const url = this.dbUrl.value.trim();
        const type = this.dbType.value;

        if (!url) return;

        try {
            const response = await axios.post('/api/connect-database', {
                database_url: url,
                database_type: type
            });

            const data = response.data;

            if (data.success) {
                this.hideDatabaseModal();
                this.addMessage(`Successfully connected to database! Found ${data.tables_count} tables.`, 'assistant', {
                    success: true,
                    confidence: 1.0
                });
                
                // Update status
                this.getSystemStatus();
                
                // Show schema summary
                if (data.schema_summary) {
                    const summary = data.schema_summary;
                    let summaryText = `Database Summary:\n`;
                    summaryText += `• Tables: ${summary.total_tables}\n`;
                    summaryText += `• Total Columns: ${summary.total_columns}\n`;
                    summaryText += `• Total Records: ${summary.total_rows?.toLocaleString() || 'Unknown'}\n`;
                    
                    if (summary.largest_tables && summary.largest_tables.length > 0) {
                        summaryText += `\nLargest Tables:\n`;
                        summary.largest_tables.slice(0, 3).forEach(([name, count]) => {
                            summaryText += `• ${name}: ${count.toLocaleString()} records\n`;
                        });
                    }
                    
                    this.addMessage(summaryText, 'assistant', {
                        success: true,
                        confidence: 0.9,
                        queryType: 'database_connection'
                    });
                }

            } else {
                throw new Error(data.error || 'Failed to connect to database');
            }

        } catch (error) {
            console.error('Database connection failed:', error);
            
            let errorMessage = 'Failed to connect to database.';
            if (error.response && error.response.data && error.response.data.error) {
                errorMessage = error.response.data.error;
            }
            
            this.addMessage(`Database connection failed: ${errorMessage}`, 'assistant', {
                success: false,
                error: error.message
            });
        }
    }

    // Metrics methods
    async showMetrics() {
        this.metricsModal.classList.remove('hidden');
        this.metricsContent.innerHTML = 'Loading metrics...';

        try {
            const response = await axios.get('/api/metrics');
            const data = response.data;

            if (data.success) {
                this.displayMetrics(data.metrics);
            } else {
                throw new Error(data.error || 'Failed to fetch metrics');
            }

        } catch (error) {
            console.error('Metrics fetch failed:', error);
            this.metricsContent.innerHTML = `
                <div class="text-red-600">
                    <i class="fas fa-exclamation-triangle mr-2"></i>
                    Failed to load metrics: ${error.message}
                </div>
            `;
        }
    }

    displayMetrics(metrics) {
        let html = '<div class="space-y-4">';
        
        // Coordinator stats
        if (metrics.coordinator_stats) {
            html += `
                <div>
                    <h4 class="font-semibold text-gray-800 mb-2">System Overview</h4>
                    <div class="grid grid-cols-3 gap-4">
                        <div class="text-center p-2 bg-blue-50 rounded">
                            <div class="text-2xl font-bold text-blue-600">${metrics.coordinator_stats.total_agents}</div>
                            <div class="text-xs text-gray-600">Active Agents</div>
                        </div>
                        <div class="text-center p-2 bg-green-50 rounded">
                            <div class="text-2xl font-bold text-green-600">${metrics.coordinator_stats.active_plans}</div>
                            <div class="text-xs text-gray-600">Active Plans</div>
                        </div>
                        <div class="text-center p-2 bg-purple-50 rounded">
                            <div class="text-2xl font-bold text-purple-600">${metrics.coordinator_stats.message_history_size}</div>
                            <div class="text-xs text-gray-600">Messages</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // Agent performance
        if (metrics.agent_performance) {
            html += '<div><h4 class="font-semibold text-gray-800 mb-2">Agent Performance</h4>';
            html += '<div class="space-y-2">';
            
            Object.values(metrics.agent_performance).forEach(agent => {
                const successRate = agent.success_rate || 0;
                const avgTime = agent.average_response_time || 0;
                
                html += `
                    <div class="border border-gray-200 rounded p-3">
                        <div class="flex justify-between items-center mb-2">
                            <span class="font-medium">${agent.agent_type.replace('_', ' ').toUpperCase()}</span>
                            <span class="text-sm ${successRate >= 80 ? 'text-green-600' : successRate >= 60 ? 'text-yellow-600' : 'text-red-600'}">
                                ${successRate.toFixed(1)}% success
                            </span>
                        </div>
                        <div class="text-xs text-gray-600">
                            Queries: ${agent.total_queries} | Avg time: ${avgTime.toFixed(3)}s | Errors: ${agent.error_count}
                        </div>
                    </div>
                `;
            });
            
            html += '</div></div>';
        }

        html += '</div>';
        this.metricsContent.innerHTML = html;
    }

    hideMetrics() {
        this.metricsModal.classList.add('hidden');
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ragChat = new RAGChatApp();
});

// Utility functions for development
window.ragUtils = {
    clearMessages: () => {
        const container = document.getElementById('messages');
        container.innerHTML = `
            <div class="message-animation bg-blue-100 border-l-4 border-blue-500 p-4 rounded-r-lg">
                <div class="flex items-start">
                    <i class="fas fa-robot text-blue-600 mr-2 mt-1"></i>
                    <div>
                        <p class="text-gray-800">Chat cleared! How can I help you today?</p>
                    </div>
                </div>
            </div>
        `;
    },
    
    testConnection: async () => {
        try {
            const response = await axios.get('/api/health');
            console.log('Connection test:', response.data);
            return response.data;
        } catch (error) {
            console.error('Connection test failed:', error);
            return error;
        }
    },
    
    getMessageHistory: () => {
        return window.ragChat ? window.ragChat.messageHistory : [];
    }
};