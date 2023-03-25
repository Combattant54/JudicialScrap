import requests
from selenium.webdriver.remote.webdriver import WebDriver
from bs4 import BeautifulSoup
import logging


URL = None
CAPTCHA_URL = None
PROXIES = {}

HEADERS = {
    "Host":"cej.pj.gob.pe",
    "Accept-Encoding": "gzip, deflate", 
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://cej.pj.gob.pe/cej/forms/busquedaform.html"
}
PARAMS = {
    "Method": "GET",
    "Path": "/cej/xyhtml"
}

def init(base_url, captcha_url, proxies={}):
    global URL
    global CAPTCHA_URL
    global PROXIES
    
    URL = str(base_url)
    CAPTCHA_URL = str(captcha_url)
    PROXIES  = dict(proxies)

def get_captcha(driver: WebDriver) -> str:
    cookies = driver.get_cookies()
    
    if isinstance(cookies, list):
        add_cookies = {d["name"]:d["value"] for d in cookies}
    
    COOKIES = add_cookies
    #cré une session de requests
    with requests.Session() as s:    
    
        #cré une requete avec les paramètres
        req = requests.Request("GET", URL + "/cej/xyhtml", cookies=COOKIES, headers=HEADERS, params=PARAMS)
        #regarde le contenue de la requete
        print("Request inspection")
        print(req.params, req.headers, req.cookies, req.url)
        print(req.data, req.auth, req.method, req.files, req.hooks)
        print(dir(req))
        #prépare la requete a l'envoit
        
        req = req.prepare()
        #affiche les headers de la requete
        print(req.headers)
        
        #envoie la requete et affiche la réponse
        r = s.send(req, proxies=PROXIES)
        print(r)
        print(r.text)