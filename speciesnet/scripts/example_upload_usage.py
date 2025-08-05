#!/usr/bin/env python3
"""Example script demonstrating how to use the new upload API endpoints."""

import base64
import json
import requests
from pathlib import Path
from typing import List, Dict, Any

class SpeciesNetUploadClient:
    """Client for interacting with SpeciesNet Upload API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
    
    def health_check(self) -> Dict[str, Any]:
        """Check server health."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def predict_filepath(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict using file paths."""
        request_data = {"instances": instances}
        response = requests.post(f"{self.base_url}/predict", json=request_data)
        response.raise_for_status()
        return response.json()
    
    def predict_upload(self, 
                      image_paths: List[str], 
                      country: str = None,
                      admin1_region: str = None,
                      latitude: float = None,
                      longitude: float = None) -> Dict[str, Any]:
        """Predict using uploaded files."""
        files = []
        for image_path in image_paths:
            with open(image_path, 'rb') as f:
                files.append(('files', f))
        
        data = {}
        if country:
            data['country'] = country
        if admin1_region:
            data['admin1_region'] = admin1_region
        if latitude is not None:
            data['latitude'] = latitude
        if longitude is not None:
            data['longitude'] = longitude
        
        response = requests.post(f"{self.base_url}/predict_upload", 
                               files=files, data=data)
        response.raise_for_status()
        return response.json()
    
    def predict_base64(self, instances: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Predict using base64 encoded images."""
        request_data = {"instances": instances}
        response = requests.post(f"{self.base_url}/predict_base64", json=request_data)
        response.raise_for_status()
        return response.json()
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Encode an image file to base64 string."""
        with open(image_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')

def print_predictions(result: Dict[str, Any]):
    """Pretty print prediction results."""
    print(f"Found {len(result.get('predictions', []))} predictions:")
    print("-" * 50)
    
    for i, pred in enumerate(result.get('predictions', [])):
        print(f"Image {i+1}:")
        
        if 'failures' in pred:
            print(f"  ❌ Failures: {pred['failures']}")
            continue
        
        if 'prediction' in pred:
            print(f"  🎯 Prediction: {pred['prediction']}")
            print(f"  📊 Score: {pred['prediction_score']:.3f}")
            print(f"  🔧 Source: {pred['prediction_source']}")
        
        if 'classifications' in pred:
            print(f"  📋 Top classifications:")
            classes = pred['classifications']['classes']
            scores = pred['classifications']['scores']
            for j, (cls, score) in enumerate(zip(classes, scores)):
                print(f"    {j+1}. {cls}: {score:.3f}")
        
        if 'detections' in pred:
            print(f"  🎯 Detections:")
            for det in pred['detections']:
                print(f"    - {det['label']} (confidence: {det['conf']:.3f})")
        
        print()

def main():
    """Main example function."""
    print("SpeciesNet Upload API Example")
    print("=" * 40)
    
    # Initialize client
    client = SpeciesNetUploadClient()
    
    # Check server health
    try:
        health = client.health_check()
        print(f"✅ Server is healthy: {health}")
    except Exception as e:
        print(f"❌ Server health check failed: {e}")
        print("Make sure the server is running on http://localhost:8000")
        return
    
    # Test data paths
    test_images = [
        "test_data/african_elephants.jpg",
        "test_data/american_black_bear.jpg",
        "test_data/domestic_dog.jpg"
    ]
    
    # Filter existing images
    existing_images = [img for img in test_images if Path(img).exists()]
    if not existing_images:
        print("❌ No test images found. Please ensure test_data directory contains images.")
        return
    
    print(f"📁 Using test images: {existing_images}")
    print()
    
    # Example 1: File path prediction
    print("1️⃣ File Path Prediction")
    print("-" * 30)
    try:
        instances = [
            {
                "filepath": existing_images[0],
                "country": "KEN"
            }
        ]
        result = client.predict_filepath(instances)
        print_predictions(result)
    except Exception as e:
        print(f"❌ File path prediction failed: {e}")
    
    # Example 2: File upload prediction
    print("2️⃣ File Upload Prediction")
    print("-" * 30)
    try:
        result = client.predict_upload(
            image_paths=[existing_images[0]],
            country="KEN"
        )
        print_predictions(result)
    except Exception as e:
        print(f"❌ File upload prediction failed: {e}")
    
    # Example 3: Base64 prediction
    print("3️⃣ Base64 Prediction")
    print("-" * 30)
    try:
        image_data = client.encode_image_to_base64(existing_images[0])
        instances = [
            {
                "image_data": image_data,
                "country": "KEN"
            }
        ]
        result = client.predict_base64(instances)
        print_predictions(result)
    except Exception as e:
        print(f"❌ Base64 prediction failed: {e}")
    
    # Example 4: Multiple files with location
    print("4️⃣ Multiple Files with Location")
    print("-" * 30)
    try:
        result = client.predict_upload(
            image_paths=existing_images[:2],  # Use first 2 images
            country="USA",
            admin1_region="CA",
            latitude=37.7749,
            longitude=-122.4194
        )
        print_predictions(result)
    except Exception as e:
        print(f"❌ Multiple files prediction failed: {e}")
    
    print("🎉 Examples completed!")

if __name__ == "__main__":
    main() 