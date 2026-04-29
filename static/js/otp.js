document.addEventListener("DOMContentLoaded", () => {
  const inputs = document.querySelectorAll(".otp-input");
  const hiddenInput = document.getElementById("fullOtp");

  inputs.forEach((input, index) => {
    input.addEventListener("input", () => {
      if (input.value.length === 1 && index < inputs.length - 1) {
        inputs[index + 1].focus();
      }
      hiddenInput.value = Array.from(inputs).map(i => i.value).join("");
    });
  });
});

function resendOtp() {
  window.location.href = "/resend-otp/";
}
