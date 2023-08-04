import argparse
import csv
import os
import re
import threading
from datetime import datetime
from urllib.request import Request, urlopen

import spacy
from dotenv import load_dotenv
from serpapi import BingSearch, BaiduSearch, DuckDuckGoSearch, GoogleSearch, NaverSearch, YahooSearch, YandexSearch

# Load Spacy English model
nlp = spacy.load('en_core_web_sm')

class ScrapeProcess(object):
    def __init__(self, filename, email_only, no_gov):
        if os.path.isfile(filename):
            filename = f"{os.path.splitext(filename)[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        self.filename = filename
        self.email_only = email_only
        self.no_gov = no_gov
        self.csvfile = open(filename, 'w+')
        self.csvwriter = csv.writer(self.csvfile)
        with open('tld.txt', 'r') as tld_file:
            self.tld_list = [line.strip() for line in tld_file]
        self.emails = {}
        self.phones = {}
        self.entities = {}
        self.search_engines = {
            "google": GoogleSearch,
            "bing": BingSearch,
            "duckduckgo": DuckDuckGoSearch,
            "yahoo": YahooSearch,
            "yandex": YandexSearch,
            "baidu": BaiduSearch,
            "yelp": GoogleSearch,
            "naver": NaverSearch,
            "glocation": GoogleSearch
        }

    def validate_email(self, email):
        email_regex = re.compile(r'[^@]+@[^@]+\.[^@]+')
        return email_regex.match(email)

    def get_tld(self, email):
        return email.split('.')[-1]

    def go(self, query, pages, engine):
        load_dotenv()
        serp_api_key = os.getenv('SERP_API_KEY')
        if engine == "all":
            for eng in self.search_engines:
                self.scrape(query, pages, eng, serp_api_key)
        elif engine == "american":
            american_engines = [eng for eng in self.search_engines if eng not in ["baidu", "naver", "yandex"]]
            for eng in american_engines:
                self.scrape(query, pages, eng, serp_api_key)
        else:
            if engine not in self.search_engines:
                print(f"Invalid engine specified: {engine}. Please choose from {', '.join(self.search_engines.keys())}, or 'all', or 'american'.")
                return
            self.scrape(query, pages, engine, serp_api_key)

    def scrape(self, query, num_pages, engine, api_key):
        for i in range(num_pages):
            params = {
                "engine": engine,
                "num": 100,
                "api_key": api_key,
            }
            if engine == "bing":
                params["cc"] = "US"
            elif engine == "yahoo":
                params["p"] = query
                params["start"] = i * 100
            elif engine == "yandex":
                params["text"] = query
            elif engine == "yelp":
                params["find_desc"] = query
            elif engine == "glocation":
                location = GoogleSearch({}).get_location("Rockville, MD", 1)[0]["canonical_name"]
                params["q"] = query
                params["location"] = location
            else:
                params["q"] = query
                params["start"] = i * 100

            search = self.search_engines[engine](params)
            results = search.get_dict().get('organic_results', [])
            print(f'Number of results: {len(results)}')
            for page in results:
                self.process_page(page)

    def process_page(self, page):
        try:
            request = Request(page['link'])
            html = urlopen(request).read().decode('utf8')
            print(f'Scraping page: {page["link"]}')
        except Exception as e:
            print(f'Could not scrape page: {page["link"]} due to {e}')
            return

        emails = re.findall(r'([A-Za-z0-9.\\+_-]+@[A-Za-z0-9\\._-]+\\.[a-zA-Z]*)', html)
        phones = re.findall(r'(\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4})', html)
        doc = nlp(html)
        entities = {ent.text: ent.label_ for ent in doc.ents}

        if args.E:
            for email in emails:
                email = email.lower()
                if self.no_gov and re.search(r'\.gov|sheriff|county|federal', email):
                    continue
                if email[-1] == '.':
                    tld = email.split('.')[-2]
                    if tld in self.tld_list:
                        email = email[:-1]
                if re.search(r'\d$', email):
                    continue
                if email not in self.emails and self.validate_email(email) and self.get_tld(email) in self.tld_list:
                    if not self.email_only:
                        exclude_patterns = ['example.com', 'yourdomainname.com', 'yourdomain.com', 'spam',
                                            'fightspam.gc.ca']
                        if not any(pattern in email for pattern in exclude_patterns) and len(email.split('@')[0]) <= 15:
                            print(f'Found email: {email}')
                            self.emails[email] = (page['title'], page['link'])
                            self.csvfile.flush()
                    else:
                        print(f'Found email: {email}')
                        self.emails[email] = (page['title'], page['link'])
                        self.csvfile.flush()
        if args.P:
            for phone in phones:
                print(f'Found phone: {phone}')
                self.phones[phone] = (page['title'], page['link'])
                self.csvfile.flush()
        if args.N:
            for entity, label in entities.items():
                if label in ["DATE", "CARDINAL", "PRODUCT", "GPE"]:
                    continue
                if label == "PERSON" and not re.match(r'\w+ \w+', entity):
                    continue
                print(f'Found entity: {entity} ({label})')
                self.entities[entity] = (label, page['title'], page['link'])
                self.csvfile.flush()

    def post_process(self):
        results = {}
        for email, (title, link) in self.emails.items():
            if link not in results:
                results[link] = {'title': title, 'email': [], 'phone': [], 'entity': []}
            results[link]['email'].append(email)
        for phone, (title, link) in self.phones.items():
            if link not in results:
                results[link] = {'title': title, 'email': [], 'phone': [], 'entity': []}
            results[link]['phone'].append(phone)
        for entity, (label, title, link) in self.entities.items():
            if link not in results:
                results[link] = {'title': title, 'email': [], 'phone': [], 'entity': []}
            results[link]['entity'].append((entity, label))

        with open('processed_' + self.filename, 'w+') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'link', 'email', 'phone', 'entity'])
            for link, data in results.items():
                writer.writerow([data['title'], link, '; '.join(data['email']), '; '.join(data['phone']), '; '.join([f'{e} ({l})' for e, l in data['entity']])])

        self.csvfile.close()


parser = argparse.ArgumentParser(description='Scrape search results for leads')
parser.add_argument('-E', action='store_true', default=True, help='Enable email scraping')
parser.add_argument('-Eo', action='store_true', help='Email only output')
parser.add_argument('-N', action='store_true', default=True, help='Enable named entity scraping')
parser.add_argument('-Ng', action='store_true', help='Exclude .gov emails')
parser.add_argument('-P', action='store_true', default=True, help='Enable phone number scraping')
parser.add_argument('-PP', action='store_true', help='Enable post-processing (lowercase and dedupe)')
parser.add_argument('-e', '--engine', type=str, default="google", help="The search engine to use (google, bing, duckduckgo, yahoo, yandex, baidu, yelp, all)")
parser.add_argument('-key', type=str, default=os.getenv('SERP_API_KEY'), help='Serp API key')
parser.add_argument('-o', type=str, default='emails.csv', help='output filename')
parser.add_argument('-pages', type=int, default=2, help='Number of search results pages to scrape per engine')
parser.add_argument('-query', type=str, default='test', help='A query to use for the search')

args = parser.parse_args()
args.o = args.o + '.csv' if '.csv' not in args.o else args.o

s = ScrapeProcess(args.o, args.Eo, args.Ng)
if args.engine == "all":
    threads = []
    for engine in s.search_engines:
        t = threading.Thread(target=s.go, args=(args.query, args.pages, engine))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()
else:
    s.go(args.query, args.pages, args.engine)
if args.PP:
    s.post_process()
