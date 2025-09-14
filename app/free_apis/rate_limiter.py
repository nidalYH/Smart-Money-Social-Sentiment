"""
Rate limiting system for managing free API calls across all services
Ensures we stay within free tier limits while maximizing data collection
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from collections import deque
import json
import time

logger = logging.getLogger(__name__)


@dataclass
class APILimit:
    """API rate limit configuration"""
    name: str
    calls_per_period: int
    period_seconds: int
    burst_limit: Optional[int] = None  # Max calls in a short burst
    burst_period: int = 60  # Burst period in seconds
    priority: int = 1  # Higher number = higher priority


@dataclass
class APICall:
    """Individual API call record"""
    api_name: str
    timestamp: datetime
    success: bool
    error_msg: Optional[str] = None
    response_time: float = 0.0


class RateLimiter:
    """Centralized rate limiter for all free APIs"""

    def __init__(self):
        # Configure limits for each free API
        self.api_limits = {
            'reddit': APILimit(
                name='reddit',
                calls_per_period=60,
                period_seconds=60,
                burst_limit=10,
                burst_period=10,
                priority=3
            ),
            'coingecko': APILimit(
                name='coingecko',
                calls_per_period=50,
                period_seconds=60,
                burst_limit=5,
                burst_period=10,
                priority=2
            ),
            'etherscan': APILimit(
                name='etherscan',
                calls_per_period=5,
                period_seconds=1,  # 5 calls per second
                burst_limit=3,
                burst_period=1,
                priority=1
            ),
            'google_trends': APILimit(
                name='google_trends',
                calls_per_period=10,
                period_seconds=60,
                burst_limit=3,
                burst_period=30,
                priority=2
            ),
            'alternative_me': APILimit(
                name='alternative_me',
                calls_per_period=30,
                period_seconds=60,
                priority=1
            ),
            'defillama': APILimit(
                name='defillama',
                calls_per_period=300,
                period_seconds=60,
                priority=1
            ),
            'coinmarketcap': APILimit(
                name='coinmarketcap',
                calls_per_period=333,
                period_seconds=86400,  # Daily limit
                priority=2
            )
        }

        # Track API calls
        self.call_history: Dict[str, deque] = {}
        self.pending_calls: Dict[str, List] = {}

        # Initialize call history for each API
        for api_name in self.api_limits.keys():
            self.call_history[api_name] = deque(maxlen=1000)
            self.pending_calls[api_name] = []

        # Rate limiter state
        self.is_running = False
        self.global_pause = False
        self.statistics = {}

    async def execute_call(self, api_name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute an API call with rate limiting"""
        if api_name not in self.api_limits:
            raise ValueError(f"Unknown API: {api_name}")

        # Wait for rate limit clearance
        await self._wait_for_rate_limit(api_name)

        # Execute the call
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            response_time = time.time() - start_time

            # Record successful call
            self._record_call(api_name, True, response_time=response_time)

            return result

        except Exception as e:
            response_time = time.time() - start_time

            # Record failed call
            self._record_call(api_name, False, str(e), response_time)

            # Re-raise the exception
            raise

    async def batch_execute(self, calls: List[Dict]) -> List[Any]:
        """
        Execute multiple API calls with intelligent scheduling

        calls format: [
            {'api_name': 'coingecko', 'func': func, 'args': [], 'kwargs': {}},
            ...
        ]
        """
        logger.info(f"Executing batch of {len(calls)} API calls")

        # Sort calls by priority
        prioritized_calls = sorted(calls, key=lambda x: self.api_limits[x['api_name']].priority, reverse=True)

        results = []

        for call_info in prioritized_calls:
            try:
                result = await self.execute_call(
                    call_info['api_name'],
                    call_info['func'],
                    *call_info.get('args', []),
                    **call_info.get('kwargs', {})
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Error in batch call to {call_info['api_name']}: {e}")
                results.append(None)

        return results

    async def _wait_for_rate_limit(self, api_name: str):
        """Wait until we can make a call without exceeding rate limits"""
        limit = self.api_limits[api_name]
        now = datetime.utcnow()

        while True:
            # Check if we're within rate limits
            if self._can_make_call(api_name, now):
                break

            # Calculate wait time
            wait_time = self._calculate_wait_time(api_name, now)

            if wait_time > 0:
                logger.debug(f"Rate limit reached for {api_name}, waiting {wait_time:.1f} seconds")
                await asyncio.sleep(wait_time)

            now = datetime.utcnow()

    def _can_make_call(self, api_name: str, now: datetime) -> bool:
        """Check if we can make a call without exceeding limits"""
        limit = self.api_limits[api_name]
        history = self.call_history[api_name]

        # Check main rate limit
        cutoff_time = now - timedelta(seconds=limit.period_seconds)
        recent_calls = [call for call in history if call.timestamp >= cutoff_time]

        if len(recent_calls) >= limit.calls_per_period:
            return False

        # Check burst limit if configured
        if limit.burst_limit:
            burst_cutoff = now - timedelta(seconds=limit.burst_period)
            burst_calls = [call for call in history if call.timestamp >= burst_cutoff]

            if len(burst_calls) >= limit.burst_limit:
                return False

        return True

    def _calculate_wait_time(self, api_name: str, now: datetime) -> float:
        """Calculate how long to wait before making the next call"""
        limit = self.api_limits[api_name]
        history = self.call_history[api_name]

        wait_times = []

        # Check main rate limit
        if history:
            cutoff_time = now - timedelta(seconds=limit.period_seconds)
            recent_calls = [call for call in history if call.timestamp >= cutoff_time]

            if len(recent_calls) >= limit.calls_per_period:
                oldest_recent_call = min(call.timestamp for call in recent_calls)
                next_available = oldest_recent_call + timedelta(seconds=limit.period_seconds)
                wait_time = (next_available - now).total_seconds()
                wait_times.append(max(wait_time, 0))

        # Check burst limit
        if limit.burst_limit and history:
            burst_cutoff = now - timedelta(seconds=limit.burst_period)
            burst_calls = [call for call in history if call.timestamp >= burst_cutoff]

            if len(burst_calls) >= limit.burst_limit:
                oldest_burst_call = min(call.timestamp for call in burst_calls)
                next_available = oldest_burst_call + timedelta(seconds=limit.burst_period)
                wait_time = (next_available - now).total_seconds()
                wait_times.append(max(wait_time, 0))

        return max(wait_times) if wait_times else 0

    def _record_call(self, api_name: str, success: bool, error_msg: str = None, response_time: float = 0.0):
        """Record an API call in the history"""
        call = APICall(
            api_name=api_name,
            timestamp=datetime.utcnow(),
            success=success,
            error_msg=error_msg,
            response_time=response_time
        )

        self.call_history[api_name].append(call)

        # Update statistics
        self._update_statistics(api_name, call)

    def _update_statistics(self, api_name: str, call: APICall):
        """Update API usage statistics"""
        if api_name not in self.statistics:
            self.statistics[api_name] = {
                'total_calls': 0,
                'successful_calls': 0,
                'failed_calls': 0,
                'avg_response_time': 0.0,
                'last_call': None,
                'calls_today': 0,
                'errors': []
            }

        stats = self.statistics[api_name]
        stats['total_calls'] += 1
        stats['last_call'] = call.timestamp

        if call.success:
            stats['successful_calls'] += 1
        else:
            stats['failed_calls'] += 1
            if call.error_msg:
                stats['errors'].append({
                    'timestamp': call.timestamp,
                    'error': call.error_msg
                })
                # Keep only last 10 errors
                stats['errors'] = stats['errors'][-10:]

        # Update average response time
        if call.success and call.response_time > 0:
            total_time = stats['avg_response_time'] * (stats['successful_calls'] - 1) + call.response_time
            stats['avg_response_time'] = total_time / stats['successful_calls']

        # Count calls today
        today = datetime.utcnow().date()
        today_calls = [c for c in self.call_history[api_name]
                      if c.timestamp.date() == today]
        stats['calls_today'] = len(today_calls)

    def get_rate_limit_status(self, api_name: str = None) -> Dict:
        """Get current rate limit status for API(s)"""
        if api_name:
            return self._get_single_api_status(api_name)
        else:
            return {name: self._get_single_api_status(name) for name in self.api_limits.keys()}

    def _get_single_api_status(self, api_name: str) -> Dict:
        """Get rate limit status for a single API"""
        if api_name not in self.api_limits:
            return {'error': f'Unknown API: {api_name}'}

        limit = self.api_limits[api_name]
        history = self.call_history[api_name]
        now = datetime.utcnow()

        # Count recent calls
        cutoff_time = now - timedelta(seconds=limit.period_seconds)
        recent_calls = [call for call in history if call.timestamp >= cutoff_time]

        # Count burst calls
        burst_calls = 0
        if limit.burst_limit:
            burst_cutoff = now - timedelta(seconds=limit.burst_period)
            burst_calls = len([call for call in history if call.timestamp >= burst_cutoff])

        # Calculate remaining calls
        remaining_calls = max(0, limit.calls_per_period - len(recent_calls))

        # Check if we can make a call now
        can_call_now = self._can_make_call(api_name, now)

        # Calculate reset time
        reset_time = None
        if recent_calls:
            oldest_call = min(call.timestamp for call in recent_calls)
            reset_time = oldest_call + timedelta(seconds=limit.period_seconds)

        status = {
            'api_name': api_name,
            'limit_per_period': limit.calls_per_period,
            'period_seconds': limit.period_seconds,
            'calls_used': len(recent_calls),
            'calls_remaining': remaining_calls,
            'reset_time': reset_time.isoformat() if reset_time else None,
            'can_call_now': can_call_now,
            'burst_calls_used': burst_calls,
            'burst_limit': limit.burst_limit,
            'next_available': now.isoformat() if can_call_now else
                            (now + timedelta(seconds=self._calculate_wait_time(api_name, now))).isoformat()
        }

        return status

    def get_usage_statistics(self) -> Dict:
        """Get comprehensive usage statistics"""
        total_stats = {
            'total_calls_all_apis': sum(stats['total_calls'] for stats in self.statistics.values()),
            'successful_calls_all_apis': sum(stats['successful_calls'] for stats in self.statistics.values()),
            'failed_calls_all_apis': sum(stats['failed_calls'] for stats in self.statistics.values()),
            'apis': {}
        }

        for api_name, stats in self.statistics.items():
            # Calculate success rate
            success_rate = (stats['successful_calls'] / max(stats['total_calls'], 1)) * 100

            # Get current status
            current_status = self._get_single_api_status(api_name)

            total_stats['apis'][api_name] = {
                **stats,
                'success_rate_percent': round(success_rate, 2),
                'current_status': current_status
            }

        return total_stats

    async def optimize_call_schedule(self, planned_calls: List[Dict]) -> List[Dict]:
        """
        Optimize the schedule of planned API calls to maximize efficiency

        Returns optimized call schedule with timing
        """
        optimized_schedule = []
        now = datetime.utcnow()

        # Group calls by API
        calls_by_api = {}
        for call in planned_calls:
            api_name = call['api_name']
            if api_name not in calls_by_api:
                calls_by_api[api_name] = []
            calls_by_api[api_name].append(call)

        # Schedule calls for each API
        for api_name, api_calls in calls_by_api.items():
            if api_name not in self.api_limits:
                continue

            limit = self.api_limits[api_name]

            # Sort by priority if specified in call
            api_calls.sort(key=lambda x: x.get('priority', 0), reverse=True)

            current_time = now
            for i, call in enumerate(api_calls):
                # Calculate when this call can be made
                while not self._can_make_call(api_name, current_time):
                    wait_time = self._calculate_wait_time(api_name, current_time)
                    current_time += timedelta(seconds=wait_time)

                # Add to schedule
                scheduled_call = {
                    **call,
                    'scheduled_time': current_time,
                    'estimated_delay': (current_time - now).total_seconds()
                }
                optimized_schedule.append(scheduled_call)

                # Simulate the call being made
                simulated_call = APICall(api_name, current_time, True)
                self.call_history[api_name].append(simulated_call)

                # Add minimal delay between calls
                current_time += timedelta(seconds=0.2)

        # Sort final schedule by time
        optimized_schedule.sort(key=lambda x: x['scheduled_time'])

        return optimized_schedule

    def pause_api(self, api_name: str, duration_seconds: int):
        """Temporarily pause an API for a specified duration"""
        logger.info(f"Pausing {api_name} for {duration_seconds} seconds")
        # Implementation would pause the specific API
        # This is a placeholder for the actual implementation

    def resume_api(self, api_name: str):
        """Resume a paused API"""
        logger.info(f"Resuming {api_name}")
        # Implementation would resume the specific API

    def set_global_pause(self, paused: bool):
        """Pause/resume all API calls globally"""
        self.global_pause = paused
        logger.info(f"Global API pause: {'ENABLED' if paused else 'DISABLED'}")

    def get_health_status(self) -> Dict:
        """Get overall health status of the rate limiting system"""
        now = datetime.utcnow()
        health_status = {
            'timestamp': now.isoformat(),
            'global_pause': self.global_pause,
            'overall_health': 'healthy',
            'api_health': {}
        }

        unhealthy_apis = 0

        for api_name in self.api_limits.keys():
            api_stats = self.statistics.get(api_name, {})

            # Calculate health score
            recent_calls = [call for call in self.call_history[api_name]
                          if call.timestamp >= now - timedelta(minutes=10)]

            if recent_calls:
                success_rate = sum(1 for call in recent_calls if call.success) / len(recent_calls)
                avg_response_time = sum(call.response_time for call in recent_calls if call.success) / max(len(recent_calls), 1)
            else:
                success_rate = 1.0
                avg_response_time = 0.0

            # Determine health status
            if success_rate < 0.8:
                api_health = 'unhealthy'
                unhealthy_apis += 1
            elif success_rate < 0.95 or avg_response_time > 5.0:
                api_health = 'degraded'
            else:
                api_health = 'healthy'

            health_status['api_health'][api_name] = {
                'status': api_health,
                'success_rate': round(success_rate * 100, 2),
                'avg_response_time': round(avg_response_time, 2),
                'recent_calls': len(recent_calls)
            }

        # Overall health assessment
        if unhealthy_apis > 2:
            health_status['overall_health'] = 'unhealthy'
        elif unhealthy_apis > 0:
            health_status['overall_health'] = 'degraded'

        return health_status

    def export_statistics(self, format: str = 'json') -> str:
        """Export usage statistics in specified format"""
        stats = self.get_usage_statistics()

        if format.lower() == 'json':
            return json.dumps(stats, indent=2, default=str)
        else:
            raise ValueError(f"Unsupported export format: {format}")


# Global rate limiter instance
_global_rate_limiter = None

def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance"""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = RateLimiter()
    return _global_rate_limiter


# Decorator for automatic rate limiting
def rate_limited(api_name: str):
    """Decorator to automatically apply rate limiting to async functions"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            rate_limiter = get_rate_limiter()
            return await rate_limiter.execute_call(api_name, func, *args, **kwargs)
        return wrapper
    return decorator


# Example usage
async def example_usage():
    """Example of how to use the rate limiter"""
    rate_limiter = get_rate_limiter()

    # Example API function
    async def fetch_coingecko_data(symbol: str):
        await asyncio.sleep(0.5)  # Simulate API call
        return f"Data for {symbol}"

    # Execute single call with rate limiting
    result = await rate_limiter.execute_call('coingecko', fetch_coingecko_data, 'BTC')
    print(f"Result: {result}")

    # Execute batch calls
    batch_calls = [
        {'api_name': 'coingecko', 'func': fetch_coingecko_data, 'args': ['BTC']},
        {'api_name': 'coingecko', 'func': fetch_coingecko_data, 'args': ['ETH']},
        {'api_name': 'coingecko', 'func': fetch_coingecko_data, 'args': ['ADA']},
    ]

    results = await rate_limiter.batch_execute(batch_calls)
    print(f"Batch results: {results}")

    # Get rate limit status
    status = rate_limiter.get_rate_limit_status()
    print(f"Rate limit status: {status}")

    # Get usage statistics
    stats = rate_limiter.get_usage_statistics()
    print(f"Usage stats: {stats}")


if __name__ == "__main__":
    asyncio.run(example_usage())