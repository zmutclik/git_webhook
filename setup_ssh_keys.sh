#!/bin/bash
# Setup SSH Deploy Keys untuk Git Webhook
# Supports GitHub, GitLab, Gitea

set -e

SECRETS_DIR="./secrets"
SSH_CONFIG_DIR="/root/.ssh"

echo "🔑 SSH Deploy Keys Setup"
echo "========================"

# Create directories
mkdir -p "$SECRETS_DIR" "$SSH_CONFIG_DIR"
chmod 700 "$SECRETS_DIR" "$SSH_CONFIG_DIR"


# Function to generate SSH key
generate_ssh_key() {
    local service="$1"
    local email="$2"
    local key_file="$SECRETS_DIR/${service}deploy_key"
    
    if [ -f "$key_file" ]; then
        echo "⚠️  SSH key untuk $service sudah ada: $key_file"
        return 0
    fi
    
    echo "🔧 Generating SSH key untuk $service..."
    ssh-keygen -t rsa -b 4096 -C "$email" -f "$key_file" -N ""
    chmod 600 "$key_file"
    chmod 644 "$key_file.pub"
    
    echo "✅ SSH key generated: $key_file"
    echo "📋 Public key untuk $service:"
    echo "=================================="
    cat "$key_file.pub"
    echo "=================================="
    echo ""
}

# Function to setup SSH config
setup_ssh_config() {
    local config_file="$SSH_CONFIG_DIR/config"
    
    echo "📝 Creating SSH config..."
    
    cat > "$config_file" << 'EOF'
# GitHub
Host github.com
    HostName github.com
    User git
    IdentityFile /app/secrets/deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# GitLab.com
Host gitlab.com
    HostName gitlab.com
    User git
    IdentityFile /app/secrets/deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Gitea RSDarsono ID
Host git.rsdarsono.id
    HostName git.rsdarsono.id
    User git
    IdentityFile /app/secrets/deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null

# Generic deploy key (fallback)
Host *
    IdentityFile /app/secrets/deploy_key
    IdentitiesOnly yes
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
EOF
    
    chmod 600 "$config_file"
    echo "✅ SSH config created: $config_file"
}

# Function to test SSH connection
test_ssh_connection() {
    local host="$1"
    local key_file="$2"
    
    echo "🔍 Testing SSH connection to $host..."
    
    if [ ! -f "$key_file" ]; then
        echo "❌ Key file not found: $key_file"
        return 1
    fi
    
    # Test connection
    ssh -i "$key_file" -T git@"$host" -o StrictHostKeyChecking=no -o ConnectTimeout=10 2>&1 | grep -q "successfully authenticated" && {
        echo "✅ SSH connection to $host: SUCCESS"
        return 0
    } || {
        echo "⚠️  SSH connection to $host: Check if public key is added to the service"
        return 1
    }
}

# Function to show public keys
show_public_keys() {
    echo "📋 Public Keys untuk Copy ke Git Services:"
    echo "=========================================="
    
    for key_file in "$SECRETS_DIR"/*.pub; do
        if [ -f "$key_file" ]; then
            service=$(basename "$key_file" | sed 's/_deploy_key.pub//')
            echo ""
            echo "🔑 $service:"
            echo "---"
            cat "$key_file"
            echo "---"
        fi
    done
    
    echo ""
    echo "📖 Instructions:"
    echo "1. Copy public key yang sesuai"
    echo "2. Add sebagai Deploy Key di Git service:"
    echo "   - GitHub: Settings → Deploy keys → Add deploy key"
    echo "   - GitLab: Settings → Repository → Deploy keys → Add key" 
    echo "   - Gitea: Settings → Deploy keys → Add deploy key"
    echo "3. Pastikan 'Allow write access' dicentang jika perlu push"
}

# Function to update docker-compose for SSH
update_docker_compose() {
    echo "🐳 Updating docker-compose.yml untuk SSH support..."
    
    # Backup original
    if [ -f "docker-compose.yml" ]; then
        cp docker-compose.yml docker-compose.yml.backup
    fi
    
    # Add SSH volumes jika belum ada
    if ! grep -q "ssh-config" docker-compose.yml 2>/dev/null; then
        echo "Adding SSH volumes to docker-compose.yml..."
        # Note: Manual edit required untuk menambahkan:
        # volumes:
        #   - ./ssh-config:/root/.ssh:ro
        echo "⚠️  Please manually add this to webhook-server volumes:"
        echo "      - ./ssh-config:/root/.ssh:ro"
    fi
}

# Function to update config
update_webhook_config() {
    echo "⚙️  Updating webhook configuration..."
    
    # Update config/webhook.env
    # if [ ! -f "config/webhook.env" ]; then
    #     mkdir -p config
    # fi
    
    # Add SSH config jika belum ada
    if ! grep -q "GIT_HOST" config/webhook.env 2>/dev/null; then
        cat >> config/webhook.env << 'EOF'

# SSH Git Configuration
GIT_HOST=github.com
GIT_USER_NAME=Webhook Bot
GIT_USER_EMAIL=webhook@your-domain.com
EOF
        echo "✅ SSH config added to config/webhook.env"
    fi
}

# Main menu
case "${1:-menu}" in
    "generate")
        echo "Generate SSH keys untuk Git services..."
        echo ""
        
        read -p "Email untuk SSH keys: " email
        if [ -z "$email" ]; then
            email="webhook@$(hostname)"
        fi
        
        echo "Generating keys dengan email: $email"
        
        # Generate keys for common services
        # generate_ssh_key "github_" "$email"
        # generate_ssh_key "gitlab_" "$email" 
        generate_ssh_key "" "$email"  # Generic key
        
        setup_ssh_config
        # update_webhook_config
        show_public_keys
        ;;
        
    "test")
        echo "Testing SSH connections..."
        test_ssh_connection "github.com" "$SECRETS_DIR/github_deploy_key"
        test_ssh_connection "gitlab.com" "$SECRETS_DIR/gitlab_deploy_key"
        ;;
        
    "show")
        show_public_keys
        ;;
        
    "clean")
        echo "🧹 Cleaning SSH keys..."
        read -p "Are you sure? This will delete all SSH keys (y/N): " confirm
        if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
            rm -f "$SECRETS_DIR"/*_deploy_key*
            rm -f "$SSH_CONFIG_DIR/config"
            echo "✅ SSH keys cleaned"
        fi
        ;;
        
    "help"|"--help"|"-h")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  generate  - Generate SSH deploy keys"
        echo "  test      - Test SSH connections"
        echo "  show      - Show public keys"
        echo "  clean     - Remove all SSH keys"
        echo "  help      - Show this help"
        echo ""
        ;;
        
    *)
        echo "Select an option:"
        echo "1) Generate SSH keys"
        echo "2) Test SSH connections" 
        echo "3) Show public keys"
        echo "4) Clean SSH keys"
        echo "5) Help"
        echo ""
        read -p "Choice (1-5): " choice
        
        case $choice in
            1) exec "$0" generate ;;
            2) exec "$0" test ;;
            3) exec "$0" show ;;
            4) exec "$0" clean ;;
            5) exec "$0" help ;;
            *) echo "Invalid choice" ;;
        esac
        ;;
esac