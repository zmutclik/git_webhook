#!/bin/bash
# Quick test script untuk webhook
# Usage: ./quick_test.sh [webhook_url] [secret_token]

# Default values
WEBHOOK_URL=${1:-"http://localhost:8000"}
SECRET_TOKEN=${2:-"your-secret-token-here"}

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Quick Webhook Test${NC}"
echo "URL: $WEBHOOK_URL"
echo "Token: ${SECRET_TOKEN:0:4}****"
echo "================================"

# Function untuk test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local description=$3
    local data=$4
    local headers=$5
    
    echo -n "Testing $description... "
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "%{http_code}" -o /tmp/webhook_response "$WEBHOOK_URL$endpoint" $headers)
    else
        response=$(curl -s -w "%{http_code}" -o /tmp/webhook_response -X "$method" "$WEBHOOK_URL$endpoint" $headers -d "$data")
    fi
    
    status_code=${response: -3}
    
    if [ "$status_code" -eq 200 ]; then
        echo -e "${GREEN}✓ ($status_code)${NC}"
    else
        echo -e "${RED}✗ ($status_code)${NC}"
        if [ -f /tmp/webhook_response ]; then
            echo "   Response: $(cat /tmp/webhook_response)"
        fi
    fi
    
    return $status_code
}

# 1. Test basic endpoints
echo -e "\n${YELLOW}📊 Basic Endpoints${NC}"
test_endpoint "GET" "/status" "Status" "" "-H 'Content-Type: application/json'"
test_endpoint "GET" "/health" "Health" "" "-H 'Content-Type: application/json'"
test_endpoint "POST" "/manual-pull" "Manual Pull" "" "-H 'Content-Type: application/json'"

# 2. Test GitHub webhook
echo -e "\n${YELLOW}🔵 GitHub Webhook${NC}"

# GitHub ping
github_ping='{
  "zen": "Responsive is better than fast.",
  "hook_id": 12345,
  "repository": {
    "name": "test-repo",
    "full_name": "user/test-repo"
  }
}'

test_endpoint "POST" "/webhook" "GitHub Ping" "$github_ping" "-H 'Content-Type: application/json' -H 'X-GitHub-Event: ping'"

# GitHub push
github_push='{
  "ref": "refs/heads/main",
  "commits": [
    {
      "id": "abc123",
      "message": "Test commit from curl",
      "author": {
        "name": "Tester",
        "email": "test@example.com"
      }
    }
  ],
  "repository": {
    "name": "test-repo",
    "full_name": "user/test-repo"
  }
}'

test_endpoint "POST" "/webhook" "GitHub Push" "$github_push" "-H 'Content-Type: application/json' -H 'X-GitHub-Event: push'"

# 3. Test GitLab webhook
echo -e "\n${YELLOW}🟠 GitLab Webhook${NC}"

gitlab_push='{
  "object_kind": "push",
  "ref": "refs/heads/main",
  "commits": [
    {
      "id": "def456",
      "message": "Test commit from GitLab",
      "author": {
        "name": "Tester",
        "email": "test@example.com"
      }
    }
  ],
  "project": {
    "name": "test-project",
    "path_with_namespace": "user/test-project"
  }
}'

test_endpoint "POST" "/webhook" "GitLab Push" "$gitlab_push" "-H 'Content-Type: application/json' -H 'X-Gitlab-Event: Push Hook'"