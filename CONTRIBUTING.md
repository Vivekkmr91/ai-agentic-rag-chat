# Contributing to AI Agentic RAG Chat

Thank you for your interest in contributing to the AI Agentic RAG Chat project! This document provides guidelines and information for contributors.

## 🚀 Project Overview

AI Agentic RAG Chat is an innovative application that combines:
- **Multi-Agent AI Architecture**: 5 specialized agents working in coordination
- **Hybrid Search Technology**: Vector + keyword search for optimal retrieval
- **Natural Language Processing**: Convert human questions to database queries
- **Modern Web Stack**: Hono + FastAPI + TypeScript + Python

## 🛠️ Development Setup

### Prerequisites
- Node.js 18+ and npm
- Python 3.8+ with pip
- Git

### Quick Start
```bash
# Clone the repository
git clone https://github.com/Vivekkmr91/ai-agentic-rag-chat.git
cd ai-agentic-rag-chat

# Install dependencies
npm install
pip install -r python_rag/requirements.txt

# Create sample database
python3 -c "exec(open('python_rag/utils/sample_database.py').read())"

# Build and start services
npm run build
pm2 start ecosystem.config.cjs

# Access the application
open http://localhost:3000
```

## 📁 Project Structure

```
├── src/                     # Hono frontend (TypeScript)
├── python_rag/             # Python RAG system
│   ├── agents/             # AI agents (Query, Schema, SQL, Text, Synthesis)
│   ├── core/               # Hybrid search & schema extraction
│   ├── api/                # FastAPI server endpoints
│   └── config/             # Settings and configuration
├── public/static/          # Frontend assets (JS, CSS)
└── ecosystem.config.cjs    # PM2 process management
```

## 🎯 Contributing Areas

### High Priority
- **Enhanced SQL Generation**: Improve natural language to SQL conversion
- **Advanced Search**: Better semantic understanding and query expansion
- **Performance Optimization**: Caching, indexing, and response time improvements
- **Database Connectors**: Add support for more database types

### Medium Priority  
- **WebSocket Support**: Real-time bidirectional communication
- **Authentication**: User management and query history
- **Visualization**: Charts and graphs for data insights
- **Export Features**: Download results in multiple formats

### Low Priority
- **Custom Agents**: Plugin system for domain-specific agents
- **Advanced Analytics**: Query pattern analysis and insights
- **Integration APIs**: Connect with BI tools and data platforms

## 🔧 Development Guidelines

### Code Style
- **TypeScript**: Use strict mode, proper typing, ESLint configuration
- **Python**: Follow PEP 8, use type hints, Black formatting
- **Documentation**: Add docstrings and inline comments for complex logic
- **Testing**: Write unit tests for new features

### Git Workflow
1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes with clear, descriptive commits
4. Add tests for new functionality
5. Update documentation as needed
6. Submit a pull request with detailed description

### Commit Messages
Use conventional commit format:
```
feat: add vector similarity search optimization
fix: resolve SQL injection vulnerability in query processor
docs: update API documentation with new endpoints
test: add unit tests for schema extraction
```

## 🧪 Testing

### Backend Testing
```bash
cd python_rag
python -m pytest tests/ -v
```

### Frontend Testing
```bash
npm test
npm run test:e2e
```

### Integration Testing
```bash
# Start services
pm2 start ecosystem.config.cjs

# Run API tests
curl -X POST http://localhost:3000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me all tables"}'
```

## 📋 Pull Request Process

1. **Update Documentation**: Ensure README and code comments reflect changes
2. **Add Tests**: Include unit/integration tests for new features
3. **Performance Check**: Verify no degradation in response times
4. **Security Review**: Check for potential vulnerabilities
5. **Backward Compatibility**: Ensure existing APIs remain functional

### PR Template
```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist
- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

## 🐛 Bug Reports

Use GitHub Issues with the bug report template:
- **Environment**: OS, Node.js version, Python version
- **Steps to Reproduce**: Clear, numbered steps
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Screenshots/Logs**: If applicable

## 💡 Feature Requests

Use GitHub Issues with the feature request template:
- **Problem Statement**: What problem does this solve?
- **Proposed Solution**: How should it work?
- **Alternatives Considered**: Other approaches considered
- **Additional Context**: Any other relevant information

## 📞 Getting Help

- **GitHub Discussions**: For questions and community support
- **GitHub Issues**: For bugs and feature requests
- **Documentation**: Check README and code comments first

## 🏆 Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes for significant contributions
- GitHub contributor graphs and statistics

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make AI Agentic RAG Chat better! 🚀