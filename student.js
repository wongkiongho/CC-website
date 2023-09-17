const studentLink = document.getElementById("studentMenu");
const submenu = document.getElementById("studentSubmenu");

submenu.style.display = "none";

studentLink.addEventListener("click", function (e) {
    e.preventDefault();
    if (submenu.style.display === "none") {
        submenu.style.display = "block";
    } else {
        submenu.style.display = "none";
        subSubmenu.style.display = "none";
    }
});

const logoutButton = document.getElementById("logoutBtn");

logoutButton.addEventListener("click", function() {
    window.location.href = "admin-login.html";
});