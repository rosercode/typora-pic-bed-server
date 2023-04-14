# main.py
import hashlib

from flask import Flask, request, jsonify, send_file, make_response
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker

import datetime
import logging
from configparser import ConfigParser


logging.basicConfig(
    format='%(asctime)s - %(filename)-8s [line:%(lineno)-4d] - %(levelname)-8s %(message)s',
    filename='1.txt',
    filemode='a'
)

config = ConfigParser()
config.read('config.ini', encoding='utf-8')
url = config['database']['url']
base_url = config["common"]['base_url']

# 连接到 SQLite 数据库
engine = create_engine(url, echo=True)

# 创建一个映射类
Base = declarative_base()

app = Flask(__name__)


class Image(Base):
    """图片信息表"""
    __tablename__ = 't_image'

    id = Column(Integer, primary_key=True, doc="主键id")
    create_at = Column(DateTime, default=datetime.datetime.now, doc="创建时间")
    image_name = Column(String, doc="图片名称")
    md5 = Column(String, doc="md5")
    sha256 = Column(String, doc="sha256")


# 创建表
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'images'
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 文件头对应的文件类型
FILE_TYPE = {
    '89504E47': 'png',
    '47494638': 'gif',
    'FFD8FF': 'jpeg',
    'FFD8FFE0': 'jpg',
    'FFD8FFE1': 'jpg',
}


def get_file_type(file):
    """
    根据文件头获取文件类型
    """
    # 读取文件头
    header = file.read(4).hex().upper()

    # 根据文件头获取文件类型
    if header in FILE_TYPE:
        return FILE_TYPE[header]
    else:
        return None


def allowed_file(filename):
    """
    检查文件类型是否合法
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# 生成随机字符串
def generate_random_string():
    import random
    import string
    letters = string.ascii_lowercase + string.digits
    return "".join(random.choice(letters) for _ in range(4))


# 生成带时间戳的文件名
def generate_filename():
    import time
    timestamp = time.strftime('%Y%m%d-%H%M%S')
    random_string = generate_random_string()
    return f"{timestamp}-{random_string}"


@app.route('/upload', methods=['POST'])
def upload_file():
    """
    上传文件接口
    """
    import os
    import datetime

    # 检查是否有文件上传
    if 'file' not in request.files:
        logging.error('No file uploaded')
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']

    # 检查文件名是否为空
    if file.filename == '':
        logging.error('Empty filename')
        return jsonify({'error': 'Empty filename'}), 400

    # 检查文件类型是否合法
    if not allowed_file(file.filename):
        logging.error(f"File type {file.filename.rsplit('.', 1)[1].lower()} not allowed")
        return jsonify({'error': 'File type not allowed'}), 400

    # 检查文件头是否合法
    file_type = get_file_type(file)
    if not file_type or file_type not in ALLOWED_EXTENSIONS:
        logging.error('Invalid file header')
        return jsonify({'error': 'Invalid file header'}), 400

    # 检查文件大小是否超过限制
    if len(file.read()) > app.config['MAX_CONTENT_LENGTH']:
        logging.error(f"File {file.filename} size exceeded maximum limit")
        return jsonify({'error': 'File size exceeded maximum limit'}), 400
    file.seek(0)

    # 获取当前时间
    now = datetime.datetime.now()

    # 生成保存路径
    created_at = '{}{}{}'.format(now.year, os.path.sep, now.month)
    root_dir = app.config['UPLOAD_FOLDER'] + os.path.sep + created_at
    if not os.path.exists(root_dir):
        os.makedirs(root_dir)

    filename = os.path.join(root_dir, f"{generate_filename()}.{file_type}")

    # 处理文件名冲突
    while os.path.exists(filename):
        filename = os.path.join(root_dir, f"{generate_filename()}.{file_type}")

    # 保存文件
    file.save(filename)
    logging.info(f"File {file.filename} saved as {filename}")

    # 计算文件的 MD5 和 SHA256 值
    md5 = hashlib.md5()
    sha256 = hashlib.sha256()

    while True:
        data = file.read(1024)
        if not data:
            break
        md5.update(data)
        sha256.update(data)

    image = Image(image_name=filename.replace(os.path.sep, "/"), md5=md5.hexdigest(), sha256=sha256.hexdigest())
    session.add(image)
    session.commit()
    global base_url
    response = f"http://{base_url}/{filename.replace(os.path.sep, '/')}"
    # 返回文件名和路径
    return make_response(response)


@app.route('/images/<path:filename>', methods=['GET'])
def get_image(filename):
    import os
    # 拼接文件路径
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace("/", os.path.sep))
    # 检查文件是否存在
    if not os.path.exists(filepath):
        return jsonify({'error': 'file not found'}), 404

    # 返回文件内容
    return send_file(filepath)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9004, debug=True)
