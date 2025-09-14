#!/usr/bin/env python3
"""
Complete System Startup Script
Starts both backend and frontend with proper configuration
"""

import os
import sys
import subprocess
import time
import signal
import platform
from pathlib import Path

def is_port_in_use(port):
    """Check if a port is in use"""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """Kill process running on specific port"""
    try:
        if platform.system() == "Windows":
            # Windows command to find and kill process on port
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if f':{port}' in line and 'LISTENING' in line:
                    pid = line.strip().split()[-1]
                    subprocess.run(['taskkill', '/F', '/PID', pid], capture_output=True)
        else:
            # Unix-like systems
            subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True)
            subprocess.run(['kill', '-9'] + subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True).stdout.strip().split(), capture_output=True)
    except Exception as e:
        print(f"Could not kill process on port {port}: {e}")

def setup_environment():
    """Setup environment variables"""
    project_dir = Path(__file__).parent

    # Backend environment
    backend_env = {
        **os.environ,
        'PYTHONPATH': str(project_dir),
        'LOG_LEVEL': 'INFO',
        'DEBUG': 'True',
        'INITIAL_DEMO_BALANCE': '100000',
        'MAX_POSITIONS': '10',
        'DATABASE_URL': 'sqlite:///./smart_money.db'
    }

    # Frontend environment
    frontend_env = {
        **os.environ,
        'REACT_APP_API_URL': 'http://localhost:8080',
        'REACT_APP_WS_URL': 'ws://localhost:8080/ws',
        'REACT_APP_ENVIRONMENT': 'development'
    }

    return backend_env, frontend_env

def start_backend(env):
    """Start the FastAPI backend server"""
    print("🚀 Starting Smart Money Backend Server...")

    # Check if port 8080 is already in use
    if is_port_in_use(8080):
        print("⚠️  Port 8080 is in use, attempting to free it...")
        kill_process_on_port(8080)
        time.sleep(2)

    try:
        # Start with uvicorn
        backend_process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn',
            'app.main:app',
            '--host', '0.0.0.0',
            '--port', '8080',
            '--reload',
            '--log-level', 'info'
        ], env=env, cwd=Path(__file__).parent)

        print("✅ Backend server starting on http://localhost:8080")
        return backend_process

    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend(env):
    """Start the React frontend server"""
    print("🎨 Starting React Frontend Server...")

    frontend_dir = Path(__file__).parent / 'frontend'

    if not frontend_dir.exists():
        print("❌ Frontend directory not found!")
        return None

    # Check if node_modules exists
    if not (frontend_dir / 'node_modules').exists():
        print("📦 Installing npm dependencies...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        except subprocess.CalledProcessError:
            print("❌ Failed to install npm dependencies")
            return None

    # Check if port 3000 is in use
    if is_port_in_use(3000):
        print("⚠️  Port 3000 is in use, attempting to free it...")
        kill_process_on_port(3000)
        time.sleep(2)

    try:
        # Start React dev server
        frontend_process = subprocess.Popen([
            'npm', 'start'
        ], env=env, cwd=frontend_dir)

        print("✅ Frontend server starting on http://localhost:3000")
        return frontend_process

    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def wait_for_servers():
    """Wait for servers to be ready"""
    print("⏳ Waiting for servers to start...")

    # Wait for backend
    for i in range(30):
        if is_port_in_use(8080):
            print("✅ Backend server is ready!")
            break
        time.sleep(1)
    else:
        print("❌ Backend server failed to start in time")
        return False

    # Wait for frontend
    for i in range(60):
        if is_port_in_use(3000):
            print("✅ Frontend server is ready!")
            break
        time.sleep(1)
    else:
        print("⚠️  Frontend server taking longer than expected...")

    return True

def main():
    """Main startup function"""
    print("🏁 Starting Smart Money Social Sentiment System...")
    print("=" * 60)

    # Setup environment
    backend_env, frontend_env = setup_environment()

    # Start backend
    backend_process = start_backend(backend_env)
    if not backend_process:
        print("❌ Could not start backend server")
        return 1

    time.sleep(5)  # Give backend time to start

    # Start frontend
    frontend_process = start_frontend(frontend_env)
    if not frontend_process:
        print("❌ Could not start frontend server")
        backend_process.terminate()
        return 1

    # Wait for servers
    if not wait_for_servers():
        print("❌ Servers failed to start properly")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        return 1

    print("\n" + "=" * 60)
    print("🎉 SMART MONEY SYSTEM READY!")
    print("=" * 60)
    print("📊 Backend API:  http://localhost:8080")
    print("🎨 Frontend:     http://localhost:3000")
    print("📚 API Docs:     http://localhost:8080/docs")
    print("🔌 WebSocket:    ws://localhost:8080/ws")
    print("=" * 60)
    print("\n🎯 QUICK ACCESS LINKS:")
    print("   • Dashboard:       http://localhost:3000/")
    print("   • Trading Panel:   http://localhost:3000/trading")
    print("   • Whale Tracker:   http://localhost:3000/whales")
    print("   • Sentiment:       http://localhost:3000/sentiment")
    print("   • Signals:         http://localhost:3000/signals")
    print("\n⚠️  Press Ctrl+C to stop all servers")

    # Handle shutdown gracefully
    def signal_handler(sig, frame):
        print("\n\n🛑 Shutting down servers...")
        if backend_process:
            backend_process.terminate()
        if frontend_process:
            frontend_process.terminate()
        print("✅ All servers stopped. Goodbye!")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Keep script running
        while True:
            time.sleep(1)

            # Check if processes are still running
            if backend_process and backend_process.poll() is not None:
                print("❌ Backend process died unexpectedly")
                break
            if frontend_process and frontend_process.poll() is not None:
                print("❌ Frontend process died unexpectedly")
                break

    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    sys.exit(main())