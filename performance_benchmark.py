"""Performance benchmarking and optimization tools for MCP Research Server."""

import asyncio
import time
import statistics
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import logging
import psutil
import sys

from server import app
from cache_manager import cache_manager
from retry_manager import retry_manager
from health_monitor import health_monitor


@dataclass
class BenchmarkResult:
    """Results from a performance benchmark test."""
    test_name: str
    total_time: float
    average_time: float
    min_time: float
    max_time: float
    median_time: float
    requests_per_second: float
    success_rate: float
    error_count: int
    memory_usage_mb: float
    cache_hit_rate: float
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class BenchmarkSuite:
    """Collection of benchmark tests."""
    suite_name: str
    tests: List[BenchmarkResult] = field(default_factory=list)
    total_duration: float = 0.0
    overall_success_rate: float = 0.0


class PerformanceBenchmark:
    """Comprehensive performance benchmarking system."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.benchmark_history: List[BenchmarkSuite] = []

    async def run_comprehensive_benchmark(
        self,
        include_stress_tests: bool = False,
        include_concurrency_tests: bool = True
    ) -> BenchmarkSuite:
        """Run a comprehensive benchmark suite."""
        self.logger.info("Starting comprehensive performance benchmark")
        start_time = time.time()

        suite = BenchmarkSuite(suite_name=f"Comprehensive Benchmark {datetime.now().isoformat()}")

        # Basic functionality benchmarks
        basic_tests = [
            ("Simple Search", self._benchmark_simple_search),
            ("Paper Details", self._benchmark_paper_details),
            ("Author Search", self._benchmark_author_search),
            ("Citation Retrieval", self._benchmark_citations),
            ("Cache Operations", self._benchmark_cache_operations),
        ]

        for test_name, test_func in basic_tests:
            try:
                result = await test_func()
                result.test_name = test_name
                suite.tests.append(result)
                self.logger.info(f"Completed {test_name}: {result.average_time:.3f}s avg, {result.success_rate:.1%} success")
            except Exception as e:
                self.logger.error(f"Benchmark test {test_name} failed: {e}")

        # Advanced functionality benchmarks
        advanced_tests = [
            ("Advanced Search", self._benchmark_advanced_search),
            ("Recommendations", self._benchmark_recommendations),
            ("Query Building", self._benchmark_query_building),
            ("Bibliography Export", self._benchmark_export),
        ]

        for test_name, test_func in advanced_tests:
            try:
                result = await test_func()
                result.test_name = test_name
                suite.tests.append(result)
                self.logger.info(f"Completed {test_name}: {result.average_time:.3f}s avg, {result.success_rate:.1%} success")
            except Exception as e:
                self.logger.error(f"Benchmark test {test_name} failed: {e}")

        # Concurrency tests
        if include_concurrency_tests:
            concurrency_tests = [
                ("Concurrent Searches", lambda: self._benchmark_concurrent_operations("search_papers")),
                ("Mixed Concurrent Operations", self._benchmark_mixed_concurrent_operations),
            ]

            for test_name, test_func in concurrency_tests:
                try:
                    result = await test_func()
                    result.test_name = test_name
                    suite.tests.append(result)
                    self.logger.info(f"Completed {test_name}: {result.average_time:.3f}s avg, {result.success_rate:.1%} success")
                except Exception as e:
                    self.logger.error(f"Benchmark test {test_name} failed: {e}")

        # Stress tests (optional)
        if include_stress_tests:
            stress_tests = [
                ("High Volume Search", self._benchmark_high_volume_search),
                ("Large Result Sets", self._benchmark_large_result_sets),
                ("Memory Stress Test", self._benchmark_memory_stress),
            ]

            for test_name, test_func in stress_tests:
                try:
                    result = await test_func()
                    result.test_name = test_name
                    suite.tests.append(result)
                    self.logger.info(f"Completed {test_name}: {result.average_time:.3f}s avg, {result.success_rate:.1%} success")
                except Exception as e:
                    self.logger.error(f"Benchmark test {test_name} failed: {e}")

        # Calculate overall metrics
        suite.total_duration = time.time() - start_time
        if suite.tests:
            suite.overall_success_rate = statistics.mean(test.success_rate for test in suite.tests)

        self.benchmark_history.append(suite)
        self.logger.info(f"Benchmark suite completed in {suite.total_duration:.2f}s")

        return suite

    async def _benchmark_simple_search(self, iterations: int = 10) -> BenchmarkResult:
        """Benchmark basic search functionality."""
        queries = [
            "machine learning",
            "neural networks",
            "deep learning",
            "artificial intelligence",
            "natural language processing",
            "computer vision",
            "reinforcement learning",
            "transformer models",
            "graph neural networks",
            "federated learning"
        ]

        return await self._run_benchmark_test(
            test_function=lambda q: app.call_tool("search_papers", {
                "query": q,
                "max_results": 5,
                "sources": "arxiv"
            }),
            test_inputs=queries[:iterations],
            test_name="Simple Search"
        )

    async def _benchmark_paper_details(self, iterations: int = 10) -> BenchmarkResult:
        """Benchmark paper details retrieval."""
        # Use common arXiv IDs that should exist
        paper_ids = [
            "1706.03762",  # Attention is All You Need
            "1512.03385",  # ResNet
            "1409.1556",   # GAN
            "1301.3781",   # Word2Vec
            "1810.04805",  # BERT
            "2005.14165",  # GPT-3
            "1412.6980",   # Adam optimizer
            "1502.03167",  # Batch normalization
            "1506.02142",  # Spatial transformer networks
            "1611.07004",  # CycleGAN
        ]

        return await self._run_benchmark_test(
            test_function=lambda pid: app.call_tool("get_paper_details", {
                "paper_id": pid,
                "source": "arxiv"
            }),
            test_inputs=paper_ids[:iterations],
            test_name="Paper Details"
        )

    async def _benchmark_author_search(self, iterations: int = 8) -> BenchmarkResult:
        """Benchmark author search functionality."""
        authors = [
            "Geoffrey Hinton",
            "Yann LeCun",
            "Yoshua Bengio",
            "Andrew Ng",
            "Fei-Fei Li",
            "Ian Goodfellow",
            "Kaiming He",
            "Andrej Karpathy"
        ]

        return await self._run_benchmark_test(
            test_function=lambda author: app.call_tool("search_author_papers", {
                "author_name": author,
                "max_results": 5,
                "sources": "arxiv"
            }),
            test_inputs=authors[:iterations],
            test_name="Author Search"
        )

    async def _benchmark_citations(self, iterations: int = 5) -> BenchmarkResult:
        """Benchmark citation retrieval."""
        # Use DOIs that should have citations in Semantic Scholar
        paper_ids = [
            "10.48550/arXiv.1706.03762",  # Transformer
            "10.48550/arXiv.1512.03385",  # ResNet
            "10.48550/arXiv.1409.1556",   # GAN
            "10.48550/arXiv.1301.3781",   # Word2Vec
            "10.48550/arXiv.1810.04805",  # BERT
        ]

        return await self._run_benchmark_test(
            test_function=lambda pid: app.call_tool("get_citations", {
                "paper_id": pid,
                "source": "semantic_scholar",
                "max_results": 10
            }),
            test_inputs=paper_ids[:iterations],
            test_name="Citations"
        )

    async def _benchmark_cache_operations(self, iterations: int = 20) -> BenchmarkResult:
        """Benchmark cache operations."""
        cache_tests = ["stats", "cleanup"] * (iterations // 2)

        return await self._run_benchmark_test(
            test_function=lambda action: app.call_tool("manage_cache", {"action": action}),
            test_inputs=cache_tests,
            test_name="Cache Operations"
        )

    async def _benchmark_advanced_search(self, iterations: int = 8) -> BenchmarkResult:
        """Benchmark advanced search functionality."""
        search_params = [
            {"title": "neural networks", "year_start": 2020, "max_results": 5},
            {"author": "hinton", "keywords": "deep learning", "max_results": 5},
            {"abstract": "transformer", "year_start": 2017, "max_results": 5},
            {"venue": "NeurIPS", "year_start": 2021, "max_results": 5},
            {"keywords": "computer vision", "year_start": 2019, "year_end": 2023, "max_results": 5},
            {"title": "GAN", "author": "goodfellow", "max_results": 5},
            {"abstract": "reinforcement learning", "year_start": 2018, "max_results": 5},
            {"keywords": "natural language processing", "year_start": 2020, "max_results": 5}
        ]

        return await self._run_benchmark_test(
            test_function=lambda params: app.call_tool("advanced_search_papers", {
                **params,
                "sources": "arxiv"
            }),
            test_inputs=search_params[:iterations],
            test_name="Advanced Search"
        )

    async def _benchmark_recommendations(self, iterations: int = 6) -> BenchmarkResult:
        """Benchmark recommendation functionality."""
        seed_queries = [
            "attention is all you need",
            "resnet deep residual learning",
            "generative adversarial networks",
            "bert pre-training transformers",
            "alexnet imagenet classification",
            "word2vec distributed representations"
        ]

        return await self._run_benchmark_test(
            test_function=lambda query: app.call_tool("recommend_papers", {
                "seed_papers": query,
                "method": "content",
                "max_recommendations": 5,
                "sources": "arxiv"
            }),
            test_inputs=seed_queries[:iterations],
            test_name="Recommendations"
        )

    async def _benchmark_query_building(self, iterations: int = 10) -> BenchmarkResult:
        """Benchmark query building functionality."""
        natural_queries = [
            "find papers about machine learning by Geoffrey Hinton",
            "recent deep learning papers from 2023",
            "computer vision papers using transformers",
            "natural language processing with attention mechanisms",
            "reinforcement learning in robotics applications",
            "graph neural networks for social networks",
            "federated learning privacy preserving",
            "few-shot learning computer vision",
            "adversarial examples neural networks",
            "transfer learning domain adaptation"
        ]

        return await self._run_benchmark_test(
            test_function=lambda query: app.call_tool("build_search_query", {
                "natural_language": query,
                "target_source": "arxiv"
            }),
            test_inputs=natural_queries[:iterations],
            test_name="Query Building"
        )

    async def _benchmark_export(self, iterations: int = 5) -> BenchmarkResult:
        """Benchmark bibliography export functionality."""
        export_queries = [
            "machine learning neural networks",
            "computer vision deep learning",
            "natural language processing",
            "reinforcement learning",
            "graph neural networks"
        ]

        return await self._run_benchmark_test(
            test_function=lambda query: app.call_tool("export_bibliography", {
                "papers": query,
                "format": "bibtex"
            }),
            test_inputs=export_queries[:iterations],
            test_name="Bibliography Export"
        )

    async def _benchmark_concurrent_operations(self, tool_name: str, iterations: int = 20) -> BenchmarkResult:
        """Benchmark concurrent operations."""
        queries = [
            "machine learning", "deep learning", "neural networks", "AI", "computer vision",
            "NLP", "reinforcement learning", "transformers", "GAN", "CNN"
        ] * (iterations // 10 + 1)

        tasks = []
        start_time = time.time()
        memory_before = self._get_memory_usage()

        # Create concurrent tasks
        for i in range(iterations):
            query = queries[i]
            if tool_name == "search_papers":
                task = app.call_tool("search_papers", {
                    "query": query,
                    "max_results": 5,
                    "sources": "arxiv"
                })
            else:
                continue  # Add other tools as needed

            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        memory_after = self._get_memory_usage()

        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        error_count = len(results) - len(successful_results)
        success_rate = len(successful_results) / len(results) if results else 0

        total_time = end_time - start_time
        avg_time = total_time / iterations if iterations > 0 else 0
        rps = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            test_name="Concurrent Operations",
            total_time=total_time,
            average_time=avg_time,
            min_time=0,  # Concurrent operations don't have individual timing
            max_time=0,
            median_time=avg_time,
            requests_per_second=rps,
            success_rate=success_rate,
            error_count=error_count,
            memory_usage_mb=memory_after - memory_before,
            cache_hit_rate=await self._get_cache_hit_rate()
        )

    async def _benchmark_mixed_concurrent_operations(self) -> BenchmarkResult:
        """Benchmark mixed concurrent operations."""
        tasks = []
        start_time = time.time()
        memory_before = self._get_memory_usage()

        # Mix of different operations
        operations = [
            ("search_papers", {"query": "machine learning", "max_results": 5}),
            ("search_papers", {"query": "deep learning", "max_results": 5}),
            ("manage_cache", {"action": "stats"}),
            ("search_author_papers", {"author_name": "hinton", "max_results": 5}),
            ("search_papers", {"query": "neural networks", "max_results": 5}),
            ("build_search_query", {"natural_language": "find AI papers", "target_source": "arxiv"}),
            ("search_papers", {"query": "computer vision", "max_results": 5}),
            ("manage_cache", {"action": "stats"}),
        ]

        for tool_name, params in operations:
            task = app.call_tool(tool_name, params)
            tasks.append(task)

        # Execute concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        memory_after = self._get_memory_usage()

        # Analyze results
        successful_results = [r for r in results if not isinstance(r, Exception)]
        error_count = len(results) - len(successful_results)
        success_rate = len(successful_results) / len(results) if results else 0

        total_time = end_time - start_time
        iterations = len(operations)
        avg_time = total_time / iterations if iterations > 0 else 0
        rps = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            test_name="Mixed Concurrent Operations",
            total_time=total_time,
            average_time=avg_time,
            min_time=0,
            max_time=0,
            median_time=avg_time,
            requests_per_second=rps,
            success_rate=success_rate,
            error_count=error_count,
            memory_usage_mb=memory_after - memory_before,
            cache_hit_rate=await self._get_cache_hit_rate()
        )

    async def _benchmark_high_volume_search(self) -> BenchmarkResult:
        """Stress test with high volume searches."""
        queries = [f"search query {i}" for i in range(50)]

        return await self._run_benchmark_test(
            test_function=lambda q: app.call_tool("search_papers", {
                "query": q,
                "max_results": 10,
                "sources": "arxiv"
            }),
            test_inputs=queries,
            test_name="High Volume Search"
        )

    async def _benchmark_large_result_sets(self) -> BenchmarkResult:
        """Benchmark with large result sets."""
        queries = [
            "machine learning",
            "deep learning",
            "neural networks"
        ]

        return await self._run_benchmark_test(
            test_function=lambda q: app.call_tool("search_papers", {
                "query": q,
                "max_results": 50,
                "sources": "arxiv"
            }),
            test_inputs=queries,
            test_name="Large Result Sets"
        )

    async def _benchmark_memory_stress(self) -> BenchmarkResult:
        """Memory stress test with multiple concurrent large operations."""
        tasks = []
        start_time = time.time()
        memory_before = self._get_memory_usage()

        # Create memory-intensive tasks
        for i in range(10):
            task = app.call_tool("search_papers", {
                "query": f"stress test {i}",
                "max_results": 30,
                "sources": "arxiv,semantic_scholar"
            })
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        end_time = time.time()
        memory_after = self._get_memory_usage()

        successful_results = [r for r in results if not isinstance(r, Exception)]
        error_count = len(results) - len(successful_results)
        success_rate = len(successful_results) / len(results) if results else 0

        total_time = end_time - start_time
        iterations = len(tasks)
        avg_time = total_time / iterations if iterations > 0 else 0
        rps = iterations / total_time if total_time > 0 else 0

        return BenchmarkResult(
            test_name="Memory Stress Test",
            total_time=total_time,
            average_time=avg_time,
            min_time=0,
            max_time=0,
            median_time=avg_time,
            requests_per_second=rps,
            success_rate=success_rate,
            error_count=error_count,
            memory_usage_mb=memory_after - memory_before,
            cache_hit_rate=await self._get_cache_hit_rate()
        )

    async def _run_benchmark_test(
        self,
        test_function: Callable,
        test_inputs: List[Any],
        test_name: str
    ) -> BenchmarkResult:
        """Run a benchmark test with timing and error tracking."""
        times = []
        errors = 0
        memory_before = self._get_memory_usage()

        for test_input in test_inputs:
            start_time = time.time()
            try:
                result = await test_function(test_input)
                end_time = time.time()
                times.append(end_time - start_time)

                # Check if result indicates an error
                if isinstance(result, str) and ("error" in result.lower() or "failed" in result.lower()):
                    errors += 1

            except Exception as e:
                end_time = time.time()
                times.append(end_time - start_time)
                errors += 1
                self.logger.warning(f"Benchmark error in {test_name}: {e}")

        memory_after = self._get_memory_usage()

        # Calculate statistics
        if times:
            total_time = sum(times)
            avg_time = statistics.mean(times)
            min_time = min(times)
            max_time = max(times)
            median_time = statistics.median(times)
            rps = len(times) / total_time if total_time > 0 else 0
        else:
            total_time = avg_time = min_time = max_time = median_time = rps = 0

        success_rate = (len(test_inputs) - errors) / len(test_inputs) if test_inputs else 0

        return BenchmarkResult(
            test_name=test_name,
            total_time=total_time,
            average_time=avg_time,
            min_time=min_time,
            max_time=max_time,
            median_time=median_time,
            requests_per_second=rps,
            success_rate=success_rate,
            error_count=errors,
            memory_usage_mb=memory_after - memory_before,
            cache_hit_rate=await self._get_cache_hit_rate()
        )

    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except Exception:
            return 0.0

    async def _get_cache_hit_rate(self) -> float:
        """Get current cache hit rate."""
        try:
            if cache_manager:
                stats = await cache_manager.get_cache_stats()
                return stats.get("hit_rate", 0.0)
        except Exception:
            pass
        return 0.0

    def generate_report(self, suite: BenchmarkSuite) -> str:
        """Generate a comprehensive benchmark report."""
        report = []
        report.append(f"# Performance Benchmark Report")
        report.append(f"**Suite**: {suite.suite_name}")
        report.append(f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"**Total Duration**: {suite.total_duration:.2f} seconds")
        report.append(f"**Overall Success Rate**: {suite.overall_success_rate:.1%}")
        report.append("")

        report.append("## Test Results")
        report.append("")

        for test in suite.tests:
            report.append(f"### {test.test_name}")
            report.append(f"- **Average Time**: {test.average_time:.3f}s")
            report.append(f"- **Min/Max Time**: {test.min_time:.3f}s / {test.max_time:.3f}s")
            report.append(f"- **Median Time**: {test.median_time:.3f}s")
            report.append(f"- **Requests/Second**: {test.requests_per_second:.2f}")
            report.append(f"- **Success Rate**: {test.success_rate:.1%}")
            report.append(f"- **Error Count**: {test.error_count}")
            report.append(f"- **Memory Usage**: {test.memory_usage_mb:.2f} MB")
            report.append(f"- **Cache Hit Rate**: {test.cache_hit_rate:.1%}")
            report.append("")

        # Performance summary
        report.append("## Performance Summary")
        report.append("")

        if suite.tests:
            fastest_test = min(suite.tests, key=lambda t: t.average_time)
            slowest_test = max(suite.tests, key=lambda t: t.average_time)
            highest_rps = max(suite.tests, key=lambda t: t.requests_per_second)

            report.append(f"- **Fastest Operation**: {fastest_test.test_name} ({fastest_test.average_time:.3f}s avg)")
            report.append(f"- **Slowest Operation**: {slowest_test.test_name} ({slowest_test.average_time:.3f}s avg)")
            report.append(f"- **Highest Throughput**: {highest_rps.test_name} ({highest_rps.requests_per_second:.2f} RPS)")

            avg_memory = statistics.mean(t.memory_usage_mb for t in suite.tests)
            avg_cache_hit = statistics.mean(t.cache_hit_rate for t in suite.tests)

            report.append(f"- **Average Memory Usage**: {avg_memory:.2f} MB per test")
            report.append(f"- **Average Cache Hit Rate**: {avg_cache_hit:.1%}")

        report.append("")
        report.append("## Recommendations")
        report.append("")

        # Generate recommendations based on results
        recommendations = self._generate_performance_recommendations(suite)
        for rec in recommendations:
            report.append(f"- {rec}")

        return "\n".join(report)

    def _generate_performance_recommendations(self, suite: BenchmarkSuite) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        if not suite.tests:
            return ["No test results available for analysis."]

        # Analyze overall performance
        avg_success_rate = suite.overall_success_rate
        if avg_success_rate < 0.95:
            recommendations.append(f"Overall success rate is {avg_success_rate:.1%}. Investigate error patterns and improve error handling.")

        # Analyze cache performance
        cache_hit_rates = [t.cache_hit_rate for t in suite.tests if t.cache_hit_rate > 0]
        if cache_hit_rates:
            avg_cache_hit = statistics.mean(cache_hit_rates)
            if avg_cache_hit < 0.5:
                recommendations.append(f"Cache hit rate is low ({avg_cache_hit:.1%}). Consider increasing cache TTL or improving cache key generation.")

        # Analyze response times
        response_times = [t.average_time for t in suite.tests]
        if response_times:
            avg_response_time = statistics.mean(response_times)
            if avg_response_time > 3.0:
                recommendations.append(f"Average response time is high ({avg_response_time:.2f}s). Consider optimizing API calls or increasing concurrency.")

        # Analyze memory usage
        memory_usage = [t.memory_usage_mb for t in suite.tests if t.memory_usage_mb > 0]
        if memory_usage:
            avg_memory = statistics.mean(memory_usage)
            if avg_memory > 100:
                recommendations.append(f"High memory usage detected ({avg_memory:.1f} MB avg). Consider implementing memory optimization strategies.")

        # Specific test recommendations
        for test in suite.tests:
            if test.success_rate < 0.9:
                recommendations.append(f"{test.test_name} has low success rate ({test.success_rate:.1%}). Review error logs and improve reliability.")

            if test.average_time > 5.0:
                recommendations.append(f"{test.test_name} is slow ({test.average_time:.2f}s avg). Consider optimization or caching.")

        if not recommendations:
            recommendations.append("Performance looks good! All metrics are within acceptable ranges.")

        return recommendations

    def save_benchmark_results(self, suite: BenchmarkSuite, filename: str = None):
        """Save benchmark results to a JSON file."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        # Convert to serializable format
        suite_data = {
            "suite_name": suite.suite_name,
            "total_duration": suite.total_duration,
            "overall_success_rate": suite.overall_success_rate,
            "timestamp": datetime.now().isoformat(),
            "tests": [
                {
                    "test_name": test.test_name,
                    "total_time": test.total_time,
                    "average_time": test.average_time,
                    "min_time": test.min_time,
                    "max_time": test.max_time,
                    "median_time": test.median_time,
                    "requests_per_second": test.requests_per_second,
                    "success_rate": test.success_rate,
                    "error_count": test.error_count,
                    "memory_usage_mb": test.memory_usage_mb,
                    "cache_hit_rate": test.cache_hit_rate,
                    "timestamp": test.timestamp.isoformat()
                }
                for test in suite.tests
            ]
        }

        try:
            with open(filename, 'w') as f:
                json.dump(suite_data, f, indent=2)
            self.logger.info(f"Benchmark results saved to {filename}")
        except Exception as e:
            self.logger.error(f"Failed to save benchmark results: {e}")


# Global benchmark instance
performance_benchmark = PerformanceBenchmark()


async def run_quick_benchmark():
    """Run a quick benchmark for basic performance testing."""
    print("Running quick performance benchmark...")
    suite = await performance_benchmark.run_comprehensive_benchmark(
        include_stress_tests=False,
        include_concurrency_tests=True
    )

    report = performance_benchmark.generate_report(suite)
    print("\n" + "="*60)
    print(report)
    print("="*60)

    return suite


if __name__ == "__main__":
    """Run benchmark when called directly."""
    asyncio.run(run_quick_benchmark())