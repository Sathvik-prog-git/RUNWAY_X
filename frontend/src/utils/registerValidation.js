/**
 * Registration form rules. They mirror backend/registration.py so people see problems immediately,
 * but the backend re-checks everything: this file is a convenience, not a security control.
 */
export const MIN_PASSWORD_LENGTH = 12;
export const MAX_PASSWORD_LENGTH = 128;

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const GSTIN_RE = /^(\d{2})[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
const GST_STATE_CODES = new Set([...Array(38).keys()].map((i) => String(i + 1).padStart(2, "0")).concat(["97", "99"]));
const COMMON_PASSWORDS = new Set([
  "password1234", "password12345", "123456789012", "1234567890123", "qwertyuiop12", "qwerty123456",
  "iloveyou1234", "admin1234567", "welcome12345", "letmein12345", "passw0rd1234", "abc123456789",
  "123456123456", "111111111111", "000000000000", "password@123", "admin@123456", "india@123456",
]);

const collapse = (s) => s.trim().replace(/\s+/g, " ");

/** "98765 43210", "+91-98765-43210", "09876543210" … → "+919876543210", or null if not a valid Indian mobile. */
export function normalizeIndianMobile(raw) {
  const cleaned = raw.replace(/[\s\-().]/g, "");
  const plus = cleaned.startsWith("+");
  let digits = plus ? cleaned.slice(1) : cleaned;
  if (!/^\d+$/.test(digits)) return null;
  if (plus) {
    if (!(digits.startsWith("91") && digits.length === 12)) return null;
    digits = digits.slice(2);
  } else if (digits.length === 12 && digits.startsWith("91")) digits = digits.slice(2);
  else if (digits.length === 11 && digits.startsWith("0")) digits = digits.slice(1);
  return /^[6-9]\d{9}$/.test(digits) ? `+91${digits}` : null;
}

export function normalizeGstin(raw) {
  return raw.trim().toUpperCase().replace(/\s+/g, "");
}

export function passwordProblem(password, email = "", fullName = "") {
  if (password.length < MIN_PASSWORD_LENGTH) return `Use at least ${MIN_PASSWORD_LENGTH} characters.`;
  if (password.length > MAX_PASSWORD_LENGTH) return `Use at most ${MAX_PASSWORD_LENGTH} characters.`;
  const lower = password.toLowerCase();
  const mail = email.trim().toLowerCase();
  if (mail && (lower === mail || lower === mail.split("@")[0])) return "Your password must not be the same as your email.";
  if (fullName.trim() && lower === fullName.trim().toLowerCase()) return "Your password must not be the same as your name.";
  if (COMMON_PASSWORDS.has(lower)) return "This password is too common. Choose something less predictable.";
  if (new Set(password).size < 5) return "This password is too repetitive. Mix in more different characters.";
  return "";
}

/** Strength meter: score 0–4 with a label. A password the backend would refuse never scores above "Weak". */
export function passwordStrength(password, email = "", fullName = "") {
  if (!password) return { score: 0, label: "", tips: [] };
  const tips = [];
  if (password.length < MIN_PASSWORD_LENGTH) tips.push(`${MIN_PASSWORD_LENGTH - password.length} more character(s)`);
  const kinds = [/[a-z]/, /[A-Z]/, /\d/, /[^A-Za-z0-9]/].filter((re) => re.test(password)).length;
  if (kinds < 2 && password.length < 18) tips.push("add numbers, capitals or symbols, or make it longer");
  if (passwordProblem(password, email, fullName)) return { score: 1, label: "Weak", tips };
  // Length matters most: a long passphrase is strong even without symbols.
  let score = 2;
  if (password.length >= 14 && kinds >= 2) score = 3;
  if ((password.length >= 18 && kinds >= 2) || password.length >= 24) score = 4;
  return { score, label: ["", "Weak", "Fair", "Good", "Strong"][score], tips: score >= 3 ? [] : tips };
}

/** Returns { fieldName: message } — empty when everything is valid. */
export function validateRegistration(v) {
  const errors = {};
  const name = collapse(v.fullName);
  if (name.length < 2 || name.length > 100 || !/\p{L}/u.test(name)) errors.fullName = "Enter your full name.";
  const email = v.email.trim();
  if (!email) errors.email = "Enter your work email.";
  else if (!EMAIL_RE.test(email) || email.length > 254) errors.email = "Enter a valid email address, like name@company.com.";
  if (!v.password) errors.password = "Create a password.";
  else {
    const problem = passwordProblem(v.password, email, name);
    if (problem) errors.password = problem;
  }
  if (!v.confirmPassword) errors.confirmPassword = "Re-enter your password.";
  else if (v.confirmPassword !== v.password) errors.confirmPassword = "The two passwords do not match.";
  const company = collapse(v.companyName);
  if (company.length < 2 || company.length > 120 || !/[\p{L}\p{N}]/u.test(company)) errors.companyName = "Enter your company name.";
  if (!v.phone.trim()) errors.phone = "Enter your mobile number.";
  else if (!normalizeIndianMobile(v.phone)) errors.phone = "Enter a valid 10-digit Indian mobile number, like 98765 43210.";
  const gstin = normalizeGstin(v.gstin);
  if (gstin && !(GSTIN_RE.test(gstin) && GST_STATE_CODES.has(gstin.slice(0, 2)))) {
    errors.gstin = "Enter a valid 15-character GSTIN, like 22AAAAA0000A1Z5, or leave it blank.";
  }
  return errors;
}
