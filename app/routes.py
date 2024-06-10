from flask import Flask, jsonify, request, render_template
from app.douyin.auto_upload import *
import time
import threading

# 创建全局变量来存储二维码和到期时间
qr_code_info = {
    "loginId": "",
    "qrCode": "",
    "expireTime": 0
}

def init_routes(app):
    @app.route('/api/douyin/get_qr_code', methods=['POST'])
    async def get_douyin_qr_code_route():
        try:
            data = request.json
            login_id = data.get('loginId')
            callback_url = data.get('callbackUrl')

            if not login_id or not callback_url:
                return jsonify({"code": 1, "msg": "缺少 loginId 或 callbackUrl", "data": {}}), 400

            img_str, storage_state = await get_douyin_qr_code(login_id, callback_url)
            if img_str is None:
                return jsonify({"code": 1, "msg": "回传二维码图片失败", "data": {}}), 500

            response = {
                "code": 0,
                "msg": "success",
                "data": {
                    # "checkType": "qrcode",
                    # "qrCode": img_str,
                    "loginId": login_id,
                    "cookieInfo": storage_state
                }
            }
            return jsonify(response), 200
        except Exception as e:
            response = {
                "code": 1,
                "msg": str(e),
                "data": {}
            }
            return jsonify(response), 500

    @app.route('/api/douyin/check_cookie', methods=['POST'])
    async def restore_session_route():
        try:
            data = request.json
            storage_state_str = data.get('cookieInfo')
            cookie_auth = await check_cookie(storage_state_str)
            response = {
                "code": 0,
                "msg": "处理成功",
                "data": {
                    "cookieAuth": cookie_auth
                }
            }
            return jsonify(response), 200
        except Exception as e:
            response = {
                "code": 1,
                "msg": str(e),
                "data": {}
            }
            return jsonify(response), 500

    @app.route('/api/douyin/qr_code/callback', methods=['POST'])
    def douyin_qr_code_callback():
        global qr_code_info
        data = request.json
        qr_code_info["loginId"] = data.get("loginId")
        qr_code_info["qrCode"] = data.get("qrCode")
        qr_code_info["expireTime"] = data.get("expireTime")
        return jsonify({"code": 0, "msg": "success"}), 200

    @app.route('/display_qr_code')
    def display_qr_code():
        return render_template('display_qr_code.html', login_id=qr_code_info["loginId"], qr_code=qr_code_info["qrCode"], expire_time=qr_code_info["expireTime"])

    def expire_checker():
        global qr_code_info
        while True:
            if qr_code_info["expireTime"] > 0 and time.time() > qr_code_info["expireTime"]:
                qr_code_info = {"loginId": "", "qrCode": "", "expireTime": 0}
            time.sleep(1)

    # 启动线程来检查二维码的过期时间
    threading.Thread(target=expire_checker, daemon=True).start()