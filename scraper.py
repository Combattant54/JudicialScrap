import requests
from bs4 import BeautifulSoup
import time

#définie l'url du site, du formulaire et le cookie (généré avec un navigateur classique parce que sinon ca marche pas)
URL = "https://cej.pj.gob.pe"
FORM_URL = "/cej/forms/busquedaform.html"
CAPTCHA_URL = "/cej/Captcha.jpg"

COOKIES = {
    "JSESSIONID": "ATDDKKHS4Qytm15i5l-Dct9S.jvmr-scomunes22", 
    "_gid": "GA1.3.967327814.1679388211",
    "_ga": "GA1.3.1330425668.1679388211"
}
PROXIES = {
    "http": "http://127.0.0.1:8080",
    "https": "https://127.0.0.1:8080"
}
PROXIES.clear()
COOKIES.clear()

#cré une session de requests
with requests.Session() as s:
    print(s)
    #requete d'initialisation
    r = s.get(URL + FORM_URL, proxies=PROXIES, timeout=10)
    
    #transformation en soupe de bs4 (pour la manipulation)
    soup = BeautifulSoup(r.text, features="html.parser")
    
    #récupère l'image pour écouter (inutile)
    div = soup.find("img", alt="Reproducir captcha", id="btnRepro")
    print(div)
    print(dict(s.cookies), COOKIES)
    
    #définie les headers et les paramètres de la requetes (ils sont pas vraiment utiles)
    headers = {
        "Host":"cej.pj.gob.pe",
        "Accept-Encoding": "gzip, deflate", 
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://cej.pj.gob.pe/cej/forms/busquedaform.html"
    }
    params = {
        "Method": "GET",
        "Path": "/cej/xyhtml"
    }
    
    img = s.get(URL + CAPTCHA_URL, proxies=PROXIES, cookies=COOKIES)
    print(len(img.content), "\n")
    time.sleep(30)
    
    #cré une requete avec les paramètres
    req = requests.Request("GET", URL + "/cej/xyhtml", cookies=COOKIES, headers=headers, params=params)
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