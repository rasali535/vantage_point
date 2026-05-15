#!/bin/bash
# 🌌 Vantage-Point 2.0: Vultr Deployment Automator
# Tested on Ubuntu 22.04 / 24.04

set -e

echo "🚀 Starting Vantage-Point Provisioning on Vultr..."

# 1. Update & Install Dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# 2. Install Docker
echo "📦 Installing Docker..."
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 3. Clone Repository
if [ ! -d "vantage_point" ]; then
    echo "📂 Cloning Vantage-Point..."
    git clone https://github.com/rasali535/vantage_point.git
    cd vantage_point
else
    cd vantage_point
    git pull origin main
fi

# 4. Environment Setup
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env <<EOF
# Vantage-Point Environment
GEMINI_API_KEY=
FEATHERLESS_API_KEY=
KRAKEN_API_KEY=
KRAKEN_API_SECRET=
TRADING_PAIR=AAPLx/USD
EOF
    echo "⚠️  ACTION REQUIRED: Edit the .env file with your API keys before running 'docker-compose up'."
fi

echo "✅ Provisioning Complete!"
echo "👉 Run: cd vantage_point && nano .env && sudo docker compose up --build -d"
