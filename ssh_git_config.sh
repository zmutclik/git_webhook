# 1. SSH Config Method (Recommended)
# Buat file ~/.ssh/config di container

mkdir -p ~/.ssh
chmod 700 ~/.ssh

cat > ~/.ssh/config << 'EOF'
Host github.com
    HostName github.com
    User git
    IdentityFile /app/secrets/github_deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no

Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile /app/secrets/gitlab_deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no

Host git.rsdarsono.id
    HostName git.rsdarsono.id
    User git
    IdentityFile /app/secrets/gitea_deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no
EOF

chmod 600 ~/.ssh/config

# Git pull command (normal)
git pull origin main

# ===================================

# 2. Direct SSH Command Method
# Menggunakan GIT_SSH_COMMAND environment variable

export GIT_SSH_COMMAND="ssh -i /app/secrets/deploy_key -o StrictHostKeyChecking=no"
git pull origin main

# ===================================

# 3. SSH Agent Method
# Start SSH agent dan add key

eval "$(ssh-agent -s)"
ssh-add /app/secrets/deploy_key
git pull origin main

# ===================================

# 4. One-liner dengan ssh-agent
ssh-agent bash -c 'ssh-add /app/secrets/deploy_key; git pull origin main'

# ===================================

# 5. Custom SSH wrapper script
cat > /app/scripts/git-ssh-wrapper.sh << 'EOF'
#!/bin/bash
ssh -i /app/secrets/deploy_key -o StrictHostKeyChecking=no "$@"
EOF

chmod +x /app/scripts/git-ssh-wrapper.sh
export GIT_SSH="/app/scripts/git-ssh-wrapper.sh"
git pull origin main

# ===================================

# 6. Function untuk berbagai Git services
git_pull_with_key() {
    local key_file="$1"
    local git_host="$2"
    local repo_url="$3"
    
    if [ ! -f "$key_file" ]; then
        echo "Error: Key file $key_file not found"
        return 1
    fi
    
    # Set proper permissions
    chmod 600 "$key_file"
    
    # Configure SSH
    export GIT_SSH_COMMAND="ssh -i $key_file -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
    
    # Pull
    git pull origin main
}

# Usage examples:
# git_pull_with_key "/app/secrets/github_key" "github.com" "git@github.com:user/repo.git"
# git_pull_with_key "/app/secrets/gitlab_key" "gitlab.com" "git@gitlab.com:user/repo.git"

# ===================================

# 7. Advanced: Multiple keys untuk different repos
setup_git_ssh_keys() {
    local ssh_dir="$HOME/.ssh"
    mkdir -p "$ssh_dir"
    chmod 700 "$ssh_dir"
    
    # Copy keys dari secrets
    cp /app/secrets/github_deploy_key "$ssh_dir/"
    cp /app/secrets/gitlab_deploy_key "$ssh_dir/"
    chmod 600 "$ssh_dir"/*_deploy_key
    
    # Create SSH config
    cat > "$ssh_dir/config" << 'EOF'
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile ~/.ssh/github_deploy_key
    IdentitiesOnly yes

# GitLab
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile ~/.ssh/gitlab_deploy_key
    IdentitiesOnly yes
    
# Custom GitLab instance
Host gitlab.mycompany.com
    HostName gitlab.mycompany.com
    User git
    IdentityFile ~/.ssh/gitlab_deploy_key
    Port 2222
    IdentitiesOnly yes
EOF
    
    chmod 600 "$ssh_dir/config"
    
    # Add known hosts
    ssh-keyscan github.com >> "$ssh_dir/known_hosts" 2>/dev/null
    ssh-keyscan gitlab.com >> "$ssh_dir/known_hosts" 2>/dev/null
    chmod 600 "$ssh_dir/known_hosts"
}

# ===================================

# 8. Docker Compose integration
# Tambahkan volume untuk SSH keys di docker-compose.yml:

# volumes:
#   - ./ssh-keys:/app/secrets:ro
#   - ./ssh-config:/root/.ssh:rw

# ===================================

# 9. Generate Deploy Key (untuk setup)
generate_deploy_key() {
    local key_name="$1"
    local email="$2"
    
    if [ -z "$key_name" ] || [ -z "$email" ]; then
        echo "Usage: generate_deploy_key <key_name> <email>"
        return 1
    fi
    
    ssh-keygen -t rsa -b 4096 -C "$email" -f "/app/secrets/$key_name" -N ""
    echo "Deploy key generated: /app/secrets/$key_name"
    echo "Public key:"
    cat "/app/secrets/$key_name.pub"
}

# Usage:
# generate_deploy_key "github_deploy_key" "webhook@mycompany.com"

# ===================================

# 10. Test SSH connection
test_ssh_connection() {
    local host="$1"
    local key_file="$2"
    
    echo "Testing SSH connection to $host..."
    ssh -i "$key_file" -T git@"$host" -o StrictHostKeyChecking=no
}

# Usage:
# test_ssh_connection "github.com" "/app/secrets/github_deploy_key"
# test_ssh_connection "gitlab.com" "/app/secrets/gitlab_deploy_key"