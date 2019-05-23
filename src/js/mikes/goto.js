function goto(var1,var2, type) {
    if (type == "calib") {
        url_str = "webUI.py?cmd=calibration&cams_id=" + var1
        window.location.href=url_str
    }
    if (type == "reduce") {
    
        url_str = "webUI.py?cmd=reduce&video_file=" + var1 + "&cal_params_file=" + var2
        window.location.href=url_str
    }
}