import sys, time
from cookieworker import CookieWorkerHandler

def parse_args(args):
    result = {"threads":1,"result_folder":"result","cookie_folder":"cookie"}
    for i in range(len(args)):
        if args[i] == "-t":
            result["threads"] = int(args[i+1])
        elif args[i] == "-r":
            result["result_folder"] = args[i+1]
        elif args[i] == "-c":
            result["cookie_folder"] = args[i+1]
    print(result)
    return result

if __name__ == "__main__":
    args = parse_args(sys.argv)
    cwh = CookieWorkerHandler(args["threads"],args["cookie_folder"],args["result_folder"])
    cwh.start()
    while True: time.sleep(1)