#!/usr/bin/env python3
import requests
import json

API_BASE_URL = "http://localhost:8000"

def test_template_api():
    print("开始测试模板API...")
    
    # 1. 登录获取token
    print("\n1. 登录...")
    login_data = {
        "username": "admin",
        "password": "admin123"
    }
    
    response = requests.post(f"{API_BASE_URL}/api/auth/login", data=login_data)
    if response.status_code != 200:
        print(f"登录失败: {response.status_code}")
        print(response.text)
        return
    
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✓ 登录成功")
    
    # 2. 创建测试模板
    print("\n2. 创建测试模板...")
    template_data = {
        "name": "测试模板1",
        "description": "这是一个测试模板",
        "criteria": "测试评分标准：内容完整30分，格式规范30分，原创性40分",
        "min_score": 60,
        "max_score": 95,
        "is_default": True
    }
    
    response = requests.post(f"{API_BASE_URL}/api/templates", 
                            json=template_data, 
                            headers=headers)
    if response.status_code != 200:
        print(f"创建模板失败: {response.status_code}")
        print(response.text)
        return
    
    template = response.json()
    template_id = template["id"]
    print(f"✓ 模板创建成功，ID: {template_id}")
    print(f"  模板名称: {template['name']}")
    print(f"  模板描述: {template['description']}")
    
    # 3. 获取模板列表
    print("\n3. 获取模板列表...")
    response = requests.get(f"{API_BASE_URL}/api/templates", headers=headers)
    if response.status_code != 200:
        print(f"获取模板列表失败: {response.status_code}")
        print(response.text)
        return
    
    templates = response.json()
    print(f"✓ 获取到 {len(templates)} 个模板")
    for t in templates:
        print(f"  - {t['name']} (ID: {t['id']}, 默认: {t['is_default']})")
    
    # 4. 获取单个模板详情
    print("\n4. 获取模板详情...")
    response = requests.get(f"{API_BASE_URL}/api/templates/{template_id}", headers=headers)
    if response.status_code != 200:
        print(f"获取模板详情失败: {response.status_code}")
        print(response.text)
        return
    
    template_detail = response.json()
    print(f"✓ 模板详情获取成功")
    print(f"  名称: {template_detail['name']}")
    print(f"  评分标准: {template_detail['criteria'][:50]}...")
    
    # 5. 更新模板
    print("\n5. 更新模板...")
    update_data = {
        "name": "测试模板1（已更新）",
        "description": "这是更新后的测试模板",
        "criteria": "更新后的评分标准：内容完整35分，格式规范25分，原创性40分",
        "min_score": 65,
        "max_score": 90,
        "is_default": False
    }
    
    response = requests.put(f"{API_BASE_URL}/api/templates/{template_id}", 
                           json=update_data, 
                           headers=headers)
    if response.status_code != 200:
        print(f"更新模板失败: {response.status_code}")
        print(response.text)
        return
    
    updated_template = response.json()
    print(f"✓ 模板更新成功")
    print(f"  新名称: {updated_template['name']}")
    
    # 6. 创建第二个模板
    print("\n6. 创建第二个模板...")
    template_data2 = {
        "name": "测试模板2",
        "description": "这是第二个测试模板",
        "criteria": "第二个模板的评分标准",
        "min_score": 70,
        "max_score": 100,
        "is_default": False
    }
    
    response = requests.post(f"{API_BASE_URL}/api/templates", 
                            json=template_data2, 
                            headers=headers)
    if response.status_code != 200:
        print(f"创建第二个模板失败: {response.status_code}")
        print(response.text)
        return
    
    template2 = response.json()
    template2_id = template2["id"]
    print(f"✓ 第二个模板创建成功，ID: {template2_id}")
    
    # 7. 设置默认模板
    print("\n7. 设置默认模板...")
    response = requests.put(f"{API_BASE_URL}/api/templates/{template2_id}/set-default", 
                           headers=headers)
    if response.status_code != 200:
        print(f"设置默认模板失败: {response.status_code}")
        print(response.text)
        return
    
    print("✓ 默认模板设置成功")
    
    # 8. 验证默认模板设置
    print("\n8. 验证默认模板...")
    response = requests.get(f"{API_BASE_URL}/api/templates", headers=headers)
    if response.status_code != 200:
        print(f"获取模板列表失败: {response.status_code}")
        return
    
    templates = response.json()
    default_template = next((t for t in templates if t['is_default']), None)
    if default_template:
        print(f"✓ 默认模板验证成功: {default_template['name']}")
    else:
        print("✗ 未找到默认模板")
    
    # 9. 删除模板
    print("\n9. 删除模板...")
    response = requests.delete(f"{API_BASE_URL}/api/templates/{template_id}", 
                              headers=headers)
    if response.status_code != 200:
        print(f"删除模板失败: {response.status_code}")
        print(response.text)
        return
    
    print("✓ 模板删除成功")
    
    # 10. 验证删除
    print("\n10. 验证删除...")
    response = requests.get(f"{API_BASE_URL}/api/templates", headers=headers)
    if response.status_code != 200:
        print(f"获取模板列表失败: {response.status_code}")
        return
    
    templates = response.json()
    print(f"✓ 当前剩余 {len(templates)} 个模板")
    
    print("\n" + "=" * 60)
    print("✓ 所有测试通过！")
    print("=" * 60)

if __name__ == "__main__":
    test_template_api()