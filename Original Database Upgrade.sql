CREATE TABLE `user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `active` tinyint(1) NOT NULL,
  `last_login_date` datetime DEFAULT NULL,
  `first_name` varchar(15) COLLATE utf8mb3_bin NOT NULL,
  `last_name` varchar(15) COLLATE utf8mb3_bin NOT NULL,
  `username` varchar(256) COLLATE utf8mb3_bin NOT NULL,
  `password_hash` varchar(256) COLLATE utf8mb3_bin NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_bin;

CREATE TABLE `user_login` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_date` datetime NOT NULL,
  `event_type` enum('Login','Logout') COLLATE utf8mb3_bin DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `user_login_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3 COLLATE=utf8mb3_bin;


ALTER TABLE `label` 
ADD COLUMN `date_created` DATETIME NOT NULL AFTER `rolling_label`,
ADD COLUMN `date_modified` DATETIME NOT NULL AFTER `date_created`,
ADD COLUMN `modified_by_user_id` INT NULL AFTER `date_modified`,
ADD COLUMN `created_by_user_id` INT NULL AFTER `modified_by_user_id`,
CHANGE COLUMN `sort_id` `sort_index` INT NOT NULL ,
CHANGE COLUMN `rolling_label` `rolling_label` TINYINT(1) NOT NULL ,
DROP INDEX `UC_part_number_sort_id` ,
ADD UNIQUE INDEX `UC_pn_value_sort_rolling` (`part_number` ASC, `value` ASC, `sort_index` ASC, `rolling_label` ASC),
ADD INDEX `label_ibfk_1_idx` (`modified_by_user_id` ASC),
ADD INDEX `label_ibfk_2_idx` (`created_by_user_id` ASC);
;
ALTER TABLE `label` 
ADD CONSTRAINT `label_ibfk_1`
  FOREIGN KEY (`modified_by_user_id`)
  REFERENCES `user` (`id`),
ADD CONSTRAINT `label_ibfk_2`
  FOREIGN KEY (`created_by_user_id`)
  REFERENCES `user` (`id`);

SET foreign_key_checks = 0;

UPDATE `label`
SET created_by_user_id = 1, modified_by_user_id = 1, date_created = NOW(), date_modified = NOW();

SET foreign_key_checks = 1;