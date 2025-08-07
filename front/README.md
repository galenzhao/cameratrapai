# 动物识别与标注系统

这是一个简单的HTML页面，可以上传图片到指定的API进行动物识别，并在图片上显示检测到的边界框（bbox）标注。

## 功能特性

- 🖼️ 支持拖拽上传图片
- 🔍 自动调用动物识别API
- 📊 显示识别结果和置信度
- 🎯 在图片上绘制检测框标注
- 📱 响应式设计，支持移动设备

## 使用方法

1. 直接在浏览器中打开 `index.html` 文件
2. 点击"选择图片"按钮或拖拽图片到上传区域
3. 系统会自动调用API进行识别
4. 识别完成后会显示：
   - 图片上的检测框标注
   - 识别结果列表（包含物种名称和置信度）

## API配置

当前配置的API地址为：`/predict_upload`

如需修改API地址，请编辑 `index.html` 文件中的 `API_URL` 变量：

```javascript
const API_URL = '你的API地址';
```

## API响应格式

系统期望的API响应格式如下：

```json
{
    "predictions": [
        {
            "classifications": {
                "classes": ["物种分类信息"],
                "scores": [置信度分数]
            },
            "detections": [
                {
                    "category": "类别",
                    "label": "标签",
                    "conf": 置信度,
                    "bbox": [x, y, width, height]
                }
            ]
        }
    ]
}
```

## 技术说明

- 使用原生JavaScript实现，无需额外依赖
- 支持所有现代浏览器
- 自动处理图片缩放和边界框坐标转换
- 包含错误处理和加载状态显示

## 注意事项

- 确保API服务器支持CORS跨域请求
- 图片文件大小建议不超过10MB
- 支持的图片格式：JPG、PNG、GIF等常见格式
