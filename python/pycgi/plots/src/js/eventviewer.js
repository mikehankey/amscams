
      /************ GRAPHICS STYLES ********************/
      var PLOT_W = 937;
      var PLOT_H = 517;
      var GRID_COLOR = 'rgba(255,255,255,.2)';
      var TICK_FONT_COLOR = 'rgba(255,255,255,.35)';
      var H_LINE_COLOR = 'rgba(255,255,255,.2)';
      var V_LINE_COLOR = 'rgba(255,255,255,.5)';
      var FONT_COLOR = '#ffffff';
      var AXIS_FONT_COLOR = '#b1b1b1';
      var PAPER_BG_COLOR = 'rgba(9,29,63,1)';
      var PLOT_BG_COLOR = PAPER_BG_COLOR;
      var TRENDLINE_COLOR = 'rgba(213,42,224,.5)';
      var DEFAULT_LINE_COLOR = 'rgba(213,42,224,.5)';

      // 3D Plot
      var D_H_LINE_COLOR = '#fff';  
      var D_V_LINE_COLOR = '#fff';  
      var D_GRID_COLOR = '#464545';
     
      // LEGEND
      var LEGEND_FONT_COLOR = FONT_COLOR;
      var LEGEND_BORDER = 'rgba(255,255,255,.0)';
      var LEGEND_BG = 'rgba(255,255,255,0)';

      // GEO
      var RIVER_COLOR = "#c8eaff";
      var LAND_COLOR = "#d4ffae";
      var SUB_UNIT_BORDER = "#ccc";

      // METEOR POSITION SYMBOL
      var DEFAULT_METEOR_SYMBOL = "square-open-dot";

      // ALL MARKERS (ONE FOR EACH STATION)
      // see https://plot.ly/javascript/reference/#scatter-marker
      var ALL_MARKERS = ["cross-open","diamond-open","square-open","pentagon-open","hexagon-open","octagon-open","star-open","hexagram-open"];
      var MARKER_CNT = 0; 

      var XY_SERIES_MAX = 3;
 
      /*******************************/
      var graph_counter = 0;


      /*********** UI ***************************/
      // Hide legend on hover (if data is behind)
      function hide_legend_on_hover() {
         $('.js-plotly-plot').mouseenter(function() {
            $(this).find('.legend').hide();
         }).mouseout(function() {
            $(this).find('.legend').show();
         });
      }

 
      /*********** PARSE URL ***************************/

      // URL PARAM:
      // j= json with plots
      // t= which plots we want to display

      // Print error
      function print_error(txt) {
         $('<div class="alert alert-danger" style="color:#fff;background:#cc0000;padding:.5em">'+txt+'</div>').appendTo($('body'));
      }
      
      // Read URL PARAMS
      function urlParams() {
         location.queryString = {};
         location.search.substr(1).split("&").forEach(function (pair) {
            if (pair === "") return;
            var parts = pair.split("=");
            location.queryString[parts[0]] = parts[1] && decodeURIComponent(parts[1].replace(/\+/g, " "));
         });
         return location.queryString;
      } 
      
      // Get URL PARAMS AND PARSE JSON
      function get_json() {
         var all_params = urlParams(); 
         var clear_cache = false;
         
      

         if(typeof all_params['clear_cache'] !== undefined) {
            clear_cache = true;
         } 
 
         if(typeof all_params['j'] !== 'undefined' && typeof all_params['t'] !== 'undefined') {
            parseJsonPlot(all_params['j'],all_params['t'],clear_cache);
         } else if(typeof all_params['j'] !== 'undefined'){
           // We create all the plots at once
           parseJsonPlot(all_params['j'],'all',clear_cache);
         } else {
            print_error('t parameter (plot type) is missing in URL')
         }
      }

      
 
      // PARSE JSON
      function parseJsonPlot(json_file,plot_ids,clear_cache) {

         var r_plot_id = plot_ids.split(",");
         var _data = {};
      
         if(clear_cache) {
            _data = {"c":Math.floor((Math.random() * 1000000) + 1)};
         }
        
         $.ajax({
            url :json_file, 
            dataType : 'json',
            data: _data,
            success : function(json_code, status){ // success est toujours en place, bien sûr !
               var f = false;
 
               if(typeof json_code['plots'] !== "undefined") { 
                   if(plot_ids == 'all') {
                     r_plot_id = []
                     $.each(json_code['plots'], function(i,v) { 
                        r_plot_id.push(v.plot_id);
                     });
                  }
                  
                  // We search the proper plots
                  $.each(json_code['plots'], function(i,v) { 
                     if(r_plot_id.indexOf(v['plot_id']) > -1)  {
                        // We Draw the corresponding plot 
                        draw_plot(v,r_plot_id.indexOf(v['plot_id']));
                        // We reset the marker counter
                        MARKER_CNT = 0;
                        f= true;
                     }
                  })
                
                

                  // Setup UI
                  hide_legend_on_hover();

                  // Change Body bg color
                  $('body').css('background-color',PAPER_BG_COLOR);

                  if(!f) {
                     print_error('Plot type <b>' + plot_ids + '</b> not found')
                  }

               } else {
                  print_error('Plots not found in ' + json_file)
               }
            },

            error : function(res, status, error){
               print_error('Impossible to parse the file ' + json_file + "<br>" + error)
            }

         });
 
      }


      /*********** DRAW PLOT ***************************/
      // HEx to RGBA 
      function hexToRgb(hex) {
         var bigint = parseInt(hex, 16);
         var r = (bigint >> 16) & 255;
         var g = (bigint >> 8) & 255;
         var b = bigint & 255;
         return r + "," + g + "," + b + ",1";
      } 
 
      function create_rainbow_colors() {
         // Create Colors
         var rainbow = new Rainbow();
         rainbow.setNumberRange(0, 255);
         return rainbow;
      }
      

