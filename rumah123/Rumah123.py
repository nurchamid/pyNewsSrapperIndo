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
from requests.exceptions import ConnectionError, TooManyRedirects
import unicodedata
import mysql.connector

class Rumah123:
    def getAllBerita(self, details, page, date=datetime.strftime(datetime.today(), '%Y/%m/%d')):
        """
        Untuk mengambil seluruh url rajamobil
        link pada indeks category tertentu
        category = berita
        date = Y/m/d
        """

        print("page ", page)
        url = "https://artikel.rumah123.com/search?page="+str(page)
        print(url)
        # Make the request and create the response object: response
        try:
            response = requests.get(url)
        except ConnectionError:
            print("Connection Error, but it's still trying...")
            time.sleep(10)
            details = self.getAllBerita(details, page, date)
        except TooManyRedirects:
            return False
        # Extract HTML texts contained in Response object: html
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")
        # print(soup)
        contentDiv = soup.find('div', {'id':'news-list-container'})
        indeks = contentDiv.findAll('li', class_="list-group-item")
        flag = True
        for post in indeks:
            link = [post.find('a', href=True)['href'], ""]
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
                if detail :
                    if self.insertDB(detail):
                        details.append(detail)

        if flag:
            el_page = soup.find('ul', class_="pagination")
            if el_page:
                max_page = el_page.findAll('li')[-2].get_text(strip=True).strip(' ')
                active_page = el_page.find('li', {'class':'active'}).get_text(strip=True).strip(' ')
                # max_page = 3
                if active_page != max_page:
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
        try:
            response = requests.get(url)
        except TooManyRedirects:
            return False
        except:
            return False
        html = response.text
        # Create a BeautifulSoup object from the HTML: soup
        soup = BeautifulSoup(html, "html5lib")
        bc = soup.find('ol', class_="breadcrumb")
        #category
        articles['category'] = 'Properti'
        articles['subcategory'] = bc.findAll('li')[-2].get_text(strip=True) if bc else ''
        if ('photo' in articles['subcategory'].lower()) or ('video' in articles['subcategory'].lower()):
            return False

        articles['url'] = url

        article = soup.find('div', class_="post-wrapper")
        if not article:
            return False

        #extract date
        pubdate = article.find('meta', {'itemprop':'datePublished'})
        pubdate = pubdate['content'][:-2] if pubdate else '1970-01-01 01:01:01'
        pubdate = pubdate.strip(' \t\n\r')
        articles['pubdate'] = datetime.strftime(datetime.strptime(pubdate, "%Y-%m-%d %H:%M:%S"), '%Y-%m-%d %H:%M:%S')
        articles['id'] = int(url.split('-')[-1])

        #extract author
        author = article.find('div', {'class': 'post-author'})
        articles['author'] = author.get_text(strip=True) if author else ''

        #extract title
        title = soup.find('meta', {'property':'og:title'})
        articles['title'] = title['content'] if title else ''

        #source
        articles['source'] = 'rumah123'

        #extract comments count
        articles['comments'] = 0

        #extract tags
        # tags = article.findAll('meta', {"property":"article:tag"})
        #tag tidak tersedia
        articles['tags'] = ''

        #extract images
        images = soup.find("meta", attrs={'property':'og:image'})
        articles['images'] = images['content'] if images else ''

        #extract detail
        detail = article.find('div', {"class":"post-text"})

        #hapus video sisip
        for div in detail.findAll('div'):
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
        for ls in detail.findAll('p'):
            if ls.find('p'):
                if 'baca' in ls.find('p').get_text(strip=True).lower():
                    if (ls.find('strong')) and (ls.find('a')):
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
