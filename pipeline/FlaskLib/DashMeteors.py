from FlaskLib.Dashboard import Dashboard
import math
from pprint import pprint

class MeteorDash(Dashboard):
   def __init__(self):
       
      Dashboard.__init__(self)


   def make_options(self,opt_data, selected_val):
      options = ""
      for val, label in opt_data:
         if val == selected_val:
            options += "<option value='" + val + "' selected>" + label + "</option>"
         else:
            options += "<option value='" + val + "'>" + label + "</option>"
      return(options)

   def meteor_main_menu(self, in_data):
      html_met_stats = """
         Birds eye view of key meteor stats by day with entry links into the gallery. 
      """ 
      mout = self.render_widget("metstats", "<a href=?cmd=metstats>Meteor Stats by Day</a>", html_met_stats, 12)

      html_met_gal = """
         All meteors detections in your local archive. 
      """ 
      mout += self.render_widget("metgal", "<a href=?cmd=metgal>Meteor Gallery</a>", html_met_gal, 12)


      return(mout)
   

   def meteor_search_form(self, in_data):
      opt_view_types = [ ["all", "All"], ["ai_meteors", "AI Meteors"], ["ai_non_meteors", "AI Non Meteors"], ["ai_fireballs", "AI Fireballs"] ]
      opt_confirm_status = [["all", "All"], ["confirmed_meteor", "Human Confirmed Meteor"], ["confirmed_non_meteor", "Human Confirmed Non-Meteor"], ["not_confirmed", "Not Human Confirmed"]]
      opt_red_status = [["all", "All"], ["reduced", "Reduced"], ["not_reduced", "Not Reduced"]]
      opt_items_per_page = [["50", "50"], ["100", "100"], ["250", "250"], ["500", "500"], ["1000", "1000"]]
      opt_sort_by = [ ["date_desc", "Date (Newest First)"], ["date_asc", "Date (Oldest First)"], ["meteor_conf_desc", "Meteor Confidence (Highest First)"], ["meteor_conf_asc", "Meteor Confidence (Lowest First)"]]

      if "view_type" in in_data:
         view_options = self.make_options(opt_view_types, in_data['view_type'])
      else:
         view_options = self.make_options(opt_view_types, "")

      if "confirm_status" in in_data:
         confirm_options = self.make_options(opt_confirm_status, in_data['confirm_status'])
      else:
         confirm_options = self.make_options(opt_confirm_status, "")


      if "red_status" in in_data:
         red_options = self.make_options(opt_red_status, in_data['red_status'])
      else:
         red_options = self.make_options(opt_items_per_page, "")

      if "ipp" in in_data:
         ipp_options = self.make_options(opt_items_per_page, in_data['ipp'])
      else:
         ipp_options = self.make_options(opt_items_per_page, "")

      if "sort_by" in in_data:
         sort_options = self.make_options(opt_sort_by, in_data['sort_by'])
      else:
         sort_options = self.make_options(opt_sort_by, "")

      form = """
            
         <div class="card">
            <div class="card-header">
               <h3 class="card-title">Search Options</h3>
            </div>
            <div class="card-body">
            <form action="/DASHBOARD/{:s}/METEORS">
            <input type='hidden' name=cmd value='metgal'>
            <div class="row">
              <div class="col-2">
  
                  <label for="view_type">Select View Type </label>
                  <select class="custom-select rounded-0" id="view_type" name="view_type">""" + view_options + """
                  
                  </select>
               </div>
               <div class="col-2">
                  <label for="confirm_status">Confirmation Status</label>
                  <select class="custom-select rounded-0" id="confirm_status" name="confirm_status">""" + confirm_options + """
                  </select>
               </div>
               <div class="col-2">
                  <label for="red_status">Reduction Status</label>
                  <select class="custom-select rounded-0" id="red_status" name="red_status">""" + red_options + """
                  </select>

               </div>
               <div class="col-2">

                  <label for="ipp">Items Per Page</label>
                  <select class="custom-select rounded-0" id="ipp" name="ipp">""" + ipp_options + """
                  </select>

               </div>
               <div class="col-2">

                  <label for="sort_by">Sort By</label>
                <div class="input-group input-group-md">
                  <select class="custom-select rounded-0" id="sort_by" name="sort_by">""" + sort_options + """
                  </select>
                    <button type="submit" class="btn btn-info btn-flat">Go!</button>
                 </div>
               </div>

             </div> 
           </div> 
         </div> 
         </form>
      """.format(self.station_id)
      return(form)

   def pagination(self,link_prefix, total_items, ipp, p):
      plinks = []
      clinks = []
      total_pages = math.ceil(int(total_items) / int(ipp))
      page = """

         <div class="card">
            <div class="card-header">
               <h3 class="card-title">{:s} results {:s} items per page {:s} pages</h3>
            </div>

                <nav aria-label="Page navigation example">
                  <ul class="pagination" style="overflow:hidden;">
                    <li class="page-item">
                      <a class="page-link" href="#" aria-label="Previous">
                        <span aria-hidden="true">&laquo;</span>
                      </a>
                    </li>
      """.format(str(total_items), str(ipp), str(total_pages))
      extra_val = int(p) - 10
      if extra_val < 0:
         extra_val = abs(p)
      else:
         extra_val = 0 
      
      for i in range (0, int(total_pages)):
         link = link_prefix + str(i)
         if i == p:
            link = """<li class="page-item active"><a class="page-link" href="{:s}">{:s}</a></li>""".format(link, str(i+1))
         else:
            link = """<li class="page-item"><a class="page-link" href="{:s}">{:s}</a></li>""".format(link, str(i+1))
         if i - 8 <= p <= i + 8 :
      
            clinks.append(link)
         else: 
            plinks.append(link)

      for clink in clinks:
         page += clink


      page += """
                      <a class="page-link" href="#" aria-label="Next">
                        <span aria-hidden="true">&raquo;</span>
                      </a>
                    </li>
                 </ul>
               </nav>
         </div>
      """
      return(page)

   def get_meteor_gallery(self,in_data=None):
      data = []
      html = ""
      if "p" not in in_data:
         p = 0
      else:
         p= in_data['p']
      if "ipp" not in in_data:
         ipp = 50
      else:
         ipp = in_data['ipp']

      if "sort_by" not in in_data:
         sort_by = "date_desc"
      else:
         sort_by = in_data['sort_by']
         if sort_by is None or sort_by == "":
            sort_by = "date_desc"

      if "view_type" not in in_data:
         view_type = "all"
      else:
         view_type = in_data['view_type']

      if "confirm_status" not in in_data:
         confirm_status = "all"
      else:
         confirm_status = in_data['confirm_status']

      if "red_status" not in in_data:
         red_status = "all"
      else:
         red_status = in_data['red_status']



      offset = int(p) * int(ipp)

      where = ""
      where_cl = "WHERE"


      if view_type == "all":
         where += ""
      elif view_type == "ai_meteors":
         where += where_cl + " meteor_yn = 1 "
         where_cl = "AND"
      elif view_type == "ai_non_meteors":
         where += where_cl + " meteor_yn = 0 "
         where_cl = "AND"
      elif view_type == "ai_fireballs":
         where += where_cl + " fireball_yn = 1 "
         where_cl = "AND"
      else:
         where += ""

      if confirm_status == "all":
         where += ""
      elif confirm_status == "confirmed_meteor":
         where += where_cl + " human_confirmed = 1 "
         where_cl = "AND"
      elif confirm_status == "confirmed_non_meteor":
         where += where_cl + " human_confirmed = -1 "
         where_cl = "AND"
      elif confirm_status == "not_confirmed":
         where += where_cl + " human_confirmed = 0 "
         where_cl = "AND"

      if red_status == "all":
         where += ""
      elif red_status == "reduced":
         where += where_cl + " reduced = 1 "
         where_cl = "AND"
      elif red_status == "not_reduced":
         where += where_cl + " reduced = 0 "
         where_cl = "AND"
      else:
         where += ""


      if sort_by == "date_desc":
         sql_order_by = "root_fn DESC"
      elif sort_by == "date_asc":
         sql_order_by = "root_fn ASC"
      elif sort_by == "meteor_conf_desc":
         sql_order_by = "meteor_yn_conf DESC"
         where += where_cl + " meteor_yn_conf is not NULL and meteor_yn_conf != ''"
         where_cl = " AND "
      elif sort_by == "meteor_conf_asc":
         sql_order_by = "meteor_yn_conf ASC"
         where += where_cl + " meteor_yn_conf is not NULL and meteor_yn_conf != ''"
         where_cl = " AND "
      else:
         sql_order_by = "root_fn DESC"
     
 
      if True:

         sql = """
                SELECT count(*) 
                  FROM meteors
                  {:s}
         """.format(where )

         self.allsky_cur.execute(sql)
         rows = self.allsky_cur.fetchall()
         total_items = rows[0][0]

         sql = """
                SELECT station_id, camera_id, root_fn, start_datetime, reduced, multi_station,
                       event_id, ang_velocity, duration, meteor_yn, ai_resp, human_confirmed
                  FROM meteors
                       {:s}
              ORDER BY {:s}
                 LIMIT {:s} OFFSET {:s}
         """.format(str(where), sql_order_by, str(ipp), str(offset))
      self.allsky_cur.execute(sql)
      print(sql)
      rows = self.allsky_cur.fetchall()

      count = 1
 
      link_prefix = "/DASHBOARD/" + self.station_id + "/METEORS?cmd=metgal&ipp={:s}&sort_by={:s}&view_type={:s}&confirm_status={:s}&red_status={:s}&p=".format(str(ipp), sort_by,view_type,confirm_status, red_status)
      search_form = self.meteor_search_form(in_data)
      page = self.pagination(link_prefix, int(total_items), int(ipp), int(p))
      html += search_form

      for row in rows:
         station_id = row[0]
         camera_id = row[1]
         root_fn = row[2]
         start_datetime = row[3]
         reduced = row[4]
         multi_station = row[5]
         event_id = row[6]
         ang_vel = row[7]
         duration = row[8]
         final_meteor_yn = row[9]
         ai_resp = row[10]
         human_confirmed = row[11]

         html += self.meteor_image(count, station_id, root_fn, final_meteor_yn, ai_resp, human_confirmed, reduced, duration, ang_vel)
         count += 1

      html += "<div style='clear:both'></div><div>" + str(page) + "</div>"

      return(data, html)

   def get_meteor_stats(self,in_data=None):
      html = ""
      sql = """
            SELECT substr(root_fn,0,11) as mday, meteor_yn, fireball_yn, human_confirmed, reduced,  count(*)
               FROM meteors
           GROUP BY mday , meteor_yn, fireball_yn, human_confirmed, reduced 
           ORDER BY mday DESC
      """
      self.allsky_cur.execute(sql)
      rows = self.allsky_cur.fetchall()
      count = 1
      data = []
      day_data = {}

      for row in rows:
         print(row)
         mday = row[0]
         if mday not in day_data:
            day_data[mday] = {}
            day_data[mday]['meteor_yes'] = 0 
            day_data[mday]['meteor_no'] = 0 
            day_data[mday]['meteor_not_run'] = 0 
            day_data[mday]['fireball_yes'] = 0 
            day_data[mday]['human_confirmed'] = 0 
            day_data[mday]['not_human_confirmed'] = 0 
            day_data[mday]['reduced'] = 0 
            day_data[mday]['not_reduced'] = 0 
            day_data[mday]['total'] = 0 

      
         meteor_yn = row[1]
         fireball_yn = row[2]
         human_confirmed = row[3]
         reduced = row[4]
         count = row[5]
         if fireball_yn == 1:
            day_data[mday]['fireball_yes'] += count 
         if human_confirmed == 1:
            day_data[mday]['human_confirmed'] += count 
         else:
            day_data[mday]['not_human_confirmed'] += count 
         if reduced == 1:
            day_data[mday]['reduced'] += count 
         else:
            day_data[mday]['not_reduced'] += count 

         if meteor_yn == 1:
            day_data[mday]['meteor_yes'] += count 
         elif meteor_yn == 0:
            day_data[mday]['meteor_no'] += count 
         else:
            day_data[mday]['meteor_not_run'] += count 
         day_data[mday]['total'] += count 
      
         data.append((mday, count))
      html += """
          <div class="box">
           <div class="box-body">
              <table class="table table-bordered">
                 <tr>
                    <th>Day</th>
                    <th>AI Yes</th>
                    <th>AI No</th>
                    <th>AI Pending</th>
                    <th>AI Fireball Yes</th>
                    <th>Reduced</th>
                    <th>Human Confirmed</th>
                    <th>Total</th>
      """
      for mday in sorted(day_data.keys(), reverse=True): 
         
         html += "<tr><td>{:s}</td><td>{:s}</td><td> {:s}</td><td> {:s}</td><td> {:s}</td><td> {:s}</td><td> {:s}</td>   <td> {:s}</td></tr>".format(str(mday), str(day_data[mday]['meteor_yes']), str(day_data[mday]['meteor_no']), str(day_data[mday]['meteor_not_run']), str(day_data[mday]['fireball_yes']), str(day_data[mday]['reduced']), str(day_data[mday]['human_confirmed']), str(day_data[mday]['total']) ) 
      html += "</table></div></div>"
      return(data, html)

   def meteors_main(self, in_data=None):
      if in_data['cmd'] == "" or in_data['cmd'] is None:
         mout = self.meteor_main_menu(in_data)
         out = mout 
      elif in_data['cmd'] == "metstats" :
         mdata, mout = self.get_meteor_stats(in_data)
         mout = self.render_widget("meteor_stats_day", "Meteor Stats by Day", mout, 12)
         mout = self.render_widget_row([mout])
         out = mout 
      elif in_data['cmd'] == "metgal":
         mdata, mout = self.get_meteor_gallery(in_data)
         mout = self.render_widget("meteor_gallery", "Meteor Gallery", mout, 12)
         mout = self.render_widget_row([mout])
         out = mout 
      else:
         out = "Command not found." + in_data['cmd']
 
   
      template = self.env.get_template("default.html")
      tout = template.render(station_id=self.station_id, sidebar=self.render_side_nav(),DEFAULT_CONTENT=out, active_meteors="active")
      return(tout)
