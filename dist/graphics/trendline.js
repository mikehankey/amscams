var GRID_COLOR = 'rgba(255,255,255,.1)';
var TICK_FONT_COLOR = 'rgba(255,255,255,.75)';
var H_LINE_COLOR = 'rgba(255,255,255,.4)';
var V_LINE_COLOR = 'rgba(255,255,255,.1)';

var trace1 =  {
      type: 'scatter',
      marker : { symbol: 'square-open-dot', size:10  },
      xaxis: "x1",
      yaxis: "y1" 
};

var trace2 = { 
   mode: 'lines',
   type: 'scatter',  
   yaxis: "x2",
   line: {
      color: 'rgba(213,42,224,.5)' 
   }
};

var layout = {
   title: { 
      font: {  color:'#ffffff' },
      xref: 'x',   
      yref: 'y',  
      x: 0.05, 
   },
   height: 517,
   width: 937,
   paper_bgcolor: "rgba(9,29,63,1)",  // For exporting in PNG!
   plot_bgcolor: "rgba(9,29,63,1)",   // For exporting in PNG!
   xaxis:{
         autorange: true,
         zerolinecolor: H_LINE_COLOR, 
         zerolinewidth: 1,
         gridcolor: GRID_COLOR, 
         linecolor: H_LINE_COLOR,  
         title: { font: { size: 15, color: '#b1b1b1' } },
         tickfont: { color: TICK_FONT_COLOR}
   },
   yaxis:{
         zerolinecolor: V_LINE_COLOR, 
         zerolinewidth: 1, 
         gridcolor: GRID_COLOR, 
         linecolor: V_LINE_COLOR,
         title: { font: {  size: 15, color: '#b1b1b1' }}, 
         tickfont: { color: TICK_FONT_COLOR} 
   },
   showlegend: false };



// If it's the same ratio on the SERIE 1
if(all_data.s_ratio1) {
   layout.yaxis.scaleanchor = "x";
   layout.yaxis.scaleratio = 1;  
}
 

// If we reverse the Y1 axis
if(all_data.y1_reverse) {
   layout.yaxis.autorange = 'reversed';
}