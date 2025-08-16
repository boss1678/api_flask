from DrissionPage import ChromiumOptions, ChromiumPage
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, request, jsonify
import time
import uuid, os, shutil

app = Flask(__name__)



def get_chrome_options(temp_dir):
    co = ChromiumOptions()

    # ✅ 启用远程调试端口（必须）
    co.set_argument('--remote-debugging-port=9222')

    # ✅ 禁用沙箱（适用于 root 用户）
    co.set_argument('--no-sandbox')

    # ✅ 避免共享内存问题（服务器常见）
    co.set_argument('--disable-dev-shm-usage')

    # ✅ 无头模式（服务器无图形界面时必须）
    co.set_argument('--headless=new')

    # ✅ 禁用 GPU 加速（无头模式下建议）
    co.set_argument('--disable-gpu')

    # ✅ 禁用扩展（提高稳定性）
    co.set_argument('--disable-extensions')

    # 清除缓存
    co.incognito()

    # 指定的浏览器缓存目录
    co.user_data_dir = temp_dir

    # ✅ 禁用信息栏（防止“Chrome 正由自动化软件控制”提示）
    co.set_argument('--disable-infobars')
    co.set_argument('referer', 'https://www.douyin.com/search')
    co.set_user_agent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36')

    return co


def get_response(song_name):
    resp_lst = []
    temp_dir = f'/tmp/chrome_profile_{uuid.uuid4()}'
    os.makedirs(temp_dir, exist_ok=True)
    co = get_chrome_options(temp_dir)
    url = f"https://www.douyin.com/search/{song_name}?aid=e8a1a21a-f91d-4f03-96ba-f14a7e8d37f7&type=general"
    page = ChromiumPage(co)
    page.listen.start('general/search/single')
    try:
        page.get(url)
        page.wait(2.5)
        for _ in range(3):
            page.run_js('window.scrollBy(0, 1500)')
            page.wait(1)
            res = page.listen.wait(timeout=0.5)
            if not res or isinstance(res, bool):
                continue
            resp = res.response.body
            if isinstance(resp, str):
                continue
            if resp in resp_lst:
                continue
            resp_lst.append(resp)
        return resp_lst
    finally:
        # ✅ 清理逻辑
        page.quit()  # 关闭浏览器
        shutil.rmtree(temp_dir, ignore_errors=True)


def song_url(item):
    dic_lst = []
    data_ = item.get('data')
    for data in data_:
        if not data:
            continue
        aweme_info = data.get('aweme_info')
        if not aweme_info:
            continue
        video = aweme_info.get('video')
        if not video:
            continue
        play_addr = video.get('play_addr')
        if not play_addr:
            continue
        url_list = play_addr.get('url_list')
        if not url_list:
            continue
        dic = {
            'desc': aweme_info.get('desc'),
            'url': url_list[-1]
        }
        dic_lst.append(dic)
    return dic_lst


def last(name):
    futures = []
    song_url_lst = get_response(name)
    with ThreadPoolExecutor(3) as t:
        for item in song_url_lst:
            if not item:
                continue
            future = t.submit(song_url, item)
            futures.append(future)
    content = [future.result() for future in futures]
    return content


@app.route('/')
def index():
    return 'flask运行正常....'


@app.route('/<word>', methods=['GET'])
def get_song_url(word):
    results = last(word)
    flat = [item for group in results for item in group]
    return jsonify({
        word: flat
    })


if __name__ == '__main__':
    # app.run(host='0.0.0.0', port=5000, debug=False)
    s = time.time()
    print(last('肥美多汁'))
    e = time.time()
    print(int(e - s))
