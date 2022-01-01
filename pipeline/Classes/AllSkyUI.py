import wx
from lib.conversions import datetime2JD
from PIL import ImageFont, ImageDraw, Image, ImageChops
import cv2
from lib.Calibration import find_stars_with_grid  , make_default_cal_params, get_catalog_stars, fetch_calib_data, update_center_radec,  get_image_stars, pair_stars, distort_xy, AzEltoRADec,HMS2deg, minimize_fov, XYtoRADec, find_stars_with_grid, draw_star_image, cat_star_report, minimize_fov


import datetime
from lib.Utils import convert_filename_to_date_cam, load_json_file, save_json_file
from lib.Network import get_station_data, fetch_url
import os
import numpy as np
from Classes.AIDB import AllSkyDB 
SHOW = 1

#class Frame(wx.Frame):

#    def __init__(self, image, parent=None, id=-1,pos=wx.DefaultPosition, title='wxPython'):
#        temp = image.ConvertToBitmap()
#        size = temp.GetWidth(), temp.GetHeight()
#        wx.Frame.__init__(self, parent, id, title, pos, size)
#        self.bmp = wx.StaticBitmap(parent=self, bitmap=temp)
#        self.SetClientSize(size)

class AllSkyUI():
    def __init__(self): 
       print("AllSkyCams User Interface")

    def startup(self):
       app = wx.App(False)
       frame = MainFrame(None, "ALLSKYCAMS STATION ADMIN")
       frame.Centre()
       frame.Show()
       app.MainLoop()

class OpenCalDialog(wx.Dialog): 
    def __init__(self, parent, title): 
       w = 300
       h = 300
       super(OpenCalDialog, self).__init__(parent, title = title, size = (w,h)) 
       panel = wx.Panel(self) 
       ID_CAL = wx.NewId()
       ID_OBS = wx.NewId()
       ID_EVT = wx.NewId()
       self.btn_new_cal = wx.Button(panel, ID_CAL, label = "Open Local File", size = (150,20), pos = (50,25))
       self.Bind(wx.EVT_MENU, self.NewCalWorkSpace, self.btn_new_cal)

