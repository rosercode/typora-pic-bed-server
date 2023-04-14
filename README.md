Python Flask 实现的简单 `typora` 图床服务



```python
import sys
import urllib3

def upload_image(url, file_path):
    # 创建一个连接池管理器，最大连接数为 10
    http = urllib3.PoolManager(num_pools=10, maxsize=10)

    # 读取文件内容
    with open(file_path, 'rb') as f:
        file_data = f.read()

    # 构造请求体
    fields = {
        'file': (file_path, file_data),
    }

    # 发送请求
    response = http.request('POST', url, fields=fields)

    # 输出响应结果
    print(response.data.decode("UTF-8"))

if __name__ == '__main__':
    # 获取命令行参数列表，第一个参数是脚本名称，从第二个参数开始是图片路径列表
    image_paths = sys.argv[1:]

    # 遍历图片路径列表，上传每个图片
    for path in image_paths:
        upload_image('http://localhost:9004/upload', path)
```