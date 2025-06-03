from flask import Flask, jsonify, request
from captcha_solver import RunningHubSlider
from loguru import logger

app = Flask(__name__)

@app.route('/solve_captcha', methods=['POST'])
def solve_captcha():
    try:
        solver = RunningHubSlider()
        gen_data = solver.gen_captcha()
        result = solver.check_captcha(gen_data)
        if result['check_result'].get("code") == 200:
            return jsonify({
                "success": True,
                "message": "验证成功",
                "data": result
            })
        else:
            return jsonify({
                "success": False,
                "message": "验证失败",
                "data": result
            })
    except Exception as e:
        logger.exception("异常")
        return jsonify({"success": False, "message": str(e)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
