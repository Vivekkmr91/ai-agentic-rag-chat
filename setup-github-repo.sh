#!/bin/bash

# GitHub Repository Setup Script for AI Agentic RAG Chat
# This script will create the repository and push all code after GitHub authorization

set -e

echo "🚀 Setting up GitHub repository: ai-agentic-rag-chat"
echo "=================================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Repository details
REPO_NAME="ai-agentic-rag-chat"
REPO_DESCRIPTION="AI-powered database chat application with multi-agent RAG system, hybrid search, and natural language query processing"
TOPICS="artificial-intelligence,rag,multi-agent-system,database-chat,nlp,fastapi,hono,typescript,python"

echo -e "${BLUE}Checking GitHub CLI authentication...${NC}"
if ! gh auth status >/dev/null 2>&1; then
    echo -e "${RED}❌ GitHub CLI not authenticated. Please run 'gh auth login' first${NC}"
    exit 1
fi

echo -e "${GREEN}✅ GitHub CLI authenticated${NC}"

# Get GitHub username
USERNAME=$(gh api user --jq '.login')
echo -e "${BLUE}GitHub username: ${USERNAME}${NC}"

echo -e "${BLUE}Creating public repository: ${REPO_NAME}...${NC}"
gh repo create "${REPO_NAME}" \
    --public \
    --description "${REPO_DESCRIPTION}" \
    --clone=false

echo -e "${GREEN}✅ Repository created successfully${NC}"

echo -e "${BLUE}Adding repository topics...${NC}"
gh repo edit "${USERNAME}/${REPO_NAME}" --add-topic "${TOPICS}"

echo -e "${BLUE}Enabling repository features...${NC}"
gh repo edit "${USERNAME}/${REPO_NAME}" \
    --enable-issues \
    --enable-wiki \
    --enable-discussions

echo -e "${BLUE}Setting up git remote...${NC}"
git remote remove origin 2>/dev/null || true
git remote add origin "https://github.com/${USERNAME}/${REPO_NAME}.git"

echo -e "${BLUE}Creating final commit with repository info...${NC}"
# Update README with correct GitHub URL
sed -i "s|https://github.com/USERNAME/ai-agentic-rag-chat|https://github.com/${USERNAME}/${REPO_NAME}|g" README.md
sed -i "s|USERNAME|${USERNAME}|g" CONTRIBUTING.md

# Add and commit the updates
git add README.md CONTRIBUTING.md LICENSE .github-setup.md setup-github-repo.sh
git commit -m "Add GitHub repository setup and documentation

- Added MIT license for open source collaboration
- Created comprehensive CONTRIBUTING.md with development guidelines  
- Added repository setup script for automated deployment
- Updated README with correct GitHub URLs and repository information
- Prepared for public release on GitHub"

echo -e "${BLUE}Pushing to GitHub repository...${NC}"
git push -u origin main

echo -e "${GREEN}🎉 SUCCESS! Repository setup complete${NC}"
echo ""
echo -e "${BLUE}Repository URL:${NC} https://github.com/${USERNAME}/${REPO_NAME}"
echo -e "${BLUE}Clone URL:${NC} git clone https://github.com/${USERNAME}/${REPO_NAME}.git"
echo ""
echo -e "${GREEN}✅ Your AI Agentic RAG Chat application is now live on GitHub!${NC}"
echo ""
echo "Next steps:"
echo "1. 🌟 Star your repository: gh repo view --web"
echo "2. 📝 Create your first release: gh release create v1.0.0"
echo "3. 🔧 Set up GitHub Actions for CI/CD"
echo "4. 📢 Share with the community!"
echo ""
echo "Repository features enabled:"
echo "• 🐛 Issues for bug reports and feature requests"
echo "• 💬 Discussions for community Q&A"
echo "• 📚 Wiki for extended documentation"
echo "• 🏷️ Topics for discoverability"
echo "• 📄 MIT License for open collaboration"