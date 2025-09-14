#!/usr/bin/env python3
"""
System Integration Test Script
Tests the backend API endpoints and verifies functionality
"""

import asyncio
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8080"

def test_endpoint(endpoint, method="GET", data=None, description=""):
    """Test a single API endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print(f"\n🔍 Testing {method} {endpoint}")
    if description:
        print(f"   📝 {description}")

    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)

        if response.status_code == 200:
            print(f"   ✅ SUCCESS - {response.status_code}")
            try:
                json_data = response.json()
                if isinstance(json_data, dict) and len(json_data) > 0:
                    # Show first few keys
                    keys = list(json_data.keys())[:3]
                    print(f"   📊 Data keys: {keys}...")
                elif isinstance(json_data, list):
                    print(f"   📊 Returned {len(json_data)} items")
                return True
            except:
                print(f"   📄 Non-JSON response")
                return True
        else:
            print(f"   ❌ FAILED - {response.status_code}: {response.text[:100]}")
            return False

    except requests.exceptions.ConnectionError:
        print(f"   ❌ CONNECTION ERROR - Server not running?")
        return False
    except requests.exceptions.Timeout:
        print(f"   ❌ TIMEOUT - Server taking too long")
        return False
    except Exception as e:
        print(f"   ❌ ERROR - {str(e)}")
        return False

def main():
    """Run comprehensive system tests"""
    print("🚀 SMART MONEY SYSTEM - INTEGRATION TEST")
    print("=" * 50)

    # Test basic endpoints
    endpoints = [
        ("/health", "GET", None, "Health check endpoint"),
        ("/status", "GET", None, "System status and metrics"),
        ("/api/system/status", "GET", None, "System health status"),
        ("/api/market/overview", "GET", None, "Market overview data"),
    ]

    # Test whale tracking
    whale_endpoints = [
        ("/api/whales/activity", "GET", None, "Recent whale activity"),
        ("/api/whales/activity?hours_back=12", "GET", None, "Whale activity (12h)"),
    ]

    # Test sentiment analysis
    sentiment_endpoints = [
        ("/api/sentiment/overview", "GET", None, "Market sentiment overview"),
    ]

    # Test signal engine
    signal_endpoints = [
        ("/api/signals/recent", "GET", None, "Recent trading signals"),
        ("/api/signals/recent?hours_back=48&min_confidence=0.5", "GET", None, "Recent signals (48h, 50% confidence)"),
    ]

    # Test trading system
    trading_endpoints = [
        ("/api/trading/portfolio", "GET", None, "Portfolio metrics"),
        ("/api/trading/positions", "GET", None, "Current positions"),
        ("/api/trading/trades", "GET", None, "Trade history"),
        ("/api/trading/auto-trading/status", "GET", None, "Auto-trading status"),
    ]

    # Test alert system
    alert_endpoints = [
        ("/api/alerts/statistics", "GET", None, "Alert statistics"),
    ]

    # Test export endpoints
    export_endpoints = [
        ("/api/export/whale-transactions?hours_back=24", "GET", None, "Export whale data"),
        ("/api/export/signals?hours_back=24", "GET", None, "Export signal data"),
    ]

    all_tests = [
        ("📊 BASIC SYSTEM", endpoints),
        ("🐋 WHALE TRACKING", whale_endpoints),
        ("💭 SENTIMENT ANALYSIS", sentiment_endpoints),
        ("🎯 SIGNAL ENGINE", signal_endpoints),
        ("💼 TRADING SYSTEM", trading_endpoints),
        ("🚨 ALERT SYSTEM", alert_endpoints),
        ("📤 EXPORT SYSTEM", export_endpoints),
    ]

    total_tests = 0
    passed_tests = 0

    for category, test_endpoints in all_tests:
        print(f"\n{category}")
        print("-" * 30)

        for endpoint, method, data, description in test_endpoints:
            total_tests += 1
            if test_endpoint(endpoint, method, data, description):
                passed_tests += 1
            time.sleep(0.5)  # Small delay between tests

    # Test some POST endpoints
    print(f"\n🔄 INTERACTIVE TESTS")
    print("-" * 30)

    # Test signal generation
    total_tests += 1
    if test_endpoint("/api/signals/generate", "POST", {"hours_back": 24}, "Generate signals manually"):
        passed_tests += 1

    # Test auto-trading toggle
    total_tests += 1
    if test_endpoint("/api/trading/auto-trading", "POST", {"enabled": False}, "Toggle auto-trading OFF"):
        passed_tests += 1

    # Summary
    print(f"\n" + "=" * 50)
    print(f"🏁 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Tests passed: {passed_tests}/{total_tests}")
    print(f"❌ Tests failed: {total_tests - passed_tests}/{total_tests}")

    if passed_tests == total_tests:
        print(f"🎉 ALL TESTS PASSED! System is fully functional.")
    elif passed_tests > total_tests * 0.8:
        print(f"⚠️  Most tests passed. Some minor issues detected.")
    else:
        print(f"❌ Many tests failed. System needs attention.")

    success_rate = (passed_tests / total_tests) * 100
    print(f"📊 Success rate: {success_rate:.1f}%")

    if passed_tests < total_tests:
        print(f"\n💡 TROUBLESHOOTING:")
        print(f"   • Make sure backend server is running on port 8080")
        print(f"   • Check if all dependencies are installed")
        print(f"   • Verify database is properly initialized")
        print(f"   • Check logs for error details")

    return passed_tests == total_tests

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)