// Add rainbdow colors to array
function  get_rainbow_colors(total,rainbowcolors) {
   var all_colors = [];
   if(total>=255) {   
      // Default color for the end...
      for (var i = 255; i <= total; i = i + step) {
         all_colors[i] = '#0000ff';
      }
      for (var i = 0; i <= 255; i = i + step) {
         all_colors[i] = '#'+rainbowcolors.colourAt(i);
      }
   } else {
      step = parseInt(255/total);  

      for (var i = 0; i <= 255; i = i + step) {
         all_colors.push('rgba('+hexToRgb(rainbowcolors.colourAt(i))+')');
      }
   }
   return all_colors;
}
   
// Set Generic LAYOUT options
function set_generic_layout_options(layout) {
   layout.title =    { 
            font: { color: FONT_COLOR },
            xref: 'x',   
            yref: 'y',  
            x: 0.05, 
   } ;
   layout.height = PLOT_H;
   layout.width =  PLOT_W;
   layout.paper_bgcolor =  PAPER_BG_COLOR;   
   layout.plot_bgcolor = PLOT_BG_COLOR; 

   layout.xaxis =  { 
      zerolinecolor: H_LINE_COLOR, 
      zerolinewidth: 1,
      gridcolor: GRID_COLOR, 
      linecolor: H_LINE_COLOR,  
      title: { font: { size: 15, color: AXIS_FONT_COLOR } },
      tickfont: { color: TICK_FONT_COLOR},
   };

   layout.yaxis =  {
      zerolinecolor: V_LINE_COLOR, 
      zerolinewidth: 1, 
      gridcolor: GRID_COLOR, 
      linecolor: V_LINE_COLOR,
      title: { font: {  size: 15, color:  AXIS_FONT_COLOR}}, 
      tickfont: { color: TICK_FONT_COLOR},
   };

   layout.showlegend = true;
   layout.legend = {
         xanchor:"right",
         yanchor:"bottom",
         y:5,  
         x:1,
         orientation: 'v',
         traceorder: 'normal',
         bordercolor: LEGEND_BORDER,  
         borderwidth: 1,
         bgcolor:  LEGEND_BG,
         font: {
            color: LEGEND_FONT_COLOR
         } 
   };

   return layout
}

