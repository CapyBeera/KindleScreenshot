import cv2
import numpy as np
import time
import os
import mss
import pyautogui
from PIL import Image
from datetime import datetime

COMMON_RESOLUTIONS = [
    (1366, 768),
    (1920, 1080),
    (2560, 1440),
    (3840, 2160),
]

def select_resolution():
    print("Select your monitor resolution:")
    print("1 - 1366x768 (HD)")
    print("2 - 1920x1080 (Full HD)")
    print("3 - 2560x1440 (QHD)")
    print("4 - 3840x2160 (4K)")
    print("5 - Custom")
    while True:
        option = input("Option (1-5): ").strip()
        if option in ['1', '2', '3', '4']:
            resolution = COMMON_RESOLUTIONS[int(option)-1]
            break
        elif option == '5':
            try:
                width = int(input("Monitor width (e.g. 1920): "))
                height = int(input("Monitor height (e.g. 1080): "))
                if width > 0 and height > 0:
                    resolution = (width, height)
                    break
                else:
                    print("Invalid values.")
            except ValueError:
                print("Please enter valid numeric values.")
        else:
            print("Invalid option.")
    print(f"Selected resolution: {resolution[0]}x{resolution[1]}")
    return resolution

def detect_book_area(monitor_resolution):
    DEFAULT_AREA = {'x': 1281, 'y': 145, 'width': 1349, 'height': 1880}

    print("Do you want to use a default area, enter coordinates, or select manually?")
    print(f"1 - Use default area ({DEFAULT_AREA})")
    print("2 - Enter coordinates manually")
    print("3 - Manual selection with mouse")
    print("4 - Exit")

    option = input("Enter option (1, 2, 3 or 4): ").strip()

    if option == '4':
        print("Exiting without selecting an area.")
        return None, None

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        detected_resolution = (monitor['width'], monitor['height'])

        screenshot = sct.grab(monitor)
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        if detected_resolution != monitor_resolution:
            img = cv2.resize(img, monitor_resolution)
            detected_resolution = monitor_resolution

        if option == '1':
            book_area = DEFAULT_AREA.copy()
            print(f"Using default area: {book_area}")

        elif option == '2':
            print("Enter the coordinates and size of the area to capture.")
            try:
                x = int(input("x (left): "))
                y = int(input("y (top): "))
                w = int(input("width: "))
                h = int(input("height: "))
                if x < 0 or y < 0 or w <= 0 or h <= 0:
                    print("Invalid values. Aborting.")
                    return None, detected_resolution
                book_area = {'x': x, 'y': y, 'width': w, 'height': h}
                print(f"Entered area: {book_area}")
            except Exception as e:
                print(f"Error entering coordinates: {e}")
                return None, detected_resolution

        elif option == '3':
            print("Please select the book area manually (a window will open).")
            roi = cv2.selectROI("Select the book area and press ENTER", img, fromCenter=False, showCrosshair=True)
            cv2.destroyWindow("Select the book area and press ENTER")
            if sum(roi) == 0:
                print("No area selected. Aborting.")
                return None, detected_resolution
            x, y, w, h = roi
            book_area = {'x': x, 'y': y, 'width': w, 'height': h}
            print("\n--- Fine Adjustment ---")
            print("You can enter positive or negative values in pixels.")
            print("To stop adjusting, type 'N' and press ENTER.")
            while True:
                print(f"\nCurrent area: x={x}, y={y}, w={w}, h={h}")
                crop = img[y:y + h, x:x + w]
                cv2.imwrite("adjusted_area.png", crop)
                print("Preview updated (captured area only): adjusted_area.png")
                side = input("\nWhich side to adjust? (left, right, top, bottom) or 'N' to finish: ").strip().lower()
                if side == "n":
                    break
                elif side not in ['left', 'right', 'top', 'bottom']:
                    print("Invalid side. Use: left, right, top, bottom or N.")
                    continue
                value_input = input(f"Adjustment amount for {side} (in pixels): ").strip()
                if not value_input.lstrip("-").isdigit():
                    print("Invalid value. Must be an integer.")
                    continue
                adjustment = int(value_input)
                if side == 'left':
                    new_x = x + adjustment
                    new_w = w - adjustment
                    if new_x < 0 or new_w <= 0:
                        print("Invalid adjustment: Area out of bounds or width <= 0")
                        continue
                    x = new_x
                    w = new_w
                elif side == 'right':
                    new_w = w - adjustment
                    if new_w <= 0:
                        print("Invalid adjustment: width <= 0")
                        continue
                    w = new_w
                elif side == 'top':
                    new_y = y + adjustment
                    new_h = h - adjustment
                    if new_y < 0 or new_h <= 0:
                        print("Invalid adjustment: Area out of bounds or height <= 0")
                        continue
                    y = new_y
                    h = new_h
                elif side == 'bottom':
                    new_h = h - adjustment
                    if new_h <= 0:
                        print("Invalid adjustment: height <= 0")
                        continue
                    h = new_h
            book_area = {'x': x, 'y': y, 'width': w, 'height': h}
            print(f"\nFinal adjusted area: {book_area}")
            print("Final image saved as adjusted_area.png")
        else:
            print("Invalid option. Exiting.")
            return None, None

        return book_area, detected_resolution

def capture_page_mss(area, detected_resolution):
    with mss.mss() as sct:
        monitor = {
            "top": area['y'],
            "left": area['x'],
            "width": area['width'],
            "height": area['height']
        }
        screenshot = sct.grab(monitor)
        img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return img

def capture_pages(num_pages, delay_between_pages, monitor_resolution):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = f"kindle_captures_{timestamp}"
    os.makedirs(folder, exist_ok=True)
    print(f"Captures will be saved in: {os.path.abspath(folder)}")
    book_area, detected_resolution = detect_book_area(monitor_resolution)
    if not book_area:
        print("Could not continue without detecting the book area.")
        return
    print("Starting captures in 10 seconds...")
    time.sleep(10)
    for i in range(num_pages):
        capture = capture_page_mss(book_area, detected_resolution)
        file_path = os.path.join(folder, f"page_{i+1:04d}.png")
        capture.save(file_path, format='PNG', compress_level=0)
        print(f"Capture {i+1}/{num_pages} saved: {file_path}")
        if i < num_pages - 1:
            pyautogui.press('right')
            time.sleep(delay_between_pages)

def main():
    print("=== Automatic Kindle Page Capturer ===")
    print("IMPORTANT: Make sure the Kindle window is open and visible")
    print("           with the book on the first page you want to capture.")
    monitor_resolution = select_resolution()
    with mss.mss() as sct:
        monitor_info = sct.monitors[0]
        print("\nSystem information:")
        print(f"Detected resolution: {monitor_info['width']}x{monitor_info['height']}")
        print(f"Selected resolution: {monitor_resolution[0]}x{monitor_resolution[1]}")
    while True:
        try:
            num_pages = int(input("\nNumber of pages to capture: "))
            if num_pages > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    while True:
        try:
            delay = float(input("Delay between pages (seconds, recommended 1.5): ") or "1.5")
            if delay > 0:
                break
            else:
                print("Please enter a positive number.")
        except ValueError:
            print("Please enter a valid number.")
    print("\nSwitch to the Kindle window and place the book on the first page.")
    print("The process has started.")
    capture_pages(num_pages, delay, monitor_resolution)
    print("\nProcess completed!")

if __name__ == "__main__":
    main()
