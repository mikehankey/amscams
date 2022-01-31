
DROP TABLE IF EXISTS "event_minutes";
CREATE TABLE IF NOT EXISTS "event_minutes" (
   "event_minute"      TEXT,
   "stations"      TEXT,
   "obs"      TEXT,
   "events"      TEXT,
   PRIMARY KEY("event_minute")
);


DROP TABLE IF EXISTS "events";
CREATE TABLE IF NOT EXISTS "events" (
        "event_id"      TEXT,
        "event_minute"      TEXT,
        "revision"      INTEGER,
        "event_start_time"      TEXT,
        "event_start_times"      TEXT,
        "stations"  TEXT,
        "obs_ids"  TEXT,
        "lats"  TEXT,
        "lons"  TEXT,
        "event_status"  TEXT,
        "run_date"      TEXT,
        "run_times"     INTEGER,
        PRIMARY KEY("event_id","revision")
);

DROP TABLE IF EXISTS "event_planes";
CREATE TABLE IF NOT EXISTS "event_planes" (
        "plane_pair"      TEXT,
        "status"      TEXT,
        "sanity"      INTEGER,
        "start_lat"      REAL,
	"start_lon"      REAL,
	"start_alt"      REAL,
	"end_lat"      REAL,
	"end_lon"      REAL,
	"end_alt"      REAL,
        PRIMARY KEY("plane_pair")
);



DROP TABLE IF EXISTS "event_obs";
CREATE TABLE IF NOT EXISTS "event_obs" (
        "event_id"      TEXT,
        "event_minute"      TEXT,
        "station_id"     ,
        "obs_id"     TEXT UNIQUE,
        "fns" TEXT,
        "times" TEXT,
        "xs"   TEXT,
        "ys"   TEXT,
        "azs"   TEXT,
        "els"   TEXT,
        "ints"  TEXT,
        "status"        TEXT,
        "ignore"        INTEGER,
        PRIMARY KEY("obs_id")
);

DROP TABLE IF EXISTS "station";
CREATE TABLE IF NOT EXISTS "station" (
        "station_id"    TEXT,
        "lat"   REAL NOT NULL,
        "lon"   REAL NOT NULL,
        "alt"   REAL NOT NULL,
        "operator_name" TEXT,
        "operator_city" TEXT,
        "operator_state"        TEXT,
        "operator_country"      TEXT,
        "photo_credit"  TEXT,
        "api_key"       TEXT,
        "username"      TEXT,
        "pwd"   TEXT,
        "pin_code"      TEXT,
        "mac_addr"      TEXT,
        "cam_ids"       TEXT,
        "station_start_date"    TEXT,
        "register_date" TEXT,
        PRIMARY KEY("station_id")
);
