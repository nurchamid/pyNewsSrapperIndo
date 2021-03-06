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

class Rumahhokie:
    def getAllBerita(self, details, page, date=datetime.strftime(datetime.today(), '%Y/%m/%d')):
        """
        Untuk mengambil seluruh url rajamobil
        link pada indeks category tertentu
        category = berita
        date = Y/m/d
        """

        print("page ", page)
        url = "http://www.rumahhokie.com/beritaproperti/page/"+str(page)+"/?s"
        print(url)
        # Make the request and create the response object: response
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(10)
            details = self.getAllBerita(details, page, date)
        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")
        indeks = soup.findAll('div', class_="td_module_16 td_module_wrap td-animation-stack")
        flag = True
        for post in indeks:
            if not post.find('a', class_="td-post-category"):
                continue
            link = [post.find('h3', class_="entry-title td-module-title").find('a', href=True)['href'], post.find('a', class_="td-post-category").get_text(strip=True)]
            #check if there are a post with same url
            con = mysql.connector.connect(user='root', password='', host='127.0.0.1', database='news_db')
            cursor = con.cursor()
            query = "SELECT count(*) FROM article WHERE url like '"+link[0]+"'"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            con.close()
            if(result[0] > 0):
                flag = False
                break
            else:
                detail = self.getDetailBerita(link)
                if detail:
                    if self.insertDB(detail):
                        details.append(detail)

        if flag:
            el_page = soup.find('div', class_="page-nav td-pb-padding-side")
            if el_page:
                if el_page.find('a', class_="last"):
                    max_page = int(el_page.find('a', class_="last").get_text(strip=True).strip(' '))
                else :
                    max_page = page+1

                # max_page = 3
                if page <= max_page:
                    time.sleep(5)
                    details = self.getAllBerita(details, page+1, date)

        return 'berhasil ambil semua berita'

    def getDetailBerita(self, link):
        """
        Mengambil seluruh element dari halaman berita
        """
        time.sleep(5)
        articles = {}
        #link
        url = link[0]
        if ('video' in url.split('/')) or ('foto' in url.split('/')) or ('uncategorized' in url.split('/')) or ('promo' in url.split('/')):
            return False

        response = requests.get(url)
        html2 = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html2, "html5lib")

        #category
        articles['category'] = 'Properti'
        articles['subcategory'] = link[1]

        articles['url'] = url
        print(url)

        article = soup.find('div', class_="td-ss-main-content")

        #extract date
        pubdate = soup.find('meta', {'property':'article:published_time'})
        pubdate = pubdate['content'] if pubdate else '1970-01-01T00:00:00+00:00'
        pubdate = pubdate[0:19].strip(' \t\n\r')
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%S"), '%Y-%m-%d %H:%M:%S')

        id = soup.find('link', {'rel':'shortlink'})
        articles['id'] = int(id['href'].replace('http://www.rumahhokie.com/beritaproperti/?p=', ''))     if id else int(datetime.strptime(pubdate, "%Y-%m-%dT%H:%M:%S").timestamp()) + len(url)

        #extract author
        author = soup.find('div', {'class': 'td-post-author-name'}).find('a')
        articles['author'] = author.get_text(strip=True).strip(' \t\n\r') if author else ''

        #extract title
        title = soup.find('h1', {'class': 'entry-title'})
        articles['title'] = title.get_text(strip=True).strip(' \t\n\r') if title else ''

        #source
        articles['source'] = 'rumahhokie'

        #extract comments count
        articles['comments'] = 0

        #extract tags
        tags = article.findAll('meta', {"property":"article:tag"})
        articles['tags'] = ','.join([x['content'] for x in tags]) if tags else ''

        #extract images
        images = soup.find("meta", attrs={'property':'og:image'})
        articles['images'] = images['content'] if images else ''

        #extract detail
        detail = article.find('div', attrs={"class":"td-post-content"})

        #hapus video sisip
        if detail.findAll('div'):
            for div in detail.findAll('div'):
                if div.find('script'):
                    div.decompose()

        #hapus all script
        for script in detail.findAll('script'):
            script.decompose()

        #hapus all noscript
        for ns in detail.findAll('noscript'):
            ns.decompose()

        #hapus all figure
        for fig in detail.findAll('figure'):
            fig.decompose()

        #hapus linksisip
        for ls in detail.findAll('ul'):
            if ls.find('em'):
                if 'baca' in ls.find('em').get_text(strip=True).lower():
                    ls.decompose()

        #extract content
        detail = BeautifulSoup(detail.decode_contents().replace('<br/>', ' '), "html5lib")
        content = re.sub(r'\n|\t|\b|\r','',unicodedata.normalize("NFKD",detail.get_text(strip=True)))
        articles['content'] = content
        print('memasukkan berita id ', articles['id'])

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
