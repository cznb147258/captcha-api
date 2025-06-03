from flask import Flask, request, jsonify
import requests
import json
import random
import time
from datetime import datetime, timedelta
import cv2
import numpy as np
import base64
from loguru import logger

app = Flask(__name__)

def generate_slide_track(distance_x, distance_y=0, points_num=100, duration_ms=None):
    start_time = datetime.now()
    if duration_ms is None:
        duration_ms = random.randint(300, 800)
    end_time = start_time + timedelta(milliseconds=duration_ms)
    track_list = []
    track_list.append({"x": 0, "y": 0, "type": "down", "t": 1500})
    for i in range(1, points_num - 1):
        progress = i / (points_num - 2)
        ease = progress * progress * (3 - 2 * progress)
        x = int(distance_x * ease) + random.randint(-2, 2)
        y = int(distance_y * ease) + random.randint(-1, 1)
        t = int(duration_ms * ease)
        track_list.append({"x": x, "y": y, "type": "move", "t": t})
    track_list.append({"x": distance_x, "y": distance_y, "type": "up", "t": duration_ms})
    return {
        "startTime": start_time.isoformat(timespec='milliseconds') + 'Z',
        "endTime": end_time.isoformat(timespec='milliseconds') + 'Z',
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
    res = cv2.matchTemplate(bg_img, tp_img, cv2.TM_CCOEFF_NORMED)
    _, _, _, max_loc = cv2.minMaxLoc(res)
    return max_loc[0]

class RunningHubSlider:
    def __init__(self, proxies=None):
        self.session = requests.Session()
        self.proxies = proxies
        self.session.headers.update({
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.runninghub.cn",
            "Referer": "https://www.runninghub.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
        })

    def gen_captcha(self):
        url = "https://www.runninghub.cn/uc/genCaptcha"
        params = {"type": "CURVE2"}
        data = json.dumps({})
        response = self.session.post(url, params=params, data=data, proxies=self.proxies)
        return response.json()

    def check_captcha(self, gen_data):
        bg = base64.b64decode(gen_data['captcha']['backgroundImage'].split(',')[1])
        tp = base64.b64decode(gen_data['captcha']['templateImage'].split(',')[1])
        gap = int(identify_gap(bg, tp) * 0.512)
        logger.debug(f"缺口位置: {gap}")
        track = generate_slide_track(gap, -2)

        url = "https://www.runninghub.cn/uc/checkCaptcha"
        payload = {
            "id": gen_data["id"],
            "data": {
                "bgImageWidth": 300,
                "bgImageHeight": 180,
                "startTime": track['startTime'],
                "stopTime": track['endTime'],
                "trackList": track['trackList']
            }
        }
        response = self.session.post(url, data=json.dumps(payload), proxies=self.proxies)
        return response.json()
@app.route('/proxy_test')
def proxy_test():
    try:
        # 从代理池 API 获取代理
        proxy_url = "http://api1.ydaili.cn/tools/MeasureApi.ashx?action=EAPI&secret=FCDF67FEA375BE0687311360BECD331260D14B775186213D95CF710ACD1D40CC7CA6CF95DD529340&number=1&orderId=SH20240319214202161&format=txt&split=3"
        proxy_resp = requests.get(proxy_url)
        proxy_ip = proxy_resp.text.strip()
        proxies = {
            "http": f"http://{proxy_ip}",
            "https": f"http://{proxy_ip}"
        }

        # 用该代理请求 httpbin.org/ip
        test_resp = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=10)
        return {
            "proxy": proxy_ip,
            "result": test_resp.json()
        }
    except Exception as e:
        return {"error": str(e)}

@app.route('/solve', methods=['GET'])
def solve():
    ip = request.args.get("ip")
    proxies = None
    if ip:
        proxies = {"http": f"http://{ip}", "https": f"http://{ip}"}
        logger.info(f"使用代理: {ip}")

    try:
        solver = RunningHubSlider(proxies=proxies)
        gen_data = solver.gen_captcha()
        result = solver.check_captcha(gen_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"处理失败: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000)