class MainFrame(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800,600))
        #self.control = wx.TextCtrl(self, style=wx.TE_MULTILINE)
        self.AIDB = AllSkyDB()

        self.CreateStatusBar()
        filemenu = wx.Menu()

        ID_CAL = wx.NewId()
        ID_OBS = wx.NewId()
        ID_EVT = wx.NewId()

        self.last_click_x = None
        self.last_click_y = None
        cal_main = filemenu.Append(ID_CAL,"&Calibration"," Calibrate Systems")
        self.Bind(wx.EVT_MENU, self.OnCal, cal_main)

        obs_main = filemenu.Append(ID_OBS,"&Observation"," Observation")
        self.Bind(wx.EVT_MENU, self.OnObs, obs_main)

        evt_main = filemenu.Append(ID_EVT,"&Event"," Event")
        self.Bind(wx.EVT_MENU, self.OnEvent, evt_main)

        meteor_review = filemenu.Append(ID_EVT,"&Review Meteors"," Review Meteors")
        self.Bind(wx.EVT_MENU, self.OnReview, meteor_review)


        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_OPEN,"&Open"," Open")
        filemenu.AppendSeparator()

        filemenu.Append(wx.ID_SAVE,"&Save"," Save All Open Files")
        filemenu.AppendSeparator()
        filemenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")

        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File")
        self.SetMenuBar(menuBar)
        self.Show(True)

        menuItem = filemenu.Append(wx.ID_ABOUT, "&About"," Information about this program")
        self.Bind(wx.EVT_MENU, self.OnAbout, menuItem)


    def OnEvent(self,e):
        dataDir = "D:\\mrh\\ALLSKYOS\\Data"
        with wx.FileDialog(self, "Open Event JSON File", dataDir, 
                       style=wx.FD_OPEN ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            try:
                #with open(pathname, 'w') as file:
                self.doOpenObs(pathname)
            except IOError:
               print("Problem.")

    def OnReview(self,e):
       print("OK")   
       self.AIDB.review_meteors()

    def OnObs(self,e):
        dataDir = "D:\\mrh\\ALLSKYOS\\Data"
        with wx.FileDialog(self, "Open OBS Video File", dataDir, 
                       style=wx.FD_OPEN ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            self.doOpenObs(pathname)
            try:
                #with open(pathname, 'w') as file:
                self.doOpenObs(pathname)
            except IOError:
               print("Problem.")



    def get_stars(self):
       first_frame = cv2.resize(self.frames[0], (1920, 1080))
       last_frame = cv2.resize(self.frames[-1], (1920, 1080))
       diff_frame = cv2.subtract(first_frame,last_frame)
      
       hdm_x = 1920 / 1280
       hdm_y = 1080 / 720

       self.cp['user_stars'] = find_stars_with_grid(first_frame)
       self.cp = pair_stars(self.cp, self.meteor_fn, self.json_conf, first_frame)


       print("IMAGE STARS:", self.cp['cat_image_stars'])
       good_stars = []
       for star in self.cp['cat_image_stars']:
          dcname,mag,ra,dec,img_ra,img_dec,match_dist,new_x,new_y,img_az,img_el,new_cat_x,new_cat_y,six,siy,cat_dist,star_int = star
          print("STAR:", dcname, new_cat_x,new_cat_y,six,siy,cat_dist)
          if cat_dist <= 10:
             good_stars.append(star)
       self.cp['cat_image_stars'] = good_stars
       self.cp['cat_image_stars'], res_px,res_deg = cat_star_report(self.cp['cat_image_stars'], 4)
       self.cp['total_res_px'] = res_px
       self.cp['total_res_deg'] = res_deg

       return(self.cp['user_stars'])

    def doOpenObs(self, meteor_video_file):
        self.frame_data = {}
        self.meteor_data = {}
        self.cp = {}
        self.meteor_video_file = meteor_video_file
        if "\\" in self.meteor_video_file:
            self.meteor_video_file = self.meteor_video_file.replace("\\", "/")


        meteor_json_file = self.meteor_video_file.replace(".mp4", ".json")

        if os.path.exists(meteor_json_file) is True:
            data = load_json_file(meteor_json_file)
            print("METEOR DATA:", data.keys())
            self.frame_data = data['frame_data']
            self.meteor_data = data['meteor_data']
            if "cp" in data:
               self.cp = data['cp']
            else:
               self.cp = {}
            print("Loaded saved file.")

        #print("CP:", self.cp['cat_image_stars'])
 
        if "cat_image_stars" not in self.cp:
           self.load_calib() 
        else:
           self.set_filename_info()

        # set the lens model
        if "x_poly" in self.lens_model:
           print(self.lens_model)
           self.cp['x_poly'] = self.lens_model['x_poly']
           self.cp['y_poly'] = self.lens_model['y_poly']
           self.cp['x_poly_fwd'] = self.lens_model['x_poly_fwd']
           self.cp['y_poly_fwd'] = self.lens_model['y_poly_fwd']

        self.add_console_data_to_image(None, 100, 1280)


      

        cap = cv2.VideoCapture(meteor_video_file)

        grabbed = True
        last_frame = None
        stacked_frame = None

        self.frames = []
        self.subframes = []
        if True:
            while grabbed is True:
                grabbed , frame = cap.read()
                if not grabbed :
                    break
                frame = cv2.resize(frame, (1280,720))
                if stacked_frame is None:
                   stacked_frame = frame
                stacked_frame = self.stack_stack(frame, stacked_frame) 
                sub_frame = cv2.subtract(frame, stacked_frame)
                self.frames.append(frame)
                self.subframes.append(sub_frame)

        # only get stars if the cp is not already loaded?
        if "cat_image_stars" not in self.cp:

            self.stars = self.get_stars()



        self.fn = 0
        self.stack_img = stacked_frame.copy() 
        stacked_frame_show = stacked_frame.copy()

        star_image = cv2.resize(stacked_frame_show,(1920,1080))
        minimize_fov(self.meteor_fn, self.cp, self.meteor_fn,star_image,self.json_conf )

        star_image = draw_star_image(star_image, self.cp['cat_image_stars'],self.cp)
        self.star_image = cv2.resize(star_image,(1280,720))


        #cv2.imshow('stars', star_image)

        if "roi_720p" not in self.meteor_data:

            cv2.imshow('pepe', stacked_frame_show)
            cv2.setMouseCallback('pepe',self.crop_roi)
            cv2.waitKey(0)
        else:
            self.roi = self.meteor_data['roi_720p']

        thresh_adj = 0
        self.star_mode = False
        while True:
            frame = self.frames[self.fn].copy()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            roi_x1,roi_y1,roi_x2,roi_y2 = self.roi
            gray_roi = gray[roi_y1:roi_y2,roi_x1:roi_x2]
            
            min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray_roi)
            avg_val = np.mean(gray_roi)
            before_fn = self.fn - 1
            after_fn = self.fn + 1
            before_cnt = None
            after_cnt = None
            if before_fn in self.frame_data:
                if "conts" in self.frame_data[before_fn]:
                    if len(self.frame_data[before_fn]['conts']) > 0:
                        before_cnt = self.frame_data[before_fn]['conts'][0]
                        print("BEFORE CNT:", before_cnt)
            if after_fn in self.frame_data:
                if "conts" in self.frame_data[after_fn]:
                    if len(self.frame_data[after_fn]['conts']) > 0:
                        after_cnt = self.frame_data[after_fn]['conts'][0]
                        print("AFTER CNT:", after_cnt)


            if self.fn in self.frame_data:
               print("FRAME DATA RECORD FOUND!", self.frame_data[self.fn])
               if "thresh_adj" in self.frame_data[self.fn]:
                  thresh_adj = self.frame_data[self.fn]['thresh_adj']
               thresh_val = (max_val * .75) + thresh_adj
            else:
               thresh_val = (max_val * .75) + thresh_adj
               if thresh_val < avg_val * 2:
                  thresh_val = avg_val * 2 
               if thresh_val < 80:
                  thresh_val = 80 

            _, thresh_img = cv2.threshold(gray_roi.copy(), thresh_val, 255, cv2.THRESH_BINARY)

         
            frame_m, roi_img_m, conts = self.do_cnts_in_thresh(frame.copy(), thresh_img, roi_x1,roi_y1)
            conts = sorted(conts, key=lambda x: (x[2]*x[3]), reverse=True)
            if self.fn not in self.frame_data:
               self.frame_data[self.fn] = {}

            if self.fn in self.frame_data:
                self.frame_data[self.fn]['thresh_adj'] = thresh_adj
                self.frame_data[self.fn]['conts'] = conts
            
            if "user_x" in self.frame_data[self.fn]:
                cv2.circle(frame_m,(int(self.frame_data[self.fn]['user_x']),int(self.frame_data[self.fn]['user_y'])), 3, (0,255,0), 1)

            if before_cnt is not None:
                bx1, by1,bx2,by2 = before_cnt
                cv2.rectangle(frame_m, (bx1, by1), (bx2,by2), (128,128,0), 1)
                print("BEFORE CNT!")


            if len(conts) > 0:
                cx1,cy1,cx2,cy2 = conts[0]
                cw = cx2 - cx1
                ch = cy2 - cy1
                if cw > ch:
                   ch = cw
                else:
                   cw = ch
                center_x = int((cx1+cx2) / 2)
                center_y = int((cy1+cy2) / 2)
                cont_img = self.frames[self.fn].copy()[cy1:cy2,cx1:cx2]

                cv2.circle(frame_m,(int(center_x),int(center_y)), 3, (0,0,255), 1)
                print("SHAP:", cont_img.shape)
                cont_img = cv2.resize(cont_img,(300,300))
                #cv2.imshow('pepe3', cont_img)
            #cv2.imshow('pepe2', thresh_img)



            hd_x = 0
            hd_y = 0
            color = (0,0,255)
            desc = str(self.fn)
            frame = self.draw_frame(frame_m, self.fn, desc,hd_x,hd_y,color)

            roi_x1,roi_y1,roi_x2,roi_y2 = self.roi
            cv2.rectangle(frame, (roi_x1, roi_y1), (roi_x2,roi_y2), color, 1)



            #cv2.imshow('pepe2', self.console_img)
            console = self.console_img.copy()
            cv2.putText(console, "FN: " + str(self.fn) ,  (10, 10), cv2.FONT_HERSHEY_SIMPLEX, .3, (255, 200, 200), 1)

            frame[620:720,0:1280] = console
            cv2.imshow('pepe', frame)
            key = cv2.waitKey(0)
            cv2.setMouseCallback('pepe',self.draw_circle)
            print("KEY:", key)
            if key == 61:
                # plus
                thresh_adj += 1
                print("THRESH VAL:", thresh_val)
                _, thresh_img = cv2.threshold(gray_roi.copy(), thresh_val, 255, cv2.THRESH_BINARY)
                frame, roi_img, conts = self.do_cnts_in_thresh(frame, thresh_img, roi_x1,roi_y1)
                self.frame_data[self.fn]['thresh_adj'] = thresh_adj
                self.frame_data[self.fn]['conts'] = conts
                print("NEW CONTS:", conts)
                cv2.imshow('pepe', frame)
               # cv2.imshow('pepe2', roi_img)

            if key == 45:
                # negative
                thresh_adj -= 1
                print("THRESH VAL:", thresh_val)
                _, thresh_img = cv2.threshold(gray_roi.copy(), thresh_val, 255, cv2.THRESH_BINARY)
                frame, roi_img, conts = self.do_cnts_in_thresh(frame, thresh_img, roi_x1=0,roi_y1=0)
                self.frame_data[self.fn]['thresh_adj'] = thresh_adj
                self.frame_data[self.fn]['conts'] = conts
                print("NEW CONTS:", conts)
                cv2.imshow('pepe', frame)
               # cv2.imshow('pepe2', roi_img)

            if key == 113:
               cv2.destroyAllWindows()

               return()
            if key == 97:
               self.fn = self.fn - 1
               if self.fn < 0 :
                  self.fn = 0
               frame = self.frames[self.fn].copy()
               desc = str(self.fn)
               frame = self.draw_frame(frame, self.fn, desc,hd_x,hd_y,color)
               print("SHOWING FRAME:", self.fn)
            if key == 102:
               self.fn = self.fn + 1
               if self.fn >= len(self.frames) - 1 :
                  self.fn = 0
               frame = self.frames[self.fn].copy()
               desc = str(self.fn)
               frame = self.draw_frame(frame, self.fn, desc,hd_x,hd_y,color)
           #    cv2.imshow('pepe', frame)
               print("SHOWING FRAME:", self.fn)
            if key == 115:
               print("SHOW [S]TARS")
               if self.star_mode is False:
                   self.star_mode = True
               else:
                   self.star_mode = False 
               cv2.imshow('pepe', self.star_image)
               cv2.waitKey(0)

            if key == 120:
               print("[X] Remove User Point for this FN", self.fn)
               if self.fn in self.frame_data:
                   if "user_x" in self.frame_data[self.fn]:
                       del self.frame_data[self.fn]['user_x'] 
                       del self.frame_data[self.fn]['user_y'] 
            if key == 109:
               print("[M]inimize FOV ", self.fn)
               minimize_fov(self.meteor_fn, self.cp, self.meteor_fn,star_image,self.json_conf )
               

            # UPDATE FRAME DATA RECORD WITH AVAILABLE INFO!
            if self.fn not in self.frame_data:
               self.frame_data[self.fn] = {}
            #self.frame_data[fn]['custom_xy'] = 
            self.save_meteor_obs()


    def do_cnts_in_thresh(self, frame, thresh_img, roi_x1=0,roi_y1=0):

        cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = self.which_cnts(cnt_res)

        conts = []
        cc = 0
        color = (0,0,255)
        for (i,c) in enumerate(cnts):
            cx,cy,cw,ch = cv2.boundingRect(cnts[i])
            rx1 = cx
            ry1 = cy
            rx2 = cx+cw
            ry2 = cy+ch

            cx1 = cx + roi_x1
            cy1 = cy + roi_y1
            cx2 = cx1+cw
            cy2 = cy1+ch
            cv2.rectangle(frame, (cx1, cy1), (cx2,cy2), color, 1)
            cv2.rectangle(thresh_img, (rx1, ry1), (rx2,ry2), (128,128,128), 1)
            conts.append((cx1,cy1,cx2,cy2))
        return(frame, thresh_img, conts)


    def mouse_zoom(self,img,x,y,size=50):
       x1 = x - int(size / 2)
       y1 = y - int(size/2) 
       x2 = x + int(size/2)
       y2 = y + int(size/2)
       if x1 < 0:
          x1 = 0
          x2 = size 
       if y1 < 0:
          y1 = 0
          y2 = size 
       if x2 > img.shape[1]:
          x2 = img.shape[1]
          x1 = img.shape[1] - size
       if y2 > img.shape[0]:
          y2 = img.shape[0]
          y1 = img.shape[0] - size
       zoom_img = img[y1:y2,x1:x2]
       zoom_img = cv2.resize(zoom_img, (300,300))
       return(zoom_img)

    def crop_roi(self, event,x,y,flags,param):
        if event == cv2.EVENT_LBUTTONDBLCLK:
            print("CROP ROI", x,y)
            self.roi_from_stack_click(self.stack_img, x, y)

    def roi_from_stack_click(self, img, x,y):
        img_res = str(img.shape[0])
        roi_key = "roi_" + img_res + "p"
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #min_val, max_val, min_loc, (mx,my)= cv2.minMaxLoc(gray)
        pos_val = int(gray[y,x] * .6)
        while True:
            _, thresh_img = cv2.threshold(gray.copy(), pos_val, 255, cv2.THRESH_BINARY)

            cnt_res = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = self.which_cnts(cnt_res)

            conts = []
            show_stack = img.copy()
            cc = 0
            for (i,c) in enumerate(cnts):
                cx,cy,cw,ch = cv2.boundingRect(cnts[i])
                x1 = cx
                y1 = cy
                x2 = cx+cw
                y2 = cy+ch
                if x1 <= x <= x2 and y1 <= y <= y2:
                   color = (255,0,0)
                   roi_x1 = x1
                   roi_x2 = x2
                   roi_y1 = y1
                   roi_y2 = y2

                   roi_x1, roi_y1, roi_x2, roi_y2 = self.bound_cnt(roi_x1,roi_y1,roi_x2,roi_y2,show_stack )
                   self.meteor_data[roi_key] = [roi_x1, roi_y1, roi_x2,roi_y2]
                   cv2.rectangle(show_stack, (roi_x1, roi_y1), (roi_x2,roi_y2), color, 1)
                else:
                   color = (128,128,128)
                desc = "obj " + str(cc)
                cv2.putText(show_stack, desc,  (x1,y1), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
                cv2.rectangle(show_stack, (x1, y1), (x2,y2), color, 1)
                cc += 1


            cv2.imshow('pepe', show_stack)
            key = cv2.waitKey(0)
            print("KEY:", key)
            if key == 113:
                break
            if key == 61:
                # plus
                pos_val += 1
            if key == 45:
                # negative 
                pos_val -= 1
            if key == 32:
                # space 
                print("ACCEPT THE ROI CROP AREA OF:", roi_x1, roi_y1, roi_x2, roi_y2)
                show_stack = img.copy()
                self.roi = [roi_x1,roi_y1,roi_x2,roi_y2]
                cv2.rectangle(show_stack, (roi_x1, roi_y1), (roi_x2,roi_y2), color, 1)
                cv2.imshow('pepe', show_stack)
                key = cv2.waitKey(0)
                break
        
    def save_meteor_obs(self):
       data = {}
       data['meteor_data'] = self.meteor_data
       data['frame_data'] = self.frame_data
       data['cp'] = self.cp
       data['meteor_video_file'] = self.meteor_video_file
       meteor_json_file = self.meteor_video_file.replace(".mp4", ".json")
       save_json_file(meteor_json_file, data)

    def draw_circle(self, event,x,y,flags,param):
        global user_clicks
        global frames

        global f
        global user_frames
        global mouseX,mouseY
        self.color = [0,255,0]
        frame = self.frames[self.fn].copy()
        if event == cv2.EVENT_MOUSEMOVE and self.star_mode is True:
            zoom_img = self.mouse_zoom(self.frames[self.fn], x,y,50)
            zoom_img[0:300,149:150] = [255,255,255]
            zoom_img[149:150,0:300] = [255,255,255]
            frame[0:300,980:1280] = zoom_img
            if self.last_click_x is not None:
               frame = self.draw_frame(frame, self.fn, None,self.last_click_x,self.last_click_y,self.color)
            cv2.imshow('pepe', frame)
        if event == cv2.EVENT_LBUTTONDBLCLK:
            #cv2.circle(frame,(x,y),100,(255,0,0),-1)
            self.last_click_x = x
            self.last_click_y = y
            mouseX,mouseY = x,y
            if self.fn not in self.frame_data:
               self.frame_data[self.fn] = {}
            if self.star_mode is False:
                self.frame_data[self.fn]['user_x'] = x
                self.frame_data[self.fn]['user_y'] = y
                fh,fw = frame.shape[:2]
                frame = self.draw_frame(frame, self.fn, None,x,y,self.color)
                zoom_img = self.mouse_zoom(self.frames[self.fn], x,y,50)
                zoom_img[0:300,149:150] = [255,255,255]
                zoom_img[149:150,0:300] = [255,255,255]
                frame[0:300,980:1280] = zoom_img
            #cv2.circle(frame,(int(x),int(y)), 3, (0,255,0), 1)
            #cv2.putText(frame, "FN: " + str(f) ,  (25, fh - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
                cv2.imshow('pepe', frame)
            #key = cv2.waitKey(0)

            print("CALLBACK:", self.fn, mouseX,mouseY)


    def OnCal(self,e):
        #dlg = wx.MessageDialog( self, "What do you want to work on? ", "ALLSKYOS MANAGER", wx.OK)

        #dlg.ShowModal()
        #dlg.Destroy()

        #a = OpenCalDialog(self, "Select Calibration Image").Show()
        dataDir = "D:\\mrh\\ALLSKYOS\\Data"
        with wx.FileDialog(self, "Open Image for Calibration", dataDir, 
                       style=wx.FD_OPEN ) as fileDialog:

            if fileDialog.ShowModal() == wx.ID_CANCEL:
                return     # the user changed their mind

            # save the current contents in the file
            pathname = fileDialog.GetPath()
            try:
                #with open(pathname, 'w') as file:
                self.doOpenCal(pathname)
            except IOError:
                wx.LogError("Cannot save current data in file '%s'." % pathname)



    def doOpenCal(self, image_file):
       if "AMS" in image_file:
          if "/" in image_file:
             image_fn = image_file.split("/")[-1]
          else:
             image_fn = image_file.split("\\")[-1]
          station_id = image_fn.split("_")[0]
          self.station_id = station_id
          print("STATION ID:", station_id)
          temp_file = image_file.replace(station_id + "_", "")
          print("TEMP:", temp_file)
          station_data, station_dict = get_station_data()
          station_conf_file = "Data/STATION_DATA/" + station_id + "_conf.json"

          if os.path.exists(station_conf_file) == 0:
             remote_file = "https://archive.allsky.tv/" + station_id + "/CAL/as6.json"
             remote_conf = fetch_url(remote_file, json=1)
             try:
                remote_conf = json.loads(remote_conf)
             except:
                print("Couldn't read the json file?")
             save_json_file(station_conf_file, remote_conf)
             print("REMOTE CONF:", remote_conf)
          else:
             remote_conf = load_json_file(station_conf_file)
          lat = remote_conf['site']['device_lat']
          lon = remote_conf['site']['device_lng']
          alt = remote_conf['site']['device_alt']

       print(station_dict.keys())
       (f_datetime, cam_id, f_date_str,fy,fmon,fd, fh, fm, fs) = convert_filename_to_date_cam(temp_file)

       for cam_num in remote_conf['cameras']:
          if remote_conf['cameras'][cam_num]['cams_id'] == cam_id:
             this_cam_num = cam_num.replace("cam", "")
             print("THIS CAM IS:", this_cam_num)

       self.SetSize(wx.Size(500,800))
       #image = wx.StaticBitmap(self, wx.ID_ANY)

       png = wx.Image(image_file, wx.BITMAP_TYPE_PNG)
       #image.SetBitmap(wx.Bitmap(image_file))


       cv2_image = cv2.imread(image_file)

       panel = wx.Panel(self)
       vbox = wx.BoxSizer(wx.VERTICAL)
       hbox1 = wx.BoxSizer(wx.HORIZONTAL)


       # LABEL
       l1 = wx.StaticText(panel, -1, "Station ID")
       hbox1.Add(l1, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_station_id = wx.TextCtrl(panel, value=station_id) 
       hbox1.Add(self.t1_station_id,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_station_id.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox1) 


       ###
       hbox1a = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l1a = wx.StaticText(panel, -1, "Cam ID")
       hbox1a.Add(l1a, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_cam_id = wx.TextCtrl(panel, value=cam_id) 
       hbox1a.Add(self.t1_cam_id,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_cam_id.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox1a) 





       hbox2 = wx.BoxSizer(wx.HORIZONTAL)

       # LABEL
       l2 = wx.StaticText(panel, -1, "Latitude")
       hbox2.Add(l2, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_lat = wx.TextCtrl(panel, value=lat) 
       hbox2.Add(self.t1_lat,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_lat.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox2) 

       hbox3 = wx.BoxSizer(wx.HORIZONTAL)
       
       # LABEL
       l3 = wx.StaticText(panel, -1, "Longitude")
       hbox3.Add(l3, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_lon = wx.TextCtrl(panel, value=lon) 
       hbox3.Add(self.t1_lon,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_lon.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox3) 

       hbox4 = wx.BoxSizer(wx.HORIZONTAL)

       # LABEL
       l4 = wx.StaticText(panel, -1, "Altitude")
       hbox4.Add(l4, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_alt = wx.TextCtrl(panel, value=alt) 
       hbox4.Add(self.t1_alt,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_alt.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox4) 

       hbox5 = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l5 = wx.StaticText(panel, -1, "Center FOV Azimuth")
       hbox5.Add(l5, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_az = wx.TextCtrl(panel) 
       hbox5.Add(self.t1_az,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_az.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox5) 


       hbox6 = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l6 = wx.StaticText(panel, -1, "Center FOV Elevation")
       hbox6.Add(l6, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_el = wx.TextCtrl(panel) 
       hbox6.Add(self.t1_el,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_el.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox6) 

       hbox7 = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l7 = wx.StaticText(panel, -1, "Position Angle")
       hbox7.Add(l7, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_pos = wx.TextCtrl(panel) 
       hbox7.Add(self.t1_pos,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_pos.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox7) 

       hbox8 = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l8 = wx.StaticText(panel, -1, "Pixel Scale")
       hbox8.Add(l8, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_pixscale = wx.TextCtrl(panel) 
       hbox8.Add(self.t1_pixscale,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_pixscale.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox8) 

       hbox9 = wx.BoxSizer(wx.HORIZONTAL)
       # LABEL
       l9 = wx.StaticText(panel, -1, "Calibration Date Time")
       hbox9.Add(l9, 1, wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5) 
       #FIELD
       self.t1_calib_datetime = wx.TextCtrl(panel, value=f_date_str) 
       hbox9.Add(self.t1_calib_datetime,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       # BIND
       self.t1_calib_datetime.Bind(wx.EVT_TEXT,self.OnKeyTyped) 
       vbox.Add(hbox9) 



       # ADD BUTTONS!
       hbox10 = wx.BoxSizer(wx.HORIZONTAL)
       self.btn_show_stars = wx.Button(panel, -1, label = "Show Catalog Stars", size = (150,20))
       hbox10.Add(self.btn_show_stars,1,wx.EXPAND|wx.ALIGN_LEFT|wx.ALL,5)
       self.btn_show_stars.Bind(wx.EVT_BUTTON,self.OnShowStars) 
       vbox.Add(hbox10) 









       panel.SetSizer(vbox)
       self.Centre()
       self.Show()
       self.Fit()

       self.SetSize(wx.Size(500,800))
       self.Show()

       #t1 = wx.TextCtrl(self) 

       default_cp = make_default_cal_params(station_id, cam_id)
       #cat_stars = get_catalog_stars(default_cp)
       #for star in cat_stars:
       #   print(star)

       #find_stars_with_grid(cv2_image)

       cv2.startWindowThread()
       cv2.namedWindow("preview")
       cv2.imshow('preview', cv2_image)
       cv2.waitKey()

       #sizer = wx.BoxSizer()
       #sizer.Add(image)
       #self.SetSizerAndFit(sizer)

    def OnShowStars(self,e):
        print("SHOW CAT STARS!")
        print("ST:", self.t1_station_id.GetValue())

    def OnKeyTyped(self,e):
        print("KEY PRESSED.")

    def OnAbout(self,e):
        dlg = wx.MessageDialog( self, "ALLSKYCAMS STATION ADMIN" "ALLSKYCAMS STATION ADMIN", wx.OK)
 
        dlg.ShowModal()
        dlg.Destroy()

    def draw_frame(self,frame, f, desc, x, y,color):
        if x is not None:
           cv2.circle(frame,(int(x),int(y)), 3, color, 1)
        fh,fw = frame.shape[:2]
        cv2.putText(frame, "FN: " + str(f) ,  (25, fh - 25), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 200, 200), 1)
        return(frame)

    def stack_stack(self, new_frame, stack_frame):
        pic1 = Image.fromarray(new_frame)
        pic2 = Image.fromarray(stack_frame)
        stacked_image=ImageChops.lighter(pic1,pic2)
        return(np.asarray(stacked_image))

    def which_cnts(self, cnt_res):
        if len(cnt_res) == 3:
            (_, cnts, xx) = cnt_res
        elif len(cnt_res) == 2:
            (cnts, xx) = cnt_res
        return(cnts)

    def bound_cnt(self, x1,y1,x2,y2,img):
       ih,iw = img.shape[:2]
       rw = x2 - x1
       rh = y2 - y1
       if rw > rh:
          rh = rw
       else:
          rw = rh
       rw += int(rw * .3)
       rh += int(rh * .3)
       if rw >= ih or rh >= ih:
          rw = int(ih*.95)
          rh = int(ih*.95)
       if rw < 100 or rh < 100:
          rw = 100
          rh = 100

       cx = int((x1 + x2)/2)
       cy = int((y1 + y2)/2)
       nx1 = cx - int(rw / 2)
       nx2 = cx + int(rw / 2)
       ny1 = cy - int(rh / 2)
       ny2 = cy + int(rh / 2)
       if nx1 <= 0:
          nx1 = 0
          nx2 = rw
       if ny1 <= 0:
          ny1 = 0
          ny2 = rh
       if nx2 >= iw:
          nx1 = iw-rw-1
          nx2 = iw-1
       if ny2 >= ih:
          ny2 = ih-1
          ny1 = ih-rh-1
       if ny1 <= 0:
          ny1 = 0
       if nx1 <= 0:
          nx1 = 0
       print("NX", nx1,ny1,nx2,ny2)
       return(nx1,ny1,nx2,ny2)


    def add_console_data_to_image(self, image, height=100, width=1280):
       color = [0,0,255]
       console_img = np.zeros((100,1280,3),dtype=np.uint8)
       station_desc = self.station_id + " - " + self.json_conf['site']['operator_name'] 
       lat = self.json_conf['site']['device_lat']
       lon = self.json_conf['site']['device_lng']
       alt = self.json_conf['site']['device_alt']
       lat_desc = str(lat) + " " + str(lon) + " " + str(alt)
       print("LENS:", self.lens_model)
       if len(self.cals_in_range) > 0:
           print("CALS IN RANGE FOUND")
           center_az, center_el, position_angle, pixel_scale = self.cals_in_range[0]
       else:
           print("NO CALS IN RANGE????")
           center_az, center_el, position_angle, pixel_scale = [0,0,0,0]
       cal_desc = str(center_az) + " " + str(center_el) + " " + str(position_angle) + " " + str(pixel_scale)
       cv2.putText(console_img, station_desc + " " + lat_desc + " " + str(cal_desc),  (10,80), cv2.FONT_HERSHEY_SIMPLEX, .4, color, 1)
       #cv2.imshow('pepe4', console_img)
       #cv2.waitKey(0)
       self.console_img = console_img
       # add site name lat/lon/alt

    def set_filename_info(self):
        if "/" in self.meteor_video_file:
           meteor_fn = self.meteor_video_file.split("/")[-1]

        el = meteor_fn.split("_")
        self.year = el[1]
        self.month = el[2]
        self.day = el[3]
        self.hour = el[4]
        self.minute = el[5]
        self.second = el[6]
        self.micro_second = el[7]
        self.extra_info = el[8]
        self.obs_date_str = self.year + "_" + self.month + "_" + self.day
        self.obs_date_datetime = datetime.datetime.strptime(self.obs_date_str, "%Y_%m_%d")
        fl = self.extra_info.split("-")
        self.camera_id = fl[0]
        self.trim_num = self.extra_info.replace(self.camera_id + "-trim", "").replace("-", "")
        self.trim_num = self.trim_num.replace(".mp4", "")
        station_id = el[0]
        self.cals_in_range = []
        self.extra_cals = []

        self.station_id = station_id
        self.meteor_fn = meteor_fn.replace(station_id + "_", "") 
        self.cal_hist, self.json_conf, self.lens_model = fetch_calib_data(station_id, self.camera_id)

        for row in self.cal_hist:
           greater_than_end = 0
           in_range = 0
           # camera, end_date, start_date center_az, center_el, center_pos, center_pix, res
           camera, end_date, start_date, center_az, center_el, center_pos, center_pix, res = row
           sdt = datetime.datetime.strptime(start_date, "%Y_%m_%d")
           edt = datetime.datetime.strptime(end_date, "%Y_%m_%d")
           #print("OBS DATE:", self.obs_date_datetime)
           #print("RANGE START:", sdt)
           #print("RANGE END:", edt)
           if camera == self.camera_id:
              if self.obs_date_datetime > edt:
                 greater_than_end = 1
              if sdt <= self.obs_date_datetime <= edt:
                 print("CAL IN RANGE!")
                 in_range = 1
                 self.cals_in_range.append((center_az, center_el,center_pos,center_pix))
              else:
                 print("CAL NOT IN RANGE!")
                 self.extra_cals.append((center_az, center_el,center_pos,center_pix))
              # check if the file date is inside the range
              print(greater_than_end, in_range, row)


    def load_calib(self):
        if "/" in self.meteor_video_file:
           meteor_fn = self.meteor_video_file.split("/")[-1]
        
        el = meteor_fn.split("_")
        self.year = el[1]
        self.month = el[2]
        self.day = el[3]
        self.hour = el[4]
        self.minute = el[5]
        self.second = el[6]
        self.micro_second = el[7]
        self.extra_info = el[8]
        self.obs_date_str = self.year + "_" + self.month + "_" + self.day 
        self.obs_date_datetime = datetime.datetime.strptime(self.obs_date_str, "%Y_%m_%d")
        fl = self.extra_info.split("-")
        self.camera_id = fl[0]
        self.trim_num = self.extra_info.replace(self.camera_id + "-trim", "").replace("-", "")
        self.trim_num = self.trim_num.replace(".mp4", "")
        self.cals_in_range = []
        self.extra_cals = []

        station_id = el[0]

        self.station_id = station_id
        self.meteor_fn = meteor_fn.replace(station_id + "_", "") 

        self.cal_hist, self.json_conf, self.lens_model = fetch_calib_data(station_id, self.camera_id)
        print("STATION/CAM:", station_id, self.camera_id, self.trim_num)
        for row in self.cal_hist:
           greater_than_end = 0
           in_range = 0
           # camera, end_date, start_date center_az, center_el, center_pos, center_pix, res
           camera, end_date, start_date, center_az, center_el, center_pos, center_pix, res = row
           sdt = datetime.datetime.strptime(start_date, "%Y_%m_%d")
           edt = datetime.datetime.strptime(end_date, "%Y_%m_%d")
           #print("OBS DATE:", self.obs_date_datetime)
           #print("RANGE START:", sdt)
           #print("RANGE END:", edt)
           if camera == self.camera_id:
              if self.obs_date_datetime > edt:
                 greater_than_end = 1
              if sdt <= self.obs_date_datetime <= edt:
                 print("CAL IN RANGE!")
                 in_range = 1
                 self.cals_in_range.append((center_az, center_el,center_pos,center_pix))
              else:
                 print("CAL NOT IN RANGE!")
                 self.extra_cals.append((center_az, center_el,center_pos,center_pix))
              # check if the file date is inside the range
              print(greater_than_end, in_range, row)

        if len(self.cals_in_range) > 0:
           center_az, center_el, position_angle, pixel_scale = self.cals_in_range[0]
           cp = {}
           cp['imagew'] = 1920
           cp['imageh'] = 1080
           cp['ra_center'] = 0
           cp['dec_center'] = 0
           cp['center_az'] = center_az
           cp['center_el'] = center_el
           cp['position_angle'] = position_angle 
           cp['pixscale'] = pixel_scale 
           cp = update_center_radec(self.meteor_fn,cp,self.json_conf)
           self.cp = cp
           print("RA DEC CENTER:???", cp['ra_center'], cp['dec_center'])




#class App(wx.App):
#    def OnInit(self):

        # Show an image
        #image = wx.Image('Data/SAMPLES/AMS18_2021_07_16_00_32_02_000_010103.png', wx.BITMAP_TYPE_PNG)
        #self.frame = MainFrame("None", "ALLSKYOS")
        #wx.Frame.__init__(self,parent,title=title,size=(200,100))
        #self.Show(True)
        #self.SetTopWindow(self.frame)

        # Main Window


        #return True
if __name__ == "__main__":
   app = wx.App(False)
   frame = MainFrame(None, "ALLSKY STATION SOFTWARE")
   frame.Centre()
   frame.Show()
   app.MainLoop()
