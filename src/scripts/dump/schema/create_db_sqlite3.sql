--
-- Database: `tts` FOR SQLITE 3 
--

-- --------------------------------------------------------

--
-- Table structure for table `faculty`
--

CREATE TABLE `faculty` (
  `acronym` varchar(10) PRIMARY KEY ,
  `name` text,
  `last_updated` datetime NOT NULL
);

-- --------------------------------------------------------
--
-- Table structure for table `course`
--

CREATE TABLE `course` (
  `id` INTEGER PRIMARY KEY,
  `faculty_id` varchar(10) NOT NULL,
  `name` varchar(200) NOT NULL,
  `acronym` varchar(10) NOT NULL,
  `course_type` varchar(50) NOT NULL,
  `year` int(11) NOT NULL,
  `url` varchar(2000) NOT NULL,
  `plan_url` varchar(2000) NOT NULL,
  `last_updated` datetime NOT NULL,
  FOREIGN KEY (`faculty_id`) REFERENCES `faculty`(`acronym`) ON DELETE CASCADE ON UPDATE CASCADE
);

-- --------------------------------------------------------
--
-- Table structure for table `course_unit`
--

CREATE TABLE `course_unit` (
  `id` INTEGER PRIMARY KEY,
  `name` varchar(200) NOT NULL,
  `acronym` varchar(16) NOT NULL,
  `recent_occr` INTEGER NOT NULL,
  `stats` TEXT ,
  `last_updated` datetime NOT NULL
);

-- --------------------------------------------------------
--
-- Table structure for table `course_metadata`
--

CREATE TABLE `course_course_unit` (
  `id` INTEGER PRIMARY KEY,
  `course_id` int(11) NOT NULL,
  `course_unit_id` int(11) NOT NULL,
  `year` tinyint(4) NOT NULL,
  `semester`  NOT NULL,
  `ects` float(4) NOT NULL,
  UNIQUE (`course_id`, `course_unit_id`, `year`, `semester`),
  FOREIGN KEY (`course_unit_id`) REFERENCES `course_unit`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`course_id`) REFERENCES `course`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE `course_course_unit_path` (
  `id` INTEGER PRIMARY KEY,
  `course_course_unit_id` int(11) NOT NULL,
  `course_path_id` int(11) NOT NULL,
  UNIQUE (`course_course_unit_id`, `course_path_id`),
  FOREIGN KEY (`course_course_unit_id`) REFERENCES `course_course_unit`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`course_path_id`) REFERENCES `course_path`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE TABLE `course_course_unit_group` (
  `id` INTEGER PRIMARY KEY,
  `course_course_unit_id` int(11) NOT NULL,
  `course_unit_group_id` int(11) NOT NULL,
  UNIQUE (`course_course_unit_id`, `course_unit_group_id`),
  FOREIGN KEY (`course_course_unit_id`) REFERENCES `course_course_unit`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`course_unit_group_id`) REFERENCES `course_unit_group`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

--
-- Table structure for table `professor`
--

CREATE TABLE `professor` (
  `id` INTEGER PRIMARY KEY,
  `name` varchar(200) NOT NULL
);

-- --------------------------------------------------------

--
-- Table structure for table `course_unit_professor`
--

CREATE TABLE `course_unit_professor` (
  `course_unit_id` int(11) NOT NULL,
  `professor_id` int(11) NOT NULL,
  PRIMARY KEY (`course_unit_id`, `professor_id`),
  FOREIGN KEY (`course_unit_id`) REFERENCES `course_unit`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`professor_id`) REFERENCES `professor`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

-- --------------------------------------------------------
--
-- Table structure for table `course_unit_group`
--

CREATE TABLE `course_unit_group` (
  `id` INTEGER PRIMARY KEY,
  `name` varchar(200) NOT NULL,
  `path_id` int(11),
  FOREIGN KEY (`path_id`) REFERENCES `course_path`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);

-- --------------------------------------------------------
--
-- Table structure for table `course_path`
--

CREATE TABLE `course_path` (
  `id` INTEGER PRIMARY KEY,
  `code` int(11) NOT NULL,
  `name` varchar(200) NOT NULL,
  `course_id` int(11) NOT NULL,
  UNIQUE (`code` , `course_id`),
  FOREIGN KEY (`course_id`) REFERENCES `course`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);


-----------------------------------------------
-- Table structure for table `exchange_faculty`
--

CREATE TABLE `exchange_faculty` (
  `id` varchar(100) PRIMARY KEY,
  `country` varchar(100) NOT NULL,
  `name` varchar(200) NOT NULL,
  `modality` varchar(50) NOT NULL,
   `thumbnail` varchar(2000),
  `address` varchar(2000),
  `website` varchar(2000) ,
  `latitude` float(10,6) ,
  `longitude` float(10,6) ,
  `last_updated` datetime NOT NULL
);

-- --------------------------------------------------------
--
-- Table structure for table `exchange_faculty_course`
--

CREATE TABLE `exchange_faculty_course` (
  `exchange_faculty_id` varchar(100)  NOT NULL,
  `course_id` int(11) NOT NULL,
  PRIMARY KEY (`exchange_faculty_id`, `course_id`),
  FOREIGN KEY (`exchange_faculty_id`) REFERENCES `exchange_faculty`(`id`) ON DELETE CASCADE ON UPDATE CASCADE,
  FOREIGN KEY (`course_id`) REFERENCES `course`(`id`) ON DELETE CASCADE ON UPDATE CASCADE
);


-- --------------------------------------------------------
------------------------------------------------
--
-- Table structure for table `info`
--

CREATE TABLE `info` (
  `date` DATETIME PRIMARY KEY
);

-- --------------------------------------------------------
