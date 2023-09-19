const adminLink = document.getElementById("admin");
const userManagementLink = document.getElementById("userManagement");
const companyManagementLink = document.getElementById("companyManagement");
const submenu = document.getElementById("submenu");
const subSubmenu = document.getElementById("sub-submenu");
const subSubmenu2 = document.getElementById("sub-submenu2");

submenu.style.display = "none";
subSubmenu.style.display = "none";

adminLink.addEventListener("click", function (e) {
    e.preventDefault();
    if (submenu.style.display === "none") {
        submenu.style.display = "block";
        subSubmenu2.style.display = "none";
    } else {
        submenu.style.display = "none";
        subSubmenu.style.display = "none";
        subSubmenu2.style.display = "none";
    }
});

userManagementLink.addEventListener("click", function (e) {
    e.preventDefault();
    if (subSubmenu.style.display === "none") {
        subSubmenu.style.display = "block";
    } else {
        subSubmenu.style.display = "none";
    }
});

companyManagementLink.addEventListener("click", function (e) {
    e.preventDefault();
    if (subSubmenu2.style.display === "none") {
        subSubmenu2.style.display = "block";
    } else {
        subSubmenu2.style.display = "none";
    }
});

const logoutButton = document.getElementById("logoutBtn");

logoutButton.addEventListener("click", function() {
    window.location.href = "admin-login.html";
});