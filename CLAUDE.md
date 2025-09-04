# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个小红书内容批量处理程序，用于自动化处理图片和文档内容，生成符合小红书平台风格的内容。主要功能包括图片滤镜处理、AI内容改写、标题生成和批量文件管理。

## 常用命令

### 运行主程序
```bash
python batch_processor.py
```

### 安装依赖
```bash
pip install -r requirements.txt
```

### 配置环境变量
```bash
cp 配置与提示词/env_example.txt 配置与提示词/.env
# 编辑配置与提示词/.env 文件设置API密钥
```

## 核心架构

### 主要类结构
- `ImageProcessor`: 图像处理类，负责滤镜、裁剪、边框等操作
- `DocumentReader`: 文档读取类，支持TXT、DOCX、MD格式
- `BatchProcessor`: 批量处理器主类，协调整个处理流程

### AI服务架构
- `配置与提示词/ai_services.py`: 统一AI服务接口，支持多模型降级
  - `rewrite_content()`: 内容改写服务（OpenRouter → DeepSeek降级）
  - `generate_title()`: 标题生成服务（Kimi专用模型）

### 处理流程
1. 扫描输入目录下的子文件夹
2. 验证每个文件夹的结构（图片+文档）
3. 图片处理：应用natural滤镜 → 裁剪底部19/20 → 添加白色边框
4. 文档读取：支持多种编码格式自动识别
5. AI改写：使用多模型降级机制改写内容为小红书风格
   - 主要模型：OpenRouter + DeepSeek-R1-0528
   - 备用模型：SiliconFlow + DeepSeek-V3.1（自动降级）
6. 标题生成：使用Kimi模型生成吸引人的标题
   - 专用模型：Moonshot + Kimi-K2-0711-Preview
7. 输出保存：创建新文件夹保存处理结果

## 配置管理

### 环境变量配置
所有配置在 `配置与提示词/.env` 文件中管理：

**必需API配置**：
- `OPENROUTER_API_KEY`: OpenRouter API密钥（主要内容改写）
- `SILICONFLOW_API_KEY`: SiliconFlow API密钥（DeepSeek备用模型）
- `MOONSHOT_API_KEY`: Moonshot API密钥（Kimi标题生成）

**可选路径配置**：
- `INPUT_FOLDER_PATH`: 输入文件夹路径（默认：当前目录）
- `OUTPUT_FOLDER_PATH`: 输出文件夹路径（默认：新生成文件）
- `PROCESSED_FOLDER_PATH`: 已处理文件路径（默认：已处理文件）
- `FOLDER_DELAY_SECONDS`: 文件夹处理间隔（默认：5.0秒）

### 提示词模板
- `配置与提示词/小红书改写.txt`: 内容改写提示词
- `配置与提示词/小红书咪蒙标题生成.txt`: 标题生成提示词

## 文件格式支持

### 图片格式
- 输入：.jpg, .jpeg, .png, .bmp, .tiff
- 输出：统一为.jpg格式

### 文档格式
- 输入：.txt, .docx, .md
- 输出：.md格式

## 错误处理和重试机制

### API调用重试
- 指数退避算法（基础延迟×2^attempt + 随机抖动）
- 最大重试3次
- 自动处理网络错误和API限制

### 文件夹处理重试
- 每个文件夹最多重试3次
- 跳过结构错误的文件夹
- 保持处理进度，支持断点续传

## 开发规范

### 代码风格
- 遵循PEP 8规范，使用4空格缩进
- 类型注解（typing模块）
- 中文注释，英文错误提示
- 函数单一职责，详细docstring

### 文件操作
- 使用OpenCV处理中文文件名路径
- pathlib进行路径管理
- 自动编码检测（UTF-8, GBK, GB2312, BIG5）

### API集成
- **多模型架构**：OpenRouter + SiliconFlow + Moonshot
- **自动降级机制**：主模型失败时自动切换到备用模型
- **统一服务接口**：通过`ai_services.py`提供一致的调用方式
- **错误处理**：完整的异常处理和重试机制
- **请求优化**：合理的temperature和max_tokens参数设置

## 输出结构

```
输入目录/
├── 子文件夹1/
│   ├── 图片1.jpg
│   ├── 正文.txt
├── 新生成文件/
│   ├── 生成的标题/
│   │   ├── 图片1.jpg (处理后的图片)
│   │   ├── 正文.md (改写后的内容)
│   │   └── 标题.txt (生成的标题)
└── 已处理文件/
    └── 子文件夹1/ (原始文件夹备份)
```

## 性能优化

### 内存管理
- 及时释放图像数组
- 批量处理时控制并发
- 处理延迟避免API限制

### 容错机制
- 单个文件失败不影响整体流程
- 详细的错误日志和进度显示
- 自动跳过已处理的文件夹