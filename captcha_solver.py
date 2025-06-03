import requests
import json
import random
import base64
from datetime import datetime, timedelta
import cv2
import numpy as np
from loguru import logger

def generate_slide_track(distance_x, distance_y=0, points_num=100, duration_ms=None):
    start_time = datetime.now()
    if duration_ms is None:
        duration_ms = random.randint(300, 800)
    end_time = start_time + timedelta(milliseconds=duration_ms)
    start_x, start_y = 0, 0
    end_x, end_y = distance_x, distance_y

    track_list = [{
        "x": start_x, "y": start_y, "type": "down", "t": 1500
    }]

    for i in range(1, points_num - 1):
        progress = i / (points_num - 2)
        ease_progress = progress * progress * (3 - 2 * progress)
        x = int(start_x + (end_x - start_x) * ease_progress) + random.randint(-2, 2)
        y = int(start_y + (end_y - start_y) * ease_progress) + random.randint(-1, 1)
        t = int(duration_ms * ease_progress)
        track_list.append({"x": x, "y": y, "type": "move", "t": t})

    track_list.append({"x": end_x, "y": end_y, "type": "up", "t": duration_ms})
    return {
        "startTime": start_time.isoformat(timespec='milliseconds') + 'Z',
        "endTime": end_time.isoformat(timespec='milliseconds') + 'Z',
        "duration_ms": duration_ms,
        "trackList": track_list
    }

def identify_gap(bg, tp):
    bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_GRAYSCALE)
    tp_img = cv2.imdecode(np.frombuffer(tp, np.uint8), cv2.IMREAD_GRAYSCALE)
    yy, xx = [], []
    for y in range(tp_img.shape[0]):
        for x in range(tp_img.shape[1]):
            if tp_img[y, x] < 200:
                yy.append(y)
                xx.append(x)
    tp_img = tp_img[min(yy):max(yy), min(xx):max(xx)]
    bg_edge = cv2.Canny(bg_img, 100, 200)
    tp_edge = cv2.Canny(tp_img, 100, 200)
    bg_pic = cv2.cvtColor(bg_edge, cv2.COLOR_GRAY2RGB)
    tp_pic = cv2.cvtColor(tp_edge, cv2.COLOR_GRAY2RGB)
    res = cv2.matchTemplate(bg_pic, tp_pic, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(res)
    return max_loc[0]

class CaptchaSolver:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.runninghub.cn",
            "Referer": "https://www.runninghub.cn/",
            "User-Agent": "Mozilla/5.0"
        })

    def solve(self):
        url = "https://www.runninghub.cn/uc/genCaptcha"
        response = self.session.post(url, params={"type": "CURVE2"}, data=json.dumps({}))
        captcha_data = response.json()
        bg = base64.b64decode(captcha_data['captcha']['backgroundImage'].split(',')[1])
        tp = base64.b64decode(captcha_data['captcha']['templateImage'].split(',')[1])
        distance = int(identify_gap(bg, tp) * 0.512)
        track = generate_slide_track(distance, -2)
        payload = {
            "id": captcha_data["id"],
            "data": {
                "bgImageWidth": 300,
                "bgImageHeight": 180,
                "startTime": track['startTime'],
                "stopTime": track['endTime'],
                "trackList": track['trackList']
            }
        }
        check_url = "https://www.runninghub.cn/uc/checkCaptcha"
        check_response = self.session.post(check_url, data=json.dumps(payload))
        return check_response.json()
