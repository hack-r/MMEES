
# MMEES Lead Generation

<div align="center">
  <img src="./MMEES.png" alt="Image Alt Text" width="width: 160px; height: 90px;">
</div>

A FOSS lead scraping tool developed by:

	Jason Miller
	Libre Agora, LLC. 

https://github.com/hack-r

NOTE: Serp API has a **free** plan - 100 searches/month, I believe. I don't work for them, but these engines change so much that if you build a traditional scraper today, it will likely be broken a next week or next month. This is a convenient solution and bypasses IP throttling as well.

## Description

MMEES = Miller's Multi-Engine E-mail Scraper. A bit of a misnomer, as it now also scrapes phones and names.

This tool extracts emails, phone numbers, and named entities from search results across multiple search engines. It supports Baidu, Bing, DuckDuckGo, Google (with or without location), Naver, Yahoo, Yelp, Yandex.

**Please ensure that you are complying with all relevant policies, laws, and regulations when using this tool. Usage is at your own risk.**

## Installation

First, clone the repository and navigate to the project directory.

Then, install the dependencies using pip:

```
pip install -r requirements.txt
```

You'll also need to install a Spacy model, if you want to extract names. 

```
python -m spacy download en_core_web_sm
```

## Usage

The script can be run from the command line with a number of arguments:

```
python mmees.py -query "OpenAI" -pages 2 -o "openai_info.csv" -e "american" -PP -Ng
```

Here are the available options:

* `-e` : The search engine to use (default: "google"). Options are "google", "bing", "duckduckgo", "yahoo", "yandex", "baidu", "yelp", "naver", "glocation", "all", or "american". The "american" option includes all engines except Baidu, Naver, and Yandex. The "glocation" option uses Google Search by location, with Rockville, MD as the default location.
* `-E` : Enable email scraping (default: True)
* `-Eo` : Email only output
* `-key` : Your Serp API key
* `-N` : Enable named entity scraping (default: True)
* `-Ng` : Exclude .gov emails
* `-o` : Output filename (default: 'emails.csv')
* `-P` : Enable phone number scraping (default: True)
* `-PP` : Enable post-processing (lowercase and dedupe)
* `-pages` : Number of search results pages to scrape per engine (default: 2)
* `-query` : The query to use for the search (default: 'test')
* `-S` : Enable entity detection via SpaCy (make sure you have downloaded the model... see  Important Installation Note.txt). This option is not recommended and may require manual editing of mmees.py.

It is **HIGHLY recommended** to use the "-PP" option. Results are written in "long" format while the app is running. If it completes successfully with the "-PP" option enabled it will, among other things, attempt to transform the data set from long to wide. This is only somewhat possible as a single page may have multiple emails, phone numbers, and names, however you'll still end up with a shorter data set than the long version. Names tend to generate a lot of uninteresting matches, so I've limited it to those that appear to have a first and last name, with an optional middle initial. 

If you're interested in other Spacy entity types it is a trivial edit to uncomment those lines.

Storage of your Serp API key in a .env file is supported.

Spacy's "PERSON" entity type seemed extremely unreliable for this type of data, so I created a list of the top 800 most common first names and used that for filtering. I did the same with US area codes.

## License

This project is licensed under the terms of the MIT license.