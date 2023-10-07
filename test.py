import requests
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver import Edge, DesiredCapabilities
from selenium.webdriver.edge.service import Service

PATH = "/cej/forms/busquedaform.html"
URL = "https://cej.pj.gob.pe"

HEADERS = {
    "Host":"cej.pj.gob.pe",
    "Accept-Encoding": "gzip, deflate", 
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://cej.pj.gob.pe/cej/forms/busquedaform.html"
}

PROXIES = {
    "http": "http://127.0.0.1:8080",
    "https": "http://127.0.0.1:8080"
}

print("\n")
print(PROXIES)
print("")


service = Service("driver/msedgedriver.exe")
proxy = Proxy()
proxy.proxy_type = ProxyType.MANUAL
proxy.http_proxy = "127.0.0.1:8080"

capabilities = DesiredCapabilities.EDGE.copy()
capabilities["plateform"] = "WINDOWS"
capabilities["version"] = "11"
proxy.add_to_capabilities(capabilities)
driver = Edge(capabilities=capabilities, service=service)

driver.get(URL)
print(driver.page_source)
print(driver.get_cookies())
driver.close()

request = requests.Request("GET", URL + "/", headers=HEADERS)
request = request.prepare()
print(repr(request))

def send(sess: requests.Session, request, redirects=False):
    return sess.send(request, verify=False, proxies=PROXIES, allow_redirects=redirects)

with requests.Session() as sess:
    r = send(sess, request, redirects=True)
    print(sess)
    
    request = requests.Request("GET", URL + PATH, headers=HEADERS)
    request = request.prepare()
    
    r = send(sess, request, redirects=True)
    for c in r.cookies:
        print(c.name, c.value)
    
    for c in sess.cookies:
        print(c.name, c.value)
    
    try:
        next = r.next
        print(next)
        while next is not None:
            print(next)
            r = send(sess, next)
            next = r.next
    except:
        print("error")
        pass
    
    req = requests.Request("GET", URL + "/cej/xyhtml", headers=HEADERS, cookies=sess.cookies)
    req = req.prepare()
    
    r = send(sess, req)
    
    