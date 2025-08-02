#!/bin/bash
# Test Commands untuk Git Webhook Server
# Ganti localhost:8000 dengan URL server Anda

# ====================================
# 1. BASIC TESTS (tanpa signature)
# ====================================

echo "=== Testing Basic Endpoints ==="

# Test status endpoint
echo "1. Testing status endpoint..."
curl -X GET http://localhost:8000/status \
  -H "Content-Type: application/json" | jq

echo -e "\n"

# Test health endpoint
echo "2. Testing health endpoint..."
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json" | jq

echo -e "\n"

# Test manual pull
echo "3. Testing manual pull..."
curl -X POST http://localhost:8000/manual-pull \
  -H "Content-Type: application/json" | jq

echo -e "\n"

# ====================================
# 2. GITHUB WEBHOOK TESTS
# ====================================

echo "=== Testing GitHub Webhooks ==="

# GitHub Ping Event
echo "4. Testing GitHub ping..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: ping" \
  -H "X-GitHub-Delivery: 12345-67890" \
  -d '{
    "zen": "Anything added dilutes everything else.",
    "hook_id": 12345,
    "hook": {
      "type": "Repository",
      "id": 12345,
      "name": "web",
      "active": true,
      "events": ["push"],
      "config": {
        "content_type": "json",
        "insecure_ssl": "0",
        "url": "http://localhost:8000/webhook"
      }
    },
    "repository": {
      "id": 123456,
      "name": "test-repo",
      "full_name": "username/test-repo"
    }
  }' | jq

echo -e "\n"

# GitHub Push Event (main branch)
echo "5. Testing GitHub push to main..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: 12345-67891" \
  -d '{
    "ref": "refs/heads/main",
    "before": "abc123def456",
    "after": "def456ghi789",
    "repository": {
      "id": 123456,
      "name": "test-repo",
      "full_name": "username/test-repo",
      "clone_url": "https://github.com/username/test-repo.git"
    },
    "pusher": {
      "name": "developer",
      "email": "dev@example.com"
    },
    "commits": [
      {
        "id": "def456ghi789",
        "tree_id": "ghi789jkl012",
        "message": "Update README.md",
        "timestamp": "2024-01-15T10:30:00Z",
        "author": {
          "name": "Developer",
          "email": "dev@example.com"
        },
        "added": ["README.md"],
        "removed": [],
        "modified": []
      }
    ]
  }' | jq

echo -e "\n"

# GitHub Push Event (different branch - should be ignored)
echo "6. Testing GitHub push to development (should be ignored)..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: 12345-67892" \
  -d '{
    "ref": "refs/heads/development",
    "before": "abc123def456",
    "after": "def456ghi789",
    "repository": {
      "id": 123456,
      "name": "test-repo",
      "full_name": "username/test-repo"
    },
    "commits": [
      {
        "id": "def456ghi789",
        "message": "Development changes"
      }
    ]
  }' | jq

echo -e "\n"

# ====================================
# 3. GITLAB WEBHOOK TESTS
# ====================================

echo "=== Testing GitLab Webhooks ==="

# GitLab Push Event
echo "7. Testing GitLab push..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Push Hook" \
  -H "X-Gitlab-Token: your-gitlab-token" \
  -d '{
    "object_kind": "push",
    "event_name": "push",
    "before": "abc123def456",
    "after": "def456ghi789",
    "ref": "refs/heads/main",
    "checkout_sha": "def456ghi789",
    "user_id": 123,
    "user_name": "Developer",
    "user_username": "dev",
    "user_email": "dev@example.com",
    "project_id": 456,
    "project": {
      "id": 456,
      "name": "test-project",
      "description": "Test project",
      "web_url": "https://gitlab.com/username/test-project",
      "git_ssh_url": "git@gitlab.com:username/test-project.git",
      "git_http_url": "https://gitlab.com/username/test-project.git",
      "namespace": "username",
      "visibility_level": 20,
      "path_with_namespace": "username/test-project",
      "default_branch": "main"
    },
    "commits": [
      {
        "id": "def456ghi789",
        "message": "Update application",
        "timestamp": "2024-01-15T10:30:00+00:00",
        "url": "https://gitlab.com/username/test-project/-/commit/def456ghi789",
        "author": {
          "name": "Developer",
          "email": "dev@example.com"
        },
        "added": ["new-file.txt"],
        "modified": ["existing-file.txt"],
        "removed": []
      }
    ],
    "total_commits_count": 1
  }' | jq

