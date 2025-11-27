# 可以抓取到验证码的爬虫，但是无法读到后续的表单等信息，一直返回502，应该不是自己的cookie失效（否则返回400），应该是那边的服务器承受不了
# 同时也直接在浏览器中直接访问了网址，https://zxgk.court.gov.cn/zhzxgk/，可以正常访问，但是在想要获取表单的时候，就会跳验证码失效，所以应该是网站本身就没有搭建好
# 注意每一次重新来都要重新获取cookie（最好），但是不更新其实好像也没事，让codex把cookie删了也没事
# 参考：https://blog.csdn.net/gitblog_06783/article/details/147667769，但这个代码有很多问题，比如说看似用了cnn实际没用，跑不了，拿codex改了

"""Manual captcha crawler for zxgk.court.gov.cn.

This script follows the same approach as zxgkScrawler: it requests the
landing page, parses the captcha id, downloads the image for manual entry,
then posts paginated searches and scrapes each case detail table.
"""
from __future__ import annotations

import json
import sys
import time
import webbrowser
from pathlib import Path
from typing import Dict, List

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://zxgk.court.gov.cn/zhzxgk/"
LIST_ENDPOINT = "searchZhcx.do"
DETAIL_ENDPOINT = "detailZhcx.do"
CAPTCHA_FILE = Path("captcha.jpg")
OUTPUT_DIR = Path("json_manual")

HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": "https://zxgk.court.gov.cn/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Cookie": (
        "JSESSIONID=2638C4922DA580B7D0BEBC9916CE4251; "
        "Hm_lvt_d59e2ad63d3a37c53453b996cb7f8d4e=1763432168; "
        "HMACCOUNT=294E5CABF819F7D0; "
        "lqWVdQzgOVyaO=57oVz3h2TPc4bX0apytYxBrAMa2YvQsaHBy8582saiAY.mDihnYHYdcuYxJ049GIE.4r.fKDStB6B1KHYpoGFiA; "
        "wzws_cid=39043083e6cd95471e8a4a3f197746a69c5f150ccc1c853bdb876b6635b3846f9a4283dd72d018ffe840daced68950bc1c90dfffe043c68ff86046cd20ef244c2a95329c72470e20997679ad63212b9f124d66c4d9c2c0934e05fa566bc67127ad74e7d23af87d098e5b2252c540470b; "
        "Hm_lpvt_d59e2ad63d3a37c53453b996cb7f8d4e=1763538921; "
        "lqWVdQzgOVyaP=OMVT.TXymHTNv.25xMkah_JzP8NkEsjlJ5wTIHVhUWl68jJaGRAQNvLT_ZNS2fSuzxcfPY_n6.gNODI9DL5QkYjy61m2pG9WMvSlmd3Z02rC.n5vUkH8ZGoghT8Xb3POtZ5MNy.senFsho1j5VWkuHxi1_k3TlgnfuHJF2Snut_Uju.iG7iL_pQfc3kIEB3MGaVQT9CPXhf_UomOEsqw8pXCqmvFL2j2rmDLswNWrkjGa1MMN9.YPfnRqcYxUpUGhrOF289OCN4AmaKhMPd3aOOOZ6IthrnvouVvZpiMxBjPBwShbK8Hf4op69c5IqHKHKz7ngXIFZ1uIx0XC.p3SY5vUsKptWmYixToIMnJdJpKplFSslBfA3FQMYGg66DOlcGwJ8TZne_lNHl3n9Qo.cHvpsl07JOg1bvtTkHDbw3"
    ),
}