// Set Layout for 2D Maps
function set_2Dmap_layout(layout,avg_lat,avg_lon) {
   layout.geo =    { 
      resolution: 50,
      showland: true,
      showlakes: false,
      showrivers: false,  
      showcountries: true,  
      showsubunits: true,
      subunitwidth:1,
      subunitcolor:SUB_UNIT_BORDER,
      landcolor: LAND_COLOR,  
      countrywidth: 1.5, 
      coastlinewidth: .5,
      width: PLOT_W,
      height: PLOT_H,
      lataxis: {
         showgrid: true,
         tickmode: 'linear',
         range: [ avg_lat-2, avg_lat+2 ],
         dtick: 5 
      },
      lonaxis:{
         showgrid: true,
         tickmode: 'linear',
         range: [avg_lon-5, avg_lon+5],
         dtick: 5 
      }
   }
   return layout
}
      
// Set 3D Graph Layout
function set_3Dmap_layout(layout, axis_details, title, data) {
   var layout = {
         title: {
            font: { color: FONT_COLOR },
            xref: 'x',
            yref: 'y',
            x: 0.05,
            text: title
         },
         height: PLOT_H,
         width: PLOT_W,
         paper_bgcolor: PAPER_BG_COLOR,
         showlegend: true,
         scene: {
            xaxis:{  
               zerolinecolor: D_H_LINE_COLOR,
               zerolinewidth: 1,
               gridcolor: D_GRID_COLOR,
               linecolor: D_H_LINE_COLOR,
               title: { font: { size: 15, color: AXIS_FONT_COLOR }, text:(typeof data['x_label']!== 'undefined'?data['x_label']:'') },
               tickfont: { color: TICK_FONT_COLOR} 
            },
            yaxis:{  
               zerolinecolor: D_H_LINE_COLOR,
               zerolinewidth: 1,
               gridcolor: D_GRID_COLOR,
               linecolor: D_H_LINE_COLOR,
               title: { font: { size: 15, color: AXIS_FONT_COLOR }, text:(typeof data['y_label']!== 'undefined'?data['y_label']:'') },
               tickfont: { color: TICK_FONT_COLOR} 
            },
            zaxis:{  
               zerolinecolor: D_H_LINE_COLOR,
               zerolinewidth: 1,
               gridcolor: D_GRID_COLOR,
               linecolor: D_H_LINE_COLOR,
               title: { font: { size: 15, color: AXIS_FONT_COLOR }, text:(typeof data['z_label']!== 'undefined'?data['z_label']:'') },
               tickfont: { color: TICK_FONT_COLOR},
            },
            camera: {
               eye: {x: -0.76, y: 1.8, z: 0.92}
            }
         },
         margin: {
            l: 0,
            r: 0,
            t: 50,
            b: 50
         },
         legend: {
            traceorder: 'normal',
            font: {
               color: LEGEND_FONT_COLOR
            }
         }
      }; 

   // Set up the ranges
   if(typeof axis_details['x_axis']!=='undefined') { 
      layout.scene.xaxis.range =axis_details['x_axis'];
   }
   if(typeof axis_details['z_axis']!=='undefined') { 
      layout.scene.zaxis.range =  axis_details['z_axis'];
   }
   if(typeof axis_details['y_axis']!=='undefined') { 
      layout.scene.yaxis.range =  axis_details['y_axis'];
   } 
   return layout;
}

// Set New Graph Container
function set_new_graph_container() {
   var graph_name = "graph_"+ graph_counter;
   $('<div id="'+graph_name+'"></div>').appendTo($('body'));   
   graph_counter++;
   return graph_name;
}

// Get Marker for a station 
function get_marker() {
   MARKER_CNT++;
   if(MARKER_CNT>ALL_MARKERS.length) MARKER_CNT = 0;
   return ALL_MARKERS[MARKER_CNT]; 
}

// Create Rainbow colors for meteor pos
function get_meteor_pos_color(total_pos) {
   var rainbow = new Rainbow(), all_colors = [], step = 1;
   rainbow.setNumberRange(0, 255);
   if(total_pos>=255) {   
      // Default color for the end...
      for (var i = 255; i <= total_pos; i = i + step) {
         all_colors[i] = '#0000ff';
      }
      for (var i = 0; i <= 255; i = i + step) {
         all_colors[i] = '#'+rainbow.colourAt(i);
      }
   } else {
      step = parseInt(255/total_pos);  

      for (var i = 0; i <= 255; i = i + step) {
         all_colors.push('rgba('+hexToRgb(rainbow.colourAt(i))+')');
      }
   }
   return all_colors;
}

