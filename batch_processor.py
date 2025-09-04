#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小红书内容批量处理程序
自动处理图片和文档，生成小红书风格的内容
"""

import os
import sys
import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any
import cv2
import numpy as np
from docx import Document
from dotenv import load_dotenv

# 加载环境变量 (从配置与提示词文件夹)
load_dotenv("配置与提示词/.env")

# 导入AI服务
from 配置与提示词.ai_services import rewrite_content, generate_title


class ImageProcessor:
    """图像处理类"""
    
    @staticmethod
    def apply_filter(image: np.ndarray, filter_type: str = "natural") -> np.ndarray:
        """应用图像滤镜"""
        if filter_type == "natural":
            # 增强对比度和饱和度
            contrast_factor = 1.1
            image = cv2.convertScaleAbs(image, alpha=contrast_factor, beta=0)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            h, s, v = cv2.split(hsv)
            s = cv2.add(s, 10)
            s = np.clip(s, 0, 255)
            hsv = cv2.merge([h, s, v])
            filtered_image = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        elif filter_type == "warm":
            increase_brightness = 10
            image = cv2.convertScaleAbs(image, alpha=1.05, beta=increase_brightness)
            b, g, r = cv2.split(image)
            r = cv2.add(r, 5)
            r = np.clip(r, 0, 255)
            filtered_image = cv2.merge([b, g, r])
        else:
            raise ValueError(f"不支持的滤镜类型: {filter_type}")
        
        return filtered_image
    
    @staticmethod
    def crop_bottom(image: np.ndarray) -> np.ndarray:
        """裁剪底部，保留上面的19/20"""
        height = image.shape[0]
        crop_height = int(height * 19 / 20)
        return image[:crop_height, :]
    
    @staticmethod
    def add_border(image: np.ndarray, border_size: int = 20, 
                  color: tuple = (255, 255, 255)) -> np.ndarray:
        """添加边框"""
        return cv2.copyMakeBorder(
            image, border_size, border_size, border_size, border_size,
            cv2.BORDER_CONSTANT, value=color
        )
    
    @staticmethod
    def read_image_chinese_path(image_path: str) -> Optional[np.ndarray]:
        """读取包含中文路径的图像文件"""
        try:
            return cv2.imdecode(
                np.fromfile(image_path, dtype=np.uint8), 
                cv2.IMREAD_UNCHANGED
            )
        except Exception as e:
            print(f"读取图像失败 {image_path}: {e}")
            return None
    
    @staticmethod
    def write_image_chinese_path(image_path: str, image: np.ndarray) -> bool:
        """保存图像到包含中文的路径"""
        try:
            is_success, buffer = cv2.imencode(".jpg", image)
            if is_success:
                with open(image_path, "wb") as f:
                    f.write(buffer)
                return True
            return False
        except Exception as e:
            print(f"保存图像失败 {image_path}: {e}")
            return False


class DocumentReader:
    """文档读取类"""
    
    @staticmethod
    def read_txt_file(file_path: str) -> Optional[str]:
        """读取TXT文件，自动处理编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'big5']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read().strip()
            except UnicodeDecodeError:
                continue
        print(f"无法识别文件编码: {file_path}")
        return None
    
    @staticmethod
    def read_docx_file(file_path: str) -> Optional[str]:
        """读取DOCX文件内容"""
        try:
            doc = Document(file_path)
            content = []
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    content.append(paragraph.text)
            return '\n'.join(content)
        except Exception as e:
            print(f"读取DOCX文件失败 {file_path}: {e}")
            return None
    
    @staticmethod
    def read_md_file(file_path: str) -> Optional[str]:
        """读取Markdown文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"读取MD文件失败 {file_path}: {e}")
            return None


def load_prompt_template(filename: str) -> str:
    """加载提示词模板"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"加载提示词文件失败 {filename}: {e}")
        return ""


