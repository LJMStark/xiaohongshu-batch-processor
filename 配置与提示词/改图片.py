import cv2
import os
import numpy as np

def apply_filter(image, filter_type="natural"):
    if filter_type == "natural":
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
    elif filter_type == "cool":
        b, g, r = cv2.split(image)
        b = cv2.add(b, 5)
        b = np.clip(b, 0, 255)
        filtered_image = cv2.merge([b, g, r])
    elif filter_type == "soft":
        blur = cv2.GaussianBlur(image, (3, 3), 0)
        alpha = 0.9
        filtered_image = cv2.addWeighted(image, alpha, blur, 1 - alpha, 0)
    elif filter_type == "bright":
        filtered_image = cv2.convertScaleAbs(image, alpha=1.1, beta=10)
    elif filter_type == "clarity":
        kernel = np.array([[-1, -1, -1],
                           [-1, 9, -1],
                           [-1, -1, -1]])
        filtered_image = cv2.filter2D(image, -1, kernel)
        filtered_image = np.clip(filtered_image, 0, 255)
    elif filter_type == "grayscale":
        filtered_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif filter_type == "negative":
        filtered_image = cv2.bitwise_not(image)
    else:
        raise ValueError("Unsupported filter type")
    return filtered_image

def crop_bottom(image):
    height = image.shape[0]
    crop_height = int(height * 19 / 20)  # 保留上面的19/20
    return image[:crop_height, :]

def add_border(image, border_size=10, color=(255, 255, 255)):
    bordered_image = cv2.copyMakeBorder(image, border_size, border_size, border_size, border_size, cv2.BORDER_CONSTANT, value=color)
    return bordered_image

def batch_apply_filter(root_folder, filter_type="sepia", border_size=10, border_color=()):
    processed_count = 0
    error_count = 0
    for dirpath, dirnames, filenames in os.walk(root_folder):
        # Skip the 'filtered_images' folder if it exists
        if 'filtered_images' in dirpath:
            continue

        # 检查当前文件夹中是否有需要处理的图片
        images_to_process = [f for f in filenames if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))]
        if not images_to_process:
            continue  # 如果没有图片，则跳过该文件夹

        # 只有在需要处理图片时才创建filtered_images文件夹
        output_folder = os.path.join(dirpath, "filtered_images")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
            print(f"Created output folder: {output_folder}")

        for filename in images_to_process:
            image_path = os.path.join(dirpath, filename)
            try:
                image = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
                if image is None:
                    raise IOError(f"Unable to read {filename}")

                filtered_image = apply_filter(image, filter_type)

                if filter_type == "grayscale":
                    filtered_image = cv2.cvtColor(filtered_image, cv2.COLOR_GRAY2BGR)

                # 在添加边框前裁剪底部
                cropped_image = crop_bottom(filtered_image)
                bordered_image = add_border(cropped_image, border_size, border_color)

                output_path = os.path.join(output_folder, filename)
                print(f"Attempting to save to: {output_path}")

                is_success, buffer = cv2.imencode(".jpg", bordered_image)
                if is_success:
                    with open(output_path, "wb") as f:
                        f.write(buffer)
                    print(f"Successfully saved: {output_path}")
                    processed_count += 1
                else:
                    print(f"Failed to encode image: {output_path}")
                    error_count += 1

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                error_count += 1

    print(f"Processing completed. Processed {processed_count} images. Encountered {error_count} errors.")

if __name__ == "__main__":
    root_folder = os.getcwd()
    filter_type = "natural"  # 可选择 "natural", "warm", "cool", "soft", "bright", "clarity", "grayscale", "negative"
    border_size = 20
    border_color = (255, 255, 255)

    batch_apply_filter(root_folder, filter_type, border_size, border_color)
    print("Batch processing completed.")
