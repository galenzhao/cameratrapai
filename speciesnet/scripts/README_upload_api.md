# SpeciesNet Upload API

这个新的服务器实现提供了三种不同的predict接口，支持图片文件数据的上传。

## 启动服务器

```bash
python speciesnet/scripts/run_server_with_upload.py --port=8000 --model=your_model_name
```

## API 接口

### 1. 传统文件路径接口 `/predict`

使用文件路径进行预测，与原接口兼容。

**请求格式:**
```json
{
    "instances": [
        {
            "filepath": "path/to/image.jpg",
            "country": "USA",
            "admin1_region": "CA",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    ]
}
```

**使用示例:**
```bash
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{
         "instances": [
             {
                 "filepath": "test_data/african_elephants.jpg",
                 "country": "KEN"
             }
         ]
     }'
```

### 2. 文件上传接口 `/predict_upload`

支持直接上传图片文件。

**请求格式:**
- 使用 `multipart/form-data` 格式
- 支持多个图片文件上传
- 可选的地理信息参数

**参数:**
- `files`: 图片文件列表（必需）
- `country`: 国家代码（可选）
- `admin1_region`: 行政区代码（可选）
- `latitude`: 纬度（可选）
- `longitude`: 经度（可选）

**使用示例:**
```bash
curl -X POST "http://localhost:8000/predict_upload" \
     -F "files=@image1.jpg" \
     -F "files=@image2.jpg" \
     -F "country=USA" \
     -F "admin1_region=CA"
```

**Python 示例:**
```python
import requests

files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb'))
]

data = {
    'country': 'USA',
    'admin1_region': 'CA'
}

response = requests.post('http://localhost:8000/predict_upload', 
                        files=files, data=data)
print(response.json())
```

### 3. Base64编码接口 `/predict_base64`

支持Base64编码的图片数据。

**请求格式:**
```json
{
    "instances": [
        {
            "image_data": "base64_encoded_image_string",
            "country": "USA",
            "admin1_region": "CA",
            "latitude": 37.7749,
            "longitude": -122.4194
        }
    ]
}
```

**Python 示例:**
```python
import requests
import base64

# 读取图片并编码为base64
with open('image.jpg', 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

request_data = {
    "instances": [
        {
            "image_data": image_data,
            "country": "USA",
            "admin1_region": "CA"
        }
    ]
}

response = requests.post('http://localhost:8000/predict_base64', 
                        json=request_data)
print(response.json())
```

## 响应格式

所有接口都返回相同的响应格式：

```json
{
    "predictions": [
        {
            "filepath": "image_path_or_id",
            "failures": [],
            "country": "USA",
            "admin1_region": "CA",
            "classifications": {
                "classes": ["species1", "species2", "species3", "species4", "species5"],
                "scores": [0.95, 0.03, 0.01, 0.005, 0.005]
            },
            "detections": [
                {
                    "category": "1",
                    "label": "animal",
                    "conf": 0.98,
                    "bbox": [0.1, 0.2, 0.3, 0.4]
                }
            ],
            "prediction": "species1",
            "prediction_score": 0.95,
            "prediction_source": "classifier",
            "model_version": "v4.0.1a"
        }
    ]
}
```

## 健康检查

```bash
curl http://localhost:8000/health
```

返回:
```json
{
    "status": "healthy",
    "model": "your_model_name"
}
```

## 依赖要求

需要安装以下额外的依赖：

```bash
pip install fastapi uvicorn python-multipart
```

## 注意事项

1. **文件清理**: 上传的文件会在处理完成后自动删除
2. **图片格式**: 支持常见的图片格式（JPEG, PNG等）
3. **文件大小**: 建议单个文件不超过10MB
4. **并发处理**: 支持多个文件同时上传和处理
5. **错误处理**: 如果某个文件处理失败，会返回相应的错误信息

## 与原接口的区别

| 特性 | 原接口 | 新接口 |
|------|--------|--------|
| 文件路径 | ✅ | ✅ |
| 文件上传 | ❌ | ✅ |
| Base64编码 | ❌ | ✅ |
| 多文件支持 | ✅ | ✅ |
| 地理信息 | ✅ | ✅ |
| 自动文档 | ❌ | ✅ (FastAPI) |
| 健康检查 | ❌ | ✅ | 