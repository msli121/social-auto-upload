# config.py
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

class Config:
    DEBUG = True  # 启用调试模式，适用于开发环境
    SECRET_KEY = 'your_secret_key_here'  # Flask应用的密钥，用于会话、CSRF保护等
    # 其他配置项可以根据需要添加，例如数据库连接、邮件服务器设置等

# 你可以根据需要添加更多的配置项，例如数据库配置、邮件服务器配置等
# 例如：
# SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'
# MAIL_SERVER = 'smtp.example.com'
# MAIL_PORT = 587
# MAIL_USE_TLS = True
# MAIL_USERNAME = 'your_email@example.com'
# MAIL_PASSWORD = 'your_email_password'