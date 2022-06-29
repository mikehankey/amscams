CREATE TABLE IF NOT EXISTS calibration_range (
        station_id    text,
        camera_id     text,
        between_start text,
        between_end   text,
        az    real,
        el    real,
        position_angle        real,
        pixel_scale   real,
        PRIMARY KEY(between_end,between_start)
);

CREATE TABLE IF NOT EXISTS calibration_files (
        cal_fn      text,
        station_id    text,
        camera_id     text,
        cal_ts  	real,
        az    	real,
        el    	real,
        ra    	real,
        dec   	real,
        position_angle        real,
        pixel_scale   real,
        zp_az    real,
        zp_el    real,
        zp_ra    real,
        zp_dec   real,
        zp_position_angle        real,
        zp_pixel_scale   real,
        x_poly        blob,
        y_poly        blob,
        x_poly_fwd    blob,
        y_poly_fwd    blob NOT NULL,
        res_px        real,
        res_deg       real,
        ai_weather     text,
        ai_weather_conf     real,
        cal_version     integer,
        last_update     real,
        PRIMARY KEY(cal_fn)
);

CREATE TABLE calfile_catalog_stars (
            cal_fn text,
            name text,
            mag real,
            ra real,
            dec real,
            new_cat_x real,
            new_cat_y real,
            zp_cat_x real,
            zp_cat_y real,
            img_x real,
            img_y real,
            star_flux real,
            star_yn real,
            star_pd integer,
            star_found integer DEFAULT 0,
            lens_model_version integer,
            PRIMARY KEY(cal_fn,ra,dec)
);

CREATE TABLE calfile_paired_stars (
            cal_fn text,
            name text,
            mag real,
            ra real,
            dec real,
            new_cat_x real,
            new_cat_y real,
            zp_cat_x real,
            zp_cat_y real,
            img_x real,
            img_y real,
            star_flux real,
            star_yn real,
            star_pd integer,
            star_found integer DEFAULT 0,
            lens_model_version integer,
	    slope real,
	    zp_slope real,
	    res_px real,
	    zp_res_px real,
	    res_deg real,
            PRIMARY KEY(cal_fn,img_x,img_y)
);

DROP TABLE IF EXISTS catalog_stars; 
CREATE TABLE catalog_stars (
   hip_id integer NOT NULL,
   name_ascii text,
   name_utf text,
   id_ascii text,
   id_utf text,
   constellation text,
   rahms text,
   dechms text,
   mag real,
   ra real,
   decl real,
   iau_ra real,
   iau_decl real,
   PRIMARY KEY(hip_id)
);

DROP TABLE IF EXISTS constellation_lines; 
CREATE TABLE constellation_lines (
   constellation text,
   star_1 integer,
   star_2 integer,
   PRIMARY KEY(constellation, star_1, star_2)
);