// Draw default x,y plot
function draw_plot_xy(data) {

      // Create Default Layout
      var layout = {}, all_colors=null, meteor_pos=false;
      layout = set_generic_layout_options(layout);
         
      // Specifics for xy
      if(typeof data['opts'] == 'undefined') {
         layout.title.x = 0.05;
         layout.xaxis.side = 'bottom';
      } else if(data['opts'] == 'meteor_pos' ) {
         
         meteor_pos = true;

         // RAINBOW Color for meteor_pos!
         all_colors = get_rainbow_colors(data['x1_vals'].length+1,create_rainbow_colors());
       
      }

      // Plot Name
      layout.title.text =  typeof data.plot_name !== 'undefined'?data.plot_name:'';   

      if(typeof data.plot_y_axis_reverse !== "undefined") {
         if(data.plot_y_axis_reverse == 1) {
               layout.yaxis.autorange = "reversed" 
         }
      }   
      // Add labels
      if(typeof data.x_label !== "undefined") {
         layout.xaxis.title.text = data.x_label; 
      }
      if(typeof data.y_label !== "undefined") {
         layout.yaxis.title.text = data.y_label; 
      }
      
      // Show Legend
      if(typeof data.showlegend !== "undefined") {
         layout.showlegend = data.showlegend;
      }
       
      // X, Y axis position
      if(typeof data.x_axis_position !== "undefined") {
         layout.xaxis.side = data.x_axis_position;
      }
      if(typeof data.y_axis_position !== "undefined") {
         layout.yaxis.side = data.y_axis_position;
      }
 


      // make traces data array for each data series
      traces = [];
      ti = 0;  // Trace Counter

      for (var i = 1; i <= XY_SERIES_MAX; i++) {
         
         // The values
         field_x           = "x" + i + "_vals";
         field_y           = "y" + i + "_vals";
         field_line_on     = "x" + i + "_line";
         data_label        = "x" + i + "_data_label";
         data_marker       = "x" + i + "_symbol;"
         data_marker_size  = "x" + i + "_symbol_size";
         data_marker_color = "x" + i + "_color";
         x_reverse         = "x" + i + "_reverse";
         y_reverse         = "y" + i + "_reverse";
         y_scale_anchor    = "y" + i + "_axis_scaleanchor"; 
         x_scale_anchor    = "x" + i + "_axis_scaleanchor"; 
         y_scale_scaleratio    = "y" + i + "_axis_scaleratio"; 
         x_scale_scaleratio    = "x" + i + "_axis_scaleratio"; 
        
         if(typeof data[field_x] !== 'undefined' && typeof data[field_y] !== 'undefined') {
            
            traces[ti] = {
               x: data[field_x],
               y: data[field_y],
               mode: 'markers',
               marker: {   symbol: (data[data_marker]?data[data_marker]:get_marker()), 
                           size: (data[data_marker_size]?data[data_marker_size]:6), 
                           type: 'scatter'
               },
               name: (data[data_label]?data[data_label]:'') 
            }; 

            // Meteor Pos => Square & Rainbow colors
            if(meteor_pos) {
               traces[ti].marker.symbol = DEFAULT_METEOR_SYMBOL;
               traces[ti].marker.size = 10;
               traces[ti].marker.color  =  all_colors;  
            }
 
            // Reverse
            if(data[x_reverse]) {
               layout.xaxis.autorange = "reversed";

               if(all_colors!== null) {
                  all_colors.reverse();
               }
            }
            if(data[y_reverse]) {
               layout.yaxis.autorange = "reversed";
            }

            // Colors
            if(data[data_marker_color]) {
               traces[ti].marker.color = data[data_marker_color]; 
            }

            // Markers size
            if(data[data_marker_size]) {
               traces[ti].marker.size = data[data_marker_size]; 
            }

            // Line
            if(typeof data[field_line_on] !== 'undefined') {
               if(data[field_line_on] == "1") {
                  traces[ti].mode="lines+markers";
               }
            }

            // Scales (only for Y for now)
            if(typeof data[y_scale_anchor] !== 'undefined') {
               layout.yaxis.scaleanchor =  data[y_scale_anchor] ;
            }
            if(typeof data[y_scale_scaleratio] !== 'undefined') {
               layout.yaxis.scaleratio =  data[y_scale_scaleratio] ;

               traces[0].xaxis = "x";
               traces[0].yaxis = "y"; 
               
            } 
            ti++;
         }
      } 


      // Line on first serie
      if(typeof data.linetype1 !== "undefined") {
         if(data.linetype1 == "lines+markers") {
            traces[0].mode = 'lines+markers'; 
            traces[0].line = {};
            traces[0].line.shape = 'spline';
            traces[0].line.color = DEFAULT_LINE_COLOR;
         }
      }


      // make the trend line if tx1_vals exist
      if(typeof data['tx1_vals'] !== 'undefined' && typeof ["ty1_vals"] !== 'undefined') {
         traces[ti] = {
            x: data["tx1_vals"],
            y: data["ty1_vals"],
            mode: 'lines',
            name: typeof data['tx1_data_label']!== "undefined"?data['tx1_data_label']:'',
            type: 'line',
            line: {
               width: 1,
               color: typeof data['tx1_line_color']!== "undefined"?data['tx1_line_color']:DEFAULT_LINE_COLOR
            }
         }
      }

         // Do we have extra Axis?
         if(typeof data['y1_axis2_title'] !== 'undefined') {
         
         // Update the Layout  
         layout.yaxis2 = {title:{font: {  size: 15, color:  AXIS_FONT_COLOR}}}
         layout.yaxis2.title.text = (typeof data['y1_axis2_title'] !== 'undefined'?data['y1_axis2_title']:'');
         layout.yaxis2.overlaying = 'y';
         layout.yaxis2.side = 'right'; 
         layout.yaxis2.showgrid = false; 
         layout.yaxis2.zerolinecolor = V_LINE_COLOR;  
         layout.yaxis2.zerolinewidth = 1;  
         layout.yaxis2.gridcolor= GRID_COLOR;  
         layout.yaxis2.linecolor= V_LINE_COLOR; 
         layout.yaxis2.tickfont = { color: TICK_FONT_COLOR};
         
         if(typeof data['plot_y_axis2_reverse'] !== "undefined") {
            layout.yaxis2.autorange = "reversed" 
         } 

         traces[3] = {
            mode : 'markers',
            marker: { size:0.1, line: {width:0} },
            yaxis: 'y2',
            y: data['y1_axis2_vals'],
            showlegend: false
         }; 
      }
       
      Plotly.newPlot( set_new_graph_container(), traces,layout);
     
}
 
