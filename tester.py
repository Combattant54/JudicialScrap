import requester
import traceback
import logging

logging.basicConfig(level=logging.DEBUG)

with open("example.html", "r") as f:
    result = ""
    l = f.readline()
    i = 1
    last = l
    while l:
        result += l
        last = l
        i += 1
        try:
            l = f.readline()
        except UnicodeDecodeError:
            traceback.print_exc()
            print("On line", i, "with", last)
        
    print(requester.get_one_form(result))