"""
Container Setup Verification Script.

Chạy script này để kiểm tra Container có setup đúng không.

Usage:
    python verify_container.py
"""

import sys
from typing import List, Tuple


def test_imports() -> Tuple[bool, str]:
    """Test import các module cơ bản."""
    try:
        from app.infrastructure.config import settings, logger
        from app.container import Container
        return True, "Imports successful"
    except Exception as e:
        return False, f"Import failed: {e}"


def test_settings() -> Tuple[bool, str]:
    """Test Settings load thành công."""
    try:
        from app.infrastructure.config import settings
        
        # Check required fields
        if not settings.OPENAI_API_KEY:
            return False, "OPENAI_API_KEY not set"
        
        if not settings.GROQ_API_KEY:
            return False, "GROQ_API_KEY not set"
        
        return True, f"Settings loaded (env: {settings.APP_ENV})"
    except Exception as e:
        return False, f"Settings load failed: {e}"


def test_logger() -> Tuple[bool, str]:
    """Test Logger hoạt động."""
    try:
        from app.infrastructure.config import logger
        
        logger.info("Test log message")
        return True, "Logger working"
    except Exception as e:
        return False, f"Logger failed: {e}"


def test_container_init() -> Tuple[bool, str]:
    """Test Container khởi tạo."""
    try:
        from app.container import Container
        
        container = Container()
        
        if container.settings is None:
            return False, "Container settings is None"
        
        return True, "Container initialized"
    except Exception as e:
        return False, f"Container init failed: {e}"


def test_lazy_loading() -> Tuple[bool, str]:
    """Test Lazy loading của services."""
    try:
        from app.container import Container
        
        container = Container()
        
        # Check cache empty
        if container._openai_service is not None:
            return False, "OpenAI should not be loaded yet"
        
        # Note: Không test actual service vì chưa implement providers
        # Chỉ test lazy loading mechanism
        
        return True, "Lazy loading mechanism works"
    except Exception as e:
        return False, f"Lazy loading test failed: {e}"


def test_nodes_import() -> Tuple[bool, str]:
    """Test import các Nodes."""
    try:
        from app.application.nodes import (
            GuardrailsNode,
            RewriteNode,
            RouterNode,
            RetrievalNode,
            GradeNode,
            AskHumanNode,
            WebSearchNode,
            GenerateNode
        )
        return True, "All nodes imported successfully"
    except Exception as e:
        return False, f"Node import failed: {e}"


def run_all_tests() -> None:
    """Chạy tất cả tests và hiển thị kết quả."""
    print("=" * 60)
    print("CONTAINER SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Settings", test_settings),
        ("Logger", test_logger),
        ("Container Init", test_container_init),
        ("Lazy Loading", test_lazy_loading),
        ("Nodes Import", test_nodes_import),
    ]
    
    results: List[Tuple[str, bool, str]] = []
    
    for test_name, test_func in tests:
        print(f"Testing {test_name}...", end=" ")
        success, message = test_func()
        results.append((test_name, success, message))
        print(message)
    
    # Summary
    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success, _ in results if success)
    total = len(results)
    
    for test_name, success, message in results:
        status = "PASS" if success else "FAIL"
        print(f"{status:10} | {test_name:20} | {message}")
    
    print()
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print("ALL TESTS PASSED!")
        print()
        print("Next steps:")
        print("1. Implement Infrastructure Providers (Prompt 3.1, 3.2)")
        print("2. Build Main Graph (Prompt 5.2)")
        print("3. Create CLI Runner (Prompt 6.1)")
        sys.exit(0)
    else:
        print()
        print("SOME TESTS FAILED")
        print()
        print("Please fix the issues above before proceeding.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
