from . import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(50), unique=True, nullable=False)
    douyin_id = db.Column(db.String(50), nullable=True)
    qr_code = db.Column(db.Text, nullable=True)
    expire_time = db.Column(db.Integer, nullable=True)
    verify_code = db.Column(db.String(10), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='未登录')