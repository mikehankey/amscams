"""

program to make nav table by year

each column is 10 rows representing days 1-10 11-20 etc
like github display

"""

one_col = """
<table >
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
<tr><td class="cell">  <td></tr>
</table>

"""

all = """
<style>
table {
   border: 0px solid black;
   padding: 0px ;
   margin: 0px ;
}
.cell  {
   width: 15px;
   height: 15px;
   border: 1px solid black;
   padding: 0px ;
   margin: 0px ;
   background: #cdcdcd ;
}

.holder {
   border: 0px solid black;
   padding: 0px ;
   margin: 0px ;
}


</style>
"""


all += """
<table cellpadding=0 cellspacing=0>
<tr>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>

<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>

<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>

<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
<td class="holder">{:s}<td>
</tr>
</table>

""".format( one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col, one_col , one_col)

print(all)