class BatchProcessor:
    """批量处理器"""
    
    def __init__(self):
        """初始化批量处理器"""
        self.image_processor = ImageProcessor()
        self.document_reader = DocumentReader()
        
        # 支持的文件格式
        self.image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        self.doc_extensions = {'.txt', '.docx', '.md'}
        
        # 加载提示词模板
        self.rewrite_prompt = load_prompt_template("配置与提示词/小红书改写.txt")
        self.title_prompt = load_prompt_template("配置与提示词/小红书咪蒙标题生成.txt")
        
        # 加载自定义路径配置
        self.input_folder_path = os.getenv("INPUT_FOLDER_PATH", ".")
        self.output_folder_path = os.getenv("OUTPUT_FOLDER_PATH", "新生成文件")
        self.processed_folder_path = os.getenv("PROCESSED_FOLDER_PATH", "已处理文件")
        
        # 加载延迟配置
        try:
            self.folder_delay_seconds = float(os.getenv("FOLDER_DELAY_SECONDS", "5.0"))
        except (ValueError, TypeError):
            self.folder_delay_seconds = 5.0
            
        print(f"📁 配置路径:")
        print(f"   输入路径: {self.input_folder_path}")
        print(f"   输出路径: {self.output_folder_path}")
        print(f"   已处理路径: {self.processed_folder_path}")
        print(f"⏱️ 处理延迟: {self.folder_delay_seconds}秒")
    
    def create_safe_filename(self, title: str) -> str:
        """创建安全的文件名，并清理前后标点符号"""
        # 清理前后的标点符号
        punctuation = '《》""''「」【】()（）[]［］<>《》，。！？；：、,."\'!?;:~`'
        title = title.strip()
        while title and title[0] in punctuation:
            title = title[1:]
        while title and title[-1] in punctuation:
            title = title[:-1]
        
        # 清理文件名中的非法字符
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            title = title.replace(char, '')
        return title.strip()[:100]  # 限制长度
    
    def validate_input_folder(self, folder_path: str) -> Dict[str, Any]:
        """验证输入文件夹结构"""
        folder = Path(folder_path)
        result = {
            'valid': False,
            'images': [],
            'document': None,
            'errors': []
        }
        
        if not folder.exists():
            result['errors'].append('文件夹不存在')
            return result
        
        # 查找图片文件
        for file in folder.iterdir():
            if file.suffix.lower() in self.image_extensions:
                result['images'].append(str(file))
        
        # 查找文档文件
        doc_files = []
        for pattern in ['正文.txt', '正文.docx', '正文.md']:
            doc_file = folder / pattern
            if doc_file.exists():
                doc_files.append(str(doc_file))
        
        if len(doc_files) > 1:
            result['errors'].append('发现多个正文文件')
        elif len(doc_files) == 1:
            result['document'] = doc_files[0]
        else:
            result['errors'].append('未找到正文文件')
        
        if not result['images']:
            result['errors'].append('未找到图片文件')
        
        result['valid'] = len(result['errors']) == 0
        return result
    
    def process_images(self, image_paths: List[str], output_dir: Path) -> int:
        """处理图片文件"""
        processed_count = 0
        
        for image_path in image_paths:
            print(f"处理图片: {image_path}")
            
            # 读取图片
            image = self.image_processor.read_image_chinese_path(image_path)
            if image is None:
                continue
            
            # 应用滤镜
            filtered_image = self.image_processor.apply_filter(image, "natural")
            
            # 裁剪底部
            cropped_image = self.image_processor.crop_bottom(filtered_image)
            
            # 添加边框
            bordered_image = self.image_processor.add_border(cropped_image, 20)
            
            # 保存处理后的图片
            filename = Path(image_path).name
            output_path = output_dir / filename
            
            if self.image_processor.write_image_chinese_path(str(output_path), bordered_image):
                print(f"✅ 图片处理成功: {output_path}")
                processed_count += 1
            else:
                print(f"❌ 图片保存失败: {output_path}")
        
        return processed_count
    
    def read_document(self, doc_path: str) -> Optional[str]:
        """读取文档内容"""
        file_ext = Path(doc_path).suffix.lower()
        
        if file_ext == '.txt':
            return self.document_reader.read_txt_file(doc_path)
        elif file_ext == '.docx':
            return self.document_reader.read_docx_file(doc_path)
        elif file_ext == '.md':
            return self.document_reader.read_md_file(doc_path)
        else:
            print(f"不支持的文档格式: {file_ext}")
            return None
    
    def create_output_folder(self, title: str) -> Path:
        """基于标题创建输出文件夹"""
        # 使用配置的输出路径
        generated_dir = Path(self.output_folder_path)
        generated_dir.mkdir(exist_ok=True)
        
        safe_title = self.create_safe_filename(title)
        output_path = generated_dir / safe_title
        
        # 如果文件夹已存在，添加数字后缀
        counter = 1
        original_path = output_path
        while output_path.exists():
            output_path = Path(f"{original_path}_{counter}")
            counter += 1
        
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path
    
    def move_source_folder(self, source_folder: str) -> bool:
        """移动源文件夹到已处理文件目录"""
        try:
            # 使用配置的已处理文件路径
            processed_dir = Path(self.processed_folder_path)
            processed_dir.mkdir(exist_ok=True)
            
            source_path = Path(source_folder)
            target_path = processed_dir / source_path.name
            
            # 如果目标路径已存在，添加数字后缀
            counter = 1
            original_target = target_path
            while target_path.exists():
                target_path = Path(f"{original_target}_{counter}")
                counter += 1
            
            # 移动文件夹
            import shutil
            shutil.move(str(source_path), str(target_path))
            print(f"✅ 源文件夹已移动到: {target_path}")
            return True
            
        except Exception as e:
            print(f"❌ 移动源文件夹失败: {e}")
            return False
    
    def process_folder_with_retry(self, folder_path: str, max_retries: int = 3) -> bool:
        """带重试机制的文件夹处理"""
        for attempt in range(max_retries):
            print(f"\n🔄 开始处理文件夹: {folder_path} (尝试 {attempt + 1}/{max_retries})")
            
            try:
                # 验证文件夹结构
                validation = self.validate_input_folder(folder_path)
                if not validation['valid']:
                    print(f"❌ 文件夹验证失败: {', '.join(validation['errors'])}")
                    return False  # 文件夹结构问题不重试
                
                # 读取文档内容
                print("📖 读取文档内容...")
                original_content = self.read_document(validation['document'])
                if not original_content:
                    raise Exception("文档读取失败")
                
                print(f"✅ 原始内容长度: {len(original_content)} 字符")
                
                # AI改写内容
                print("🤖 AI改写内容中...")
                rewritten_content = rewrite_content(original_content, self.rewrite_prompt)
                if not rewritten_content:
                    raise Exception("内容改写失败")
                
                print("✅ 内容改写完成")
                
                # 生成标题
                print("🎯 生成标题中...")
                title = generate_title(rewritten_content, self.title_prompt)
                if not title:
                    raise Exception("标题生成失败")
                
                print(f"✅ 生成标题: {title}")
                
                # 创建输出文件夹
                output_dir = self.create_output_folder(title)
                print(f"📁 创建输出文件夹: {output_dir}")
                
                # 处理图片
                print("🖼️ 处理图片中...")
                processed_images = self.process_images(validation['images'], output_dir)
                if processed_images == 0:
                    raise Exception("图片处理失败")
                print(f"✅ 处理了 {processed_images} 张图片")
                
                # 保存改写后的内容
                content_file = output_dir / "正文.md"
                with open(content_file, 'w', encoding='utf-8') as f:
                    f.write(rewritten_content)
                print(f"✅ 保存改写内容: {content_file}")
                
                # 保存标题
                title_file = output_dir / "标题.txt"
                with open(title_file, 'w', encoding='utf-8') as f:
                    f.write(title)
                print(f"✅ 保存标题: {title_file}")
                
                # 移动源文件夹到已处理文件
                print("📦 移动源文件夹...")
                if not self.move_source_folder(folder_path):
                    print("⚠️ 源文件夹移动失败，但处理已完成")
                
                print(f"🎉 文件夹处理完成: {folder_path}")
                return True
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"❌ 文件夹处理最终失败: {e}")
                    return False
                else:
                    print(f"⚠️ 处理失败，准备重试 (尝试 {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)  # 短暂等待后重试
        
        return False
    
    def run(self):
        """运行批量处理"""
        print("🚀 小红书内容批量处理程序启动")
        print("=" * 50)
        
        # 使用配置的输入路径
        input_dir = Path(self.input_folder_path)
        if not input_dir.exists():
            print(f"❌ 输入路径不存在: {input_dir}")
            return
        
        # 获取输入目录下的所有子文件夹，排除特殊文件夹
        exclude_folders = {'.', '..', '__pycache__', '.cursor', '配置与提示词',
                          Path(self.processed_folder_path).name, 
                          Path(self.output_folder_path).name}
        subfolders = [f for f in input_dir.iterdir() 
                     if f.is_dir() and f.name not in exclude_folders and not f.name.startswith('.')]
        
        if not subfolders:
            print("❌ 未找到任何子文件夹")
            return
        
        print(f"📂 发现 {len(subfolders)} 个子文件夹")
        
        success_count = 0
        total_count = len(subfolders)
        
        for i, folder in enumerate(subfolders, 1):
            print(f"\n{'='*50}")
            print(f"📋 进度: {i}/{total_count}")
            
            if self.process_folder_with_retry(str(folder)):
                success_count += 1
            else:
                print(f"⚠️ 跳过文件夹: {folder}")
            
            # 在处理文件夹之间添加延迟，避免频繁API调用
            if i < total_count and self.folder_delay_seconds > 0:
                print(f"⏳ 等待 {self.folder_delay_seconds} 秒后处理下一个文件夹...")
                time.sleep(self.folder_delay_seconds)
        
        print(f"\n{'='*50}")
        print(f"🏁 批量处理完成!")
        print(f"✅ 成功处理: {success_count}/{total_count} 个文件夹")
        print(f"❌ 失败: {total_count - success_count} 个文件夹")


def main():
    """主函数"""
    try:
        processor = BatchProcessor()
        processor.run()
    except KeyboardInterrupt:
        print("\n⏹️ 用户中断程序")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
