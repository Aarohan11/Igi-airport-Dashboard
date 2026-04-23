#!/usr/bin/env python3
"""Minimal Flask test"""
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Home works!"

@app.route("/api/test")
def test_api():
    return {"status": "ok", "message": "API works"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
