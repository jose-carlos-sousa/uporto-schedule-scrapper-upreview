import getpass
import hashlib
import re
import scrapy
from datetime import datetime
from scrapy.http import Request, FormRequest
import urllib.parse
from configparser import ConfigParser, ExtendedInterpolation
import json
from datetime import time

from scrapper.settings import CONFIG, PASSWORD, USERNAME

from ..database.Database import Database
from ..items import  ExchangeFaculty, ExchangeFacultyCourse

class ExchangeFacultySpider(scrapy.Spider):
    name = "exchange_faculties"
    allowed_domains = ['sigarra.up.pt']
    login_page_base = 'https://sigarra.up.pt/feup/pt/mob_val_geral.autentica'
    days = {'Segunda-feira': 0, 'Terça-feira': 1, 'Quarta-feira': 2,
            'Quinta-feira': 3, 'Sexta-feira': 4, 'Sábado': 5}

    def __init__(self, password=None, category=None, *args, **kwargs):
        super(ExchangeFacultySpider, self).__init__(*args, **kwargs)
        self.open_config()
        self.user = USERNAME
        self.password = PASSWORD
        self.professor_name_pattern = r"\d+\s-\s[A-zÀ-ú](\s[A-zÀ-ú])*"
        self.inserted_teacher_ids = set()

    def open_config(self):
        """
        Reads and saves the configuration file. 
        """
        config_file = "./config.ini"
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read(config_file)

    def format_login_url(self):
        return '{}?{}'.format(self.login_page_base, urllib.parse.urlencode({
            'pv_login': self.user,
            'pv_password': self.password
        }))

    def start_requests(self):
        """This function is called before crawling starts."""

        if self.password is None:
            self.password = getpass.getpass(prompt='Password: ', stream=None)

        yield Request(url=self.format_login_url(), callback=self.check_login_response)

    def check_login_response(self, response):
        """Check the response returned by a login request to see if we are
        successfully logged in. Since we used the mobile login API endpoint,
        we can just check the status code.
        """
    
        if response.status == 200:
            response_body = json.loads(response.body)
            if response_body['authenticated']:
                print('Login successful.', flush=True)
                sql = """
                    SELECT faculty.acronym
                    FROM faculty
                """
                db = Database()
                db.cursor.execute(sql)
                faculties = db.cursor.fetchall()
                db.connection.close()
                print(faculties)
                for faculty in faculties:
                    url = f"https://sigarra.up.pt/{faculty[0]}/pt/coop_candidatura_geral.ver_vagas"
                    print(url)
                    yield scrapy.Request(url= url, callback=self.parseExchangeFaculties, meta={'faculty_acronym': faculty[0]})
                self.getMapInfo()
            else:
                message = 'Login failed. SIGARRA\'s response: error type "{}";\nerror message "{}"'.format(
                    response_body.erro, response_body.erro_msg)
                print(message, flush=True)
                self.log(message)
        else:
            print('Login Failed. HTTP Error {}'.format(
                response.status), flush=True)
            self.log('Login Failed. HTTP Error {}'.format(response.status))
    def func(self, error):
        print("An error has occurred: ", error)
        return

    def getMapInfo(self):
        """
        Get the map information from the response.
        """
        sql = """
            select name from exchange_faculty
        """
        db = Database()
        db.cursor.execute(sql)
        faculties = db.cursor.fetchall()
        db.connection.close()
        print(faculties)
        # write to example-queries.txt file
        with open('./google-maps-scrapper/example-queries.txt', 'w') as f:
            for faculty in faculties:
                f.write(f"{faculty[0]}\n")
    def parseExchangeFaculties(self, response):
        print("Parsing exchange faculties")
        for table in response.xpath('//div[@id="conteudoinner"]/table[@class="dados"]'):
            course_name = table.xpath('preceding-sibling::h2[1]/text()').get()
         
            db = Database() 
            sql = """
                SELECT course.id
                FROM course 
                WHERE course.name = '{}'
            """.format(course_name)
            db.cursor.execute(sql)
            course_id = db.cursor.fetchone()[0]
  
            db.connection.close()
            for row in table.xpath('.//tr[@class="d"]'):
                
                faculty = ExchangeFaculty(
                    country=re.sub(r'[^a-zA-ZÀ-ú\s]', '', row.xpath('td[1]/text()').get().strip()),
                    id=row.xpath('td[2]/text()').get().strip(),
                    name=row.xpath('td[3]/text()').get().strip(),
                    modality=row.xpath('td[9]/text()').get().strip(),
                    last_updated=datetime.now()
                    
                )
                yield faculty

                course = ExchangeFacultyCourse(
                    exchange_faculty_id=row.xpath('td[2]/text()').get().strip(),
                    course_id=course_id
                )
        
                yield course
        
            
    