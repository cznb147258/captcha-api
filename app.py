from flask import Flask, request, jsonify
import requests
from loguru import logger
import json
import random
from datetime import datetime, timedelta
import cv2
import numpy as np
import base64
import sys

sys.stdout.reconfigure(encoding='utf-8')

app = Flask(__name__)

def generate_slide_track(distance_x, distance_y=0, points_num=100, duration_ms=None):
    start_time = datetime.now()
    if duration_ms is None:
        duration_ms = random.randint(300, 800)
    end_time = start_time + timedelta(milliseconds=duration_ms)
    start_x, start_y = 0, 0
    end_x = distance_x
    end_y = distance_y
    track_list = []
    track_list.append({
        "x": start_x,
        "y": start_y,
        "type": "down",
        "t": 1500
    })
    for i in range(1, points_num - 1):
        progress = i / (points_num - 2)
        ease_progress = progress * progress * (3 - 2 * progress)
        x = int(start_x + (end_x - start_x) * ease_progress)
        y = int(start_y + (end_y - start_y) * ease_progress)
        x += random.randint(-2, 2)
        y += random.randint(-1, 1)
        t = int(duration_ms * ease_progress)
        track_list.append({
            "x": x,
            "y": y,
            "type": "move",
            "t": t
        })
    track_list.append({
        "x": end_x,
        "y": end_y,
        "type": "up",
        "t": duration_ms
    })
    start_time_str = start_time.isoformat(timespec='milliseconds') + 'Z'
    end_time_str = end_time.isoformat(timespec='milliseconds') + 'Z'
    return {
        "startTime": start_time_str,
        "endTime": end_time_str,
        "duration_ms": duration_ms,
        "trackList": track_list
    }

def identify_gap(bg, tp):
    bg_img = cv2.imdecode(np.frombuffer(bg, np.uint8), cv2.IMREAD_GRAYSCALE)
    tp_img = cv2.imdecode(np.frombuffer(tp, np.uint8), cv2.IMREAD_GRAYSCALE)
    yy = []
    xx = []
    for y in range(tp_img.shape[0]):
        for x in range(tp_img.shape[1]):
            r = tp_img[y, x]
            if r < 200:
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

class runningHubSilder():
    def __init__(self):
        self.session = requests.Session()
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.runninghub.cn",
            "Pragma": "no-cache",
            "Referer": "https://www.runninghub.cn/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Chromium\";v=\"136\", \"Google Chrome\";v=\"136\", \"Not.A/Brand\";v=\"99\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\""
        }
        self.session.headers.update(headers)

    def genCaptcha(self, ip):
        url = "https://www.runninghub.cn/uc/genCaptcha"
        params = {
            "type": "CURVE2"
        }
        data = json.dumps({})
        response = self.session.post(url, params=params, data=data, proxies=ip).json()
        return response

    def checkCaptcha(self, ip, genCaptcha_data):
        url = "https://www.runninghub.cn/uc/checkCaptcha"
        backgroundImage = base64.b64decode(genCaptcha_data['captcha']['backgroundImage'].replace('data:image/jpeg;base64,', ''))
        templateImage = base64.b64decode(genCaptcha_data['captcha']['templateImage'].replace('data:image/png;base64,',''))
        gay = int(identify_gap(backgroundImage, templateImage) * 0.512)
        logger.debug(f'缺口距离:{gay}')
        result = generate_slide_track(distance_x=gay, distance_y=-2)
        data = {
            "id": genCaptcha_data["id"],
            "data": {
                "bgImageWidth": 300,
                "bgImageHeight": 180,
                "startTime": result['startTime'],
                "stopTime": result['endTime'],
                "trackList": result['trackList']
            }
        }
        data = json.dumps(data, separators=(',', ':'))
        response = self.session.post(url, data=data, proxies=ip)
        logger.debug(f"请求结果: {response.text}")
        return response.json()

@app.route('/solve')
def solve():
    ip_param = request.args.get('ip')
    if not ip_param:
        return jsonify({"error": "缺少参数 ip"}), 400
    proxy = {
        "http": f"http://{ip_param}",
        "https": f"http://{ip_param}"
    }
    try:
        captcha_solver = runningHubSilder()
        gen_data = captcha_solver.genCaptcha(proxy)
        result = captcha_solver.checkCaptcha(proxy, gen_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"异常: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
