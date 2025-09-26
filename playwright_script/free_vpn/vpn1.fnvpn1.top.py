#!/usr/bin/env python
# coding=utf-8
import datetime
import random
import string
import requests
import yaml
import os
from playwright.sync_api import Playwright, sync_playwright


def generate_random_string(length):
    characters = string.ascii_letters + string.digits
    return "".join(random.choices(characters, k=length))


def get_random_domain():
    DOMAINS = [
        "163.com",
        "126.com",
        "yeah.net",
        "188.com",
        "qq.com",
        "foxmail.com",
        "sina.com",
        "sina.cn",
        "sohu.com",
        "139.com",
        "189.cn",
        "aliyun.com",
        "88.com",
        "263.net",
        "tom.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "gmail.com",
        "zoho.com",
        "huawei.com",
    ]
    return DOMAINS[random.randint(0, len(DOMAINS) - 1)]


def generate_email():
    today = datetime.date.today()
    ten_years_ago = today.replace(year=today.year - 21)
    today_date = ten_years_ago.strftime("%Y%m")
    email_domain = get_random_domain()
    email_user = generate_random_string(22 - len(email_domain))
    return f"{email_user}{today_date}@{email_domain}"


def generate_password():
    return generate_random_string(random.randint(65, 88))


def get_response_text(url: str) -> str:
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.text


def convert_to_clash_yaml(config_string: str) -> str:
    config = {"proxies": [], "proxy-groups": [], "rules": []}

    lines = config_string.strip().split("\n")
    current_section = None

    proxy_names = []
    for line in lines:
        if line.startswith("[Proxy]"):
            current_section = "Proxy"
            continue
        elif line.startswith("["):
            current_section = None

        if current_section == "Proxy" and "=" in line:
            proxy_name = line.split("=")[0].strip()
            proxy_names.append(proxy_name)

    auto_select_proxy_group = {
        "name": "auto",
        "type": "url-test",
        "interval": 300,
        "url": "http://www.gstatic.com/generate_204",
        "proxies": proxy_names,
    }
    config["proxy-groups"].append(auto_select_proxy_group)

    default_proxy_group_name = None
    current_section = None
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#!"):
            continue

        if line.startswith("[General]"):
            current_section = "General"
            config["dns"] = {
                "enable": True,
                "listen": "0.0.0.0:53",
                "enhanced-mode": "fake-ip",
                "nameserver": [],
            }
            continue
        elif line.startswith("[Proxy]"):
            current_section = "Proxy"
            continue
        elif line.startswith("[Proxy Group]"):
            current_section = "Proxy Group"
            continue
        elif line.startswith("[Rule]"):
            current_section = "Rule"
            continue
        elif line.startswith("["):
            current_section = None
            continue

        if current_section == "General":
            if line.startswith("dns-server"):
                servers = line.split("=")[1].strip().split(",")
                config["dns"]["nameserver"] = [s.strip() for s in servers]
            elif line.startswith("doh-server"):
                config["dns"]["fallback"] = [line.split("=")[1].strip()]

        elif current_section == "Proxy":
            if "=" not in line:
                continue
            name, details = line.split("=", 1)
            params = details.strip().split(",")
            proxy_info = {"name": name.strip(), "type": params[0].strip()}
            for param in params[1:]:
                key_val = param.strip().split("=", 1)
                if len(key_val) == 2:
                    key, value = key_val
                    if key.strip() == "encrypt-method":
                        proxy_info["cipher"] = value.strip()
                    else:
                        proxy_info[key.strip()] = value.strip()
                else:
                    if "server" not in proxy_info:
                        proxy_info["server"] = param.strip()
                    elif "port" not in proxy_info:
                        proxy_info["port"] = int(param.strip())
            if "udp-relay" in proxy_info:
                proxy_info["udp"] = proxy_info["udp-relay"].lower() == "true"
                del proxy_info["udp-relay"]
            config["proxies"].append(proxy_info)

        elif current_section == "Proxy Group":
            if "=" not in line:
                continue
            name, details = line.split("=", 1)
            name = name.strip()
            default_proxy_group_name = name
            parts = [p.strip() for p in details.strip().split(",")]
            group_type = parts[0]
            group_info = {
                "name": name,
                "type": group_type,
                "proxies": ["auto"] + proxy_names,
            }
            config["proxy-groups"].append(group_info)

    config["rules"].append("GEOIP,CN,DIRECT")
    config["rules"].append(f"MATCH,{default_proxy_group_name}")
    return yaml.dump(config, allow_unicode=True, sort_keys=False, indent=2)


def upload_to_gist(content: str, gist_id: str, filename: str = "subscribe.yaml") -> None:
    token = os.environ.get("GITHUB_TOKEN","")
    if not token:
        raise RuntimeError("未找到 GITHUB_TOKEN 环境变量")

    url = f"https://api.github.com/gists/{gist_id}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
    }
    payload = {"files": {filename: {"content": content}}}
    resp = requests.patch(url, headers=headers, json=payload)
    resp.raise_for_status()
    print(f"Gist {gist_id} 已更新: 文件 {filename}")


def run(playwright: Playwright, gist_id: str, filename) -> None:
    browser = playwright.firefox.launch()
    context = browser.new_context()
    page = context.new_page()

    # --- 1. 注册新用户 ---
    print("正在导航至注册页面...")
    page.goto("https://vpn1.fnvpn1.top/#/register")

    email = generate_email()
    password = generate_password()
    print(f"生成的邮箱: {email}")
    print(f"生成的密码: {password}")

    print("正在填写注册信息...")
    page.locator("xpath=(//input)[1]").fill(email)
    page.locator("xpath=(//input)[2]").fill(password)
    page.locator("xpath=(//input)[3]").fill(password)
    page.locator("xpath=//div[@class='agree']//input").check()
    page.locator("xpath=//button[@type='submit']").click()
    print("注册信息已提交。")

    # --- 2. 登录 ---
    print("正在导航至登录页面...")
    page.goto("https://vpn1.fnvpn1.top/#/login")
    page.locator("xpath=(//input)[1]").fill(email)
    page.locator("xpath=(//input)[2]").fill(password)
    page.locator("xpath=//button[@type='submit']").click()
    print("登录信息已提交。")

    print("正在等待跳转至用户后台...")
    page.wait_for_url("https://vpn1.fnvpn1.top/#/stage/dashboard")
    print("登录成功，已进入用户后台。")

    # --- 3. 获取订阅 ---
    print("正在获取订阅链接...")
    page.locator("xpath=((//ul[contains(@class,'link')])[2]//li)[last()]").click()
    page.locator("xpath=//i[contains(@class,'clipboard')]").click()
    subscription_url = page.evaluate("navigator.clipboard.readText()")
    print(f"成功复制到剪贴板内容: {subscription_url}")

    subscription_str = get_response_text(subscription_url)
    subscription_yaml_str = convert_to_clash_yaml(subscription_str)

    # --- 上传 gist ---
    upload_to_gist(subscription_yaml_str, gist_id,filename)

    print("任务完成，关闭浏览器。")
    context.close()
    browser.close()


if __name__ == "__main__":
    gist_id = os.environ.get("GIST_ID", "")
    file_name = os.environ.get("FILE_NAME", "")
    with sync_playwright() as playwright:
        run(playwright, gist_id,file_name)
