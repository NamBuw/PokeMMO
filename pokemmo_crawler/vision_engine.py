import cv2
import mss
import numpy as np
import pytesseract
import time

class VisionEngine:
    def __init__(self):
        try:
            self.sct = mss.mss()
            self.monitor = self.sct.monitors[1] # Primary monitor by default
            self.has_display = True
        except Exception as e:
            print(f"WARNING: Running in headless environment. Screen capturing disabled. ({e})")
            self.sct = None
            self.has_display = False
            self.monitor = {'width': 1920, 'height': 1080}
        
        # PokeMMO Game Window Bounding Box (to be auto-detected or manually set)
        self.game_bbox = None 
        
        # Relative ROIs (Region of Interest) mapped as fractions of the game_bbox
        # (x_percent, y_percent, width_percent, height_percent)
        self.rois = {
            'enemy_name': (0.1, 0.05, 0.3, 0.08),
            'enemy_hp_bar': (0.15, 0.15, 0.25, 0.02),
            'chat_box': (0.05, 0.8, 0.4, 0.15),
            'combat_menu': (0.6, 0.75, 0.35, 0.2)
        }

    def capture_screen(self):
        """Captures the full primary monitor as a numpy array (BGR)."""
        if not self.has_display:
            # Return a blank mock frame (e.g. 1080p black image)
            return np.zeros((1080, 1920, 3), dtype=np.uint8)
            
        sct_img = self.sct.grab(self.monitor)
        # Convert to numpy array
        img = np.array(sct_img)
        # MSS captures in BGRA, convert to BGR for OpenCV
        return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

    def set_game_bbox(self, bbox: dict):
        """
        Manually set or auto-detect the game bounding box.
        bbox format: {'top': 100, 'left': 100, 'width': 800, 'height': 600}
        """
        self.game_bbox = bbox

    def get_roi_image(self, roi_name: str, frame=None):
        """
        Extracts a specific Region of Interest from the screen.
        """
        if self.game_bbox is None:
            # Fallback to full screen if game window not set
            self.game_bbox = {'top': 0, 'left': 0, 'width': self.monitor['width'], 'height': self.monitor['height']}
            
        if frame is None:
            frame = self.capture_screen()
            
        if roi_name not in self.rois:
            raise ValueError(f"Unknown ROI: {roi_name}")
            
        x_pct, y_pct, w_pct, h_pct = self.rois[roi_name]
        
        x = int(self.game_bbox['left'] + (self.game_bbox['width'] * x_pct))
        y = int(self.game_bbox['top'] + (self.game_bbox['height'] * y_pct))
        w = int(self.game_bbox['width'] * w_pct)
        h = int(self.game_bbox['height'] * h_pct)
        
        return frame[y:y+h, x:x+w]

    def read_text(self, roi_name: str, config='--psm 7') -> str:
        """
        Reads text from a specific ROI using Tesseract OCR.
        """
        roi_img = self.get_roi_image(roi_name)
        
        # Preprocessing for better OCR
        gray = cv2.cvtColor(roi_img, cv2.COLOR_BGR2GRAY)
        # Thresholding (binary)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
        
        text = pytesseract.image_to_string(thresh, config=config)
        return text.strip()

    def detect_shiny_star(self, frame=None) -> bool:
        """
        Uses template matching to search for the Shiny Star (★) icon.
        Requires a 'shiny_star_template.png' asset.
        """
        # Placeholder for template matching logic
        # For now, we rely on OCR checking for '★' or 'Shiny'
        name_text = self.read_text('enemy_name')
        chat_text = self.read_text('chat_box')
        
        if '★' in name_text or 'Shiny' in chat_text:
            return True
        return False

    def estimate_hp_percentage(self, roi_name='enemy_hp_bar', frame=None) -> float:
        """
        Estimates HP percentage by measuring the length of the green/yellow/red bar 
        relative to the total ROI width.
        """
        roi_img = self.get_roi_image(roi_name, frame)
        hsv = cv2.cvtColor(roi_img, cv2.COLOR_BGR2HSV)
        
        # Define color ranges for HP (Green, Yellow, Red)
        lower_green = np.array([35, 50, 50])
        upper_green = np.array([85, 255, 255])
        
        lower_yellow = np.array([20, 50, 50])
        upper_yellow = np.array([35, 255, 255])
        
        lower_red = np.array([0, 50, 50])
        upper_red = np.array([10, 255, 255])
        
        # Create masks
        mask_g = cv2.inRange(hsv, lower_green, upper_green)
        mask_y = cv2.inRange(hsv, lower_yellow, upper_yellow)
        mask_r = cv2.inRange(hsv, lower_red, upper_red)
        
        # Combine masks
        mask_hp = cv2.bitwise_or(mask_g, cv2.bitwise_or(mask_y, mask_r))
        
        # Calculate percentage of HP pixels vs width
        # This is a simplified estimation (counting colored pixels)
        total_hp_pixels = cv2.countNonZero(mask_hp)
        total_pixels = mask_hp.shape[0] * mask_hp.shape[1]
        
        # If no HP detected, return 0
        if total_pixels == 0: return 0.0
        
        return (total_hp_pixels / total_pixels) * 100.0

if __name__ == "__main__":
    print("Initializing Vision Engine...")
    engine = VisionEngine()
    print("Capturing test screen...")
    img = engine.capture_screen()
    print(f"Captured screen of shape: {img.shape}")
