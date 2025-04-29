import hashlib
import time
import sqlite3
import requests
import logging

class SmileOneBot:
    def __init__(self, api_email, api_uid, api_key, product_name, admin_ids, sandbox_mode=False):
        # Logging setup
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        self.logger = logging.getLogger(__name__)

        # API Configuration
        self.SANDBOX_MODE = sandbox_mode
        self.API_URL = "https://frontsmie.smile.one" if self.SANDBOX_MODE else "https://www.smile.one/ph"
        self.API_EMAIL = api_email
        self.API_UID = api_uid
        self.API_KEY = api_key
        self.PRODUCT_NAME = product_name
        self.ADMIN_IDS = admin_ids

        # Global product IDs
        self.GLOBAL_PRODUCT_IDS = ["22590", "22591", "22592", "22593", "13", "23", "25", "26", "27", "28", "29", "30", "33", "16642"]

        # Product mappings
        self.CODE_MAPPING = {
            "11": "212", "22": "213", "56": "214", "112": "215", "223": "216",
            "336": "217", "570": "218", "1163": "219", "2398": "220", "6042": "221",
            "TwilightPH": "224", "WeeklyPH": "16641",
            "86": "13", "172": "23", "257": "25", "706": "26", "2195": "27",
            "3688": "28", "5532": "29", "9288": "30", "Twilight": "33", "Weekly": "16642",
            "Weekly2": "16642", "Weekly3": "16642", "Weekly4": "16642", "Weekly5": "16642",
            "50x2": "22590", "150x2": "22591", "250x2": "22592", "500x2": "22593",
        }

        self.combo_multipliers = {
            "Weekly2": 2, "Weekly3": 3, "Weekly4": 4, "Weekly5": 5,
            "50x2": 2, "150x2": 2, "250x2": 2, "500x2": 2
        }

        self.combo_pairs = {
            "343": ["25", "13"], "429": ["25", "23"], "514": ["25", "25"], "600": ["25", "25", "13"],
            "792": ["26", "13"], "878": ["26", "23"], "963": ["26", "25"], "1050": ["26", "25", "13"],
            "1135": ["26", "25", "23"], "1220": ["26", "25", "25"], "1412": ["26", "26"], "1584": ["26", "26", "23"],
            "1755": ["26", "26", "25", "13"], "1926": ["26", "26", "25", "25"], "2538": ["27", "25", "13"],
            "2901": ["27", "26"], "4394": ["28", "26"], "6238": ["29", "26"], "6944": ["29", "26", "26"],
            "7727": ["29", "27"], "8433": ["29", "27", "26"], "10700": ["30", "26", "26"],
            "172+wpk": ["23", "16642"], "257+wpk": ["25", "16642"], "33": ["212", "212", "212"],
            "44": ["213", "213"], "67": ["214", "212"], "78": ["214", "213"], "89": ["214", "213", "212"],
            "100": ["214", "213", "213"]
        }

        self.display_names = {
            "50x2": "100 Diamond", "150x2": "300 Diamond", "250x2": "500 Diamond", "500x2": "1000 Diamond",
            "Value Pass": "Value Pass", "86": "86 Diamond", "172": "172 Diamond", "257": "257 Diamond",
            "343": "343 Diamond", "429": "429 Diamond", "514": "514 Diamond", "600": "600 Diamond",
            "706": "706 Diamond", "792": "792 Diamond", "878": "878 Diamond", "963": "963 Diamond",
            "1050": "1050 Diamond", "1135": "1135 Diamond", "1412": "1412 Diamond", "1584": "1584 Diamond",
            "1755": "1755 Diamond", "1926": "1926 Diamond", "2195": "2195 Diamond", "2538": "2538 Diamond",
            "2901": "2901 Diamond", "3688": "3688 Diamond", "4394": "4394 Diamond", "5532": "5532 Diamond",
            "6238": "6238 Diamond", "6944": "6944 Diamond", "7727": "7727 Diamond", "8433": "8433 Diamond",
            "9288": "9288 Diamond", "10700": "10700 Diamond", "Twilight": "Twilight Pass",
            "Coupon Pass": "Coupon Pass", "Weekly": "Weekly Pass", "Weekly2": "2 x Weekly Pass",
            "Weekly3": "3 x Weekly Pass", "Weekly4": "4 x Weekly Pass", "Weekly5": "5 x Weekly Pass",
            "172+wpk": "172 + Weekly Pass", "257+wpk": "257 + Weekly Pass",
            "11": "11 Diamond", "22": "22 Diamond", "56": "56 Diamond", "112": "112 Diamond",
            "223": "223 Diamond", "336": "336 Diamond", "570": "570 Diamond", "1163": "1163 Diamond",
            "2398": "2398 Diamond", "6042": "6042 Diamond", "TwilightPH": "Growth Plan",
            "WeeklyPH": "Weekly Pass PH",
            "33": "33 Diamond", "44": "44 Diamond", "67": "67 Diamond", "78": "78 Diamond",
            "89": "89 Diamond", "100": "100 Diamond"
        }

        # Database setup
        self.conn = sqlite3.connect("bot_data.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0.0
        )
        """)
        self.conn.commit()

    def generate_sign(self, params: dict) -> str:
        params_sorted = dict(sorted(params.items()))
        str_to_hash = ""
        for key, value in params_sorted.items():
            str_to_hash += f"{key}={value}&"
        str_to_hash += self.API_KEY
        return hashlib.md5(hashlib.md5(str_to_hash.encode()).hexdigest().encode()).hexdigest()

    def get_user_balance(self, user_id: int) -> float:
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            self.cursor.execute("INSERT INTO users (user_id, balance) VALUES (?, 0.0)", (user_id,))
            self.conn.commit()
            return 0.0

    def update_user_balance(self, user_id: int, amount: float):
        current_balance = self.get_user_balance(user_id)
        new_balance = current_balance + amount
        self.cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
        self.conn.commit()

    def get_product_list(self, product_id: str = None):
        params = {
            "uid": self.API_UID,
            "email": self.API_EMAIL,
            "product": self.PRODUCT_NAME,
            "time": int(time.time())
        }
        params["sign"] = self.generate_sign(params)
        region = "" if product_id in self.GLOBAL_PRODUCT_IDS else "ph"
        url = f"https://www.smile.one/{region}/smilecoin/api/productlist" if region else "https://www.smile.one/smilecoin/api/productlist"
        try:
            response = requests.post(
                url,
                data=params,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == 200:
                return data.get("data", {}).get("product", [])
            return None
        except Exception as e:
            self.logger.error(f"Error fetching products: {e}")
            return None

    def create_order(self, userid: str, zoneid: str, productid: str):
        order_api_url = "https://www.smile.one/smilecoin/api/createorder" if productid in self.GLOBAL_PRODUCT_IDS else f"{self.API_URL}/smilecoin/api/createorder"
        params = {
            "uid": self.API_UID,
            "email": self.API_EMAIL,
            "userid": userid,
            "zoneid": zoneid,
            "product": self.PRODUCT_NAME,
            "productid": productid,
            "time": int(time.time())
        }
        params["sign"] = self.generate_sign(params)
        try:
            response = requests.post(
                order_api_url,
                data=params,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            response.raise_for_status()
            data = response.json()
            if data.get("status") == 200:
                return data.get("order_id", "N/A"), None
            return None, data.get("message", "Unknown error")
        except Exception as e:
            self.logger.error(f"Error creating order: {e}")
            return None, str(e)