def fetch_captcha(session: requests.Session) -> Dict[str, str]:
    """Return captcha metadata after downloading the image to disk."""
    resp = session.get(BASE_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    img_tag = soup.find("img", id="captchaImg")
    if not img_tag:
        raise RuntimeError("未找到验证码图片")
    img_src = img_tag["src"]
    captcha_id = img_src.split("captchaId=")[-1].split("&")[0]
    captcha_url = f"{BASE_URL}{img_src}/captcha.jpg"
    img_resp = None
    for attempt in range(3):
        try:
            img_resp = session.get(captcha_url, headers=HEADERS, timeout=20)
            img_resp.raise_for_status()
            break
        except requests.HTTPError as exc:
            if attempt == 2:
                raise
            print(f"验证码下载失败({exc}), 1秒后重试...")
            time.sleep(1)
    assert img_resp is not None
    CAPTCHA_FILE.write_bytes(img_resp.content)
    try:
        webbrowser.open(CAPTCHA_FILE.resolve().as_uri())
    except Exception:
        # best effort – 用户也可以手动打开 captcha.jpg
        pass
    print(f"验证码已保存到 {CAPTCHA_FILE.resolve()}，请查看后输入。")
    return {"captcha_id": captcha_id, "captcha_code": input("请输入验证码：").strip()}


def build_list_payload(name: str, id_card: str, code: str, captcha_id: str, page: int) -> Dict[str, str]:
    return {
        "pName": name,
        "pCardNum": id_card,
        "selectCourtId": "0",
        "pCode": code,
        "captchaId": captcha_id,
        "searchCourtName": "全国法院（包含地方各级法院）",
        "selectCourtArrange": "1",
        "currentPage": str(page),
    }


def scrape_list(session: requests.Session, payload: Dict[str, str]) -> List[Dict[str, str]]:
    resp = None
    for attempt in range(3):
        try:
            resp = session.post(BASE_URL + LIST_ENDPOINT, data=payload, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            break
        except requests.HTTPError as exc:
            if attempt == 2:
                raise
            print(f"列表页请求失败({exc}), 1秒后重试...")
            time.sleep(1)
    assert resp is not None
    data = resp.json()
    if not data or "result" not in data[0]:
        raise RuntimeError(f"列表页返回异常: {data}")
    return data[0]["result"]


def scrape_detail(session: requests.Session, name: str, id_card: str, code: str, captcha_id: str, case_code: str) -> Dict[str, str]:
    params = {
        "pnameNewDel": name,
        "cardNumNewDel": id_card,
        "j_captchaNewDel": code,
        "caseCodeNewDel": case_code,
        "captchaIdNewDel": captcha_id,
    }
    resp = None
    for attempt in range(3):
        try:
            resp = session.get(BASE_URL + DETAIL_ENDPOINT, params=params, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            break
        except requests.HTTPError as exc:
            if attempt == 2:
                raise
            print(f"  详情页请求失败({exc}), 1秒后重试...")
            time.sleep(1)
    assert resp is not None
    soup = BeautifulSoup(resp.text, "lxml")
    cells = soup.find_all("td")
    case_data: Dict[str, str] = {}
    key = None
    for idx, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        if idx % 2 == 0:
            key = text
        elif key:
            case_data[key] = text
            key = None
    if not case_data:
        case_data["caseCode"] = case_code
    return case_data


def crawl(name: str, id_card: str, pages: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        # disable inherited system proxies (Mac上常见全局代理)
        session.trust_env = False
        session.proxies = {"http": None, "https": None}
        print(f"开始获取验证码...（姓名: {name}, 身份证: {id_card or '未填写'}）")
        captcha_meta = fetch_captcha(session)
        captcha_code = captcha_meta["captcha_code"]
        captcha_id = captcha_meta["captcha_id"]
        for page in range(1, pages + 1):
            try:
                print(f"准备请求第 {page} 页列表...")
                result_list = scrape_list(
                    session,
                    build_list_payload(name, id_card, captcha_code, captcha_id, page),
                )
            except Exception as exc:
                print(f"第 {page} 页列表失败: {exc}")
                break
            print(f"正在处理第 {page} 页，共 {len(result_list)} 条案件")
            page_data = []
            for item in result_list:
                case_code = item.get("caseCode", "")
                try:
                    detail = scrape_detail(session, name, id_card, captcha_code, captcha_id, case_code)
                except Exception as exc:
                    print(f"  案件 {case_code} 详情失败: {exc}")
                    continue
                page_data.append(detail)
                time.sleep(0.2)
            out_file = OUTPUT_DIR / f"jsonPage{page}.json"
            out_file.write_text(json.dumps(page_data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"第 {page} 页写入 {out_file}")
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        driver.set_window_size(1920, 1080)
        driver.get(BASE_URL)
        from pathlib import Path
        desktop = Path.home() / "Desktop" / (name or "zxgk")
        desktop.mkdir(parents=True, exist_ok=True)
        screenshot_path = desktop / f"ZXGK_inter_{name or 'result'}_{int(time.time())}.png"
        driver.save_screenshot(str(screenshot_path))
        print(f"截图已保存至 {screenshot_path}")
        driver.quit()
    except Exception as e:
        print(f"截图时出错: {e}")


def main() -> None:
    name = input("请输入被执行人姓名（必填）：").strip()
    if not name:
        print("姓名为必填项，程序退出。")
        sys.exit(1)
    id_card = input("请输入被执行人身份证号（选填，可留空）：").strip()
    # pages_text = input("请输入需要抓取的页数（默认 112，可输入数字）：").strip()
    # pages = int(pages_text) if pages_text else 112
    pages = 1
    print(f"即将开始抓取，姓名：{name}，身份证：{id_card or '未填写'}，计划页数：{pages}")
    crawl(name, id_card, pages)


if __name__ == "__main__":
    main()
