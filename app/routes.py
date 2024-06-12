from flask import Flask, jsonify, request, render_template
from app.douyin.auto_upload import *
import threading

# 创建全局变量来存储二维码和到期时间
douyin_login_info_map = {}


# douyin_login_info_map = {
#     "2024061000001": {
#         "loginId": "2024061000001",
#         "douyinId": "pupusong",
#         "qrCode": "",
#         "expireTime": "",
#         "verifyCode": ""
#     }
# }


def init_routes(app):
    @app.route('/api/douyin/get_qr_code', methods=['POST'])
    async def get_douyin_qr_code_route():
        try:
            data = request.json
            login_id = data.get('loginId')
            callback_url = data.get('callbackUrl')

            new_login_info = {
                "loginId": login_id,
                "douyinId": "",
                "qrCode": "",
                "expireTime": "",
                "verifyCode": "",
                "status": "未登录"
            }
            douyin_login_info_map[login_id] = new_login_info

            if not login_id or not callback_url:
                return jsonify({"code": 1, "msg": "缺少 loginId 或 callbackUrl", "data": {}}), 400

            img_str, cookie_info, douyin_id = await get_douyin_qr_code(login_id, callback_url, callback_url,
                                                                       douyin_login_info_map)

            new_login_info["douyinId"] = douyin_id
            new_login_info["status"] = "已登录"
            new_login_info["qrCode"] = ""

            if img_str is None:
                return jsonify({"code": 1, "msg": "回传二维码图片失败", "data": {}}), 500

            response = {
                "code": 0,
                "msg": "success",
                "data": {
                    "loginId": login_id,
                    "douyinId": douyin_id,
                    "cookieInfo": cookie_info
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
    async def check_cookie_auth():
        try:
            data = request.json
            douyinId = data.get('douyinId')
            cookie_auth = await check_cookie(douyinId)
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

    @app.route('/api/douyin/callback', methods=['POST'])
    def douyin_qr_code_callback():
        global douyin_login_info_map
        data = request.json
        login_id = data.get("loginId")
        if login_id in douyin_login_info_map:
            login_info = douyin_login_info_map[login_id]
            login_info["qrCode"] = data.get("qrCode")
            login_info["verifyCode"] = ""
            login_info["expireTime"] = data.get("expireTime")
        else:
            douyin_login_info_map[login_id] = {
                "loginId": login_id,
                "qrCode": data.get("qrCode"),
                "expireTime": data.get("expireTime"),
                "verifyCode": ""
            }
        return jsonify({"code": 0, "msg": "success"}), 200

    @app.route('/display')
    def display_qr_code():
        return render_template('display_douyin_login_info.html', douyin_login_info_map=douyin_login_info_map)

    @app.route('/api/douyin/update_verification_code', methods=['POST'])
    def update_verification_code():
        global douyin_login_info_map
        data = request.json
        login_id = data.get("loginId")
        verify_code = data.get("verifyCode")

        if login_id in douyin_login_info_map:
            douyin_login_info_map[login_id]["verifyCode"] = verify_code
            douyin_login_info_map[login_id]["qrCode"] = ""
            return jsonify({"code": 0, "msg": "验证码已更新"}), 200
        else:
            return jsonify({"code": 1, "msg": "登录ID不存在"}), 400

    async def cookie_auto_check():
        global douyin_login_info_map
        while True:

            for login_id, info in douyin_login_info_map.items():
                if info.douyinId:
                    cookie_auth = await check_cookie(info["douyinId"])
                    if cookie_auth:
                        info["status"] = "已登录"
                    else:
                        info["status"] = "未登录"
            await asyncio.sleep(20)

    # 启动线程来检查二维码的过期时间
    threading.Thread(target=cookie_auto_check, daemon=True).start()
