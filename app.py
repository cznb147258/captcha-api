from flask import Flask, jsonify
from captcha_solver import CaptchaSolver

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return jsonify({"message": "Captcha API is running."})

@app.route("/solve", methods=["GET"])
def solve():
    solver = CaptchaSolver()
    result = solver.solve()
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
