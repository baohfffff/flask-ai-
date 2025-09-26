import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///attendance.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 百度AI配置 :cite[3]:cite[6]:cite[9]
    BAIDU_APP_ID = os.environ.get('BAIDU_APP_ID') or '百度ai的账号id'
    BAIDU_API_KEY = os.environ.get('BAIDU_API_KEY') or '百度ai的api'
    BAIDU_SECRET_KEY = os.environ.get('BAIDU_SECRET_KEY') or '百度ai的key'
    BAIDU_GROUP_ID = "你百度ai的分组"  # 人脸库分组ID