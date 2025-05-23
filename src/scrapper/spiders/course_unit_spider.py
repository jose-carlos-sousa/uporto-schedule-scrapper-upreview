
import scrapy
# import sqlite3
import getpass
from scrapy.http import FormRequest, Request
from urllib.parse import urlparse, parse_qs, urlencode
from configparser import ConfigParser, ExtendedInterpolation
from scrapper.settings import PASSWORD, USERNAME
from datetime import datetime
import pandas as pd
import logging
import json
from io import StringIO

# from scrapper.settings import CONFIG

from ..database.Database import Database
from ..items import CourseUnit, CourseCourseUnit
import hashlib

class CourseUnitSpider(scrapy.Spider):
    name = "course_units"
    course_units_ids = set()
    course_courses_units_hashes = set()
    prof_ids = set()
    course_unit_professors = set()
    login_page_base = 'https://sigarra.up.pt/feup/pt/mob_val_geral.autentica'
    
    def open_config(self):
        """
        Reads and saves the configuration file. 
        """
        config_file = "./config.ini"
        self.config = ConfigParser(interpolation=ExtendedInterpolation())
        self.config.read(config_file) 

    def __init__(self, *args, **kwargs):
        super(CourseUnitSpider, self).__init__(*args, **kwargs)
        self.open_config()
        self.user = USERNAME
        self.password = PASSWORD
        logging.getLogger('scrapy').propagate = False

    def format_login_url(self):
        return '{}?{}'.format(self.login_page_base, urlencode({
            'pv_login': self.user,
            'pv_password': self.password
        }))

    async def start(self):
        "This function is called before crawling starts."
        if self.password is None:
            self.password = getpass.getpass(prompt='Password: ', stream=None)
            
        yield Request(url=self.format_login_url(), callback=self.check_login_response, errback=self.login_response_err)

    def login_response_err(self, failure):
        print('Login failed. SIGARRA\'s response: error type 404;\nerror message "{}"'.format(failure))
        print("Check your password")
    
    def check_login_response(self, response):
        """Check the response returned by a login request to see if we are
        successfully logged in. Since we used the mobile login API endpoint,
        we can just check the status code.
        """ 

        if response.status == 200:
            response_body = json.loads(response.body)
            if response_body['authenticated']:
                self.log("Successfully logged in. Let's start crawling!")
                return self.courseRequests()

    def courseRequests(self):
        print("Gathering course units") 
        db = Database() 

        sql = """
            SELECT course.id, year, faculty.acronym 
            FROM course JOIN faculty 
            ON course.faculty_id= faculty.id
        """
        db.cursor.execute(sql)
        self.courses = db.cursor.fetchall()
        db.connection.close()

        self.log("Crawling {} courses".format(len(self.courses)))

        for course in self.courses:
            course_id, year, faculty_acronym = course
            yield scrapy.http.Request(
                url = f'https://sigarra.up.pt/{faculty_acronym}/pt/cur_geral.cur_view?pv_ano_lectivo={year}&pv_origem=CUR&pv_tipo_cur_sigla=M&pv_curso_id={course_id}',
                meta={'course_id': course_id, 'year': year, 'faculty_acronym': faculty_acronym},
                callback=self.extractStudyPlanPages)
            
    def extractStudyPlanPages(self, response):
        plan_link = response.xpath('//h3[text()="Planos de Estudos"]/following-sibling::div//ul/li/a/@href').extract_first()
        if plan_link:
            plan_id = plan_link.split("pv_plano_id=")[1].split("&")[0]
            plan_url = f'https://sigarra.up.pt/{response.meta["faculty_acronym"]}/pt/cur_geral.cur_planos_estudos_view?pv_plano_id={plan_id}&pv_ano_lectivo={response.meta["year"]}&pv_tipo_cur_sigla=M'
            yield scrapy.Request(url=plan_url, callback=self.extractCourseUnits, meta=response.meta)
        else:
            print(f"No Planos de Estudos link found for course ID: {response.meta['course_id']}")
        
    def extractCourseUnits(self, response):
        course_rows = response.xpath('.//table[contains(@class, "dadossz")]/tr')
        for row in course_rows:
            link = row.xpath('.//td[@class="t"]/a/@href').extract_first()
            if link and not link.strip().lower().startswith("javascript:"):  
                yield scrapy.http.Request(
                    url=response.urljoin(link),
                    meta=response.meta,
                    callback=self.extractCourseUnitInfo)

    def extractCourseUnitInfo(self, response):
        content = response.xpath('//div[@id="conteudoinner"]/h1[2]/text()').get()
        if not content:
            href = response.xpath('//td[@class="k t"]/a/@href').get()
            yield scrapy.http.Request(
                    url=response.urljoin(href),
                    meta=response.meta,
                    callback=self.extractCourseUnitInfo)
            return
        else: 
            name = content.strip()

        # Checks if the course unit page is valid.
        # If name == 'Sem Resultados', then it is not.
        if name == 'Sem Resultados' or name == '':
            return None  # Return None as yielding would continue the program and crash at the next assert

        current_occurence_id = parse_qs(urlparse(response.url).query)['pv_ocorrencia_id'][0]

        # Get the link with text "Outras ocorrências" and extract the course unit ID from its URL
        course_unit_id = parse_qs(urlparse(response.xpath('//a[text()="Outras ocorrências"]/@href').get()).query)['pv_ucurr_id'][0]

        acronym = response.xpath(
            '//div[@id="conteudoinner"]/table[@class="formulario"][1]//td[text()="Sigla:"]/following-sibling::td[1]/text()').extract_first()

        # Some pages have Acronym: instead of Sigla:
        if acronym is None: 
            acronym = response.xpath(
                '//div[@id="conteudoinner"]/table[@class="formulario"][1]//td[text()="Acronym:"]/following-sibling::td[1]/text()').extract_first()

        if acronym is not None:
            acronym = acronym.replace(".", "_")

        # url = response.url
        # # If there is no schedule for this course unit
        # if schedule_url is not None:
        #     schedule_url = response.urljoin(schedule_url)

        # Instance has a string that contains both the year and the semester type
        Instance = response.css('#conteudoinner > h2::text').extract_first()

        # Possible types: '1', '2', 'A', 'SP'
        # '1' and '2' represent a semester
        # 'A' represents an annual course unit
        # 'SP' represents a course unit without effect this year
        semester = Instance[24:26].strip()

        # Represents the civil year. If the course unit is taught on the curricular year
        # 2017/2018, then year is 2017.
        year = int(Instance[12:16])

        assert semester == '1S' or semester == '2S' or semester == 'A' or semester == 'SP' \
            or semester == '1T' or semester == '2T' or semester == '3T' or semester == '4T'

        assert year > 2000

      
        if (course_unit_id not in self.course_units_ids):
            self.course_units_ids.add(course_unit_id)
            yield CourseUnit(
                id=course_unit_id,
                name=name,
                acronym=acronym,
                recent_occr=current_occurence_id, # This might be wrong but I fix it later xd just cuz not null
                last_updated=datetime.now()
            )
        
        study_cycles = response.xpath('//h3[text()="Ciclos de Estudo/Cursos"]/following-sibling::table[1]').get()
        if study_cycles is None:
            return
        df = pd.read_html(StringIO(study_cycles), decimal=',', thousands='.', extract_links="all")[0]
        for (_, row) in df.iterrows():
                if(parse_qs(urlparse(row.iloc[0][1]).query).get('pv_curso_id')[0] == str(response.meta['course_id'])):
                    cu = CourseCourseUnit(
                            course_id= parse_qs(urlparse(row.iloc[0][1]).query).get('pv_curso_id')[0],
                            course_unit_id=course_unit_id,
                            year=row.iloc[3][0],
                            semester=semester,
                            ects=row.iloc[5][0],
                            )
                    hash_ccu = hashlib.md5((cu['course_id']+cu['course_unit_id']+cu['year']+ cu['semester']).encode()).hexdigest()
                    if(hash_ccu not in self.course_courses_units_hashes):
                        self.course_courses_units_hashes.add(hash_ccu)
                        yield cu
        yield scrapy.http.Request(
                url="https://sigarra.up.pt/feup/pt/mob_ucurr_geral.outras_ocorrencias?pv_ocorrencia_id={}".format(current_occurence_id),
                meta={'course_unit_id': course_unit_id, 'semester': semester, 'year': year},
                callback=self.extractInstances
            )

                       
                
    def extractInstances(self, response):
        data = json.loads(response.body)
        
        valid_instances = [uc for uc in data if uc.get('ano_letivo') >= response.meta['year']]
        
        today = datetime.now()
        
        month = today.month

        if month >= 9 or month <= 1:
            current_semester = '1S'
        elif month >= 2 and month <= 7:
            current_semester = '2S'
        else:
            current_semester = None 

        def sort_key(uc):
            instance_semester = uc.get('semestre')
            if current_semester and instance_semester and current_semester == instance_semester or instance_semester == 'A':
                return 0  # Current semester instances first
            else:
                return 1  # Other semesters after

        valid_instances = [uc for uc in data if uc.get('ano_letivo') == response.meta['year']]
        valid_instances.sort(key=sort_key)

        max_occr_id = valid_instances[0].get('id') if valid_instances else None
        
        db = Database()
        sql = """
            UPDATE course_unit
            SET recent_occr = ?
            WHERE id = ?
        """
        db.cursor.execute(sql, (max_occr_id, response.meta['course_unit_id']))
        db.connection.commit()
        db.connection.close()
        
        for uc in data:
            yield scrapy.http.FormRequest(
                            url="https://sigarra.up.pt/flup/pt/EST_AJAX.DIST_RESULT_OCORR_DETAIL_TBL",
                            formdata={'pv_ocorrencia_id': str(max_occr_id), 'PV_ANO_LETIVO': str(uc.get('ano_letivo')), 'PV_SHOW_TITLE': 'S'},
                            meta={'course_unit_id': response.meta['course_unit_id'], 'PV_ANO_LETIVO': uc.get('ano_letivo')},
                            callback=self.extractResults,
                    )


    def extractResults(self, response):

        rows = response.css('table.dados > tbody > tr.d')
        results = []
        total_num_students = 0
        for row in rows:
            result_type = row.css('td:nth-child(1)::text').get()
            num_students = row.css('td:nth-child(3)::text').get()
            if result_type and num_students:
                num_students = int(num_students)
                total_num_students += num_students
                results.append(f"{result_type}-{num_students}")
        
        if total_num_students == 0:
            return
        
        year = response.meta['PV_ANO_LETIVO']
        results_str = f"{year}_" + "_".join(results)

        
        db = Database()
        sql = """
            UPDATE course_unit
            SET stats = ?
            WHERE id = ? AND (stats IS NULL OR stats = '' OR CAST(SUBSTR(stats, 1, 4) AS INTEGER) < ?)
        """
        db.cursor.execute(sql, (results_str, response.meta['course_unit_id'], response.meta['PV_ANO_LETIVO']))
        db.connection.commit()
        db.connection.close()