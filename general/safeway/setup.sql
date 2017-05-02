-- --------------------------------------------------------
-- Host:                         192.168.126.101
-- Server version:               5.6.19 - MySQL Community Server (GPL)
-- Server OS:                    Win32
-- HeidiSQL Version:             9.3.0.4985
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8mb4 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;

CREATE DATABASE IF NOT EXISTS `safeway` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `safeway`;


CREATE TABLE IF NOT EXISTS `history` (
  
  `product_id` varchar(45) NOT NULL,
  `site_name` varchar(45) NOT NULL,
  `zipcode` varchar(45) NOT NULL,
  `store` varchar(100) DEFAULT NULL,
  `price` float(7,2) DEFAULT NULL,
  `note` varchar(100) DEFAULT NULL,
  `updated` datetime NOT NULL,

  
  PRIMARY KEY (`product_id`, `site_name`, `updated`)
  
) ENGINE=MyISAM DEFAULT CHARSET=utf8;


