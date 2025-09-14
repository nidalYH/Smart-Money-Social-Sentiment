#!/bin/bash

# Smart Money Social Sentiment Analyzer Setup Script

set -e

echo "🚀 Setting up Smart Money Social Sentiment Analyzer..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    print_status "Creating .env file from template..."
    cp env.example .env
    print_warning "Please edit .env file with your API keys before starting the application."
    print_warning "Required API keys:"
    echo "  - ETHERSCAN_API_KEY (get from https://etherscan.io/apis)"
    echo "  - TWITTER_BEARER_TOKEN (get from https://developer.twitter.com/)"
    echo "  - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo "  - SECRET_KEY (generate a random string)"
    echo ""
    read -p "Press Enter to continue after updating .env file..."
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p logs
mkdir -p nginx/ssl
mkdir -p data/postgres
mkdir -p data/redis

# Set permissions
chmod 755 logs
chmod 755 nginx/ssl

# Build and start services
print_status "Building and starting services..."
docker-compose build

print_status "Starting database services..."
docker-compose up -d postgres redis

# Wait for database to be ready
print_status "Waiting for database to be ready..."
sleep 10

# Check database connection
print_status "Checking database connection..."
until docker-compose exec postgres pg_isready -U smartmoney -d smartmoney; do
    print_status "Waiting for PostgreSQL..."
    sleep 2
done

# Start the main application
print_status "Starting Smart Money application..."
docker-compose up -d smartmoney-app

# Wait for application to be ready
print_status "Waiting for application to be ready..."
sleep 15

# Check application health
print_status "Checking application health..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_status "✅ Application is healthy and running!"
else
    print_error "❌ Application health check failed. Check logs with: docker-compose logs smartmoney-app"
    exit 1
fi

# Display status
echo ""
print_status "🎉 Smart Money Social Sentiment Analyzer is now running!"
echo ""
echo "📊 Dashboard: http://localhost:8080"
echo "🔧 API Docs: http://localhost:8080/docs"
echo "❤️  Health Check: http://localhost:8080/health"
echo ""
echo "📝 Useful commands:"
echo "  View logs: docker-compose logs -f smartmoney-app"
echo "  Stop services: docker-compose down"
echo "  Restart services: docker-compose restart"
echo "  Update application: docker-compose pull && docker-compose up -d"
echo ""
echo "🔑 Don't forget to:"
echo "  1. Configure your API keys in .env file"
echo "  2. Set up Telegram bot and Discord webhook for alerts"
echo "  3. Configure your whale wallet addresses"
echo "  4. Set up monitoring and backups"
echo ""

# Optional: Start with nginx for production
if [ "$1" = "--production" ]; then
    print_status "Starting with Nginx reverse proxy..."
    docker-compose --profile production up -d nginx
    echo "🌐 Application is now available at http://localhost (port 80)"
fi

print_status "Setup complete! 🚀"


