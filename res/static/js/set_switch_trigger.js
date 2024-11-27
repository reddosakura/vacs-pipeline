function switchCheck() {
    var switch_check = document.getElementById("switch_check");
    if (switch_check.checked === false){
        window.location = '/sudpapp/proc/consider'
    } else {
        window.location = '/sudpapp/proc/approve'
    }
}