// Draw 2D plot map
function draw_plot_map(data) {
      
      var map_data = [], lats = [], lons = [], names= [], traces = [];
      // MAKE POINTS FROM DATA 
      for (var i = 0; i < data['points'].length; i++) {
 
         tlat = parseFloat(data['points'][i][0])
         tlon = parseFloat(data['points'][i][1]) 
   
         trace =  {
            type: 'scattergeo',
            mode: 'markers+text' ,
            lon: [tlon],
            lat: [tlat],
            marker: {
               size: 10, 
               symbol:  get_marker(),
               line : {  width: 2  }
            },
            text:  [data['point_names'][i]],
            textposition: ["top center"],
            name: data['point_names'][i]
         } 
         lats.push(tlat) 
         lons.push(tlon)  
         traces.push(trace) 
      }
  
   
      // MAKE LINES FROM DATA 
      $.each( data['lines'], function(i,line) {
         traces.push( {
            type: 'scattergeo',
            mode: 'lines' ,
            lon: [parseFloat(line[1]), parseFloat(line[3])],
            lat: [parseFloat(line[0]), parseFloat(line[2])],
            marker: { 
               color: DEFAULT_LINE_COLOR,
               line : {   width: 1  }
               
            },
            name: "Meteor" 
         });

         lats.push(parseFloat(line[0]));
         lats.push(parseFloat(line[2]));
         lons.push(parseFloat(line[1]));
         lons.push(parseFloat(line[3]));
      });


    var n   = lats.length, sum_lat = 0, sum_lon = 0;
    while(n--) sum_lat += parseFloat(lats[n]) || 0;
    n   = lons.length;
    while(n--) sum_lon += parseFloat(lons[n]) || 0;
    
    avg_lat = (sum_lat/lats.length) || 0;
    avg_lon = (sum_lon/lons.length) || 0; 

 
      // Create Default Layout
      var layout = {};
      layout = set_generic_layout_options(layout);
      layout = set_2Dmap_layout(layout,avg_lat,avg_lon);

      // Add the map scope if any
      if(typeof data['scope'] !== 'undefined') {
         layout.geo.scope = data['scope'];
      }
      

      // Set Title
      layout.title.text = (typeof data['plot_name'] !== "undefined")?data['plot_name'] :""
      
      // DRAW
      Plotly.newPlot( set_new_graph_container(), traces,layout);
}

