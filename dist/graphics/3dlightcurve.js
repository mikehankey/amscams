var GRID_COLOR = 'rgba(255,255,255,.1)';
var TICK_FONT_COLOR = 'rgba(255,255,255,.75)';
var H_LINE_COLOR = 'rgba(255,255,255,.4)';
var V_LINE_COLOR = 'rgba(255,255,255,.1)';
var TYPE = "3Dlightcurve";
var trace1 =  {
      type: 'surface' 
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
         zerolinecolor: H_LINE_COLOR, 
         zerolinewidth: 1,
         gridcolor: GRID_COLOR, 
         linecolor: H_LINE_COLOR,  
         title: { font: { size: 15, color: '#fff' } },
         tickfont: { color: TICK_FONT_COLOR} 
   },
   yaxis:{
         zerolinecolor: V_LINE_COLOR, 
         zerolinewidth: 1, 
         gridcolor: GRID_COLOR, 
         linecolor: V_LINE_COLOR,
         title: { font: {  size: 15, color: '#fff' }}, 
         tickfont: { color: TICK_FONT_COLOR} 
   },
   zaxis:{
      zerolinecolor: V_LINE_COLOR, 
      zerolinewidth: 1, 
      gridcolor: GRID_COLOR, 
      linecolor: V_LINE_COLOR,
      title: { font: {  size: 15, color: '#b1b1b1' }}, 
      tickfont: { color: TICK_FONT_COLOR} 
   },
   showlegend: true,
   legend: {
      traceorder: 'normal',
      font: {
       color: '#fff'
      } 
    },
    margin: {
      l: 65,
      r: 50,
      b: 65,
      t: 90,
    }
}; 


