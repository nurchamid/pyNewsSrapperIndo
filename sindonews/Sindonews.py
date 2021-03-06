import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import locale
locale.setlocale(locale.LC_ALL, 'ID')
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time
from requests.exceptions import ConnectionError
import unicodedata
import mysql.connector

class Sindonews:
    def getAllBerita(self, details, page, cat_link, offset, date=datetime.strftime(datetime.today(), '%Y-%m-%d')):
        """
        Untuk mengambil seluruh url
        link pada indeks category tertentu
        date format : YYYY/mm/dd
        """

        print("page ", page)
        url = "https://index.sindonews.com/index/"+ str(cat_link)+ "/" + str(offset)+ "?t="+ date
        print(url)

        # Make the request and create the response object: response
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(5)
            details = self.getAllBerita(details, page, cat_link, offset, date)
        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        contentDiv = soup.find('div', class_="indeks-news")
        if contentDiv:
            for post in contentDiv.findAll('div', class_="indeks-title"):
                link = [post.find('a', href=True)['href'], ""]
                detail = self.getDetailBerita(link)
                if detail:
                    if self.insertDB(detail):
                        details.append(detail)

            el_page = soup.find('div', class_="pagination")
            if el_page:
                active_page = el_page.find('li', class_="active").get_text(strip=True)
                max_page = el_page.findAll('a')[-1]
                if max_page:
                    if active_page != max_page.get_text(strip=True):
                        time.sleep(5)
                        details = self.getAllBerita(details, page+1, cat_link, offset+10, date)
                    # else:
                    #     max_page = page
        return 'berhasil ambil semua berita'

    def getDetailBerita(self, link):


        time.sleep(5)
        articles = {}
        #link
        url = link[0]
        response = requests.get(url)
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")

        #extract subcategory from breadcrumb
        bc = soup.find('ul', class_="breadcrumb")
        if not bc:
            return False
        cat = bc.findAll('a')[-2].get_text(strip=True)
        sub = bc.findAll('a')[-1].get_text(strip=True)

        #articleid
        url_split = url.replace('//','').split('/')
        article_id = url_split[2]
        articles['id'] = article_id

        #category
        articles['category'] = cat
        articles['subcategory'] = sub

        #article_url
        articles['url'] = url

        #article
        article = soup.find("div", id="content")
        if not article:
            return False

        #extract date
        pubdate = soup.find('time').get_text(strip=True)
        pubdate = pubdate.strip(' \t\n\r')
        pubdate = pubdate.replace(' WIB','')
        pubdate = pubdate.replace("Jum'at", "Jumat")
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%A, %d %B %Y - %H:%M"), "%Y-%m-%d %H:%M:%S")

        #extract author
        # reporter = soup.find('div', class_="reporter")
        author = soup.find('p', class_="author")
        articles['author'] = author.find('a').get_text(strip=True) if author else ''

        #extract title
        title = soup.find('div', class_="article")
        articles['title'] = title.find('h1').get_text(strip=True) if title else ''

        #source
        articles['source'] = 'Sindonews'

        #extract comments count
        articles['comments'] = 0

        #extract tags
        tags = soup.find('div', class_='tag-list')
        articles['tags'] = ','.join([x.get_text(strip=True) for x in tags]) if tags else ''

        #extract images
        image = soup.find('div', class_="article").find('img')
        articles['images'] = image['src'] if image else ''

        # hapus link baca juga
        for baca in article.findAll('strong'):
            if "baca juga" in baca.get_text(strip=True).lower():
                baca.decompose()

        # hapus script comments
        for script in article.findAll('script'):
            script.decompose()

        #hapus link sisip image
        for link in article.findAll('img'):
            link.decompose() if link else ''

        #extract content
        detail = BeautifulSoup(article.decode_contents().replace('<br/>', ' '), "html5lib")
        content = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",detail.get_text(strip=True)))

        #articles['content'] = re.sub('google*','', content).strip(' ')
        articles['content'] = content
        #print('memasukkan berita id ', articles['id'])

        return articles

    def insertDB(self, articles):
        """
        Untuk memasukkan berita ke DB
        """
        con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
        print(articles['url'])
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
