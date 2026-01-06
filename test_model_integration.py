"""
测试前端模型选择和后端API集成
验证豆包模型是否能在前端选择并正确调用
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from api_server import invoke_ark_model

async def test_model_integration():
    """测试不同模型的集成"""
    print("=" * 60)
    print("测试模型集成")
    print("=" * 60)
    
    test_prompt = "请简要介绍一下单摆实验的原理。"
    
    # 测试的模型列表
    models_to_test = [
        "doubao-seed-1-6-lite-251015",
        "glm-4.7",
        "thudm/glm-z1-9b-0414",
        "qwen/qwen3-8b"
    ]
    
    results = {}
    
    for model_name in models_to_test:
        print(f"\n{'=' * 60}")
        print(f"测试模型: {model_name}")
        print(f"{'=' * 60}")
        
        try:
            response = await invoke_ark_model(test_prompt, model_name=model_name, max_retries=2, timeout=60)
            
            if response:
                print(f"✓ 模型 {model_name} 调用成功")
                print(f"响应长度: {len(response)} 字符")
                print(f"响应内容预览: {response[:100]}...")
                results[model_name] = {"status": "success", "response": response}
            else:
                print(f"✗ 模型 {model_name} 调用失败: 无响应")
                results[model_name] = {"status": "failed", "error": "无响应"}
                
        except Exception as e:
            print(f"✗ 模型 {model_name} 调用失败: {str(e)}")
            results[model_name] = {"status": "failed", "error": str(e)}
    
    # 汇总结果
    print(f"\n{'=' * 60}")
    print("测试结果汇总")
    print(f"{'=' * 60}")
    
    success_count = 0
    for model_name, result in results.items():
        status_icon = "✓" if result["status"] == "success" else "✗"
        print(f"{status_icon} {model_name}: {result['status']}")
        if result["status"] == "success":
            success_count += 1
    
    print(f"\n成功: {success_count}/{len(models_to_test)}")
    
    return success_count == len(models_to_test)

if __name__ == "__main__":
    success = asyncio.run(test_model_integration())
    sys.exit(0 if success else 1)