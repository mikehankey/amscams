BEGIN TRANSACTION;
DROP TABLE IF EXISTS "station";
CREATE TABLE IF NOT EXISTS "station" (
	"station_id"	TEXT,
	"lat"	REAL NOT NULL,
	"lon"	REAL NOT NULL,
	"alt"	REAL NOT NULL,
	"operator_name"	TEXT,
	"operator_city"	TEXT,
	"operator_state"	TEXT,
	"operator_country"	TEXT,
	"photo_credit"	TEXT,
	"api_key"	TEXT,
	"username"	TEXT,
	"pwd"	TEXT,
	"pin_code"	TEXT,
	"mac_addr"	TEXT,
	"cam_ids"	TEXT,
	"station_start_date"	TEXT,
	"register_date"	TEXT,
	PRIMARY KEY("station_id")
);
DROP TABLE IF EXISTS "calibration_range";
CREATE TABLE IF NOT EXISTS "calibration_range" (
	"station_id"	INTEGER,
	"camera_id"	INTEGER,
	"between_start"	TEXT,
	"between_end"	TEXT,
	"az"	REAL,
	"el"	REAL,
	"position_angle"	REAL,
	"pixel_scale"	REAL,
	PRIMARY KEY("between_end","between_start")
);
DROP TABLE IF EXISTS "calibration_files";
CREATE TABLE IF NOT EXISTS "calibration_files" (
	"station_id"	INTEGER,
	"camera_id"	INTEGER,
	"calib_fn"	TEXT,
	"cal_datetime"	NUMERIC,
	"az"	REAL,
	"el"	REAL,
	"ra"	REAL,
	"dec"	REAL,
	"position_angle"	REAL,
	"pixel_scale"	REAL,
	"user_stars"	BLOB,
	"auto_stars"	BLOB,
	"cat_image_stars"	BLOB,
	"x_poly"	BLOB,
	"y_poly"	BLOB,
	"x_poly_fwd"	BLOB,
	"y_poly_fwd"	BLOB NOT NULL,
	"res_px"	REAL,
	"res_deg"	REAL
);
DROP TABLE IF EXISTS "non_meteors";
CREATE TABLE IF NOT EXISTS "non_meteors" (
	"meteor_fn"	INTEGER,
	"start_datetime"	TEXT,
	"start_datetime_ts"	INTEGER,
	"roi"	TEXT,
	"meteor_yn"	INTEGER,
	"meteor_yn_conf"	REAL,
	"meteor_fireball_yn"	INTEGER,
	"meteor_fireball_yn_conf"	REAL,
	"multi_class"	INTEGER,
	"multi_class_conf"	REAL,
	"save_media"	INTEGER,
	"purge_media_date"	TEXT,
	"purge_media_date_ts"	INTEGER,
	"human_label"	TEXT
);
DROP TABLE IF EXISTS "meteor_frame_data";
CREATE TABLE IF NOT EXISTS "meteor_frame_data" (
	"station_id"	TEXT,
	"camera_id"	TEXT,
	"video_fn"	TEXT,
	"meteor_id"	INTEGER NOT NULL,
	"fn"	TEXT,
	"dt"	TEXT,
	"cnt_x"	REAL,
	"cnt_y"	REAL,
	"cnt_w"	REAL,
	"cnt_h"	REAL,
	"ra"	REAL,
	"dec"	REAL,
	"az"	REAL,
	"el"	REAL,
	"intensity"	REAL,
	"cx"	REAL,
	"cy"	REAL,
	"user_x"	REAL,
	"user_y"	REAL,
	"lead_x"	REAL,
	"lead_y"	REAL,
	PRIMARY KEY("video_fn")
);
DROP TABLE IF EXISTS "all_stations";
CREATE TABLE IF NOT EXISTS "all_stations" (
	"station_id"	TEXT,
	"lat"	INTEGER,
	"lon"	INTEGER,
	"alt"	INTEGER,
	"operator_name"	INTEGER,
	"operator_city"	INTEGER,
	"operator_state"	INTEGER,
	"operator_country"	NUMERIC,
	"photo_credit"	INTEGER,
	"op_status"	INTEGER,
	PRIMARY KEY("station_id")
);
DROP TABLE IF EXISTS "events";
CREATE TABLE IF NOT EXISTS "events" (
	"event_id"	TEXT,
	PRIMARY KEY("event_id")
);
DROP TABLE IF EXISTS "event_observations";
CREATE TABLE IF NOT EXISTS "event_observations" (
	"event_id"	TEXT,
	"station_id"	INTEGER,
	"camera_id"	INTEGER,
	"meteor_fn"	TEXT
);
DROP TABLE IF EXISTS "event_solutions";
CREATE TABLE IF NOT EXISTS "event_solutions" (
	"event_id"	INTEGER,
	"run_datetime"	INTEGER,
	"solver"	INTEGER,
	PRIMARY KEY("event_id","run_datetime")
);
DROP TABLE IF EXISTS "meteors";
CREATE TABLE IF NOT EXISTS "meteors" (
	"station_id"	TEXT,
	"camera_id"	BLOB,
	"meteor_fn"	INTEGER,
	"sd_vid"	TEXT,
	"hd_vid"	NUMERIC,
	"start_datetime"	INTEGER,
	"meteor_yn"	INTEGER,
	"meteor_yn_conf"	REAL,
	"fireball_yn"	INTEGER,
	"fireball_yn_conf"	REAL,
	"multi_class"	INTEGER,
	"multi_class_conf"	REAL,
	"reduced"	INTEGER,
	"multi_station"	INTEGER,
	"event_id"	TEXT,
	"ang_velocity"	REAL,
	"duration"	REAL,
	"roi"	TEXT,
	"sync_status"	INTEGER,
	"calib"	BLOB,
	PRIMARY KEY("sd_vid")
);
DROP TABLE IF EXISTS "event_planes";
CREATE TABLE IF NOT EXISTS "event_planes" (
	"event_id"	TEXT,
	"obs1_fn"	TEXT,
	"obs2_fn"	TEXT,
	"obs1_el_start"	REAL,
	"obs1_az_start"	REAL,
	"obs1_el_end"	REAL,
	"obs1_az_end"	REAL,
	"obs1_az_start_line"	TEXT,
	"obs1_az_end_line"	TEXT,
	"obs2_az_start"	REAL,
	"obs2_el_start"	REAL,
	"obs2_az_end"	REAL,
	"obs2_el_end"	REAL,
	"obs2_az_start_line"	TEXT,
	"obs2_az_end_line"	TEXT,
	"solved_status"	INTEGER,
	"start_lat"	REAL,
	"start_lon"	REAL,
	"start_alt"	REAL,
	"end_lat"	REAL,
	"end_lon"	REAL,
	"end_alt"	REAL,
	PRIMARY KEY("obs1_fn","obs2_fn","event_id")
);
DROP TABLE IF EXISTS "ml_class";
CREATE TABLE IF NOT EXISTS "ml_class" (
	"volume"	TEXT,
	"mc_model"	TEXT,
	"class_name"	TEXT,
	"sub_class"	TEXT,
	PRIMARY KEY("class_name","sub_class","mc_model")
);
DROP TABLE IF EXISTS "ml_models";
CREATE TABLE IF NOT EXISTS "ml_models" (
	"model_id"	INTEGER,
	"model_name"	TEXT,
	"model_desc"	INTEGER,
	"model_version"	INTEGER,
	"model_create_date"	INTEGER,
	"model_type"	INTEGER,
	"model_subtype"	INTEGER,
	"source_image_repo"	INTEGER,
	"model_h5_file"	INTEGER,
	"total_source_images"	INTEGER,
	"final_accuracy"	INTEGER,
	"final_loss"	INTEGER,
	PRIMARY KEY("model_id")
);
COMMIT;
