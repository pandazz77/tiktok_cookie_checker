import threading, os, requests, codecs, signal, re, time

exit_event = threading.Event()

def signal_handler(signum, frame):
    exit_event.set()

signal.signal(signal.SIGINT, signal_handler)

class CookieWorkerException(Exception):
    pass

class CookieWorker(threading.Thread):
    def __init__(self, num_thread:int, cookie_folder:str, cookie_list:list, result_folder:str):
        super().__init__()
        self.num_thread = num_thread
        self.cookie_folder = cookie_folder
        self.cookie_list = cookie_list
        self.result_folder = result_folder

    def printf(self,msg:str):
        print(f"CookieWorker[{self.num_thread}] "+msg)

    def read_file(self,filename):
        try:
            with codecs.open(filename, 'r', encoding='utf-8', errors='ignore') as file:
                file_data = file.readlines()
                return file_data
        except IOError:
            print("Can't read from file, IO error")
            exit(1)

    def write_file(self,filename,data):
        with open(filename,"w",encoding="utf-8") as f:
            f.write(data)

    def get_cookie_json(self, file):
        #file_name = os.path.splitext(file)[0]
        list_of_lines = self.read_file(file)
        list_of_dic = []
        cookie_counter = 0
        for item in list_of_lines:
            if len(item) > 10:
                list_flags = item.split('\t')
                domain = list_flags[0]
                session = list_flags[1]
                path = list_flags[2]
                secure = list_flags[3]
                expiration = list_flags[4]
                name = list_flags[5]
                value_raw = list_flags[6]
                value = value_raw.rstrip("\r\n")
                dic = {'domain': domain,
                        'expirationDate': expiration,
                        'hostOnly': bool('false'),
                        'httpOnly': bool('false'),
                        'name': name,
                        'path': path,
                        "sameSite": "no_restriction",
                        'secure': bool(secure),
                        'session': bool(session),
                        'value': value,
                        'id': cookie_counter
                        }

                list_of_dic.append(dic)
                cookie_counter += 1
        return list_of_dic

    def get_cookie_jar(self, cookies):
        cookie_jar = requests.cookies.RequestsCookieJar()
        for cookie in cookies:
            cookie_jar.set(cookie["name"],cookie["value"],
                domain=cookie["domain"],
                path=cookie["path"],
                expires=cookie["expirationDate"],
                secure=cookie["secure"]
            )
        return cookie_jar

    def check_cookie(self, cookies:dict):
        time.sleep(1)
        result = {"status":"","user_name":"","followers_count":0,"comment":""}
        url = "https://www.tiktok.com/passport/web/account/info/?aid=1459&app_language=ru-RU&app_name=tiktok_web&browser_language=ru-RU&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0 (Windows)&channel=tiktok_web&cookie_enabled=true&device_id=7188303296481691141&device_platform=web_pc&focus_state=true&from_page=user&history_len=3&is_fullscreen=false&is_page_visible=true&os=windows&priority_region=BR&referer=&region=RU&screen_height=1080&screen_width=1920&tz_name=Europe/Moscow&verifyFp=verify_ldhr490s_Oip53Pcu_5eAq_4Cfe_9wA1_fi1F7KQ7rRmz&webcast_language=ru-RU"
        cookie_jar = self.get_cookie_jar(cookies)
        headers = {
            'user-agent': 'Mozilla/5.0 (X11; Linukflrb[ cyjd? fkx x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36',
            'accept':'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        }
        response = requests.get(url,cookies=cookie_jar, headers = headers)
        if response.status_code!=200:
            result["status"] = "ERROR"
            result["comment"] = f"Status Code {response.status_code}"
            return result

        response_json = response.json()["data"]
        if "username" not in response_json:
            result["status"] = "ERROR"
            result["comment"] = f"invalid cookie"
            return result 
        
        result["user_name"] = response_json["username"]


        headers["accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"

        response = requests.get(f'https://www.tiktok.com/@{result["user_name"]}',cookies=cookie_jar, headers = headers)
        if response.status_code!=200:
            result["status"] = "ERROR"
            result["comment"] = f"status code {response.status_code}"
            return result

        followers_match = re.findall(r'data-e2e="followers-count">([-+]?\d+)<',response.text)
        if not followers_match:
            result["followers_count"] = 0
            result["comment"] = "followers not found"
        else:
            result["followers_count"] = int(followers_match[0])
        result["status"] = "SUCCESS"
        
        return result

    def run(self):
        self.printf("has started")
        for file in self.cookie_list:
            json_cookie = self.get_cookie_json(file)
            result = self.check_cookie(json_cookie)
            if result["status"] == "SUCCESS":
                filename = f"[{result['followers_count']} sub] [{result['user_name']}].txt"
                try:
                    os.rename(file,os.path.join(self.result_folder,filename))
                except FileExistsError:
                    continue
            if exit_event.is_set():
                break
            self.printf(str(result))

class CookieWorkerHandler():
    def __init__(self,workers_count:int, cookie_folder:str,result_folder:str):
        self.cookie_folder = cookie_folder
        self.result_folder = result_folder
        self.workers_count = workers_count
        self.workers = []

    def get_folder_files(self, folder):
        folderPath = os.path.join(os.getcwd(),folder)
        files = os.listdir(folderPath)
        result = map(lambda name: os.path.join(folderPath, name), files)
        return list(result)

    def split_files(self, files:list,count:int):
        result = []
        chunk_size = int(len(files)/count)
        for i in range(0, len(files), chunk_size):
            result.append(files[i:i+chunk_size])
        if len(result)>count:
            result[-2] = result[-2]+result[-1]
            result.pop(len(result)-1)
        return result
    
    def start(self):
        cookie_chunks = self.split_files(self.get_folder_files(self.cookie_folder),self.workers_count)
        for num_thread in range(self.workers_count):
            new_worker = CookieWorker(num_thread+1,self.cookie_folder,cookie_chunks[num_thread],self.result_folder)
            self.workers.append(new_worker)
        for worker in self.workers:
            worker.daemon = True
            worker.start()
