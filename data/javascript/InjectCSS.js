function injectStyleSheet(css) {
    let s = document.createElement("style");
    s.setAttribute('type', 'text/css');
    s.appendChild(document.createTextNode(css));
    document.head.appendChild(s)
}

injectStyleSheet(atob('@CSS@'));
xhr_running --;
if (xhr_running == 0 ) {
    html = document.querySelector("html");
    html.style.display = "block";
}
