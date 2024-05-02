from collections.abc import Callable, Iterable, Mapping
from typing import Any
from datetime import datetime
from fastapi import FastAPI, Response # the high-level server part
import scraper, requester # the link to the data being scraped
import json, uvicorn, threading # the low-level server part
import os, platform, traceback, signal, asyncio # to stop the script
import socket

try:
    from ..build_logger import get_logger
except ImportError:
    from build_logger import get_logger

logger = get_logger(__name__)

app = FastAPI()
SERVER_THREAD = None
api_initialized_time = datetime.now()
api_started_time = None
MAIN_TASK = None

class ThreadCanceledException(threading.ThreadError):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

class CancelableThread(threading.Thread):
    def __init__(self, group =None, target: Callable =None, name: str =None, args: Iterable =[], kwargs: Mapping =None, *, daemon: bool =None) -> None:
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.canceled = threading.Event()
    def run(self) -> None:
        if self.canceled.is_set():
            raise ThreadCanceledException("The thread stoped due to the canceled flag set to True")
        return super().run()
    def cancel(self):
        self.canceled.set()
    def reset(self):
        self.canceled.clear()

def get_free_port() -> int:
    sock = socket.socket()
    sock.bind(("", 0))
    return sock.getsockname()[1]

def get_json():
    DATA = {}
    DATA["COOKIES_QUEUE_AMOUNT"] = requester.cookies_queue.qsize()
    DATA["COOKIES_QUEUE_MAXSIZE"] = requester.cookies_queue.maxsize
    DATA["IS_DIRECT_SAVER"] = scraper.DIRECT_SAVER

    api_infos = {}
    api_infos["intialized_time"] = str(api_initialized_time)
    api_infos["started_time"] = str(api_started_time)
    if api_started_time is not None:
        api_infos["running_time"] = str(datetime.now() - api_started_time)
    DATA["api_status"] = api_infos
    
    scraper_conf = {}
    scraper_conf["URL"] = scraper.URL
    scraper_conf["FORM_URL"] = scraper.FORM_URL
    scraper_conf["synchronous_amount"] = scraper.SYNCRONOUS_AMOUNT
    scraper_conf["breaks_amount"] = scraper.BREAKS_AMOUNT
    scraper_conf["districts"] = list(scraper.DISTRICTS)
    scraper_conf["years"] = list(scraper.YEARS)
    scraper_conf["instances"] = list(scraper.INSTANCES)
    scraper_conf["specialized"] = list(scraper.SPECIALIZED)

    DATA["scraper_configuration"] = scraper_conf

    scrap_adv = {}
    scrap_adv["page_scraped"] = scraper.page_scraped
    scrap_adv["scraped_scraped"] = list(scraper.scraped_years)
    scrap_adv["scraped_districts"] = list(scraper.scraped_districts)
    scrap_adv["scraped_instances"] = list(scraper.scraped_instances)
    scrap_adv["scraped_specialized"] = list(scraper.scraped_specialized)
    scrap_adv["scraped_n_expedientes"] = list(scraper.scraped_n_expedientes)

    scrap_adv["scraping_scraped"] = list(scraper.scraping_years)
    scrap_adv["scraping_districts"] = list(scraper.scraping_districts)
    scrap_adv["scraping_instances"] = list(scraper.scraping_instances)
    scrap_adv["scraping_specialized"] = list(scraper.scraping_specialized)
    scrap_adv["scraping_n_expedientes"] = list(scraper.scraping_n_expedientes)

    DATA["scraper_advancement"] = scrap_adv
    try:
        json_data = json.dumps(DATA, indent=2)
    except Exception as e:
        print(e)
        json_data = str(DATA)
    
    return json_data
@app.get("/stop")
async def stop():
    result = "Fine finished"
    logger.critical("STOPPING THE SCRIPT FROM API")
    try:
        SERVER_THREAD.cancel()
        asyncio.get_event_loop().stop()
        from main import exit
        exit()
    except Exception as e:
        result = str(e)
    finally:
        return Response(content=result, media_type="application/text")

@app.get("/")
async def root():
    json_data = get_json()
    
    return Response(content=json_data, media_type="application/json")

def start():
    global api_started_time
    global SERVER_THREAD
    api_started_time = datetime.now()
    port = get_free_port()
    print("Starting server on port " + str(port))
    print(f"access to api on http://127.0.0.1:{port} or using ' curl http://127.0.0.1:{port} '")
    thread = CancelableThread(None, uvicorn.run, kwargs={"app": __name__+":app", "host": "0.0.0.0", "port": port})
    thread.start()
    SERVER_THREAD = thread
    logger.info("SERVER_THREAD : " + str(thread.getName()))

def set_main_task(main_task):
    global MAIN_TASK
    MAIN_TASK = main_task

def exit():
    if SERVER_THREAD is not None:
        SERVER_THREAD.cancel()
    traceback.print_stack(limit=15)
    formated_stack = traceback.format_stack(limit=15)
    for formated_stack_frame in formated_stack:
        logger.warning(formated_stack_frame)
    try:
        try:
            MAIN_TASK.cancel()
        except:
            logger.warning("Can't cancell the task " + str(MAIN_TASK))
        scraper.stop()
    except:
        pass
    finally:
        if platform.system() == "Windows":
            os.system("taskkill /IM python.exe /F")
        else:
            logger.critical("pkill running")
            os.system("pkill -e -c -f python.exe; pkill -e -c -f python3.9; pkill -e -c -f bash")
            logger.critical("kill running")
            os.system("kill -9 $(pidof python3.9); echo 'first kill done'; kill -9 $(pidof java)")
            logger.critical("os.kill running")
            os.kill(os.getpid(), signal.SIGKILL)