echo -e "\n"

# ====================================
# 4. GITEA WEBHOOK TESTS
# ====================================

echo "=== Testing Gitea Webhooks ==="

# Gitea Push Event
echo "8. Testing Gitea push..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-Gitea-Event: push" \
  -H "X-Gitea-Delivery: 12345-67890" \
  -d '{
    "ref": "refs/heads/main",
    "before": "abc123def456",
    "after": "def456ghi789",
    "compare_url": "https://gitea.example.com/username/test-repo/compare/abc123def456...def456ghi789",
    "commits": [
      {
        "id": "def456ghi789",
        "message": "Update files",
        "url": "https://gitea.example.com/username/test-repo/commit/def456ghi789",
        "author": {
          "name": "Developer",
          "email": "dev@example.com",
          "username": "dev"
        },
        "committer": {
          "name": "Developer",
          "email": "dev@example.com",
          "username": "dev"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "added": ["new-feature.js"],
        "removed": [],
        "modified": ["README.md"]
      }
    ],
    "repository": {
      "id": 789,
      "owner": {
        "id": 123,
        "login": "username",
        "full_name": "User Name",
        "email": "user@example.com",
        "avatar_url": "https://gitea.example.com/avatars/123",
        "username": "username"
      },
      "name": "test-repo",
      "full_name": "username/test-repo",
      "description": "Test repository",
      "empty": false,
      "private": false,
      "fork": false,
      "html_url": "https://gitea.example.com/username/test-repo",
      "ssh_url": "git@gitea.example.com:username/test-repo.git",
      "clone_url": "https://gitea.example.com/username/test-repo.git",
      "default_branch": "main"
    },
    "pusher": {
      "id": 123,
      "login": "username",
      "full_name": "User Name",
      "email": "user@example.com",
      "avatar_url": "https://gitea.example.com/avatars/123",
      "username": "username"
    },
    "sender": {
      "id": 123,
      "login": "username",
      "full_name": "User Name",
      "email": "user@example.com",
      "avatar_url": "https://gitea.example.com/avatars/123",
      "username": "username"
    }
  }' | jq

echo -e "\n"

# ====================================
# 5. SIGNATURE VERIFICATION TESTS
# ====================================

echo "=== Testing Signature Verification ==="

# Function untuk generate GitHub signature
generate_github_signature() {
    local secret="$1"
    local payload="$2"
    echo -n "$payload" | openssl dgst -sha256 -hmac "$secret" | sed 's/^.*= /sha256=/'
}

# Test dengan signature yang benar (GitHub)
echo "9. Testing GitHub webhook dengan signature..."
SECRET="your-secret-token-here"
PAYLOAD='{"ref":"refs/heads/main","commits":[{"id":"test123","message":"Test commit"}]}'
SIGNATURE=$(generate_github_signature "$SECRET" "$PAYLOAD")

curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: $SIGNATURE" \
  -d "$PAYLOAD" | jq

echo -e "\n"

# ====================================
# 6. ERROR TESTS
# ====================================

echo "=== Testing Error Cases ==="

# Test dengan payload kosong
echo "10. Testing empty payload..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '' | jq

echo -e "\n"

# Test dengan JSON invalid
echo "11. Testing invalid JSON..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -d '{invalid json}' | jq

echo -e "\n"

# Test dengan signature salah
echo "12. Testing wrong signature..."
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=wrongsignature" \
  -d '{"ref":"refs/heads/main","commits":[]}' | jq

echo -e "\n"

# ====================================
# 7. STRESS TEST (OPTIONAL)
# ====================================

echo "=== Stress Test (Optional) ==="
echo "13. Sending multiple requests..."

for i in {1..5}; do
    echo "Request $i..."
    curl -s -X POST http://localhost:8000/webhook \
      -H "Content-Type: application/json" \
      -H "X-GitHub-Event: push" \
      -d "{\"ref\":\"refs/heads/main\",\"commits\":[{\"id\":\"test$i\",\"message\":\"Test commit $i\"}]}" > /dev/null
done

echo "Stress test completed!"

echo -e "\n=== All Tests Completed ==="