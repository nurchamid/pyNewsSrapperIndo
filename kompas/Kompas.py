import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import locale
locale.setlocale(locale.LC_ALL, 'ID')
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import html
import json
import time
from requests.exceptions import ConnectionError
import unicodedata
import mysql.connector

# from selenium import webdriver
# from selenium.webdriver.support.wait import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
# from selenium.webdriver.common.by import By

class Kompas:
    def getAllBerita(self, details, page, cat_link, category, date=datetime.strftime(datetime.today(), '%Y-%m-%d')):
        """
        Untuk mengambil seluruh url
        link pada indeks category tertentu
        date format : YYYY-mm-dd
        """

        print("page ", page)
        url = "https://indeks.kompas.com/"+cat_link+"/"+date+"/"+str(page)
        print(url)
        # Make the request and create the response object: response

        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(20)
            details = self.getAllBerita(details, page, cat_link, category, date)

        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")
        contentDiv = soup.findAll('div', class_="article__list clearfix")
        for post in contentDiv:
            link = [post.find('a', href=True)['href'], category]
            detail = self.getDetailBerita(link)
            if detail:
                if self.insertDB(detail):
                    details.append(detail)

        el_page =  soup.find('div', class_="paging__wrap clearfix")
        if el_page:
            a_page = el_page.findAll('div', class_='paging__item')[-1].find('a')
            if  el_page.findAll('div', class_='paging__item')[-1].find('a', class_="paging__link paging__link--active"):
                max_page = page
            else:
                max_page = int(a_page['data-ci-pagination-page'].replace('\n', '').strip(' '))

            if page < max_page:
                time.sleep(20)
                details = self.getAllBerita(details, page+1, cat_link, category, date)



        return 'berhasil ambil semua berita'

    def getDetailBerita(self, link):

        time.sleep(20)
        articles = {}
        #link
        url = link[0]
        response = requests.get(url)
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        #articleid
        articles['id'] = int(soup.find("meta", attrs={'name':'cXenseParse:articleid'})['content'])

        #category
        articles['category'] = link[1]
        articles['url'] = url

        #extract subcategory from breadcrumb
        bc = soup.find('ul', class_="breadcrumb__wrap")
        articles['subcategory'] = bc.findAll('li')[2].get_text(strip=True)

        #article
        article = soup.find("div", class_="read__content")

        #extract date
        pubdate = soup.find("meta", attrs={"name":"content_PublishedDate"})['content']
        pubdate = pubdate.strip(' \t\n\r')
        articles['pubdate']=datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S")

        #extract author
        articles['author'] = soup.find('div', class_="read__author").get_text(strip=True)

        #extract title
        articles['title'] = soup.find('h1', class_="read__title").get_text(strip=True)

        #source
        articles['source'] = 'kompas'

        #extract comments count
        #articles['comments'] = 0
        # options = Options()
        # options.add_argument('--headless')
        # options.add_argument('--disable-gpu')  # Last I checked this was necessary.
        # options.add_argument('--disable-extensions')
        #
        # driver = webdriver.Chrome("../chromedriver.exe", chrome_options=options)
        # driver.get(url)
        # html = driver.page_source
        # soup = BeautifulSoup(html, 'html5lib')
        #
        # comment = soup.find('div', class_="span4 comments-count tright")
        # comment_num = comment.get_text(strip=True).replace('Ada ', '')
        # comment_num = comment_num.replace(' komentar untuk artikel ini', '')
        articles['comments'] = 0

        #extract tags
        tags = soup.find("meta", attrs={'name':'content_tag'})['content']
        articles['tags'] = tags

        #extract images
        articles['images'] = soup.find('meta', attrs={'property':'og:image'})['content']

        #hapus all script
        for script in article.findAll('script'):
            script.decompose()

        for baca in article.findAll('p'):
            if baca.find('strong'):
                if 'baca juga:' in baca.find('strong').get_text(strip=True).lower():
                    baca.decompose()

        #extract content
        detail = BeautifulSoup(article.decode_contents().replace('<br/>', ' '), "html5lib")
        content = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",detail.get_text(strip=True)))
        articles['content'] = content
        #print('memasukkan berita id ', articles['id'])

        return articles

    def insertDB(self, articles):
        """
        Untuk memasukkan berita ke DB
        """
        con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
        print("Insert berita ", articles['title'])
        cursor = con.cursor()
        query = "SELECT count(*) FROM article WHERE url like '"+articles['url']+"'"
        cursor.execute(query)
        result = cursor.fetchone()
        if result[0] <= 0:
            add_article = ("INSERT INTO article (post_id, author, pubdate, category, subcategory, content, comments, images, title, tags, url, source) VALUES (%(id)s, %(author)s, %(pubdate)s, %(category)s, %(subcategory)s, %(content)s, %(comments)s, %(images)s, %(title)s, %(tags)s, %(url)s, %(source)s)")
            # Insert article
            cursor.execute(add_article, articles)
            con.commit()
            print('masuk')
            cursor.close()
            con.close()
            return True
        else:
            cursor.close()
            print('salah2')
            con.close()
            return False
