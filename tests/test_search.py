import json
import re
import unittest
import urllib.request
import urllib.parse

BASE_URL = "http://127.0.0.1:8000"


def request(path, **params):
    url = BASE_URL + path

    if params:
        url += "?" + urllib.parse.urlencode(params)

    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def search(query):
    return request("/api/agent", q=query, limit=4)


class SearchTests(unittest.TestCase):

    def test_health(self):
        data = request("/health")
        self.assertEqual(data["status"], "ok")

    def test_customer_queries(self):
        cases = [
            ("astra linux", r"astra linux"),
            ("Microsoft Office для дома и бизнеса",
             r"microsoft office для дома и бизнеса"),
            ("kaspersky small office security",
             r"kaspersky small office security"),
            ("крипто про csp 5.0", r"криптопро csp.*5\.0"),
            ("anydesk", r"^anydesk"),
            ("кибер бэкап", r"киберпротект.*кибер бэкап"),
            ("сканер-вс", r"сканер[-– ]*вс"),
            ("мтс", r"мтс линк"),
            ("max patrol", r"max\s*patrol"),
            ("365", r"microsoft 365.*(family|для семьи)")
        ]

        for query, pattern in cases:
            with self.subTest(query=query):
                data = search(query)

                self.assertEqual(data["mode"], "hybrid")
                self.assertGreater(data["total"], 0)

                self.assertRegex(
                    data["items"][0]["name"].lower(),
                    pattern
                )

    def test_slang(self):
        data = search("антивирь")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertIn(
                "антивирус",
                item["category_path"].lower()
            )

    def test_server_hardware(self):
        data = search("сервер")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertTrue(
                item["category_path"].startswith(
                    "Серверы и опции"
                )
            )

    def test_server_security(self):
        data = search("антивирус для сервера")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertIn(
                "антивирус",
                item["category_path"].lower()
            )

    def test_video_software(self):
        data = search("сервис для онлайн-совещаний")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertNotRegex(
                item["name"].lower(),
                r"гарнитура|наушники|веб-камера"
            )

    def test_headsets(self):
        data = search("гарнитура для переговоров")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertRegex(
                item["name"].lower(),
                r"гарнитур|headset"
            )

    def test_office(self):
        data = search("редактор электронных таблиц")
        self.assertGreaterEqual(data["total"], 4)

        for item in data["items"]:
            self.assertTrue(
                item["category_path"].startswith(
                    "Офисные программы"
                )
            )

    def test_mobile_recovery(self):
        data = search("восстановление данных iPhone")
        self.assertGreater(data["total"], 0)

        for item in data["items"]:
            self.assertRegex(
                item["name"].lower(),
                r"ios|iphone"
            )

    def test_desktop_recovery(self):
        data = search(
            "программа для восстановления файлов на компьютере"
        )

        for item in data["items"]:
            self.assertNotRegex(
                item["name"].lower(),
                r"ios|android|iphone|ipad"
            )

        self.assertGreater(data["total"], 0)

        self.assertTrue(any(
            "феникс" in item["name"].lower()
            for item in data["items"]
        ))

        print("\nDesktop recovery products:", data["total"])

    def test_unavailable_products(self):
        data = search(
            "Microsoft Office для дома и бизнеса"
        )

        self.assertGreaterEqual(
            len(data["unavailable_alternatives"]), 2
        )

        for item in data["unavailable_alternatives"]:
            self.assertFalse(item["available"])
            self.assertIsNone(item["price"])

    def test_recommendations(self):
        for query in [
            "astra linux",
            "сервер",
            "мтс",
            "Microsoft Office для дома и бизнеса"
        ]:
            with self.subTest(query=query):
                data = search(query)

                self.assertGreater(
                    len(data["recommendations"]), 0
                )

                ids = {
                    item["id"] for item in data["items"]
                }

                for item in data["recommendations"]:
                    self.assertNotIn(item["id"], ids)
                    self.assertTrue(
                        item["source"].startswith("https://")
                    )
                    ids.add(item["id"])

    def test_unknown_query(self):
        data = search("qzxv987654")

        self.assertEqual(data["total"], 0)
        self.assertEqual(data["recommendations"], [])
        self.assertEqual(data["alternatives"], [])
        self.assertEqual(
            data["unavailable_alternatives"], []
        )

    def test_suggestions(self):
        data = request("/api/suggest", q="micro")
        self.assertGreater(len(data["suggestions"]), 0)

    def test_unknown_suggestions(self):
        data = request("/api/suggest", q="qzxv987654")
        self.assertEqual(data["suggestions"], [])

    def test_analytics(self):
        data = request("/api/metrics")
        self.assertGreater(len(data["metrics"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
