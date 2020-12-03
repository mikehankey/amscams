var v = Cookies.get('wpAMS-10091976');
if(v == undefined) {
    if (window.pathname != "/") {
       window.location.href = "/"
    }
}
