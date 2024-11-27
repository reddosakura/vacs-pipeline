function commentCollapse() {
    let checkBox = document.querySelector(".checkbox");
    // Get the output text
    // let comment = document.querySelector(".collapse-area")
    let comment = document.querySelectorAll(".collapse-area")

    // If the checkbox is checked, display the output text
    if (checkBox.checked == false){
        for (let i = 0; i < comment.length; i++) {
          comment[i].classList.add("display-none");
        }
    } else {
        for (let i = 0; i < comment.length; i++) {
          comment[i].classList.remove("display-none");
        }
    }
}