import getpass
import scrapy

import sqlite3

from scrapy.http import Request, FormRequest
from urllib.parse import urlparse, parse_qs, urlencode
from configparser import ConfigParser, ExtendedInterpolation
from datetime import datetime
import logging
import json

from scrapper.settings import CONFIG, PASSWORD, USERNAME

from ..database.Database import Database
from ..items import CourseUnit, CourseUnitInstance, CourseCourseUnit

class CourseUnitSpider(scrapy.Spider):
    name = "course_units"
    course_units_ids = set()

    def start_requests(self):
        "This function is called before crawling starts."
        return self.courseRequests()

    def courseRequests(self):
        print("Gathering course units") 
        db = Database() 

        sql = """
            SELECT course.id, year, faculty.acronym 
            FROM course JOIN faculty 
            ON course.faculty_id= faculty.acronym
        """
        db.cursor.execute(sql)
        self.courses = db.cursor.fetchall()
        db.connection.close()

        self.log("Crawling {} courses".format(len(self.courses)))

        for course in self.courses:
            yield scrapy.http.Request(
                url='https://sigarra.up.pt/{}/pt/ucurr_geral.pesquisa_ocorr_ucs_list?pv_ano_lectivo={}&pv_curso_id={}'.format(
                    course[2], course[1], course[0]),
                meta={'course_id': course[0]},
                callback=self.extractSearchPages)
            
    def extractSearchPages(self, response):
        last_page_url = response.css(
            ".paginar-saltar-barra-posicao > div:last-child > a::attr(href)").extract_first()
        last_page = int(parse_qs(urlparse(last_page_url).query)[
            'pv_num_pag'][0]) if last_page_url is not None else 1
        for x in range(1, last_page + 1):
            yield scrapy.http.Request(
                url=response.url + "&pv_num_pag={}".format(x),
                meta=response.meta,
                callback=self.extractCourseUnits)

    def extractCourseUnits(self, response):
        course_units_table = response.css("table.dados .d")

        for course_unit_row in course_units_table:
            yield scrapy.http.Request(
                url=response.urljoin(course_unit_row.css(
                    ".t > a::attr(href)").extract_first()),
                meta=response.meta,
                callback=self.extractCourseUnitInfo)

    def extractCourseUnitInfo(self, response):
        name = response.xpath(
            '//div[@id="conteudoinner"]/h1[2]/text()').extract_first().strip()

        # Checks if the course unit page is valid.
        # If name == 'Sem Resultados', then it is not.
        if name == 'Sem Resultados':
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

        url = response.url
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

        semesters = []

        # FIXME: Find a better way to allocate trimestral course units
        if semester == '1S' or semester == '1T' or semester == '2T':
            semesters = [1]
        elif semester == '2S' or semester == '3T' or semester == '4T':
            semesters = [2]
        elif semester == 'A':
            semesters = [1, 2]

        for semester in semesters:
                if (course_unit_id in self.course_units_ids): continue
                self.course_units_ids.add(course_unit_id)
                yield CourseUnit(
                    id=course_unit_id,
                    name=name,
                    acronym=acronym,
                    url=url,
                    last_updated=datetime.now()
                )
                study_cycles_table = response.xpath('//h3[text()="Ciclos de Estudo/Cursos"]/following-sibling::table[1]')
                
                if study_cycles_table:
                    for row in study_cycles_table.xpath('.//tr[@class="d"]'):

                        course_link = row.xpath('.//td[1]/a/@href').get()
                        
                        if course_link:
                            course_id_meta = response.meta.get('course_id')
                            query_params = parse_qs(urlparse(course_link).query)
                            if 'pv_curso_id' in query_params:
                                course_id = query_params['pv_curso_id'][0]
                                if str(course_id_meta) == course_id:
                                    course_acronym = row.xpath('.//td[1]/a/text()').get()
                                    ects = row.xpath('.//td[6]/text()').get()
                                    curricular_years = row.xpath('.//td[4]/text()').get()
                                    
                                    if course_acronym and ects:
                                        if curricular_years:
                                            for year in curricular_years.split(','):
                                                yield CourseCourseUnit(
                                                    course_id=course_id_meta,
                                                    course_unit_id=course_unit_id,
                                                    course_unit_year=year.strip(),
                                                    ects=ects
                                                )

                    yield scrapy.http.Request(
                        url="https://sigarra.up.pt/feup/pt/mob_ucurr_geral.outras_ocorrencias?pv_ocorrencia_id={}".format(current_occurence_id),
                        meta={'course_unit_id': course_unit_id, 'semester': semester, 'year': year},
                        callback=self.extractInstances
                    )
                else:
                    yield None
                
    def extractInstances(self, response):
        data = json.loads(response.body)
        
        for uc in data:
            if(uc.get('ano_letivo') > 2022): #Just for now
                yield CourseUnitInstance(
                    course_unit_id=response.meta['course_unit_id'],
                    id=uc.get('id'),
                    year=uc.get('ano_letivo'),
                    semester=uc.get('periodo_nome'),
                    last_updated=datetime.now()
                )