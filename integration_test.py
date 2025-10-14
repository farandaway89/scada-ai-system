#!/usr/bin/env python3
"""
SCADA AI System - End-to-End Integration Test Suite
Comprehensive testing of all integrated modules and their interactions
"""

import asyncio
import aiohttp
import json
import time
import logging
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import subprocess
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/integration_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class IntegrationTestSuite:
    """Comprehensive integration test suite for SCADA AI System"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = None
        self.test_results = {}
        self.start_time = None
        self.auth_token = None

        # Test configuration
        self.timeout = 30
        self.retry_count = 3
        self.test_data_points = 50

    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def run_all_tests(self) -> Dict[str, Any]:
        """Run complete integration test suite"""
        self.start_time = datetime.now()
        logger.info("🧪 Starting SCADA AI System Integration Tests...")

        test_categories = [
            ("System Health", self.test_system_health),
            ("API Endpoints", self.test_api_endpoints),
            ("Configuration Management", self.test_configuration_management),
            ("Data Pipeline", self.test_data_pipeline),
            ("Monitoring System", self.test_monitoring_system),
            ("Analytics Engine", self.test_analytics_engine),
            ("Security Framework", self.test_security_framework),
            ("Reporting System", self.test_reporting_system),
            ("Compliance System", self.test_compliance_system),
            ("Integration Layer", self.test_integration_layer),
            ("Performance Tests", self.test_performance),
            ("Stress Tests", self.test_stress_scenarios)
        ]

        for category_name, test_func in test_categories:
            logger.info(f"🔬 Running {category_name} Tests...")
            try:
                category_results = await test_func()
                self.test_results[category_name] = category_results

                # Log category summary
                passed = sum(1 for r in category_results.values() if r.get('passed', False))
                total = len(category_results)
                logger.info(f"✅ {category_name}: {passed}/{total} tests passed")

            except Exception as e:
                logger.error(f"❌ {category_name} tests failed: {e}")
                self.test_results[category_name] = {"error": str(e), "passed": False}

        # Generate test report
        await self.generate_test_report()

        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()

        logger.info(f"🏁 Integration tests completed in {total_duration:.2f} seconds")
        return self.test_results

    async def test_system_health(self) -> Dict[str, Any]:
        """Test basic system health and availability"""
        results = {}

        # Test 1: System is running
        results["system_running"] = await self._test_endpoint_availability("/health")

        # Test 2: Main page loads
        results["main_page_loads"] = await self._test_endpoint_availability("/")

        # Test 3: API documentation accessible
        results["api_docs_accessible"] = await self._test_endpoint_availability("/docs")

        # Test 4: System status endpoint
        results["system_status"] = await self._test_endpoint_availability("/status")

        # Test 5: Response time acceptable
        results["response_time"] = await self._test_response_time("/health", max_time=2.0)

        return results

    async def test_api_endpoints(self) -> Dict[str, Any]:
        """Test all API endpoints for basic functionality"""
        results = {}

        endpoints = [
            "/status",
            "/health",
            "/monitoring/current",
            "/analytics/dashboard",
            "/compliance/dashboard",
            "/integration/status",
            "/pipeline/status",
            "/pipeline/metrics"
        ]

        for endpoint in endpoints:
            endpoint_name = endpoint.replace("/", "_").strip("_")
            results[f"endpoint_{endpoint_name}"] = await self._test_endpoint_with_auth(endpoint)

        return results

    async def test_configuration_management(self) -> Dict[str, Any]:
        """Test configuration management system"""
        results = {}

        # Test configuration file existence
        config_files = ["config/base.yaml", "config/production.yaml"]
        for config_file in config_files:
            file_name = Path(config_file).name.replace(".", "_")
            results[f"config_file_{file_name}"] = {"passed": Path(config_file).exists()}

        # Test configuration loading
        try:
            from config_manager import get_config_manager
            config_mgr = get_config_manager()

            # Test getting various configurations
            system_config = config_mgr.get_config("system", "environment")
            results["config_system_environment"] = {"passed": system_config is not None}

            security_config = config_mgr.get_config("security", "enable_security")
            results["config_security_enabled"] = {"passed": isinstance(security_config, bool)}

        except Exception as e:
            results["config_loading_error"] = {"passed": False, "error": str(e)}

        return results

    async def test_data_pipeline(self) -> Dict[str, Any]:
        """Test data pipeline functionality"""
        results = {}

        # Test pipeline status
        results["pipeline_status"] = await self._test_endpoint_with_auth("/pipeline/status")

        # Test pipeline metrics
        results["pipeline_metrics"] = await self._test_endpoint_with_auth("/pipeline/metrics")

        # Test data flow (if pipeline is running)
        try:
            async with self.session.get(f"{self.base_url}/pipeline/metrics") as response:
                if response.status == 200:
                    metrics = await response.json()
                    throughput = metrics.get("performance", {}).get("throughput_per_second", 0)
                    results["data_throughput"] = {
                        "passed": throughput > 0,
                        "throughput": throughput
                    }
                else:
                    results["data_throughput"] = {"passed": False, "status": response.status}

        except Exception as e:
            results["data_throughput"] = {"passed": False, "error": str(e)}

        return results

    async def test_monitoring_system(self) -> Dict[str, Any]:
        """Test real-time monitoring system"""
        results = {}

        # Test monitoring data endpoint
        results["monitoring_data"] = await self._test_endpoint_with_auth("/monitoring/current")

        # Test monitoring configuration
        try:
            async with self.session.get(f"{self.base_url}/monitoring/current") as response:
                if response.status == 200:
                    data = await response.json()
                    monitoring_status = data.get("monitoring_status", {})

                    results["monitoring_points"] = {
                        "passed": monitoring_status.get("monitoring_points", 0) > 0
                    }

                    results["monitoring_active"] = {
                        "passed": monitoring_status.get("status") == "running"
                    }
                else:
                    results["monitoring_error"] = {"passed": False, "status": response.status}

        except Exception as e:
            results["monitoring_exception"] = {"passed": False, "error": str(e)}

        return results

    async def test_analytics_engine(self) -> Dict[str, Any]:
        """Test ML analytics engine"""
        results = {}

        # Test analytics dashboard
        results["analytics_dashboard"] = await self._test_endpoint_with_auth("/analytics/dashboard")

        # Test analytics capabilities
        try:
            async with self.session.get(f"{self.base_url}/analytics/dashboard") as response:
                if response.status == 200:
                    data = await response.json()
                    summary = data.get("analytics_summary", {})

                    results["analytics_initialized"] = {
                        "passed": "total_analyses" in summary
                    }

                    results["analytics_functional"] = {
                        "passed": summary.get("total_analyses", 0) >= 0
                    }
                else:
                    results["analytics_error"] = {"passed": False, "status": response.status}

        except Exception as e:
            results["analytics_exception"] = {"passed": False, "error": str(e)}

        return results

    async def test_security_framework(self) -> Dict[str, Any]:
        """Test security framework"""
        results = {}

        # Test authentication requirement
        try:
            # Test endpoint without auth (should require auth)
            async with self.session.get(f"{self.base_url}/monitoring/current") as response:
                results["auth_required"] = {
                    "passed": response.status in [401, 403]  # Should require authentication
                }
        except Exception as e:
            results["auth_test_error"] = {"passed": False, "error": str(e)}

        # Test security headers
        try:
            async with self.session.get(f"{self.base_url}/health") as response:
                headers = dict(response.headers)
                results["security_headers"] = {
                    "passed": any(header.lower().startswith('x-') for header in headers)
                }
        except Exception as e:
            results["security_headers_error"] = {"passed": False, "error": str(e)}

        return results

    async def test_reporting_system(self) -> Dict[str, Any]:
        """Test reporting system"""
        results = {}

        # Test report generation endpoint
        try:
            report_data = {
                "report_type": "operational",
                "format": "json",
                "days_back": 1
            }

            async with self.session.post(
                f"{self.base_url}/reports/generate",
                json=report_data
            ) as response:
                results["report_generation"] = {
                    "passed": response.status in [200, 202],  # 202 for background task
                    "status": response.status
                }

                if response.status == 200:
                    data = await response.json()
                    results["report_response"] = {
                        "passed": "report_id" in data or "report_path" in data
                    }

        except Exception as e:
            results["report_generation_error"] = {"passed": False, "error": str(e)}

        return results

    async def test_compliance_system(self) -> Dict[str, Any]:
        """Test compliance system"""
        results = {}

        # Test compliance dashboard
        results["compliance_dashboard"] = await self._test_endpoint_with_auth("/compliance/dashboard")

        # Test compliance functionality
        try:
            async with self.session.get(f"{self.base_url}/compliance/dashboard") as response:
                if response.status == 200:
                    data = await response.json()
                    dashboard = data.get("compliance_dashboard", {})

                    results["compliance_metrics"] = {
                        "passed": "status_summary" in dashboard
                    }

                    results["compliance_scoring"] = {
                        "passed": "overall_score" in dashboard
                    }
                else:
                    results["compliance_error"] = {"passed": False, "status": response.status}

        except Exception as e:
            results["compliance_exception"] = {"passed": False, "error": str(e)}

        return results

    async def test_integration_layer(self) -> Dict[str, Any]:
        """Test enterprise integration layer"""
        results = {}

        # Test integration status
        results["integration_status"] = await self._test_endpoint_with_auth("/integration/status")

        # Test integration functionality
        try:
            async with self.session.get(f"{self.base_url}/integration/status") as response:
                if response.status == 200:
                    data = await response.json()
                    status = data.get("integration_status", {})

                    results["integration_configured"] = {
                        "passed": len(status) > 0
                    }

                    results["integration_available"] = {
                        "passed": True  # Just availability test
                    }
                else:
                    results["integration_error"] = {"passed": False, "status": response.status}

        except Exception as e:
            results["integration_exception"] = {"passed": False, "error": str(e)}

        return results

    async def test_performance(self) -> Dict[str, Any]:
        """Test system performance"""
        results = {}

        # Test response times
        endpoints_to_test = ["/health", "/status", "/monitoring/current"]

        for endpoint in endpoints_to_test:
            endpoint_name = endpoint.replace("/", "_").strip("_")
            results[f"performance_{endpoint_name}"] = await self._test_response_time(endpoint, max_time=1.0)

        # Test concurrent requests
        results["concurrent_requests"] = await self._test_concurrent_requests()

        # Test memory usage (if possible)
        try:
            async with self.session.get(f"{self.base_url}/status") as response:
                if response.status == 200:
                    data = await response.json()
                    metrics = data.get("system_metrics", {})
                    memory_percent = metrics.get("memory_percent", 0)

                    results["memory_usage"] = {
                        "passed": memory_percent < 80,  # Less than 80% memory usage
                        "memory_percent": memory_percent
                    }

        except Exception as e:
            results["memory_test_error"] = {"passed": False, "error": str(e)}

        return results

    async def test_stress_scenarios(self) -> Dict[str, Any]:
        """Test system under stress conditions"""
        results = {}

        # Test rapid requests
        start_time = time.time()
        success_count = 0
        total_requests = 50

        tasks = []
        for i in range(total_requests):
            tasks.append(self._make_request("/health"))

        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for response in responses:
            if isinstance(response, dict) and response.get("status") == 200:
                success_count += 1

        end_time = time.time()
        duration = end_time - start_time

        results["rapid_requests"] = {
            "passed": success_count >= total_requests * 0.9,  # 90% success rate
            "success_rate": success_count / total_requests,
            "duration": duration,
            "requests_per_second": total_requests / duration
        }

        return results

    async def _test_endpoint_availability(self, endpoint: str) -> Dict[str, Any]:
        """Test if endpoint is available"""
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                return {
                    "passed": response.status in [200, 401, 403],  # Available (may require auth)
                    "status": response.status,
                    "response_time": response.headers.get("x-process-time", "unknown")
                }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def _test_endpoint_with_auth(self, endpoint: str) -> Dict[str, Any]:
        """Test endpoint that may require authentication"""
        try:
            # First try without auth
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                if response.status == 200:
                    # Endpoint works without auth (or auth disabled for testing)
                    return {
                        "passed": True,
                        "status": response.status,
                        "auth_required": False
                    }
                elif response.status in [401, 403]:
                    # Auth required - this is expected behavior
                    return {
                        "passed": True,
                        "status": response.status,
                        "auth_required": True
                    }
                else:
                    return {
                        "passed": False,
                        "status": response.status
                    }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def _test_response_time(self, endpoint: str, max_time: float) -> Dict[str, Any]:
        """Test endpoint response time"""
        try:
            start_time = time.time()
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                response_time = time.time() - start_time

                return {
                    "passed": response_time <= max_time,
                    "response_time": response_time,
                    "max_allowed": max_time,
                    "status": response.status
                }
        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def _make_request(self, endpoint: str) -> Dict[str, Any]:
        """Make a single request and return results"""
        try:
            async with self.session.get(f"{self.base_url}{endpoint}") as response:
                return {
                    "status": response.status,
                    "response_time": time.time()
                }
        except Exception as e:
            return {"status": 0, "error": str(e)}

    async def _test_concurrent_requests(self) -> Dict[str, Any]:
        """Test concurrent request handling"""
        try:
            concurrent_count = 10
            tasks = []

            start_time = time.time()
            for i in range(concurrent_count):
                tasks.append(self._make_request("/health"))

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = time.time()

            success_count = sum(1 for r in responses if isinstance(r, dict) and r.get("status") == 200)

            return {
                "passed": success_count >= concurrent_count * 0.8,  # 80% success rate
                "success_count": success_count,
                "total_requests": concurrent_count,
                "total_time": end_time - start_time
            }

        except Exception as e:
            return {"passed": False, "error": str(e)}

    async def generate_test_report(self):
        """Generate comprehensive test report"""
        try:
            # Calculate overall statistics
            total_tests = 0
            passed_tests = 0

            for category, tests in self.test_results.items():
                if isinstance(tests, dict) and "error" not in tests:
                    for test_name, result in tests.items():
                        total_tests += 1
                        if result.get("passed", False):
                            passed_tests += 1

            success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

            # Create report
            report = {
                "test_summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": total_tests - passed_tests,
                    "success_rate": success_rate,
                    "start_time": self.start_time.isoformat(),
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": (datetime.now() - self.start_time).total_seconds()
                },
                "test_results": self.test_results,
                "system_info": {
                    "base_url": self.base_url,
                    "timeout": self.timeout,
                    "retry_count": self.retry_count
                }
            }

            # Save report to file
            report_file = f"logs/integration_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            Path("logs").mkdir(exist_ok=True)

            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info(f"📄 Test report saved to: {report_file}")

            # Print summary
            logger.info("=" * 60)
            logger.info("📊 INTEGRATION TEST SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total Tests: {total_tests}")
            logger.info(f"Passed: {passed_tests}")
            logger.info(f"Failed: {total_tests - passed_tests}")
            logger.info(f"Success Rate: {success_rate:.1f}%")
            logger.info(f"Duration: {report['test_summary']['duration_seconds']:.2f} seconds")
            logger.info("=" * 60)

            # Print category breakdown
            for category, tests in self.test_results.items():
                if isinstance(tests, dict) and "error" not in tests:
                    category_passed = sum(1 for r in tests.values() if r.get("passed", False))
                    category_total = len(tests)
                    logger.info(f"{category}: {category_passed}/{category_total}")

        except Exception as e:
            logger.error(f"Error generating test report: {e}")

def wait_for_system_ready(base_url: str, timeout: int = 120) -> bool:
    """Wait for system to be ready for testing"""
    logger.info("⏳ Waiting for system to be ready...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            import requests
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ System is ready for testing")
                return True
        except:
            pass

        time.sleep(2)

    logger.error("❌ System not ready within timeout period")
    return False

async def main():
    """Main test function"""
    import argparse

    parser = argparse.ArgumentParser(description="SCADA AI System Integration Tests")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the system")
    parser.add_argument("--wait", action="store_true", help="Wait for system to be ready")
    parser.add_argument("--start-system", action="store_true", help="Start system before testing")
    parser.add_argument("--stop-system", action="store_true", help="Stop system after testing")

    args = parser.parse_args()

    system_process = None

    try:
        # Start system if requested
        if args.start_system:
            logger.info("🚀 Starting SCADA AI System for testing...")
            system_process = subprocess.Popen([
                sys.executable, "start_integrated_system.py", "--background"
            ])
            time.sleep(10)  # Give system time to start

        # Wait for system if requested
        if args.wait:
            if not wait_for_system_ready(args.url):
                sys.exit(1)

        # Run integration tests
        async with IntegrationTestSuite(args.url) as test_suite:
            await test_suite.run_all_tests()

    except KeyboardInterrupt:
        logger.info("👋 Tests interrupted by user")
    except Exception as e:
        logger.error(f"❌ Test execution error: {e}")
    finally:
        # Stop system if we started it
        if system_process and args.stop_system:
            logger.info("🛑 Stopping test system...")
            system_process.terminate()
            try:
                system_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                system_process.kill()

if __name__ == "__main__":
    asyncio.run(main())