# Miller's Multi-Engine Email Scraper (MMEES)

This tool scrapes email addresses from all major search engines' results. You can specify the search query, the number of pages of search results to scrape, and the output filename. The tool supports multiple search engines: Google, Bing, DuckDuckGo, Yahoo, Yandex, Baidu, and Yelp. 

by Jason M. (https://github.com/hack-r)

SerpAPI does most of the heavy lifting.

## How to Run

1. Clone this repository.
2. Install the required Python packages: `pip install -r requirements.txt`
3. Set up your .env file with your SerpAPI key: `SERP_API_KEY=your_api_key`
4. Run the script: `python scraper.py -query "your search term" -pages 10 -o output.csv -e google`

## Command-Line Arguments

- `-query`: The search term to use. Default is "test".
- `-pages`: The number of search result pages to scrape. Default is 10.
- `-o`: The output filename. Default is "emails.csv".
- `-key`: Your SerpAPI key. Default is the key in your .env file.
- `-P`: Enable post-processing (lowercase and dedupe).
- `-Eo`: Output only email addresses.
- `-Ng`: Exclude .gov email addresses.
- `-e`, `--engine`: The search engine to use (google, bing, duckduckgo, yahoo, yandex, baidu, yelp, all). Default is "google".

It is highly recommended to use "-P", unless your use case is very different from the usual ones and you want to avoid any loss of information.

## Output Format

The output file is a CSV file with the following columns:

- Page title: The title of the page where the email address was found.
- Page link: The URL of the page where the email address was found.
- Email: The email address.

If the `-Eo` option is used, the output file will contain only the email addresses.
