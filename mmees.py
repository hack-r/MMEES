#########
# MMEES #
#########

# Libs
import area_code_nanp
import argparse
import csv
import os
import re
import threading
import spacy
import urllib

from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
from serpapi import BingSearch, BaiduSearch, DuckDuckGoSearch, GoogleSearch, NaverSearch, YahooSearch, YandexSearch
from urllib.request import Request, urlopen


# Area codes
def get_all_area_codes():
    regions = [
        'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut',
        'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa',
        'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan',
        'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey',
        'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
        'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia',
        'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia', 'Puerto Rico', 'Guam',
        'U.S. Virgin Islands', 'Northern Mariana Islands'
    ]

    all_area_codes = set()
    for region in regions:
        codes = area_code_nanp.get_area_codes(region)
        if codes is not None:
            all_area_codes.update(codes)

    return sorted(list(all_area_codes))


area_codes = get_all_area_codes()

# Names filter
with open('first_names.txt', 'r') as file:
    first_names = file.read().lower().split(',')


# Main function
class ScrapeProcess(object):
    def __init__(self, filename, email_only, no_gov, indefinite):
        if os.path.isfile(filename):
            filename = f"{os.path.splitext(filename)[0]}_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        self.filename = filename
        # Adding new values to be used for post-processing
        self.num_pages = -1
        self.indefinite = indefinite
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
            "baidu": BaiduSearch,
            "bing": BingSearch,
            "duckduckgo": DuckDuckGoSearch,
            "glocation": GoogleSearch,
            "google": GoogleSearch,
            "naver": NaverSearch,
            "yahoo": YahooSearch,
            "yandex": YandexSearch,
        }
        self.visited_pages = set()
        # Overwriting post_processed file if pages is indefinite
        if self.indefinite:
            with open('processed_' + self.filename, 'w+') as f:
                writer = csv.writer(f)
                writer.writerow(['title', 'link', 'email', 'phone', 'entity'])

    @staticmethod
    def validate_email(email):
        email_regex = re.compile(r'[^@]+@[^@]+\.[^@]+')
        return email_regex.match(email)

    @staticmethod
    def get_tld(email):
        return email.split('.')[-1]

    def spider_page(self, page, original_domain):
        soup = BeautifulSoup(page, 'html.parser')
        for link in soup.find_all('a'):
            url = link.get('href')
            # Check that url is not None and is a relative URL or on the same domain
            if url is not None and (not url.startswith('http') or urllib.parse.urlparse(url).netloc == original_domain):
                # Construct absolute URL
                url = urllib.parse.urljoin(page, url)
                # Avoid visiting the same page twice
                if url not in self.visited_pages:
                    self.visited_pages.add(url)
                    self.process_page(url)

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
                print(
                    f"Invalid engine specified: {engine}. Please choose from {', '.join(self.search_engines.keys())}, or 'all', or 'american'.")
                return
            self.scrape(query, pages, engine, serp_api_key)

    """
        To scraping indefinitely, run the loop forever until keyboard interrupt.
    """

    def scrape(self, query, num_pages, engine, api_key):
        page_infinite = False
        if type(num_pages) is str and num_pages == 'all':
            print("Enter Ctrl-C or Ctrl-Z when satisfied")

            page_infinite = True
            num_pages = 0
        else:
            num_pages = int(num_pages)
        i = 0
        try:
            while (i < num_pages) or page_infinite:
                self.num_pages = i
                params = {
                    "engine": engine,
                    "num": 100,
                    "api_key": api_key,
                    # 'async': True,  # for async requests
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
                    try:
                        location = GoogleSearch({}).get_location("Rockville, MD", 1)[0]["canonical_name"]
                        params["q"] = query
                        params["location"] = location
                    except IndexError:
                        print("Could not fetch location. Skipping...")
                else:
                    params["q"] = query
                    params["start"] = i * 100
                search = self.search_engines[engine](params)
                results = search.get_dict().get('organic_results', [])
                print(f'Number of results: {len(results)}')
                for page in results[:1]:
                    self.process_page(page)
                i += 1
        except KeyboardInterrupt:
            print("Ending Process. CSV Updated.")
            raise "Exiting"

    def process_page(self, page):
        if self.no_gov and ".gov" in page["link"]:
            print(f'Skipping .gov page: {page["link"]}')
            return
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
            request = Request(page['link'], headers=headers)
            html = urlopen(request).read().decode('utf8')
            print(f'Scraping page: {page["link"]}')
        except Exception as e:
            print(f'Could not scrape page: {page["link"]} due to {e}')
            return

        # Remove HTML tags using BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        text = soup.get_text()

        # Changing regex pattern for emails
        emails = re.findall(r'[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+', text)
        phones = re.findall(r'\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b', text)

        entities = {}
        if args.S:
            if len(text) > 100000:
                print("Text too long for NLP, skipping...")
            else:
                doc = nlp(text)
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
                            # self.csvfile.flush()
                    else:
                        print(f'Found email: {email}')
                        self.emails[email] = (page['title'], page['link'])
                        # self.csvfile.flush()
                    # Spider the page:
                    self.spider_page(page['link'], urllib.parse.urlparse(page['link']).netloc)

        if args.P:
            for phone in phones:
                # Normalize phone to just digits
                phone_digits = re.sub(r'\D', '', phone)
                area_code = phone_digits[:3]
                # Fixing area_code
                if int(area_code) not in area_codes:
                    continue
                print(f'Found phone: {phone}')
                self.phones[phone] = (page['title'], page['link'])
                # self.csvfile.flush()

        if args.N:
            for entity, label in entities.items():
                if label in ["DATE", "CARDINAL", "PRODUCT", "GPE", "ORG", "LANGUAGE", "MONEY", "NORP", "TIME"]:
                    continue
                if label == "PERSON" and not re.match(r'\w+ \w+', entity):
                    continue
                if label == "PERSON":
                    name_parts = entity.split()
                    if len(name_parts) in [2, 3] and name_parts[0].lower() in first_names:
                        if len(name_parts) == 3:
                            # Check if the second part is a middle initial
                            if re.fullmatch(r"[A-Z]\.", name_parts[1]):
                                print(f'Found entity: {entity} ({label})')
                                self.entities[entity] = (label, page['title'], page['link'])
                        else:
                            print(f'Found entity: {entity} ({label})')
                            self.entities[entity] = (label, page['title'], page['link'])
        # Post-processing after scraping a page immediately if num_pages is all
        if self.indefinite:
            self.post_process()

    def post_process(self, post_process=False):
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

        if post_process:
            with open('processed_' + self.filename, 'w+') as f:
                writer = csv.writer(f)
                writer.writerow(['title', 'link', 'email', 'phone', 'entity'])
        with open('processed_' + self.filename, 'a+') as f:
            writer = csv.writer(f)
            for link, data in results.items():
                writer.writerow([data['title'], link, '; '.join(data['email']), '; '.join(data['phone']),
                                 '; '.join([f'{e} ({l})' for e, l in data['entity']])])

        self.csvfile.close()


"""
    For all pages, the argument for -p must be 'all'. For example:
        python3 mmees.py -query "apple" -o apple -pages all -e "google" -Ng
"""
parser = argparse.ArgumentParser(description='Scrape search results for leads')
parser.add_argument('-e', '--engine', type=str, default="google",
                    help="The search engine to use (google, bing, duckduckgo, yahoo, yandex, baidu, yelp, all)")
parser.add_argument('-E', action='store_true', default=True, help='Enable email scraping')
parser.add_argument('-Eo', action='store_true', help='Email only output')
parser.add_argument('-key', type=str, default=os.getenv('SERP_API_KEY'), help='Serp API key')
parser.add_argument('-N', action='store_true', default=True, help='Enable named entity scraping')
parser.add_argument('-Ng', action='store_true', help='Exclude .gov emails')
parser.add_argument('-o', type=str, default='emails.csv', help='output filename')
parser.add_argument('-P', action='store_true', default=True, help='Enable phone number scraping')
parser.add_argument('-PP', action='store_true', help='Enable post-processing (lowercase and dedupe)')
parser.add_argument('-pages', default=2, help='Number of search results pages to scrape per engine')
parser.add_argument('-query', type=str, default='test', help='A query to use for the search')
parser.add_argument('-S', action='store_true', default=True, help='Use SpaCy ML to perform entity detection.')

args = parser.parse_args()
args.o = args.o + '.csv' if '.csv' not in args.o else args.o

if args.S is True:
    nlp = spacy.load('en_core_web_sm')

s = ScrapeProcess(args.o, args.Eo, args.Ng, args.pages == "all")
if args.engine == "all":
    threads = []
    try:
        for engine in s.search_engines:
            t = threading.Thread(target=s.go, args=(args.query, args.pages, engine))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    except:
        print("Not waiting for all threads to join. Exiting.")
        exit()
else:
    try:
        s.go(args.query, args.pages, args.engine)
    except:
        print("Exiting")
        exit()

if args.PP and args.pages != "all":
    s.post_process(args.PP and args.pages != "all")
