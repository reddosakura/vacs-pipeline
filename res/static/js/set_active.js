"use strict";
const buttons = document.querySelectorAll('.header-item')
buttons.forEach(function (item) {
    item.classList.remove("btn-active");
    if (window.location.href.includes(item.href)){
        item.classList.add("btn-active");
    }
});


