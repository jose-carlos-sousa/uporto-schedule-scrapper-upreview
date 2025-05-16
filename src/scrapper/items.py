# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Faculty(scrapy.Item):
    acronym = scrapy.Field()
    name = scrapy.Field()
    last_updated = scrapy.Field()


class Course(scrapy.Item):
    id = scrapy.Field()
    faculty_id = scrapy.Field()
    name = scrapy.Field()
    acronym = scrapy.Field()
    course_type = scrapy.Field()
    url = scrapy.Field()
    year = scrapy.Field()
    plan_url = scrapy.Field()
    last_updated = scrapy.Field()


class CourseUnit(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    acronym = scrapy.Field()
    last_updated = scrapy.Field()
    recent_occr = scrapy.Field()
    stats = scrapy.Field()

class CourseCourseUnit(scrapy.Item):
    id = scrapy.Field()
    course_id = scrapy.Field()
    course_unit_id = scrapy.Field()
    group_id = scrapy.Field()
    ramo_id = scrapy.Field()
    year = scrapy.Field()
    semester = scrapy.Field()
    ects = scrapy.Field()
    
class CourseCourseUnitPath(scrapy.Item):
    id = scrapy.Field()
    course_course_unit_id  = scrapy.Field()
    course_path_id = scrapy.Field()

class CourseCourseUnitGroup(scrapy.Item):
    id = scrapy.Field()
    course_course_unit_id  = scrapy.Field()
    course_unit_group_id  = scrapy.Field()

class CourseUnitProfessor(scrapy.Item):
    course_unit_id = scrapy.Field()
    professor_id = scrapy.Field()
    
class Professor(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    
class CourseUnitGroup(scrapy.Item):
    id = scrapy.Field()
    name = scrapy.Field()
    path_id = scrapy.Field()

class CoursePath(scrapy.Item):
    id = scrapy.Field()
    code = scrapy.Field()
    name = scrapy.Field()
    course_id = scrapy.Field()
    
class ExchangeFaculty(scrapy.Item):
    id = scrapy.Field()
    country = scrapy.Field()
    name = scrapy.Field()
    modality = scrapy.Field()
    last_updated = scrapy.Field()
    thumbnail = scrapy.Field()
    address = scrapy.Field()
    website = scrapy.Field()
    latitude = scrapy.Field()
    longitude = scrapy.Field()


class ExchangeFacultyCourse(scrapy.Item):
    exchange_faculty_id = scrapy.Field()
    course_id = scrapy.Field()
    faculty_id = scrapy.Field()