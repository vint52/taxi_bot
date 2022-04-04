import requests
from lxml import html
from datetime import datetime


class Taxi:
    def __init__(self, login, password):
        self.base_url = "http://65050.homeip.net"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
        })

        self.login(login, password)

    def get_profile_info(self):
        response = self.session.get(self.__url('/corp/taxi/corp'))
        # print(response.text)
        # print("###################################")
        tree = html.fromstring(response.text)
        table = tree.xpath('//table[@id="sortTable"]/tbody/tr')

        trips = []
        for item in table:
            trips.append({
                "time": int(datetime.timestamp(datetime.strptime(item.xpath(".//td[2]/text()")[0], '%Y-%m-%d %H:%M'))),
                "phone": item.xpath(".//td[3]/text()")[0],
                "name": item.xpath(".//td[4]/text()")[0],
                "from": item.xpath(".//td[5]/a/text()")[0],
                "to": item.xpath(".//td[6]/a/text()")[0],
                "distance": float(item.xpath(".//td[7]/text()")[0]),
                "waiting": float(item.xpath(".//td[8]/text()")[0]),
                "price": int(item.xpath(".//td[9]/text()")[0])
            })

        return {
            "balance": int(tree.xpath('//div[@id="balance"]/div/p/strong/text()')[0]),
            "trips": trips
        }

    def login(self, login, password):
        response = self.session.get(self.__url('/corp/taxi/corp'))
        if len(response.cookies) > 0:
            self.session.cookies.update(response.cookies)
        tree = html.fromstring(response.text)
        form = tree.xpath('//form[@id="taxi-client-form"]')[0]
        form_build_id = form.xpath('.//input[@name="form_build_id"]/@value')[0]
        form_id = form.xpath('.//input[@name="form_id"]/@value')[0]
        response = self.session.post(self.__url('/corp/taxi/corp'),
                          data={"mail": login, "pass": password, "form_build_id": form_build_id,
                                "form_id": form_id, "op": "Войти"})
        tree = html.fromstring(response.text)
        error_message = tree.xpath('//div[@class="messages error"]')
        if len(error_message) > 0:
            raise Exception("Wrong auth")

    def __url(self, path):
        return self.base_url + path
