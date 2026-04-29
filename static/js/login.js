function switchForm(id) {
    document.querySelectorAll('#loginForm, #signupForm, #otpForm, #forgotForm').forEach(f => f.style.display = "none");
    document.getElementById(id).style.display = "flex";
}

function showLoader() {
    document.getElementById('loader').style.display = 'flex';
}

function hideLoader() {
    document.getElementById('loader').style.display = 'none';
}

document.addEventListener("DOMContentLoaded", function () {
    // Handle signup form submission
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const name = this.querySelector('input[name="name"]').value;
            const email = this.querySelector('input[name="email"]').value;
            showLoader();
            alert(`Hi ${name}! We're sending an OTP to ${email}. Please verify to complete your registration.`);
            this.submit();
        });
    }

    // Handle forgot password form submission
    const forgotForm = document.getElementById('forgotForm');
    if (forgotForm) {
        forgotForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const email = this.querySelector('input[name="email"]').value;
            const captcha = this.querySelector('input[name="captcha"]').value;
            
            if (captcha) {
                showLoader();
                alert(`We're sending an OTP to ${email}. Please verify to reset your password.`);
                this.submit();
            }
        });
    }

    // Captcha refresh functionality
    const refresh = document.getElementById("refreshCaptcha");
    if (refresh) {
        refresh.addEventListener("click", function (e) {
            e.preventDefault();
            const captchaUrl = "/refresh-captcha/";
            fetch(captchaUrl)
                .then(response => {
                    if (response.ok) {
                        return response.json();
                    }
                    throw new Error("Network response was not ok.");
                })
                .then(data => {
                    console.log("Captcha refreshed:", data);
                    document.getElementById("captchaData").innerText = data.captcha;
                })
                .catch(error => {
                    console.error("There was a problem with the fetch operation:", error);
                });
        });
    }
});