#!/usr/bin/env python3
"""
测试 prefer_mode 功能的脚本
"""

import json
import requests

BASE_URL = "http://localhost:5201"
ADMIN_API_KEY = "your-admin-api-key"  # 需要配置实际的 admin key

headers = {
    "X-API-Key": ADMIN_API_KEY,
    "Content-Type": "application/json"
}


def test_create_account_with_prefer_mode():
    """测试创建账户时指定 prefer_mode"""

    # 测试 1: 创建 OAuth 偏好账户
    print("=== 测试 1: 创建 OAuth 偏好账户 ===")
    account_data = {
        "cookie_value": "test_cookie_oauth_prefer",
        "organization_uuid": "12345678-1234-1234-1234-123456789001",
        "capabilities": ["claude-3-5-sonnet"],
        "prefer_mode": "oauth"
    }

    response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json=account_data
    )

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"账户 UUID: {result['organization_uuid']}")
        print(f"认证类型: {result['auth_type']}")
        print(f"偏好模式: {result.get('prefer_mode', 'None')}")
    else:
        print(f"错误: {response.text}")

    print()

    # 测试 2: 创建 Web 偏好账户
    print("=== 测试 2: 创建 Web 偏好账户 ===")
    account_data = {
        "cookie_value": "test_cookie_web_prefer",
        "organization_uuid": "12345678-1234-1234-1234-123456789002",
        "capabilities": ["claude-3-5-sonnet"],
        "prefer_mode": "web"
    }

    response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json=account_data
    )

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"账户 UUID: {result['organization_uuid']}")
        print(f"认证类型: {result['auth_type']}")
        print(f"偏好模式: {result.get('prefer_mode', 'None')}")
    else:
        print(f"错误: {response.text}")

    print()

    # 测试 3: 创建自动模式账户
    print("=== 测试 3: 创建自动模式账户 ===")
    account_data = {
        "cookie_value": "test_cookie_auto",
        "organization_uuid": "12345678-1234-1234-1234-123456789003",
        "capabilities": ["claude-3-5-sonnet"]
        # 不指定 prefer_mode
    }

    response = requests.post(
        f"{BASE_URL}/api/accounts",
        headers=headers,
        json=account_data
    )

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"账户 UUID: {result['organization_uuid']}")
        print(f"认证类型: {result['auth_type']}")
        print(f"偏好模式: {result.get('prefer_mode', 'None')}")
    else:
        print(f"错误: {response.text}")


def test_list_accounts():
    """测试列出所有账户,查看 prefer_mode 字段"""
    print("\n=== 列出所有账户 ===")

    response = requests.get(
        f"{BASE_URL}/api/accounts",
        headers=headers
    )

    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        accounts = response.json()
        print(f"账户总数: {len(accounts)}\n")

        for account in accounts[:5]:  # 只显示前5个
            print(f"UUID: {account['organization_uuid']}")
            print(f"认证类型: {account['auth_type']}")
            print(f"偏好模式: {account.get('prefer_mode', 'None')}")
            print(f"Pro: {account['is_pro']}, Max: {account['is_max']}")
            print("-" * 50)
    else:
        print(f"错误: {response.text}")


def test_messages_api_with_header():
    """测试 messages API,检查响应头中的 X-Clove-Mode"""
    print("\n=== 测试 Messages API 响应头 ===")

    messages_data = {
        "model": "claude-sonnet-4-20250514",
        "messages": [
            {"role": "user", "content": "Hello!"}
        ],
        "max_tokens": 100,
        "stream": False
    }

    response = requests.post(
        f"{BASE_URL}/v1/messages",
        headers={
            "X-API-Key": ADMIN_API_KEY,  # 或使用普通 API key
            "Content-Type": "application/json"
        },
        json=messages_data
    )

    print(f"状态码: {response.status_code}")
    print(f"X-Clove-Mode 响应头: {response.headers.get('X-Clove-Mode', '未找到')}")

    if response.status_code == 200:
        print("✓ 请求成功")
    else:
        print(f"错误: {response.text}")


if __name__ == "__main__":
    print("开始测试 prefer_mode 功能\n")
    print("=" * 60)

    # 注意: 运行前请确保:
    # 1. Clove 服务正在运行 (http://localhost:5201)
    # 2. 已配置 ADMIN_API_KEY

    try:
        # test_create_account_with_prefer_mode()
        test_list_accounts()
        # test_messages_api_with_header()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 Clove 服务,请确保服务正在运行")
    except Exception as e:
        print(f"❌ 测试出错: {e}")

    print("\n" + "=" * 60)
    print("测试完成")
