class AllSkyWeather():

   def __init__(self, station_id=None, start_date=None, end_date=None):
      if station_id is not None:
         self.station_id = station_id
      else:
         self.station_id = None
      if start_date is not None:
         self.start_date = start_date 
      else:
         self.start_date = None
      if end_date is not None:
         self.end_date = end_date 
      else:
         self.end_date = None