// Draw Iframe (orbit)
function draw_iframe(data) {
   console.log(data);
   // Build iframe
   $('<iframe frameborder=0 width="'+PLOT_W+'" height="'+PLOT_H+'" src="'+data['plot_url']+'">').appendTo($('body'));
}

// Draw 3D Map (meteor + stations)
function draw_plot_map_3D(data) {
    
   var traces = [], all_lats = [], all_lons = [], cc=0, axis_details={};
   
   // Get Station Points with proper marker
   for (var i = 0; i < data['points'].length; i++) {
      tlat = parseFloat(data['points'][i][0]);
      tlon = parseFloat(data['points'][i][1]);
      trace =  {
         type: 'scatter3d',
         mode: 'markers' ,
         x: [tlon], y: [tlat], z: [0],
         marker: {
               size: 8, 
               symbol:  get_marker(),
               line : {  width: 2  }
         },
         name: data['point_names'][i]
      };
      all_lats.push(tlat);
      all_lons.push(tlon);
      traces.push(trace);
   } 

   // MAKE LINES FROM DATA
   // the first line is always green and the last one is red
  

   for (var i = 0; i < data['lines'].length; i++) {
      slat = parseFloat(data['lines'][i][0])
      slon = parseFloat(data['lines'][i][1])
      salt = parseFloat(data['lines'][i][2])
      elat = parseFloat(data['lines'][i][3])
      elon = parseFloat(data['lines'][i][4])
      ealt = parseFloat(data['lines'][i][5])
      all_lats.push(slat)
      all_lons.push(slon)
      all_lats.push(elat)
      all_lons.push(elon)
      trace =  {
         type: 'scatter3d',
         mode: 'lines' ,
         x: [slon,elon],
         y: [slat,elat],
         z: [salt,ealt],
         marker: {  
            line : {  width: 1   },
            color: (i>0)?(cc%2==0?'red':'green'):DEFAULT_LINE_COLOR  // The first line is always the meteor
         },
         name: data['line_names'][i]
      }

      // Hide the legend we don't care
      // 3 = the meteor + 1 start line + 1 end line
      if(cc>=3) {
         trace.showlegend = false;
      }

      traces.push(trace)
      cc++;
   }
 
   // Get range for x,y axis
   min_lat = Math.min.apply(null,all_lats);
   max_lat = Math.max.apply(null,all_lats);
   lat_diff = Math.abs(max_lat - min_lat)/2;

   min_lng = Math.min.apply(null,all_lons);
   max_lng = Math.max.apply(null,all_lons);
   lng_diff = Math.abs(max_lng - min_lng)/2;


   axis_details = {
      y_axis: [min_lat-lat_diff, max_lat+lat_diff],
      x_axis: [min_lng-lng_diff, max_lng+lng_diff],
      z_axis: [0,100]  // From 0 to 100km by default for the altitude
   }
    
   // Create Default Layout
   var layout = {}; 
   layout = set_3Dmap_layout(layout,axis_details,(typeof(data['plot_name'])!=='undefined'?data['plot_name']:''),data);
   Plotly.newPlot(set_new_graph_container(), traces,layout);

}
       
// Main function to draw all plots
function draw_plot(data, order) {

   var plot_type = typeof data['plot_type'] !== 'undefined'?data['plot_type'] :'xy_scatter';

   switch(plot_type) {
      case "iframe":
         draw_iframe(data);
         break;
      case "3Dmap":
         draw_plot_map_3D(data);
         break;
      case "map":
         draw_plot_map(data);
         break;
      default:
         draw_plot_xy(data);
         break;
   } 

   // End of Loading
   $("body").removeClass('waiting');
}

$(function() {
   get_json();
});