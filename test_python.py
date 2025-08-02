#!/usr/bin/env python3
"""
Script untuk testing webhook dengan signature verification
Mendukung GitHub, GitLab, dan Gitea
"""

import hmac
import hashlib
import json
import requests
import sys
from datetime import datetime

# Konfigurasi
WEBHOOK_URL = "http://localhost:8000/webhook"
SECRET_TOKEN = "your-secret-token-here"  # Harus sama dengan config server

def generate_github_signature(secret, payload):
    """Generate signature untuk GitHub webhook"""
    mac = hmac.new(secret.encode(), payload.encode(), hashlib.sha256)
    return f"sha256={mac.hexdigest()}"

def generate_gitlab_signature(secret, payload):
    """Generate signature untuk GitLab webhook (X-Gitlab-Token)"""
    return secret

def generate_gitea_signature(secret, payload):
    """Generate signature untuk Gitea webhook"""
    mac = hmac.new(secret.encode(), payload.encode(), hashlib.sha256)
    return mac.hexdigest()

def test_github_webhook():
    """Test GitHub webhook dengan signature"""
    print("🔵 Testing GitHub Webhook...")
    
    payload = {
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
                "message": "Update README.md via webhook test",
                "timestamp": datetime.now().isoformat() + "Z",
                "author": {
                    "name": "Developer",
                    "email": "dev@example.com"
                },
                "added": ["README.md"],
                "removed": [],
                "modified": []
            }
        ]
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    signature = generate_github_signature(SECRET_TOKEN, payload_str)
    
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "push",
        "X-GitHub-Delivery": f"github-{datetime.now().timestamp()}",
        "X-Hub-Signature-256": signature,
        "User-Agent": "GitHub-Hookshot/test"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data=payload_str)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_gitlab_webhook():
    """Test GitLab webhook dengan token"""
    print("🟠 Testing GitLab Webhook...")
    
    payload = {
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
            "description": "Test project for webhook",
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
                "message": "Update application via GitLab webhook",
                "timestamp": datetime.now().isoformat() + "+00:00",
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
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    
    headers = {
        "Content-Type": "application/json",
        "X-Gitlab-Event": "Push Hook",
        "X-Gitlab-Token": SECRET_TOKEN,
        "User-Agent": "GitLab/test"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data=payload_str)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_gitea_webhook():
    """Test Gitea webhook"""
    print("🟢 Testing Gitea Webhook...")
    
    payload = {
        "ref": "refs/heads/main",
        "before": "abc123def456",
        "after": "def456ghi789",
        "compare_url": "https://gitea.example.com/username/test-repo/compare/abc123def456...def456ghi789",
        "commits": [
            {
                "id": "def456ghi789",
                "message": "Update files via Gitea webhook",
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
                "timestamp": datetime.now().isoformat() + "Z",
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
            "description": "Test repository for webhook",
            "empty": False,
            "private": False,
            "fork": False,
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
    }
    
    payload_str = json.dumps(payload, separators=(',', ':'))
    
    headers = {
        "Content-Type": "application/json",
        "X-Gitea-Event": "push",
        "X-Gitea-Delivery": f"gitea-{datetime.now().timestamp()}",
        "User-Agent": "Gitea/test"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data=payload_str)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   Error: {e}")
        return False

def test_ping_events():
    """Test ping events dari berbagai services"""
    print("🔔 Testing Ping Events...")
    
    # GitHub ping
    print("   GitHub ping...")
    github_ping = {
        "zen": "Anything added dilutes everything else.",
        "hook_id": 12345,
        "hook": {
            "type": "Repository",
            "id": 12345,
            "name": "web",
            "active": True,
            "events": ["push"],
            "config": {
                "content_type": "json",
                "insecure_ssl": "0",
                "url": WEBHOOK_URL
            }
        },
        "repository": {
            "id": 123456,
            "name": "test-repo",
            "full_name": "username/test-repo"
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "ping",
        "X-GitHub-Delivery": f"ping-{datetime.now().timestamp()}"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=github_ping)
        print(f"     Status: {response.status_code}")
    except Exception as e:
        print(f"     Error: {e}")

def test_error_cases():
    """Test berbagai error cases"""
    print("❌ Testing Error Cases...")
    
    # Test signature salah
    print("   Testing wrong signature...")
    payload = {"ref": "refs/heads/main", "commits": []}
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "push",
        "X-Hub-Signature-256": "sha256=wrongsignature"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload)
        print(f"     Status: {response.status_code} (should be 401)")
    except Exception as e:
        print(f"     Error: {e}")
    
    # Test payload kosong
    print("   Testing empty payload...")
    headers = {
        "Content-Type": "application/json",
        "X-GitHub-Event": "push"
    }
    
    try:
        response = requests.post(WEBHOOK_URL, headers=headers, data="")
        print(f"     Status: {response.status_code} (should be 400)")
    except Exception as e:
        print(f"     Error: {e}")

def main():
    """Main function"""
    print("🚀 Starting Webhook Tests...")
    print(f"Target URL: {WEBHOOK_URL}")
    print(f"Secret Token: {'***' + SECRET_TOKEN[-4:] if len(SECRET_TOKEN) > 4 else '***'}")
    print("=" * 50)
    
    # Test basic endpoints
    print("📊 Testing Basic Endpoints...")
    try:
        response = requests.get(WEBHOOK_URL.replace('/webhook', '/status'))
        print(f"   Status endpoint: {response.status_code}")
    except Exception as e:
        print(f"   Status endpoint error: {e}")
    
    print()
    
    # Test webhook events
    success_count = 0
    total_tests = 3
    
    if test_github_webhook():
        success_count += 1
    print()
    
    if test_gitlab_webhook():
        success_count += 1
    print()
    
    if test_gitea_webhook():
        success_count += 1
    print()
    
    # Test ping events
    test_ping_events()
    print()
    
    # Test error cases
    test_error_cases()
    print()
    
    # Summary
    print("=" * 50)
    print(f"✅ Tests Completed: {success_count}/{total_tests} successful")
    
    if success_count == total_tests:
        print("🎉 All webhook tests passed!")
        sys.exit(0)
    else:
        print("⚠️  Some tests failed. Check your webhook server configuration.")
        sys.exit(1)

if __name__ == "__main__":
    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print("❌ Error: requests library not installed")
        print("Install with: pip install requests")
        sys.exit(1)
    
    # Allow custom URL and secret from command line
    if len(sys.argv) > 1:
        WEBHOOK_URL = sys.argv[1]
    
    if len(sys.argv) > 2:
        SECRET_TOKEN = sys.argv[2]
    
    main()