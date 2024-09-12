import os
from abc import ABC, abstractmethod
import requests
from bs4 import BeautifulSoup
import json
import logging
from typing import List, Tuple
from config import setup_shared_logger


class BaseScraper(ABC):
    """
    A base class for web scrapers, providing common functionalities such as downloading PDFs,
    saving metadata, and processing non-PDF URLs. Specific scrapers should inherit from this
    class and implement their own search and URL extraction methods.
    """

    def __init__(self, key_words, base_url, limited_pages, driver, site_name):
        """
        Initializes the BaseScraper with the given parameters.

        :param key_words: A list of keywords to search for on the site.
        :param base_url: The base URL of the website to scrape.
        :param limited_pages: The maximum number of pages to process.
        :param driver: A Selenium WebDriver instance.
        :param site_name: The name of the site being scraped.
        """
        self.key_words = key_words
        self.base_url = base_url
        self.limited_pages = limited_pages
        self.driver = driver
        self.site_name = site_name
        self.logger = setup_shared_logger(f"{site_name}_log")

    @abstractmethod
    def search_for_keyword(self, keyword):
        """
        Abstract method to be implemented by subclasses to define how a keyword is searched on the website.

        :param keyword: The keyword to search for.
        """
        pass

    @abstractmethod
    def get_urls(self, keyword, limited_pages):
        """
        Abstract method to be implemented by subclasses to define how URLs are extracted from the website.

        :param keyword: The keyword to search for.
        :param limited_pages: The maximum number of pages to process.
        :return: A tuple of lists containing PDF URLs and non-PDF URLs.
        """
        pass

    def start(self):
        """
        Starts the scraping process by iterating through the list of keywords, downloading PDFs,
        and processing non-PDF URLs.
        """
        self.logger.info("Starting the scraping process.")
        for keyword in self.key_words:
            self.create_folder_structure(keyword)
            pdf_urls, non_pdf_urls = self.get_urls(keyword, self.limited_pages)
            pdf_data = self.download_pdf_files(pdf_urls, keyword)
            self.save_pdf_data(keyword, pdf_data)
            self.process_non_pdf_urls(non_pdf_urls, keyword)
        self.driver.quit()
        self.logger.info("Scraping process completed.")

    def create_folder_structure(self, keyword):
        """
        Creates the folder structure for storing raw data (PDFs, metadata, text, etc.) based on the keyword.

        :param keyword: The keyword for which the folder structure is created.
        """
        keyword_folder = os.path.join(f"data/raw/{self.site_name}", keyword.replace(':', '').replace(' ', '_'))
        os.makedirs(keyword_folder, exist_ok=True)
        os.makedirs(os.path.join(keyword_folder, 'pdf'), exist_ok=True)
        os.makedirs(os.path.join(keyword_folder, 'text'), exist_ok=True)
        os.makedirs(os.path.join(keyword_folder, 'metadata'), exist_ok=True)
        os.makedirs(os.path.join(keyword_folder, 'json'), exist_ok=True)
        self.logger.info(f"Folder structure created for {keyword}.")

    def download_pdf_files(self, urls: List[Tuple[str, str, str, str]], keyword: str) -> List[dict]:
        """
        Downloads PDF files from the provided list of URLs and saves their metadata and descriptions.

        :param urls: A list of tuples containing the URL, date, file name, and description.
        :param keyword: The keyword associated with the search.
        :return: A list of dictionaries containing PDF file data and metadata.
        """
        self.logger.info(f"Downloading PDF files for keyword: {keyword}")
        data = []
        for url, date, name, description in urls:
            try:
                pdf_response = requests.get(url)
                data.append({
                    'url': url,
                    'date': date,
                    'file_name': name,
                    'content': pdf_response.content
                })
                self.logger.info(f"Downloaded: {name}")
                self.save_metadata(keyword, {
                    "name": name,
                    "notified_date": date,
                    "notified_country": None,
                    "URL": url,
                    "keyword": keyword
                })
                self.save_summary(keyword, url, date, name, description)
            except Exception as e:
                self.logger.error(f"Error downloading {url}: {str(e)}")
        return data

    def process_non_pdf_urls(self, urls: List[Tuple[str, str, str, str]], keyword: str):
        """
        Processes non-PDF URLs by downloading the content, extracting tables, and saving the metadata and description.

        :param urls: A list of tuples containing the URL, date, file name, and description.
        :param keyword: The keyword associated with the search.
        """
        self.logger.info(f"Processing non-PDF URLs for keyword: {keyword}")
        for url, date, name, description in urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                self.save_summary(keyword, url, date, name, description)
                self.extract_and_save_tables(soup, keyword, name, date)
                self.logger.info(f"Extracted summary and checked for tables from: {url}")
                self.save_metadata(keyword, {
                    "name": name,
                    "notified_date": date,
                    "notified_country": None,
                    "URL": url,
                    "keyword": keyword
                })
            except Exception as e:
                self.logger.error(f"Error processing {url}: {str(e)}")

    def save_metadata(self, keyword: str, metadata: dict):
        """
        Saves the metadata for a specific document in a JSON file.

        :param keyword: The keyword associated with the search.
        :param metadata: A dictionary containing metadata information.
        """
        metadata_folder = os.path.join(f'data/raw/{self.site_name}', keyword.replace(':', '').replace(' ', '_'),
                                       'metadata')
        os.makedirs(metadata_folder, exist_ok=True)
        metadata_file_name = os.path.join(metadata_folder, f"metadata_{metadata['name']}.json")
        with open(metadata_file_name, 'w', encoding='utf-8') as metadata_file:
            json.dump(metadata, metadata_file, ensure_ascii=False, indent=4)
        self.logger.info(f"Metadata saved to {metadata_file_name}")

    def save_summary(self, keyword: str, url: str, date: str, name: str, description: str):
        """
        Saves the summary of a document in a text file.

        :param keyword: The keyword associated with the search.
        :param url: The URL of the document.
        :param date: The distribution date of the document.
        :param name: The name of the document.
        :param description: The description or summary of the document.
        """
        text_folder = os.path.join(f'data/raw/{self.site_name}', keyword.replace(':', '').replace(' ', '_'), 'text')
        os.makedirs(text_folder, exist_ok=True)
        summary_file_name = os.path.join(text_folder, f"{name}.txt")
        with open(summary_file_name, 'w', encoding='utf-8') as summary_file:
            summary_file.write(f"Title: {name}\n")
            summary_file.write(f"Distribution date: {date}\n")
            summary_file.write(f"Keywords: {keyword}\n")
            summary_file.write(f"Summary: {description}\n")
        self.logger.info(f"Summary saved to {summary_file_name}")

    def save_pdf_data(self, keyword: str, data: List[dict]):
        """
        Saves downloaded PDF files to the appropriate directory.

        :param keyword: The keyword associated with the search.
        :param data: A list of dictionaries containing the PDF file content and metadata.
        """
        pdf_folder = os.path.join(f'data/raw/{self.site_name}', keyword.replace(':', '').replace(' ', '_'), 'pdf')
        os.makedirs(pdf_folder, exist_ok=True)
        for item in data:
            pdf_name = os.path.join(pdf_folder, f"{item['file_name']}.pdf")
            with open(pdf_name, 'wb') as pdf_file:
                pdf_file.write(item['content'])
            self.logger.info(f"PDF saved to {pdf_name}")

    def extract_and_save_tables(self, soup: BeautifulSoup, keyword: str, name: str, date: str):
        """
        Extracts tables from a webpage and saves them as JSON files.

        :param soup: The BeautifulSoup object representing the page content.
        :param keyword: The keyword associated with the search.
        :param name: The name of the document.
        :param date: The distribution date of the document.
        """
        self.logger.info(f"Extracting tables from page: {name}")
        tables_data = []
        tables = soup.find_all('table')
        for i, table in enumerate(tables):
            headers = [th.get_text().strip() for th in table.find_all('th')]
            rows = [
                [cell.get_text().strip() for cell in row.find_all('td')]
                for row in table.find_all('tr') if row.find_all('td')
            ]
            if rows and headers:
                table_data = {
                    'headers': headers,
                    'rows': rows
                }
                tables_data.append(table_data)
        if tables_data:
            json_folder = os.path.join(f'data/raw/{self.site_name}', keyword.replace(':', '').replace(' ', '_'), 'json')
            os.makedirs(json_folder, exist_ok=True)
            table_file_name = os.path.join(json_folder, f"{name}.json")
            with open(table_file_name, 'w', encoding='utf-8') as table_file:
                json.dump(tables_data, table_file, ensure_ascii=False, indent=4)
            self.logger.info(f"Saved tables to {table_file_name}")

    def log_error(self, error: Exception, url: str):
        """
        Logs errors that occur during the scraping process.

        :param error: The exception that occurred.
        :param url: The URL being processed when the error occurred.
        """
        self.logger.error(f"An error occurred while downloading {url}: {str(error)}")
