#!/usr/bin/env python3
"""Test script for the new upload API endpoints."""

import base64
import json
import requests
from pathlib import Path

# 服务器配置
SERVER_URL = "http://localhost:8000"

def test_health_check():
    """测试健康检查接口"""
    print("Testing health check...")
    try:
        response = requests.get(f"{SERVER_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_predict_filepath():
    """测试传统文件路径接口"""
    print("\nTesting predict filepath endpoint...")
    
    # 使用测试数据中的图片
    test_image = "test_data/african_elephants.jpg"
    if not Path(test_image).exists():
        print(f"Test image {test_image} not found, skipping test")
        return False
    
    request_data = {
        "instances": [
            {
                "filepath": test_image,
                "country": "KEN"
            }
        ]
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/predict", json=request_data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Predictions: {len(result.get('predictions', []))}")
            if result.get('predictions'):
                pred = result['predictions'][0]
                print(f"Prediction: {pred.get('prediction', 'N/A')}")
                print(f"Score: {pred.get('prediction_score', 'N/A')}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_predict_upload():
    """测试文件上传接口"""
    print("\nTesting predict upload endpoint...")
    
    # 使用测试数据中的图片
    test_image = "test_data/african_elephants.jpg"
    if not Path(test_image).exists():
        print(f"Test image {test_image} not found, skipping test")
        return False
    
    try:
        with open(test_image, 'rb') as f:
            files = [('files', f)]
            data = {'country': 'KEN'}
            
            response = requests.post(f"{SERVER_URL}/predict_upload", 
                                   files=files, data=data)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Predictions: {len(result.get('predictions', []))}")
            if result.get('predictions'):
                pred = result['predictions'][0]
                print(f"Prediction: {pred.get('prediction', 'N/A')}")
                print(f"Score: {pred.get('prediction_score', 'N/A')}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_predict_base64():
    """测试Base64编码接口"""
    print("\nTesting predict base64 endpoint...")
    
    # 使用测试数据中的图片
    test_image = "test_data/african_elephants.jpg"
    if not Path(test_image).exists():
        print(f"Test image {test_image} not found, skipping test")
        return False
    
    try:
        # 读取图片并编码为base64
        with open(test_image, 'rb') as f:
            image_data = base64.b64encode(f.read()).decode('utf-8')
        
        request_data = {
            "instances": [
                {
                    "image_data": image_data,
                    "country": "KEN"
                }
            ]
        }
        
        response = requests.post(f"{SERVER_URL}/predict_base64", 
                               json=request_data)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Predictions: {len(result.get('predictions', []))}")
            if result.get('predictions'):
                pred = result['predictions'][0]
                print(f"Prediction: {pred.get('prediction', 'N/A')}")
                print(f"Score: {pred.get('prediction_score', 'N/A')}")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_multiple_files():
    """测试多文件上传"""
    print("\nTesting multiple files upload...")
    
    # 使用测试数据中的多个图片
    test_images = [
        "test_data/african_elephants.jpg",
        "test_data/american_black_bear.jpg"
    ]
    
    existing_images = [img for img in test_images if Path(img).exists()]
    if len(existing_images) < 2:
        print(f"Need at least 2 test images, found {len(existing_images)}, skipping test")
        return False
    
    try:
        files = []
        for img_path in existing_images[:2]:  # 只使用前两个
            with open(img_path, 'rb') as f:
                files.append(('files', f))
        
        data = {'country': 'USA'}
        
        response = requests.post(f"{SERVER_URL}/predict_upload", 
                               files=files, data=data)
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"Predictions: {len(result.get('predictions', []))}")
            for i, pred in enumerate(result.get('predictions', [])):
                print(f"Image {i+1}: {pred.get('prediction', 'N/A')} (score: {pred.get('prediction_score', 'N/A')})")
        else:
            print(f"Error: {response.text}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """运行所有测试"""
    print("SpeciesNet Upload API Test Suite")
    print("=" * 40)
    
    tests = [
        ("Health Check", test_health_check),
        ("Filepath Predict", test_predict_filepath),
        ("Upload Predict", test_predict_upload),
        ("Base64 Predict", test_predict_base64),
        ("Multiple Files", test_multiple_files),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append((test_name, False))
    
    # 打印测试结果摘要
    print("\n" + "="*50)
    print("TEST RESULTS SUMMARY")
    print("="*50)
    
    passed = 0
    for test_name, success in results:
        status = "PASS" if success else "FAIL"
        print(f"{test_name:<20} : {status}")
        if success:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(results)} tests")
    
    if passed == len(results):
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed. Please check the server and try again.")

if __name__ == "__main__":
    main() 