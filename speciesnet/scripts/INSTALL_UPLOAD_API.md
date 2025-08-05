# SpeciesNet Upload API 安装和使用说明

## 安装依赖

### 方法1: 使用项目的可选依赖（推荐）

```bash
# 安装包含服务器依赖的版本
pip install "speciesnet[server]"

# 或者安装所有依赖
pip install "speciesnet[all]"
```

### 方法2: 手动安装依赖

```bash
pip install fastapi uvicorn python-multipart
```

## 启动服务器

### 基本启动

```bash
python speciesnet/scripts/run_server_with_upload.py
```

### 自定义配置启动

```bash
python speciesnet/scripts/run_server_with_upload.py \
    --port=8080 \
    --host=0.0.0.0 \
    --model=your_model_name \
    --geofence=True \
    --extra_fields=field1,field2
```

### 参数说明

- `--port`: 服务器端口（默认: 8000）
- `--host`: 服务器主机（默认: 0.0.0.0）
- `--model`: 模型名称（默认: 使用DEFAULT_MODEL）
- `--geofence`: 是否启用地理围栏（默认: True）
- `--extra_fields`: 额外的字段列表，用逗号分隔

## 测试接口

### 1. 健康检查

```bash
curl http://localhost:8000/health
```

### 2. 运行完整测试套件

```bash
# 确保服务器正在运行
python speciesnet/scripts/test_upload_api.py
```

### 3. 手动测试各个接口

#### 文件路径接口
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

#### 文件上传接口
```bash
curl -X POST "http://localhost:8000/predict_upload" \
     -F "files=@test_data/african_elephants.jpg" \
     -F "country=KEN"
```

#### Base64编码接口
```bash
# 首先将图片转换为base64
python -c "
import base64
with open('test_data/african_elephants.jpg', 'rb') as f:
    data = base64.b64encode(f.read()).decode('utf-8')
    print('Base64 data length:', len(data))
"

# 然后使用curl发送请求（需要替换实际的base64数据）
curl -X POST "http://localhost:8000/predict_base64" \
     -H "Content-Type: application/json" \
     -d '{
         "instances": [
             {
                 "image_data": "YOUR_BASE64_DATA_HERE",
                 "country": "KEN"
             }
         ]
     }'
```

## API文档

启动服务器后，可以访问自动生成的API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 常见问题

### 1. 端口被占用

```bash
# 使用不同的端口
python speciesnet/scripts/run_server_with_upload.py --port=8080
```

### 2. 模型加载失败

确保模型路径正确，或者使用Kaggle/HuggingFace模型标识符：

```bash
# 使用Kaggle模型
python speciesnet/scripts/run_server_with_upload.py --model="kaggle:google/speciesnet-v4-0-1a"

# 使用HuggingFace模型
python speciesnet/scripts/run_server_with_upload.py --model="hf:google/speciesnet-v4-0-1a"
```

### 3. 依赖安装失败

如果遇到依赖安装问题，可以尝试：

```bash
# 升级pip
pip install --upgrade pip

# 安装编译工具（如果需要）
pip install wheel setuptools

# 重新安装
pip install "speciesnet[server]"
```

### 4. 文件上传失败

检查文件格式和大小：

- 支持的格式：JPEG, PNG, GIF等常见图片格式
- 建议文件大小：小于10MB
- 确保文件是有效的图片文件

### 5. 内存不足

如果处理大图片时遇到内存问题：

- 减小图片尺寸
- 使用较小的batch_size
- 增加服务器内存

## 性能优化

### 1. 多进程模式

```bash
# 使用多进程处理（需要更多内存）
python speciesnet/scripts/run_server_with_upload.py --workers_per_device=4
```

### 2. GPU加速

确保安装了CUDA版本的PyTorch：

```bash
# 检查GPU是否可用
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### 3. 批量处理

对于大量图片，建议使用批量上传而不是单个上传，以提高效率。

## 监控和日志

服务器会输出详细的日志信息，包括：

- 模型加载状态
- 请求处理时间
- 错误信息
- 内存使用情况

可以通过日志来监控服务器性能和诊断问题。 