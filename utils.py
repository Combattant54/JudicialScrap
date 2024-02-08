from selenium.webdriver.remote.webdriver import WebDriver
import typing

def get_cookies_dict(cookies_list: typing.List[dict] =None, driver:WebDriver =None):
    cookies = {}
    if cookies_list is not None:
        cookies.update({d["name"]:d["value"] for d in cookies_list})
    if driver is not None:
        cookies.update({d["name"]:d["value"] for d in driver.get_cookies()})
    
    return cookies